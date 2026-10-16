"""소켓을 선점한 채 서버를 실행하고 최초 연결 화면을 연다."""

import logging
import os
import re
import secrets
import socket
import webbrowser

import uvicorn

from app import paths
from app.main import create_app
from app.wrappers import binaries


def pairing_key():
    path = paths.LOGS_DIR / 'connection.key'
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        value = path.read_text(encoding='utf-8')
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', value):
            raise RuntimeError('기존 연결 키를 확인할 수 없습니다. 설치 상태를 확인해 주세요.')
        return value
    value = secrets.token_urlsafe(32)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        stream.write(value)
    return value


def open_listener(preferred=9000):
    """선호 포트를 잡고, 다른 프로그램이 쓰고 있으면 빈 포트로 물러난다."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if os.name != "nt":
        # 플랫폼 분기(핸드오프 5절): POSIX는 직전 연결의 TIME_WAIT가 bind를 막으므로 재사용을 허용한다.
        # Windows의 SO_REUSEADDR는 다른 프로그램이 듣고 있는 포트까지 가로채므로 켜지 않는다.
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listener.bind(("127.0.0.1", preferred))
    except OSError:
        listener.bind(("127.0.0.1", 0))
    return listener


def main():
    paths.ensure_runtime_dirs()
    missing = binaries.missing()
    if missing:
        raise RuntimeError("영상 처리 파일이 준비되지 않았습니다. bin 폴더의 설치 상태를 확인해 주세요.")
    logging.basicConfig(filename=paths.LOG_FILE, encoding="utf-8", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    with open_listener() as listener:
        port = listener.getsockname()[1]
        app = create_app(token=pairing_key(), port=port)
        listener.listen(128)
        # 기기 연결 키는 gitignore 파일에 보존하고 URL과 실행 로그에는 남기지 않는다.
        webbrowser.open(f"http://127.0.0.1:{port}/connect")
        uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port,
                                     workers=1, reload=False, access_log=False)).run(sockets=[listener])


if __name__ == "__main__":
    main()
