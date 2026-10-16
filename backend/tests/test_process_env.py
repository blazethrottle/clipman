import sys

import pytest

from app import processes


def test_macos_points_bundled_openssl_to_system_ca_bundle(tmp_path):
    bundle = tmp_path / 'cert.pem'
    bundle.write_text('ca')
    env = processes.child_env(platform='darwin', environ={'PATH': '/usr/bin'}, ca_bundle=bundle)
    assert env == {'PATH': '/usr/bin', 'SSL_CERT_FILE': str(bundle)}


def test_user_ca_setting_is_kept(tmp_path):
    bundle = tmp_path / 'cert.pem'
    bundle.write_text('ca')
    env = processes.child_env(platform='darwin', environ={'SSL_CERT_FILE': '/custom.pem'}, ca_bundle=bundle)
    assert env['SSL_CERT_FILE'] == '/custom.pem'


@pytest.mark.parametrize('platform', ['win32', 'linux'])
def test_other_platforms_are_unchanged(tmp_path, platform):
    bundle = tmp_path / 'cert.pem'
    bundle.write_text('ca')
    assert processes.child_env(platform=platform, environ={'A': '1'}, ca_bundle=bundle) == {'A': '1'}


def test_missing_bundle_is_not_injected(tmp_path):
    env = processes.child_env(platform='darwin', environ={}, ca_bundle=tmp_path / 'absent.pem')
    assert 'SSL_CERT_FILE' not in env


@pytest.mark.skipif(sys.platform != 'darwin', reason='macOS 실물 검사')
def test_owned_process_receives_ca_bundle_on_macos(monkeypatch):
    monkeypatch.delenv('SSL_CERT_FILE', raising=False)
    proc = processes.OwnedProcess([sys.executable, '-c', "import os;print(os.environ.get('SSL_CERT_FILE'))"])
    try:
        assert proc.stdout.read().strip() == str(processes.MACOS_CA_BUNDLE)
    finally:
        proc.wait(timeout=5)
        proc.stdout.close()
