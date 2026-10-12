"""스레드 작업의 상태, 원본 보존 및 Popen 취소를 관리한다."""

from __future__ import annotations

import math
import shutil
import subprocess
import time
from copy import deepcopy
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from threading import RLock
from uuid import uuid4

from app import paths
from app.capture import Selection, SourceTimeline
from app.processes import OwnedProcess
from app.wrappers.ffmpeg import EditOptions
from app.wrappers.ffprobe import SourceMeta


class JobStatus(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    ENCODING = "encoding"
    DONE = "done"
    ERROR = "error"
    CANCELED = "canceled"


class InvalidTransition(ValueError):
    """현재 단계에서 요청한 작업을 시작할 수 없다."""


@dataclass
class JobState:
    job_id: str
    selection: Selection
    work_dir: Path
    quality: str = "best"
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    message: str = ""
    error_code: str | None = None
    source_path: Path | None = None
    source_meta: SourceMeta | None = None
    source_timeline: SourceTimeline | None = None
    outputs: list[Path] = field(default_factory=list)
    last_edit: EditOptions | None = None
    generation: int = 0
    created_at: int = field(default_factory=time.time_ns)
    updated_at: int = field(default_factory=time.time_ns)
    _proc: subprocess.Popen | None = field(default=None, repr=False, compare=False)


class JobManager:
    def __init__(self, work_root: Path | None = None):
        self.work_root = (paths.WORK_DIR if work_root is None else work_root).resolve()
        self._jobs: dict[str, JobState] = {}
        self._lock = RLock()

    def create(self, selection: Selection, quality: str = "best") -> JobState:
        with self._lock:
            job_id = uuid4().hex
            directory = self.work_root / job_id
            directory.mkdir(parents=True)
            self._jobs[job_id] = JobState(job_id, selection, directory, quality)
            return self.get(job_id)

    def get(self, job_id: str) -> JobState:
        with self._lock:
            # Popen에는 복사할 수 없는 핸들과 잠금이 있다. 상태 사본에는 넣지 않는다.
            return deepcopy(replace(self._jobs[job_id], _proc=None))

    def list_jobs(self) -> list[JobState]:
        with self._lock:
            return [self.get(job_id) for job_id in self._jobs]

    def _start(self, job: JobState, status: JobStatus) -> int:
        job.status = status
        job.generation += 1
        job.progress = 0.0
        job.error_code = None
        job.message = "구간 가져오는 중" if status == JobStatus.DOWNLOADING else "쇼츠 만드는 중"
        job.updated_at = time.time_ns()
        return job.generation

    def begin_download(self, job_id: str) -> int:
        with self._lock:
            job = self._jobs[job_id]
            if job.status != JobStatus.QUEUED:
                raise InvalidTransition("대기 중인 작업만 가져올 수 있습니다.")
            return self._start(job, JobStatus.DOWNLOADING)

    def begin_encode(self, job_id: str, options: EditOptions) -> int:
        with self._lock:
            job = self._jobs[job_id]
            if job.status not in {JobStatus.DOWNLOADED, JobStatus.DONE, JobStatus.ERROR, JobStatus.CANCELED}:
                raise InvalidTransition("이 작업은 지금 편집을 시작할 수 없습니다.")
            if not job.source_path or not job.source_path.is_file() or not job.source_timeline:
                raise InvalidTransition("편집할 구간 원본이 없습니다.")
            job.source_timeline.original_range(options.trim_start, options.trim_end)
            (job.work_dir / "tmp").mkdir(exist_ok=True)
            job.last_edit = deepcopy(options)
            return self._start(job, JobStatus.ENCODING)

    def _current(self, job: JobState, generation: int, status: JobStatus | None = None) -> bool:
        return (job.generation == generation
                and job.status in {JobStatus.DOWNLOADING, JobStatus.ENCODING}
                and (status is None or job.status == status))

    @staticmethod
    def _stop(proc: subprocess.Popen) -> None:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
        # 부모가 먼저 끝나도 소유한 Windows Job 또는 POSIX 자식 그룹을 정리한다.
        if isinstance(proc, OwnedProcess):
            proc.kill()

    def attach_process(self, job_id: str, generation: int, proc: subprocess.Popen) -> bool:
        with self._lock:
            job = self._jobs[job_id]
            if self._current(job, generation) and job._proc is None:
                job._proc = proc
                return True
        # 취소와 실행 사이의 경합으로 늦게 생성된 프로세스도 반드시 종료한다.
        self._stop(proc)
        return False

    def start_process(self, job_id: str, generation: int, args: list[str]) -> subprocess.Popen | None:
        with self._lock:
            job = self._jobs[job_id]
            if not self._current(job, generation):
                return None
            if job._proc is not None:
                raise InvalidTransition("이미 실행 중인 프로세스가 있습니다.")
            job._proc = OwnedProcess(args)
            return job._proc

    def release_process(self, job_id: str, generation: int, proc: subprocess.Popen) -> bool:
        with self._lock:
            job = self._jobs[job_id]
            if not self._current(job, generation) or job._proc is not proc:
                return False
            if proc.poll() is None:
                raise InvalidTransition("프로세스가 아직 종료되지 않았습니다.")
            if isinstance(proc, OwnedProcess):
                proc.close_tree()
            job._proc = None
            return True

    def publish(self, job_id: str, generation: int, temporary: Path, output: Path) -> bool:
        with self._lock:
            job = self._jobs[job_id]
            if not self._current(job, generation, JobStatus.ENCODING):
                return False
            if temporary.resolve().parent != job.work_dir / "tmp":
                raise ValueError("잘못된 임시 출력 경로입니다.")
            if output.resolve().is_relative_to(self.work_root) or output.exists():
                raise ValueError("완성 출력 경로가 안전하지 않습니다.")
            self._nonempty_file(temporary)
            if job._proc is not None:
                raise InvalidTransition("프로세스 종료 확인이 필요합니다.")
            temporary.replace(output)
            return self.completed(job_id, generation, output)

    def progress(self, job_id: str, generation: int, value: float) -> bool:
        if not math.isfinite(value):
            raise ValueError("진행률이 유한값이어야 합니다.")
        with self._lock:
            job = self._jobs[job_id]
            if not self._current(job, generation):
                return False
            job.progress = max(job.progress, min(1.0, max(0.0, value)))
            job.updated_at = time.time_ns()
            return True

    @staticmethod
    def _nonempty_file(path: Path) -> None:
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError("완성된 영상 파일이 없거나 비어 있습니다.")

    @staticmethod
    def _finish(job: JobState, status: JobStatus, message: str) -> None:
        if job._proc is not None and job._proc.poll() is None:
            raise InvalidTransition("실행 중인 프로세스가 아직 종료되지 않았습니다.")
        job._proc = None
        job.status = status
        job.message = message
        job.updated_at = time.time_ns()

    def downloaded(
        self, job_id: str, generation: int, source: Path,
        meta: SourceMeta, timeline: SourceTimeline,
    ) -> bool:
        with self._lock:
            job = self._jobs[job_id]
            if not self._current(job, generation, JobStatus.DOWNLOADING):
                return False
            source = source.resolve()
            if source.parent != job.work_dir or not math.isclose(meta.duration, timeline.duration_sec):
                raise ValueError("원본 경로 또는 실제 길이와 시각 매핑이 일치하지 않습니다.")
            self._nonempty_file(source)
            self._finish(job, JobStatus.DOWNLOADED, "구간 준비 완료")
            job.source_path, job.source_meta, job.source_timeline = source, meta, timeline
            job.progress = 1.0
            return True

    def completed(self, job_id: str, generation: int, output: Path) -> bool:
        with self._lock:
            job = self._jobs[job_id]
            if not self._current(job, generation, JobStatus.ENCODING):
                return False
            output = output.resolve()
            if output.is_relative_to(self.work_root):
                raise ValueError("완성 출력은 정리 대상 작업 폴더 밖에 저장해야 합니다.")
            self._nonempty_file(output)
            self._finish(job, JobStatus.DONE, "쇼츠 저장 완료")
            job.outputs.append(output)
            job.progress = 1.0
            return True

    def failed(self, job_id: str, generation: int, code: str, message: str) -> bool:
        with self._lock:
            job = self._jobs[job_id]
            if not self._current(job, generation):
                return False
            self._finish(job, JobStatus.ERROR, message)
            job.error_code = code
            if job.source_path is None and job.work_dir.exists():
                shutil.rmtree(job.work_dir)
            return True

    def cancel(self, job_id: str) -> JobState:
        with self._lock:
            job = self._jobs[job_id]
            if job.status not in {JobStatus.QUEUED, JobStatus.DOWNLOADING, JobStatus.ENCODING}:
                raise InvalidTransition("현재 취소할 실행 작업이 없습니다.")
            encoding = job.status == JobStatus.ENCODING
            if job._proc is not None:
                self._stop(job._proc)
            self._finish(job, JobStatus.CANCELED, "작업 취소됨")
            job.generation += 1
            target = job.work_dir / "tmp" if encoding else job.work_dir
            # root나 다른 작업을 삭제하지 않으며 종료 확인에 실패하면 정리하지 않는다.
            if target.parent != (job.work_dir if encoding else self.work_root):
                raise ValueError("작업 정리 경로가 올바르지 않습니다.")
            if target.exists():
                shutil.rmtree(target)
            return self.get(job_id)
