"""실제 CLI 계약과 로컬 HTTP 영상 확보. 외부 YouTube 접속을 대체하지 않는다."""
import functools
import http.server
import json
import subprocess
import threading

import pytest

from app.wrappers import binaries, ffmpeg, ffprobe, ytdlp
from app.capture import Selection

pytestmark = pytest.mark.integration


def run(args):
    return subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60, check=True)


@pytest.fixture(scope='module')
def executables():
    try:
        return {name: binaries.require(name) for name in binaries.NAMES}
    except binaries.BinaryNotFound as exc:
        pytest.skip(str(exc))


@pytest.fixture(scope='module')
def video_server(tmp_path_factory, executables):
    directory = tmp_path_factory.mktemp('http-video')
    video = directory / 'fixture.mp4'
    pattern = "color=black:size=640x360:rate=10:duration=4"
    for x, before, after in ((0, 'red', 'lime'), (320, 'blue', 'yellow')):
        for color, condition in ((before, 'lt(t,2)'), (after, 'gte(t,2)')):
            pattern += f",drawbox=x={x}:y=0:w=320:h=360:color={color}:t=fill:enable='{condition}'"
    run([str(executables['ffmpeg']), '-v', 'error', '-f', 'lavfi', '-i', pattern, '-f', 'lavfi', '-i', 'sine=frequency=440:duration=4', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', '-shortest', str(video)])
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/fixture.mp4'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def probe(executables, path):
    return ffprobe.parse_probe_json(run(ffprobe.build_probe_args(path, executables['ffprobe'])).stdout)


def test_progress_from_real_download_is_parseable(video_server, executables, tmp_path):
    result = run(ytdlp.build_download_args(video_server, 'best', tmp_path, ffmpeg_dir=executables['ffmpeg'].parent, exe=executables['yt-dlp']))
    values = [ytdlp.parse_progress_line(line) for line in (result.stdout + result.stderr).splitlines()]
    assert any(value is not None and value > 0 for value in values), result.stdout + result.stderr
    assert 1.0 in values
    assert probe(executables, tmp_path / 'source.mp4').has_audio


def test_muxed_quality_fallback_obeys_height_cap(executables, tmp_path):
    info = {'id': 'fixture', 'title': 'fixture', 'extractor': 'generic', 'extractor_key': 'Generic', 'webpage_url': 'https://example.invalid/fixture', 'formats': [
        {'format_id': str(h), 'ext': 'mp4', 'height': h, 'width': h * 16 // 9, 'vcodec': 'avc1', 'acodec': 'aac', 'url': 'https://example.invalid/video.mp4'} for h in (720, 1080)
    ]}
    source = tmp_path / 'info.json'
    source.write_text(json.dumps(info), encoding='utf-8')
    args = ytdlp.build_download_args('unused', '720p', tmp_path, exe=executables['yt-dlp'])[:-1]
    result = run(args + ['--load-info-json', str(source), '--simulate', '--dump-json'])
    assert json.loads(result.stdout)['height'] == 720


@pytest.mark.parametrize('crop_x,expected', [(0, (0, 255, 0)), (400, (255, 255, 0))])
def test_section_capture_crop_and_audio(video_server, executables, tmp_path, crop_x, expected):
    # 원본 2~3.5초는 처음 2초의 빨강/파랑과 달라야 한다.
    selected = Selection('BaW_jenozKc', 'https://youtu.be/BaW_jenozKc', 2.0, 3.5)
    args = ytdlp.build_download_args(selected.url, 'best', tmp_path, ffmpeg_dir=executables['ffmpeg'].parent, exe=executables['yt-dlp'], selection=selected)
    # 통제된 원본으로 CLI만 검증하며 YouTube URL 보안 검사는 우회 구현하지 않는다.
    args[-1] = video_server
    run(args)
    source = tmp_path / 'source.mp4'
    meta = probe(executables, source)
    assert meta.duration == pytest.approx(1.5, abs=0.2)
    assert meta.has_audio
    output = tmp_path / 'shorts.mp4'
    edit = ffmpeg.EditOptions(trim_start=0.0, trim_end=1.0, crop_x=crop_x)
    run(ffmpeg.build_encode_args(source, output, edit, meta, executables['ffmpeg']))
    exported = probe(executables, output)
    assert (exported.width, exported.height) == (1080, 1920)
    assert exported.duration == pytest.approx(1.0, abs=0.2)
    assert exported.has_audio
    for when in (0, 0.8):
        frame = subprocess.run([str(executables['ffmpeg']), '-v', 'error', '-ss', str(when), '-i', str(output), '-frames:v', '1', '-vf', 'scale=1:1', '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'], capture_output=True, timeout=30, check=True).stdout
        assert len(frame) == 3
        assert all(abs(actual - desired) < 20 for actual, desired in zip(frame, expected)), (frame, expected)
