"""네이티브 픽셀 x가 실제 출력의 좌우 장면을 바꾸는지 확인한다."""
import subprocess

import pytest

from app.wrappers import binaries, ffmpeg, ffprobe

pytestmark = pytest.mark.integration


@pytest.fixture(scope='module')
def color_halves(tmp_path_factory):
    try:
        exe = binaries.require(binaries.FFMPEG)
    except binaries.BinaryNotFound as exc:
        pytest.skip(str(exc))
    source = tmp_path_factory.mktemp('crop-scenes') / 'halves.mp4'
    subprocess.run([str(exe), '-v', 'error', '-y',
        '-f', 'lavfi', '-i', 'color=red:size=960x1080:rate=30:duration=1',
        '-f', 'lavfi', '-i', 'color=blue:size=960x1080:rate=30:duration=1',
        '-filter_complex', '[0:v][1:v]hstack[v]', '-map', '[v]',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(source)],
        check=True, capture_output=True, timeout=20)
    return exe, source


@pytest.mark.parametrize('x,color_channel', [(0, 0), (1312, 2)])
def test_native_x_selects_matching_left_or_right_scene(color_halves, tmp_path, x, color_channel):
    exe, source = color_halves
    output = tmp_path / 'crop.mp4'
    subprocess.run(ffmpeg.build_encode_args(source, output, ffmpeg.EditOptions(crop_x=x),
        ffprobe.SourceMeta(1920, 1080, 1, False), exe=exe),
        check=True, capture_output=True, timeout=20)
    pixel = subprocess.run([str(exe), '-v', 'error', '-i', str(output), '-frames:v', '1',
        '-vf', 'scale=1:1', '-pix_fmt', 'rgb24', '-f', 'rawvideo', 'pipe:1'],
        check=True, capture_output=True, timeout=10).stdout
    assert pixel[color_channel] > 200
    assert all(value < 30 for index, value in enumerate(pixel) if index != color_channel)
