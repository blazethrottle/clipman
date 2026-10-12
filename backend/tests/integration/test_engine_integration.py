"""API -> 서비스 -> 실제 실행파일 -> MP4의 개발 연결 검증."""
import subprocess
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
from fastapi.testclient import TestClient

from app.jobs.manager import JobManager
from app.main import create_app, EXTENSION_ID
from app.services.engine import Engine
from app.wrappers import binaries, ytdlp, ffprobe

pytestmark = pytest.mark.integration


def wait_for(client, path, headers, target):
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        state = client.get(path, headers=headers).json()
        assert state['status'] != 'error', state
        if state['status'] == target:
            return state
        time.sleep(.05)
    pytest.fail(f"작업 완료 시간 초과: {state}")


def test_real_acquire_export_range_and_reedit(tmp_path, monkeypatch):
    for name in binaries.NAMES:
        try:
            binaries.require(name)
        except binaries.BinaryNotFound as exc:
            pytest.skip(str(exc))
    source = tmp_path / 'fixture.mp4'
    subprocess.run([str(binaries.require(binaries.FFMPEG)), '-v', 'error', '-y',
        '-f', 'lavfi', '-i', 'testsrc=size=640x360:rate=30:duration=4',
        '-f', 'lavfi', '-i', 'sine=frequency=440:duration=4',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
        '-movflags', '+faststart', '-shortest', str(source)], check=True, capture_output=True, timeout=30)
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    http = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(tmp_path)))
    thread = Thread(target=http.serve_forever, daemon=True)
    thread.start()
    original = ytdlp.build_download_args
    def synthetic_download(*args, **kwargs):
        command = original(*args, **kwargs)
        command[-1] = f'http://127.0.0.1:{http.server_port}/fixture.mp4'
        command[1:1] = ['--proxy', '']
        return command
    monkeypatch.setattr(ytdlp, 'build_download_args', synthetic_download)
    engine = Engine(JobManager(tmp_path / 'work'), tmp_path / 'output')
    headers = {'X-Clipman-Token': 'integration-key', 'X-Clipman-Extension': EXTENSION_ID}
    try:
        with TestClient(create_app(engine, 'integration-key', 9000), base_url='http://127.0.0.1:9000') as client:
            response = client.post('/api/jobs', headers=headers, json={'video_id': 'BaW_jenozKc', 'url': 'https://youtu.be/BaW_jenozKc', 'start_sec': 1, 'end_sec': 3})
            assert response.status_code == 201, response.text
            path = '/api/jobs/' + response.json()['job_id']
            ready = wait_for(client, path, headers, 'downloaded')
            assert ready['source_timeline']['origin_start_sec'] == 1
            assert client.get(ready['source_url'], headers={'Range': 'bytes=0-127'}).status_code == 206
            assert client.post(path + '/export', headers=headers, json={'trim_start': .25, 'trim_end': 1.25, 'mode': 'crop', 'crop_x': 100}).status_code == 202
            first = wait_for(client, path, headers, 'done')
            assert len(first['outputs']) == 1
            assert client.get(first['outputs'][0]['url'] + '&download=true').status_code == 200
            original_path = engine.manager.get(first['job_id']).source_path
            assert client.post(path + '/export', headers=headers, json={'trim_start': 0, 'trim_end': 1, 'mode': 'pad'}).status_code == 202
            final = wait_for(client, path, headers, 'done')
            assert len(final['outputs']) == 2
            assert engine.manager.get(first['job_id']).source_path == original_path
            for output in engine.manager.get(first['job_id']).outputs:
                probe = subprocess.run(ffprobe.build_probe_args(output, exe=binaries.require(binaries.FFPROBE)), check=True, capture_output=True, text=True, timeout=10)
                meta = ffprobe.parse_probe_json(probe.stdout)
                assert (meta.width, meta.height) == (1080, 1920)
                assert meta.duration == pytest.approx(1, abs=.2)
                assert meta.has_audio
    finally:
        http.shutdown(); http.server_close(); thread.join(timeout=3)
