"""clipman이 생성한 프로세스 그룹만 종료한다. 플랫폼 분기는 여기 둔다."""

import os
import signal
import subprocess

WINDOWS = os.name == "nt"


class OwnedProcess(subprocess.Popen):
    def __init__(self, args):
        options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if WINDOWS else {"start_new_session": True}
        super().__init__(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace", **options)

    def _signal_tree(self, sig):
        if WINDOWS:
            if self.poll() is not None:
                return
            result = subprocess.run(["taskkill", "/PID", str(self.pid), "/T", "/F"],
                                    capture_output=True, timeout=10)
            if result.returncode and self.poll() is None:
                raise RuntimeError("영상 처리 프로세스 종료에 실패했습니다.")
        else:
            try:
                os.killpg(self.pid, sig)
            except ProcessLookupError:
                pass

    def terminate(self):
        self._signal_tree(signal.SIGTERM)

    def kill(self):
        self._signal_tree(getattr(signal, 'SIGKILL', 9) if not WINDOWS else signal.SIGTERM)
