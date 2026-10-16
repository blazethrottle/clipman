"""clipman이 생성한 프로세스 그룹만 종료한다. 플랫폼 분기는 여기 둔다."""

import os
import signal
import subprocess
import sys
import time

WINDOWS = os.name == "nt"
MACOS_CA_BUNDLE = "/etc/ssl/cert.pem"


def child_env(platform=None, environ=None, ca_bundle=MACOS_CA_BUNDLE):
    """번들 실행파일에 넘길 환경 변수.

    macOS 정적 ffmpeg의 OpenSSL은 빌드 기기의 인증서 경로를 보므로 시스템 인증서를 찾지 못한다.
    --download-sections에서는 ffmpeg가 YouTube에 직접 HTTPS로 접속하므로 시스템 묶음을 지정한다.
    """
    env = dict(os.environ if environ is None else environ)
    current = sys.platform if platform is None else platform
    if current == "darwin" and "SSL_CERT_FILE" not in env and os.path.isfile(ca_bundle):
        env["SSL_CERT_FILE"] = str(ca_bundle)
    return env

if WINDOWS:
    import ctypes
    from ctypes import wintypes

    class _Limits(ctypes.Structure):
        _fields_ = [("user", ctypes.c_longlong), ("job_user", ctypes.c_longlong),
                    ("flags", wintypes.DWORD), ("min_ws", ctypes.c_size_t),
                    ("max_ws", ctypes.c_size_t), ("active_limit", wintypes.DWORD),
                    ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                    ("scheduling", wintypes.DWORD)]

    class _ExtendedLimits(ctypes.Structure):
        _fields_ = [("basic", _Limits), ("io", ctypes.c_ulonglong * 6),
                    ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                    ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]

    class _Accounting(ctypes.Structure):
        _fields_ = [("times", ctypes.c_longlong * 4), ("faults", wintypes.DWORD),
                    ("total", wintypes.DWORD), ("active", wintypes.DWORD),
                    ("terminated", wintypes.DWORD)]

    _kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    _kernel.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    _kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _kernel.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
    _kernel.CloseHandle.argtypes = [wintypes.HANDLE]

    def _checked(result):
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())
        return result

    class _WindowsJob:
        def __init__(self):
            self.handle = _checked(_kernel.CreateJobObjectW(None, None))
            limits = _ExtendedLimits()
            limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            try:
                _checked(_kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
            except BaseException:
                self.close()
                raise

        def assign(self, process):
            _checked(_kernel.AssignProcessToJobObject(self.handle, int(process._handle)))

        def stop(self):
            if not self.handle:
                return
            _checked(_kernel.TerminateJobObject(self.handle, 1))
            deadline = time.monotonic() + 5
            while True:
                accounting = _Accounting()
                _checked(_kernel.QueryInformationJobObject(self.handle, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None))
                if not accounting.active:
                    self.close()
                    return
                if time.monotonic() >= deadline:
                    raise TimeoutError("영상 처리 자식 프로세스가 종료되지 않았습니다.")
                time.sleep(.01)

        def close(self):
            if getattr(self, "handle", None):
                _kernel.CloseHandle(self.handle)
                self.handle = None

        def __del__(self):
            self.close()


class OwnedProcess(subprocess.Popen):
    def __init__(self, args):
        self._job = _WindowsJob() if WINDOWS else None
        options = {"creationflags": subprocess.CREATE_NO_WINDOW, "stdin": subprocess.PIPE} if WINDOWS else {"start_new_session": True}
        # Job 할당 전에는 대상 프로그램이 자식을 만들 수 없도록 Python 부트스트랩을 대기시킨다.
        # 현재 실행기는 venv Python을 사용한다. frozen 배포 시에는 이 부트스트랩도 교체해야 한다.
        command = [sys.executable, "-u", "-c",
                   "import subprocess,sys; ready=sys.stdin.read(1); sys.exit(subprocess.call(sys.argv[1:],stdin=subprocess.DEVNULL,creationflags=0x08000000) if ready=='1' else 1)",
                   *map(str, args)] if WINDOWS else args
        try:
            super().__init__(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace", env=child_env(), **options)
            if self._job:
                self._job.assign(self)
                self.stdin.write("1")
                self.stdin.close()
                self.stdin = None
        except BaseException:
            if self._job:
                self._job.close()
            if getattr(self, "_child_created", False):
                subprocess.Popen.kill(self)
                self.wait(timeout=5)
                if self.stdin:
                    self.stdin.close()
                self.stdout.close()
            raise

    def _signal_tree(self, sig):
        if WINDOWS:
            self._job.stop()
        else:
            try:
                os.killpg(self.pid, sig)
            except ProcessLookupError:
                pass

    def terminate(self):
        self._signal_tree(signal.SIGTERM)

    def kill(self):
        self._signal_tree(getattr(signal, 'SIGKILL', 9) if not WINDOWS else signal.SIGTERM)

    def close_tree(self):
        if WINDOWS:
            self._job.stop()
