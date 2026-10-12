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
