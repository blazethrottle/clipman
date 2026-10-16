import re

from app import paths
from app.launch import pairing_key


def test_pairing_key_survives_restart_and_is_not_in_url(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, 'LOGS_DIR', tmp_path)
    first = pairing_key()
    assert re.fullmatch(r'[A-Za-z0-9_-]{43}', first)
    assert pairing_key() == first
    assert (tmp_path / 'connection.key').read_text() == first


def test_invalid_existing_key_is_preserved(tmp_path, monkeypatch):
    import pytest
    monkeypatch.setattr(paths, 'LOGS_DIR', tmp_path)
    path = tmp_path / 'connection.key'
    path.write_text('invalid')
    with pytest.raises(RuntimeError):
        pairing_key()
    assert path.read_text() == 'invalid'


def test_listener_reclaims_port_left_in_time_wait():
    """사용 직후 다시 실행해도 같은 포트(9000 역할)를 잡아야 확장의 저장된 연결이 유지된다.

    2026-10-16 macOS QA 실측: 서버를 끄고 바로 start.command를 열면 직전 연결의
    TIME_WAIT 소켓 때문에 bind가 실패해 임의 포트(52468)로 열렸다.
    """
    import socket
    from app.launch import open_listener

    first = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    first.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    first.bind(("127.0.0.1", 0))
    first.listen(1)
    port = first.getsockname()[1]
    client = socket.create_connection(("127.0.0.1", port))
    server_side, _ = first.accept()
    server_side.close()  # 서버가 먼저 닫아 TIME_WAIT를 서버 쪽에 남긴다
    client.close()
    first.close()

    listener = open_listener(port)
    try:
        assert listener.getsockname()[1] == port
    finally:
        listener.close()
