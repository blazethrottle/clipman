import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.capture import Selection, SourceTimeline
from app.jobs.manager import JobManager, JobStatus, InvalidTransition
from app.wrappers.ffmpeg import EditOptions
from app.wrappers.ffprobe import SourceMeta


@pytest.fixture
def manager(tmp_path):
    return JobManager(tmp_path / "work")


def create(manager):
    return manager.create(Selection("BaW_jenozKc", "https://youtu.be/BaW_jenozKc", 120, 135))


def downloaded(manager):
    job = create(manager)
    generation = manager.begin_download(job.job_id)
    source = job.work_dir / "source.mp4"
    source.write_bytes(b"acquired")
    manager.downloaded(job.job_id, generation, source, SourceMeta(1920, 1080, 15, True), SourceTimeline(120, 15))
    return manager.get(job.job_id)


def test_queued_download_export_and_reedit_preserve_source(manager, tmp_path):
    job = downloaded(manager)
    assert job.status == JobStatus.DOWNLOADED
    generation = manager.begin_encode(job.job_id, EditOptions(trim_start=2, trim_end=5))
    first = tmp_path / "first.mp4"
    first.write_bytes(b"complete")
    assert manager.completed(job.job_id, generation, first)
    assert manager.get(job.job_id).status == JobStatus.DONE
    next_generation = manager.begin_encode(job.job_id, EditOptions())
    second = tmp_path / "second.mp4"
    second.write_bytes(b"complete2")
    manager.completed(job.job_id, next_generation, second)
    state = manager.get(job.job_id)
    assert state.outputs == [first, second]
    assert state.source_path.read_bytes() == b"acquired"
    assert state.selection.start_sec == 120


def test_snapshot_cannot_change_registry(manager):
    job = create(manager)
    job.outputs.append("wrong")
    job.status = JobStatus.DONE
    assert manager.get(job.job_id).status == JobStatus.QUEUED
    assert manager.get(job.job_id).outputs == []


def test_only_legal_transitions_and_ranges_are_allowed(manager):
    job = create(manager)
    with pytest.raises(InvalidTransition):
        manager.begin_encode(job.job_id, EditOptions())
    ready = downloaded(manager)
    with pytest.raises(ValueError):
        manager.begin_encode(ready.job_id, EditOptions(trim_end=16))
    token = manager.begin_encode(ready.job_id, EditOptions())
    with pytest.raises(InvalidTransition):
        manager.begin_encode(ready.job_id, EditOptions())
    assert token > 0


def test_progress_is_monotonic_and_resets_for_encode(manager):
    job = create(manager)
    token = manager.begin_download(job.job_id)
    manager.progress(job.job_id, token, .7)
    manager.progress(job.job_id, token, .2)
    assert manager.get(job.job_id).progress == .7
    source = job.work_dir / "source.mp4"
    source.write_bytes(b"source")
    manager.downloaded(job.job_id, token, source, SourceMeta(1920, 1080, 15, True), SourceTimeline(120, 15))
    token = manager.begin_encode(job.job_id, EditOptions())
    assert manager.get(job.job_id).progress == 0
    manager.progress(job.job_id, token, 2)
    assert manager.get(job.job_id).progress == 1
    with pytest.raises(ValueError):
        manager.progress(job.job_id, token, float("nan"))


def test_download_cancel_removes_only_its_job_directory(manager):
    job = create(manager)
    neighbor = create(manager)
    token = manager.begin_download(job.job_id)
    (job.work_dir / "partial").write_bytes(b"partial")
    manager.cancel(job.job_id)
    assert not job.work_dir.exists()
    assert neighbor.work_dir.exists()
    assert not manager.failed(job.job_id, token, "NETWORK", "late error")
    assert manager.get(job.job_id).status == JobStatus.CANCELED


def test_encode_cancel_preserves_original_and_complete_outputs(manager, tmp_path):
    job = downloaded(manager)
    token = manager.begin_encode(job.job_id, EditOptions())
    output = tmp_path / "completed.mp4"
    output.write_bytes(b"completed")
    manager.completed(job.job_id, token, output)
    token = manager.begin_encode(job.job_id, EditOptions())
    (job.work_dir / "tmp" / "partial.mp4").write_bytes(b"partial")
    manager.cancel(job.job_id)
    assert job.source_path.exists()
    assert output.exists()
    assert not (job.work_dir / "tmp").exists()
    assert not manager.completed(job.job_id, token, output)
    assert manager.get(job.job_id).outputs == [output]
    new_token = manager.begin_encode(job.job_id, EditOptions())
    assert new_token != token
    assert not manager.progress(job.job_id, token, 1)
    assert not manager.failed(job.job_id, token, "ENCODE_FAILED", "late")
    assert manager.get(job.job_id).status == JobStatus.ENCODING


def test_real_process_cancel_waits_before_cleaning_files(manager):
    job = create(manager)
    token = manager.begin_download(job.job_id)
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        assert manager.attach_process(job.job_id, token, proc)
        manager.cancel(job.job_id)
        assert proc.poll() is not None
        assert manager.get(job.job_id).status == JobStatus.CANCELED
        assert not job.work_dir.exists()
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def test_late_process_registration_is_stopped(manager):
    job = create(manager)
    token = manager.begin_download(job.job_id)
    manager.cancel(job.job_id)
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        assert not manager.attach_process(job.job_id, token, proc)
        assert proc.poll() is not None
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def test_failed_encode_can_retry_with_same_source(manager):
    job = downloaded(manager)
    token = manager.begin_encode(job.job_id, EditOptions())
    assert manager.failed(job.job_id, token, "ENCODE_FAILED", "변환 실패")
    assert manager.get(job.job_id).error_code == "ENCODE_FAILED"
    manager.begin_encode(job.job_id, EditOptions())
    assert manager.get(job.job_id).error_code is None
    assert manager.get(job.job_id).source_path == job.source_path


def test_completion_requires_a_nonempty_file(manager, tmp_path):
    job = downloaded(manager)
    token = manager.begin_encode(job.job_id, EditOptions())
    empty = tmp_path / "empty.mp4"
    empty.touch()
    with pytest.raises(ValueError):
        manager.completed(job.job_id, token, empty)
    assert manager.get(job.job_id).status == JobStatus.ENCODING


def test_completed_output_cannot_be_an_encoding_temporary_file(manager):
    job = downloaded(manager)
    token = manager.begin_encode(job.job_id, EditOptions())
    temporary = job.work_dir / "tmp" / "not-published.mp4"
    temporary.write_bytes(b"temporary")
    with pytest.raises(ValueError):
        manager.completed(job.job_id, token, temporary)
    assert manager.get(job.job_id).outputs == []


def test_concurrent_starts_allow_one_encoder(manager):
    job = downloaded(manager)
    def start(_):
        try:
            return manager.begin_encode(job.job_id, EditOptions())
        except InvalidTransition:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        tokens = list(pool.map(start, range(16)))
    assert len([token for token in tokens if token is not None]) == 1


def test_cancel_waiting_editor_is_conflict(manager):
    job = downloaded(manager)
    with pytest.raises(InvalidTransition):
        manager.cancel(job.job_id)


def test_source_must_be_inside_this_job_and_match_timeline(manager, tmp_path):
    job = create(manager)
    token = manager.begin_download(job.job_id)
    foreign = tmp_path / "foreign.mp4"
    foreign.write_bytes(b"foreign")
    with pytest.raises(ValueError):
        manager.downloaded(job.job_id, token, foreign, SourceMeta(1920, 1080, 15, True), SourceTimeline(120, 15))
    source = job.work_dir / "source.mp4"
    source.write_bytes(b"source")
    with pytest.raises(ValueError):
        manager.downloaded(job.job_id, token, source, SourceMeta(1920, 1080, 15, True), SourceTimeline(120, 10))


def test_unresponsive_process_is_killed_before_cleanup(manager):
    job = create(manager)
    token = manager.begin_download(job.job_id)
    class UnresponsiveProcess:
        alive = True
        def poll(self):
            return None if self.alive else -9
        def terminate(self):
            pass
        def wait(self, timeout):
            if self.alive:
                raise subprocess.TimeoutExpired("worker", timeout)
            return -9
        def kill(self):
            assert job.work_dir.exists()
            self.alive = False
    proc = UnresponsiveProcess()
    manager.attach_process(job.job_id, token, proc)
    manager.cancel(job.job_id)
    assert not proc.alive
    assert not job.work_dir.exists()


def test_failed_termination_does_not_delete_running_work(manager):
    job = create(manager)
    token = manager.begin_download(job.job_id)
    class UnstoppableProcess:
        def poll(self):
            return None
        def terminate(self):
            raise PermissionError("cannot stop")
    manager.attach_process(job.job_id, token, UnstoppableProcess())
    with pytest.raises(PermissionError):
        manager.cancel(job.job_id)
    assert job.work_dir.exists()
    assert manager.get(job.job_id).status == JobStatus.DOWNLOADING
