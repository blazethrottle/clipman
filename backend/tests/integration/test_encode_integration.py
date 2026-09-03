"""M1-6: 번들 ffmpeg 실물로 세 가지를 1회 검증한다 (아키텍처 15절 재심 1번).

검증 대상: 출력 해상도, 클립 길이, **오디오 스트림 존재**.
오디오 단언이 이 파일의 존재 이유다. 무음 mp4는 v1 품질의 하한선을 깨는 결함이고,
합성 픽스처에 sine 입력이 없으면 원리적으로 잡을 수 없다.

실행 방법 (bin/ 조달 후):
    ./.venv/bin/pytest -m integration
"""

from __future__ import annotations

import subprocess

import pytest

from app.wrappers import binaries, ffmpeg, ffprobe

pytestmark = pytest.mark.integration

CLIP_SECONDS = 5
SOURCE_WIDTH, SOURCE_HEIGHT = 1920, 1080


def _binary_or_skip(name: str):
    try:
        return binaries.require(name)
    except binaries.BinaryNotFound as exc:
        pytest.skip(f"{name} 미조달: {exc}")


@pytest.fixture(scope="module")
def ffmpeg_exe():
    return _binary_or_skip(binaries.FFMPEG)


@pytest.fixture(scope="module")
def ffprobe_exe():
    return _binary_or_skip(binaries.FFPROBE)


@pytest.fixture(scope="module")
def synthetic_source(tmp_path_factory, ffmpeg_exe):
    """오디오를 포함한 합성 영상. sine 입력이 없으면 무음 결함을 못 잡는다."""
    src = tmp_path_factory.mktemp("fixtures") / "source.mp4"
    subprocess.run(
        [
            str(ffmpeg_exe), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"testsrc=size={SOURCE_WIDTH}x{SOURCE_HEIGHT}:rate=30:duration={CLIP_SECONDS}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={CLIP_SECONDS}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            str(src),
        ],
        check=True,
        capture_output=True,
    )
    return src


def probe(ffprobe_exe, path) -> ffprobe.SourceMeta:
    result = subprocess.run(
        ffprobe.build_probe_args(path, exe=ffprobe_exe),
        check=True,
        capture_output=True,
        text=True,
    )
    return ffprobe.parse_probe_json(result.stdout)


def test_fixture_has_audio(synthetic_source, ffprobe_exe):
    """픽스처 자체가 오디오를 갖는지 먼저 확인한다. 아니면 아래 단언이 무의미해진다."""
    meta = probe(ffprobe_exe, synthetic_source)
    assert meta.has_audio is True
    assert (meta.width, meta.height) == (SOURCE_WIDTH, SOURCE_HEIGHT)


@pytest.mark.parametrize("mode", [ffmpeg.EncodeMode.CROP, ffmpeg.EncodeMode.PAD])
def test_encode_produces_vertical_clip_with_audio(
    mode, synthetic_source, ffmpeg_exe, ffprobe_exe, tmp_path
):
    source_meta = probe(ffprobe_exe, synthetic_source)
    out = tmp_path / f"shorts_{mode.value}.mp4"
    opts = ffmpeg.EditOptions(trim_start=1.0, trim_end=3.0, mode=mode)

    completed = subprocess.run(
        ffmpeg.build_encode_args(synthetic_source, out, opts, source_meta, exe=ffmpeg_exe),
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    # 종료코드 0이어도 산출물이 없거나 비어 있으면 실패로 본다(아키텍처 10절).
    assert out.exists() and out.stat().st_size > 0

    result_meta = probe(ffprobe_exe, out)
    assert (result_meta.width, result_meta.height) == (1080, 1920)
    assert result_meta.duration == pytest.approx(2.0, abs=0.2)
    assert result_meta.has_audio is True, "세로 변환 후 오디오가 사라졌다"


def test_narrow_source_is_padded_not_failed(ffmpeg_exe, ffprobe_exe, tmp_path):
    """이미 세로인 소스에 CROP을 요청해도 자동 PAD 전환으로 성공해야 한다."""
    narrow = tmp_path / "narrow.mp4"
    subprocess.run(
        [
            str(ffmpeg_exe), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"testsrc=size=720x1280:rate=30:duration={CLIP_SECONDS}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={CLIP_SECONDS}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            str(narrow),
        ],
        check=True,
        capture_output=True,
    )

    meta = probe(ffprobe_exe, narrow)
    assert ffmpeg.resolve_mode(meta, ffmpeg.EncodeMode.CROP) is ffmpeg.EncodeMode.PAD

    out = tmp_path / "narrow_out.mp4"
    completed = subprocess.run(
        ffmpeg.build_encode_args(narrow, out, ffmpeg.EditOptions(), meta, exe=ffmpeg_exe),
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    result_meta = probe(ffprobe_exe, out)
    assert (result_meta.width, result_meta.height) == (1080, 1920)
    assert result_meta.has_audio is True


def test_progress_output_is_parseable(synthetic_source, ffmpeg_exe, ffprobe_exe, tmp_path):
    """진행률 파서가 실제 -progress 출력과 맞물리는지 확인한다(out_time_us 함정 검증)."""
    source_meta = probe(ffprobe_exe, synthetic_source)
    opts = ffmpeg.EditOptions(trim_start=0.0, trim_end=2.0)
    clip_len = ffmpeg.clip_duration(source_meta, opts)

    completed = subprocess.run(
        ffmpeg.build_encode_args(
            synthetic_source, tmp_path / "progress.mp4", opts, source_meta, exe=ffmpeg_exe
        ),
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    values = [
        v
        for v in (ffmpeg.parse_progress_line(line, clip_len) for line in completed.stdout.splitlines())
        if v is not None
    ]
    assert values, "진행률을 한 건도 파싱하지 못했다"
    assert all(0.0 <= v <= 1.0 for v in values)
    assert values[-1] == pytest.approx(1.0, abs=0.05)
