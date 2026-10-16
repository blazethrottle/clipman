import os
import subprocess
import sys

import pytest

from app.capture import Selection
from app.jobs.manager import JobManager
from app import processes


@pytest.mark.skipif(os.name != 'nt', reason='Windows Job Object 실물 검사')
def test_target_cannot_start_when_job_assignment_fails(tmp_path, monkeypatch):
    marker = tmp_path / 'must-not-exist'
    def fail_assignment(self, process):
        raise OSError('assignment refused')
    monkeypatch.setattr(processes._WindowsJob, 'assign', fail_assignment)
    with pytest.raises(OSError, match='assignment refused'):
        processes.OwnedProcess([sys.executable, '-c', 'from pathlib import Path; Path(' + repr(str(marker)) + ').touch()'])
    assert not marker.exists()


@pytest.mark.skipif(os.name != 'nt', reason='Windows Job Object 실물 검사')
def test_cancel_after_parent_exit_stops_child_writes(tmp_path):
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    marker = tmp_path / 'child.log'
    child = "import time,pathlib; p=pathlib.Path(" + repr(str(marker)) + ");\nfor i in range(200):\n p.write_text(str(i)); time.sleep(.05)"
    parent = "import subprocess,sys;p=subprocess.Popen([sys.executable,'-c'," + repr(child) + "]);print(p.pid,flush=True)"
    manager = JobManager(tmp_path / 'work')
    job = manager.create(Selection('BaW_jenozKc', 'https://youtu.be/BaW_jenozKc', 0, 2))
    generation = manager.begin_download(job.job_id)
    proc = manager.start_process(job.job_id, generation, [sys.executable, '-c', parent])
    child_pid = int(proc.stdout.readline())
    handle = kernel.OpenProcess(0x100000 | 1, False, child_pid)
    assert handle
    try:
        proc.wait(timeout=5)
        manager.cancel(job.job_id)
        assert kernel.WaitForSingleObject(handle, 1000) == 0, '부모 종료 후 자식이 파일 쓰기를 계속함'
    finally:
        kernel.TerminateProcess(handle, 0)
        kernel.WaitForSingleObject(handle, 3000)
        kernel.CloseHandle(handle)
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
        proc.stdout.close()
