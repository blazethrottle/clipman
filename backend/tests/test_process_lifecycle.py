import subprocess
import sys

import pytest

from app.capture import Selection
from app.jobs.manager import JobManager, InvalidTransition


def test_process_cannot_start_after_cancel(tmp_path, monkeypatch):
    manager = JobManager(tmp_path / "work")
    job = manager.create(Selection("BaW_jenozKc", "https://youtu.be/BaW_jenozKc", 0, 2))
    generation = manager.begin_download(job.job_id)
    manager.cancel(job.job_id)
    def forbidden(*args, **kwargs):
        pytest.fail("취소 후 프로세스를 생성함")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert manager.start_process(job.job_id, generation, ["must-not-run"]) is None


def test_registered_process_finishes_before_next_command(tmp_path):
    manager = JobManager(tmp_path / "work")
    job = manager.create(Selection("BaW_jenozKc", "https://youtu.be/BaW_jenozKc", 0, 2))
    generation = manager.begin_download(job.job_id)
    proc = manager.start_process(job.job_id, generation, [sys.executable, "-c", "print('ready')"])
    assert proc.communicate(timeout=5)[0].strip() == "ready"
    assert manager.release_process(job.job_id, generation, proc)
    second = manager.start_process(job.job_id, generation, [sys.executable, "-c", "print('next')"])
    assert second.communicate(timeout=5)[0].strip() == "next"
    manager.release_process(job.job_id, generation, second)


def test_active_process_cannot_be_overwritten(tmp_path):
    manager = JobManager(tmp_path / "work")
    job = manager.create(Selection("BaW_jenozKc", "https://youtu.be/BaW_jenozKc", 0, 2))
    generation = manager.begin_download(job.job_id)
    manager.start_process(job.job_id, generation, [sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        with pytest.raises(InvalidTransition):
            manager.start_process(job.job_id, generation, [sys.executable, "-c", "pass"])
    finally:
        manager.cancel(job.job_id)


def test_failed_acquisition_removes_partial_source(tmp_path):
    manager = JobManager(tmp_path / 'work')
    job = manager.create(Selection('BaW_jenozKc', 'https://youtu.be/BaW_jenozKc', 0, 2))
    generation = manager.begin_download(job.job_id)
    (job.work_dir / 'source.mp4.part').write_bytes(b'incomplete')
    manager.failed(job.job_id, generation, 'NETWORK', 'failed')
    assert not job.work_dir.exists()
