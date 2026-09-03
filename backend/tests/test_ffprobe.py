"""wrappers.ffprobe: 소스 메타 조회 인자 조립과 JSON 파싱.

오디오 스트림 유무 판정이 특히 중요하다. 아키텍처 8절이 critical로 지목한
"결과물 무음" 결함을 잡으려면 원본에 오디오가 있었는지부터 알아야 한다.
"""

import json

import pytest

from app.wrappers import ffprobe

BASE_JSON = {
    "streams": [
        {
            "index": 0,
            "codec_type": "video",
            "codec_name": "h264",
            "width": 1920,
            "height": 1080,
            "duration": "754.120000",
        },
        {"index": 1, "codec_type": "audio", "codec_name": "aac"},
    ],
    "format": {"duration": "754.166667", "format_name": "mov,mp4,m4a"},
}


def probe_json(**overrides):
    data = json.loads(json.dumps(BASE_JSON))
    data.update(overrides)
    return json.dumps(data)


class TestBuildProbeArgs:
    def test_requests_json_streams_and_format(self):
        args = ffprobe.build_probe_args("/work/abc/source.mp4", exe="/bin/ffprobe")
        assert args[0] == "/bin/ffprobe"
        assert "-print_format" in args and "json" in args
        assert "-show_streams" in args
        assert "-show_format" in args
        assert args[-1] == "/work/abc/source.mp4"

    def test_accepts_path_objects(self, tmp_path):
        args = ffprobe.build_probe_args(tmp_path / "source.mp4")
        assert all(isinstance(a, str) for a in args)

    def test_quiet_output_so_stdout_is_pure_json(self):
        args = ffprobe.build_probe_args("src.mp4")
        assert "-v" in args and "error" in args


class TestParseProbeJson:
    def test_reads_dimensions_and_duration(self):
        meta = ffprobe.parse_probe_json(probe_json())
        assert (meta.width, meta.height) == (1920, 1080)
        assert meta.duration == pytest.approx(754.166667)

    def test_detects_audio_stream(self):
        assert ffprobe.parse_probe_json(probe_json()).has_audio is True

    def test_detects_missing_audio_stream(self):
        data = json.loads(probe_json())
        data["streams"] = [s for s in data["streams"] if s["codec_type"] != "audio"]
        assert ffprobe.parse_probe_json(json.dumps(data)).has_audio is False

    def test_falls_back_to_stream_duration_when_format_missing(self):
        data = json.loads(probe_json())
        data["format"] = {"format_name": "matroska"}
        assert ffprobe.parse_probe_json(json.dumps(data)).duration == pytest.approx(754.12)

    @pytest.mark.parametrize("rotation", [90, -90, 270, -270])
    def test_rotated_video_reports_display_dimensions(self, rotation):
        """세로로 찍힌 영상은 회전 메타 때문에 가로로 보고될 수 있다.

        이 판정이 틀리면 이미 세로인 소스에 세로 크롭을 걸어 ffmpeg가 실패한다.
        """
        data = json.loads(probe_json())
        data["streams"][0]["side_data_list"] = [
            {"side_data_type": "Display Matrix", "rotation": rotation}
        ]
        meta = ffprobe.parse_probe_json(json.dumps(data))
        assert (meta.width, meta.height) == (1080, 1920)

    def test_legacy_rotate_tag_is_honoured(self):
        data = json.loads(probe_json())
        data["streams"][0]["tags"] = {"rotate": "270"}
        meta = ffprobe.parse_probe_json(json.dumps(data))
        assert (meta.width, meta.height) == (1080, 1920)

    def test_180_rotation_keeps_dimensions(self):
        data = json.loads(probe_json())
        data["streams"][0]["side_data_list"] = [{"rotation": 180}]
        meta = ffprobe.parse_probe_json(json.dumps(data))
        assert (meta.width, meta.height) == (1920, 1080)

    def test_missing_video_stream_raises(self):
        data = json.loads(probe_json())
        data["streams"] = [s for s in data["streams"] if s["codec_type"] != "video"]
        with pytest.raises(ffprobe.ProbeError):
            ffprobe.parse_probe_json(json.dumps(data))

    def test_missing_duration_raises(self):
        data = json.loads(probe_json())
        data["format"] = {}
        del data["streams"][0]["duration"]
        with pytest.raises(ffprobe.ProbeError):
            ffprobe.parse_probe_json(json.dumps(data))

    def test_invalid_json_raises_probe_error(self):
        with pytest.raises(ffprobe.ProbeError):
            ffprobe.parse_probe_json("not json at all")


class TestSourceMeta:
    def test_knows_when_source_is_wider_than_9_16(self):
        assert ffprobe.SourceMeta(1920, 1080, 10.0, True).is_wider_than_9_16 is True
        assert ffprobe.SourceMeta(1080, 1920, 10.0, True).is_wider_than_9_16 is False
        # 정확히 9:16인 소스는 크롭할 여백이 없다.
        assert ffprobe.SourceMeta(1080, 1920, 10.0, True).is_wider_than_9_16 is False
