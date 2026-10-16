import os
import sys
import time

import pytest

from app.capture import Selection
from app.jobs.manager import JobManager


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # 종료됐지만 회수되지 않은 좀비는 파일 쓰기를 할 수 없으므로 종료로 본다.
    status = os.popen(f'ps -o stat= -p {pid}').read().strip()
    return bool(status) and not status.startswith('Z')


def _wait_dead(pid, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _alive(pid):
            return True
        time.sleep(.05)
    return False


def _start(tmp_path, parent_code):
    marker = tmp_path / 'child.log'
    child = "import time,pathlib; p=pathlib.Path(" + repr(str(marker)) + ");\nfor i in range(400):\n p.write_text(str(i)); time.sleep(.05)"
    parent = ("import subprocess,sys;p=subprocess.Popen([sys.executable,'-c'," + repr(child) + "]);"
              "print(p.pid,flush=True);" + parent_code)
    manager = JobManager(tmp_path / 'work')
    job = manager.create(Selection('BaW_jenozKc', 'https://youtu.be/BaW_jenozKc', 0, 2))
    generation = manager.begin_download(job.job_id)
    proc = manager.start_process(job.job_id, generation, [sys.executable, '-c', parent])
    child_pid = int(proc.stdout.readline())
    return manager, job, proc, child_pid


def _cleanup(proc, child_pid):
    if _alive(child_pid):
        os.kill(child_pid, 9)
    if proc.poll() is None:
        proc.kill()
        proc.wait(timeout=5)
    proc.stdout.close()


@pytest.mark.skipif(os.name == 'nt', reason='POSIX 프로세스 그룹 실물 검사')
def test_cancel_after_parent_exit_stops_posix_child(tmp_path):
    manager, job, proc, child_pid = _start(tmp_path, '')
    try:
        proc.wait(timeout=5)
        assert _alive(child_pid), '시험 전제: 부모 종료 뒤 자식이 남아 있어야 함'
        manager.cancel(job.job_id)
        assert _wait_dead(child_pid), '부모 종료 후 자식이 계속 실행됨'
    finally:
        _cleanup(proc, child_pid)


@pytest.mark.skipif(os.name == 'nt', reason='POSIX 프로세스 그룹 실물 검사')
def test_cancel_running_parent_stops_posix_child(tmp_path):
    manager, job, proc, child_pid = _start(tmp_path, 'p.wait()')
    try:
        manager.cancel(job.job_id)
        assert _wait_dead(child_pid), '실행 중 취소 후 자식이 계속 실행됨'
        assert proc.wait(timeout=5) is not None
    finally:
        _cleanup(proc, child_pid)
