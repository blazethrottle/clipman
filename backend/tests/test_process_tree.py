import os
import subprocess
import sys

from app.capture import Selection
from app.jobs.manager import JobManager


def test_cancel_ends_owned_child_process_tree(tmp_path):
    manager = JobManager(tmp_path / 'work')
    job = manager.create(Selection('BaW_jenozKc', 'https://youtu.be/BaW_jenozKc', 0, 2))
    generation = manager.begin_download(job.job_id)
    script = "import subprocess,sys;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);print(p.pid,flush=True);p.wait()"
    proc = manager.start_process(job.job_id, generation, [sys.executable, '-c', script])
    child_pid = int(proc.stdout.readline())
    handle = None
    try:
        if os.name == 'nt':
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            handle = kernel.OpenProcess(0x100000, False, child_pid)
            assert handle
        manager.cancel(job.job_id)
        assert proc.poll() is not None
        if handle:
            assert kernel.WaitForSingleObject(handle, 3000) == 0
        else:
            # 부모와 같은 전용 세션에서 종료 신호를 받았는지 프로세스 그룹으로 확인한다.
            assert proc.returncode != 0
    finally:
        if handle:
            kernel.CloseHandle(handle)
        if proc.poll() is None:
            proc.kill(); proc.wait(timeout=3)
        proc.stdout.close()
