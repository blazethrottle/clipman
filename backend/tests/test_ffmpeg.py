"""wrappers.ffmpeg: 필터그래프 조립, 모드 자동 전환, 진행률 파싱.

기대 명령은 아키텍처 8절 원문을 정본으로 삼아 문자열 단위로 대조한다.
바이너리 없이 검증되므로 어느 기기에서든 이 계약이 깨지면 즉시 드러난다.
"""

import pytest

from app.wrappers import ffmpeg
from app.wrappers.ffprobe import SourceMeta

LANDSCAPE = SourceMeta(width=1920, height=1080, duration=754.0, has_audio=True)
PORTRAIT = SourceMeta(width=1080, height=1920, duration=30.0, has_audio=True)
SQUARE = SourceMeta(width=1080, height=1080, duration=30.0, has_audio=True)
# 9:16(0.5625)보다 좁은 소스. 크롭 폭이 원본 폭을 넘어 ffmpeg가 실패하는 구간이다.
NARROW = SourceMeta(width=500, height=1000, duration=30.0, has_audio=True)


def opts(**kwargs):
    return ffmpeg.EditOptions(**kwargs)


class TestResolveMode:
    def test_landscape_keeps_crop(self):
        assert ffmpeg.resolve_mode(LANDSCAPE, ffmpeg.EncodeMode.CROP) is ffmpeg.EncodeMode.CROP

    @pytest.mark.parametrize("meta", [PORTRAIT, NARROW])
    def test_narrow_source_falls_back_to_pad(self, meta):
        """9:16보다 넓지 않은 소스에 크롭을 걸면 ffmpeg가 실패한다(아키텍처 8절 가드)."""
        assert ffmpeg.resolve_mode(meta, ffmpeg.EncodeMode.CROP) is ffmpeg.EncodeMode.PAD

    def test_square_source_is_still_croppable(self):
        """정사각형은 9:16보다 넓으므로 크롭 여백이 있다. 과도한 PAD 전환을 막는다."""
        assert ffmpeg.resolve_mode(SQUARE, ffmpeg.EncodeMode.CROP) is ffmpeg.EncodeMode.CROP

    def test_pad_request_is_never_upgraded(self):
        assert ffmpeg.resolve_mode(LANDSCAPE, ffmpeg.EncodeMode.PAD) is ffmpeg.EncodeMode.PAD


class TestClampCropX:
    def test_negative_becomes_zero(self):
        assert ffmpeg.clamp_crop_x(-50, LANDSCAPE) == 0

    def test_beyond_right_edge_is_clamped(self):
        # 1920 - floor(1080*9/16) = 1920 - 607 = 1313 -> 짝수로 내림
        assert ffmpeg.clamp_crop_x(99999, LANDSCAPE) == 1312

    def test_rounds_down_to_even_for_chroma_alignment(self):
        assert ffmpeg.clamp_crop_x(101, LANDSCAPE) == 100

    def test_none_stays_none_meaning_centered(self):
        assert ffmpeg.clamp_crop_x(None, LANDSCAPE) is None


class TestClipDuration:
    def test_explicit_range(self):
        assert ffmpeg.clip_duration(LANDSCAPE, opts(trim_start=80.0, trim_end=105.0)) == 25.0

    def test_open_end_runs_to_source_end(self):
        assert ffmpeg.clip_duration(LANDSCAPE, opts(trim_start=754.0 - 4.0)) == pytest.approx(4.0)

    def test_no_trim_is_whole_source(self):
        assert ffmpeg.clip_duration(LANDSCAPE, opts()) == pytest.approx(754.0)

    def test_reversed_range_rejected(self):
        with pytest.raises(ValueError):
            ffmpeg.clip_duration(LANDSCAPE, opts(trim_start=100.0, trim_end=90.0))


class TestBuildEncodeArgs:
    def test_center_crop_matches_architecture_command(self):
        args = ffmpeg.build_encode_args(
            "src.mp4", "out.mp4", opts(trim_start=80.0, trim_end=105.0), LANDSCAPE, exe="ffmpeg"
        )
        vf = args[args.index("-vf") + 1]
        assert vf == "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920,setsar=1"

    def test_offset_crop_uses_numeric_x(self):
        args = ffmpeg.build_encode_args(
            "src.mp4", "out.mp4", opts(crop_x=300), LANDSCAPE, exe="ffmpeg"
        )
        vf = args[args.index("-vf") + 1]
        assert vf == "crop=ih*9/16:ih:300:0,scale=1080:1920,setsar=1"

    def test_pad_mode_matches_architecture_command(self):
        args = ffmpeg.build_encode_args(
            "src.mp4", "out.mp4", opts(mode=ffmpeg.EncodeMode.PAD), LANDSCAPE, exe="ffmpeg"
        )
        vf = args[args.index("-vf") + 1]
        assert vf == (
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
        )

    def test_seek_before_input_and_duration_after(self):
        """-ss를 -i 앞에 두어야 빠른 시크가 되고, -to 대신 -t로 버전 혼선을 막는다."""
        args = ffmpeg.build_encode_args(
            "src.mp4", "out.mp4", opts(trim_start=80.0, trim_end=105.0), LANDSCAPE
        )
        assert args.index("-ss") < args.index("-i") < args.index("-t")
        assert args[args.index("-ss") + 1] == "80.0"
        assert args[args.index("-t") + 1] == "25.0"
        assert "-to" not in args

    def test_no_trim_omits_ss_and_t(self):
        args = ffmpeg.build_encode_args("src.mp4", "out.mp4", opts(), LANDSCAPE)
        assert "-ss" not in args
        assert "-t" not in args

    def test_encode_tail_is_present(self):
        args = ffmpeg.build_encode_args("src.mp4", "out.mp4", opts(), LANDSCAPE)
        joined = " ".join(args)
        for fragment in (
            "-c:v libx264",
            "-crf 23",
            "-preset veryfast",
            "-pix_fmt yuv420p",
            "-movflags +faststart",
            "-c:a aac",
            "-b:a 128k",
            "-progress pipe:1",
        ):
            assert fragment in joined

    def test_error_only_logging_so_stderr_stays_diagnosable(self):
        args = ffmpeg.build_encode_args("src.mp4", "out.mp4", opts(), LANDSCAPE)
        assert "-hide_banner" in args
        assert args[args.index("-loglevel") + 1] == "error"

    def test_output_path_is_last(self):
        args = ffmpeg.build_encode_args("src.mp4", "/out/shorts.mp4", opts(), LANDSCAPE)
        assert args[-1] == "/out/shorts.mp4"

    def test_narrow_source_is_padded_even_when_crop_requested(self):
        args = ffmpeg.build_encode_args("src.mp4", "out.mp4", opts(), PORTRAIT)
        vf = args[args.index("-vf") + 1]
        assert vf.startswith("scale=1080:1920:force_original_aspect_ratio=decrease")

    def test_all_args_are_strings(self):
        args = ffmpeg.build_encode_args(
            "src.mp4", "out.mp4", opts(trim_start=1.5, crop_x=10), LANDSCAPE
        )
        assert all(isinstance(a, str) for a in args)

    def test_blur_pad_is_not_available_in_v1(self):
        """blur_pad는 v1.1 범위다. 실수로 새어 들어오면 실패해야 한다."""
        assert not hasattr(ffmpeg.EncodeMode, "BLUR_PAD")


class TestParseProgressLine:
    def test_out_time_us_is_primary(self):
        assert ffmpeg.parse_progress_line("out_time_us=5000000", clip_len=10.0) == pytest.approx(0.5)

    def test_out_time_string_is_fallback(self):
        assert ffmpeg.parse_progress_line("out_time=00:00:02.500000", clip_len=10.0) == pytest.approx(0.25)

    def test_out_time_ms_is_ignored(self):
        """이름과 달리 마이크로초라 값이 1000배 틀어진다. 쓰지 않는다."""
        assert ffmpeg.parse_progress_line("out_time_ms=5000000", clip_len=10.0) is None

    def test_na_placeholder_is_defended(self):
        assert ffmpeg.parse_progress_line("out_time_us=N/A", clip_len=10.0) is None

    def test_progress_end_reports_complete(self):
        assert ffmpeg.parse_progress_line("progress=end", clip_len=10.0) == 1.0

    def test_unrelated_line_returns_none(self):
        assert ffmpeg.parse_progress_line("bitrate= 2000.0kbits/s", clip_len=10.0) is None

    def test_value_is_capped_at_one(self):
        assert ffmpeg.parse_progress_line("out_time_us=99000000", clip_len=10.0) == 1.0

    def test_zero_clip_length_does_not_divide_by_zero(self):
        assert ffmpeg.parse_progress_line("out_time_us=5000000", clip_len=0.0) is None
