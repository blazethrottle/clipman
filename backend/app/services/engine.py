from __future__ import annotations

import math
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app import paths
from app.capture import Selection, SourceTimeline
from app.jobs.manager import JobManager, JobStatus
from app.wrappers import binaries, ffmpeg, ffprobe, ytdlp


ERROR_MESSAGES = {
    "BOT_BLOCK": "YouTube에서 가져오기를 제한했습니다. 다른 영상을 시도해 주세요.",
    "FORMAT_UNAVAILABLE": "이 영상에서 요청한 화질을 가져올 수 없습니다.",
    "NETWORK": "영상에 연결하지 못했습니다. 네트워크를 확인해 주세요.",
    "HTTP_403": "YouTube가 영상 전송을 일시적으로 거부했습니다. 잠시 후 다시 시도해 주세요.",
}
# 일시적 거부만 다시 시도한다. 봇 차단과 화질 부재는 반복해도 결과가 같다.
RETRYABLE = {"HTTP_403"}


class Canceled(Exception):
    pass


class ProcessingError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message
        super().__init__(message)


class Engine:
    def __init__(self, manager=None, output_root=None):
        self.manager = manager or JobManager()
        self.output_root = Path(output_root or paths.OUTPUT_DIR).resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="clipman")

    def _run(self, job_id, generation, args, parser=None):
        proc = self.manager.start_process(job_id, generation, args)
        if proc is None:
            raise Canceled()
        lines = deque(maxlen=500)
        try:
            for line in proc.stdout:
                lines.append(line)
                if parser:
                    value = parser(line)
                    if value is not None:
                        self.manager.progress(job_id, generation, value)
            code = proc.wait()
        finally:
            proc.stdout.close()
            if proc.poll() is None:
                self.manager._stop(proc)
            accepted = self.manager.release_process(job_id, generation, proc)
        if not accepted:
            raise Canceled()
        text = "".join(lines)
        if code:
            error_code = ytdlp.classify_error(text) if Path(args[0]).stem == "yt-dlp" else "PROCESS_FAILED"
            message = ERROR_MESSAGES.get(error_code,
                       "이 구간을 처리할 수 없습니다. 영상이 재생 가능한지 확인하거나 다른 구간을 시도해 주세요.")
            raise ProcessingError(error_code, message)
        return text

    def _probe(self, job_id, generation, source):
        return ffprobe.parse_probe_json(self._run(job_id, generation,
            ffprobe.build_probe_args(source, exe=binaries.require(binaries.FFPROBE))))

    def acquire(self, selection: Selection, quality: str = "best"):
        ytdlp.format_selector(quality)
        for name in binaries.NAMES:
            binaries.require(name)
        job = self.manager.create(selection, quality)
        generation = self.manager.begin_download(job.job_id)
        self.pool.submit(self._acquire, job.job_id, generation)
        return self.manager.get(job.job_id)

    def _acquire(self, job_id, generation):
        job = self.manager.get(job_id)
        try:
            args = ytdlp.build_download_args(job.selection.url, job.quality, job.work_dir,
                ffmpeg_dir=paths.BIN_DIR, exe=binaries.require(binaries.YTDLP), selection=job.selection)
            try:
                self._run(job_id, generation, args, ytdlp.parse_progress_line)
            except ProcessingError as exc:
                if exc.code not in RETRYABLE:
                    raise
                # 실패한 시도의 부분 파일이 남으면 확보 파일을 하나로 특정할 수 없다.
                for partial in job.work_dir.glob("source.*"):
                    partial.unlink(missing_ok=True)
                self._run(job_id, generation, args, ytdlp.parse_progress_line)
            sources = [p for p in job.work_dir.glob("source.*") if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}]
            if len(sources) != 1:
                raise ProcessingError("DOWNLOAD_FAILED", "확보한 영상 파일을 확인할 수 없습니다.")
            meta = self._probe(job_id, generation, sources[0])
            if not math.isclose(meta.duration, job.selection.duration_sec, abs_tol=.25):
                raise ProcessingError("SECTION_MISMATCH", "가져온 구간 길이가 선택과 다릅니다. 구간을 다시 선택해 주세요.")
            # 정밀 컷 요청 기준 매핑이다. 실제 YouTube 장면의 시각 실증과 구분한다.
            self.manager.downloaded(job_id, generation, sources[0], meta,
                SourceTimeline(job.selection.start_sec, meta.duration))
        except Canceled:
            pass
        except Exception as exc:
            self._fail(job_id, generation, exc, "DOWNLOAD_FAILED")

    def export(self, job_id, options: ffmpeg.EditOptions):
        for name in (binaries.FFMPEG, binaries.FFPROBE):
            binaries.require(name)
        generation = self.manager.begin_encode(job_id, options)
        self.pool.submit(self._encode, job_id, generation)

    def _encode(self, job_id, generation):
        job = self.manager.get(job_id)
        temporary = job.work_dir / "tmp" / f"shorts-{generation}.mp4"
        try:
            length = ffmpeg.clip_duration(job.source_meta, job.last_edit)
            args = ffmpeg.build_encode_args(job.source_path, temporary, job.last_edit,
                                           job.source_meta, exe=binaries.require(binaries.FFMPEG))
            self._run(job_id, generation, args, lambda line: ffmpeg.parse_progress_line(line, length))
            meta = self._probe(job_id, generation, temporary)
            if ((meta.width, meta.height) != (1080, 1920)
                    or not math.isclose(meta.duration, length, abs_tol=.25)
                    or (job.source_meta.has_audio and not meta.has_audio)):
                raise ProcessingError("OUTPUT_INVALID", "출력 영상의 구간, 크기 또는 음성이 올바르지 않습니다.")
            self.manager.publish(job_id, generation, temporary,
                self.output_root / f"clipman-{job_id[:12]}-{generation}.mp4")
        except Canceled:
            pass
        except Exception as exc:
            self._fail(job_id, generation, exc, "ENCODE_FAILED")
        finally:
            temporary.unlink(missing_ok=True)

    def _fail(self, job_id, generation, exc, default):
        code = exc.code if isinstance(exc, ProcessingError) and exc.code != "PROCESS_FAILED" else default
        message = exc.message if isinstance(exc, ProcessingError) else "처리 중 오류가 발생했습니다. 다시 시도해 주세요."
        self.manager.failed(job_id, generation, code, message)

    def close(self):
        for job in self.manager.list_jobs():
            if job.status in {JobStatus.QUEUED, JobStatus.DOWNLOADING, JobStatus.ENCODING}:
                self.manager.cancel(job.job_id)
        self.pool.shutdown(wait=True, cancel_futures=True)
