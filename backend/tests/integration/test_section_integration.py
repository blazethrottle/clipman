"""선택 구간 플래그를 통제된 HTTP 영상으로 실행한다. YouTube 검증이 아니다."""

import subprocess
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from app.capture import Selection
from app.wrappers import binaries, ffprobe, ytdlp


pytestmark = pytest.mark.integration


def test_real_section_download_keeps_selected_scene_and_audio(tmp_path):
    try:
        ffmpeg_exe = binaries.require(binaries.FFMPEG)
        ffprobe_exe = binaries.require(binaries.FFPROBE)
        ytdlp_exe = binaries.require(binaries.YTDLP)
    except binaries.BinaryNotFound as exc:
        pytest.skip(str(exc))

    # 0~2초 빨강, 2~4초 파랑. 2.25~3.75초 선택은 파랑이어야 한다.
    source = tmp_path / "fixture.mp4"
    subprocess.run([
        str(ffmpeg_exe), "-v", "error", "-y",
        "-f", "lavfi", "-i", "color=red:size=320x180:rate=30:duration=2",
        "-f", "lavfi", "-i", "color=blue:size=320x180:rate=30:duration=2",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
        "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-c:a", "aac",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest", str(source),
    ], check=True, capture_output=True, timeout=30)

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(tmp_path)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    work = tmp_path / "download"
    work.mkdir()
    selected = Selection("BaW_jenozKc", "https://youtu.be/BaW_jenozKc", 2.25, 3.75)
    args = ytdlp.build_download_args(selected.url, "best", work, ffmpeg_exe.parent,
                                     exe=ytdlp_exe, selection=selected)
    # YouTube 획득은 별도 관문이다. 이 검사는 소유한 합성 영상으로 명령만 실행한다.
    args[-1] = f"http://127.0.0.1:{server.server_port}/fixture.mp4"
    args[1:1] = ["--ignore-config", "--proxy", ""]
    try:
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=60)
        assert result.returncode == 0, result.stderr
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)

    outputs = list(work.glob("source.*"))
    assert len(outputs) == 1
    probe = subprocess.run(ffprobe.build_probe_args(outputs[0], exe=ffprobe_exe),
                           check=True, capture_output=True, text=True, timeout=10)
    meta = ffprobe.parse_probe_json(probe.stdout)
    assert meta.duration == pytest.approx(1.5, abs=.15)
    assert meta.has_audio
    # 종료코드와 길이 외에 실제 선택한 장면인지도 확인한다.
    pixel = subprocess.run([
        str(ffmpeg_exe), "-v", "error", "-ss", "0.1", "-i", str(outputs[0]),
        "-frames:v", "1", "-vf", "scale=1:1", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1",
    ], check=True, capture_output=True, timeout=10).stdout
    red, green, blue = pixel
    assert blue > 200 and red < 30 and green < 30
