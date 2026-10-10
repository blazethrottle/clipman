"""wrappers.ytdlp: 메타 조회, 다운로드 인자 조립, 진행률 파싱, 에러 분류.

에러 분류는 "동작을 분기시키는 소수 코드"만 둔다는 아키텍처 10절 원칙을 따른다.
분류가 틀리면 봇 차단인데 그냥 실패로 끝나거나, 네트워크 문제인데 재시도를 못 한다.
"""

import json

import pytest

from app.wrappers import ytdlp

INFO = {
    "title": "무대 직캠 4K",
    "duration": 754,
    "thumbnail": "https://i.example/thumb.jpg",
    "uploader": "채널명",
    "width": 1920,
    "height": 1080,
    "formats": [
        {"format_id": "140", "vcodec": "none", "acodec": "mp4a", "height": None},
        {"format_id": "160", "vcodec": "avc1", "acodec": "none", "height": 144},
        {"format_id": "137", "vcodec": "avc1", "acodec": "none", "height": 1080},
        {"format_id": "136", "vcodec": "avc1", "acodec": "none", "height": 720},
        {"format_id": "248", "vcodec": "vp9", "acodec": "none", "height": 1080},
        {"format_id": "storyboard", "vcodec": "none", "acodec": "none", "height": None},
    ],
}


class TestBuildMetadataArgs:
    def test_dumps_single_json(self):
        args = ytdlp.build_metadata_args("https://youtu.be/abc", exe="/bin/yt-dlp")
        assert args[0] == "/bin/yt-dlp"
        assert "-J" in args
        assert "--no-warnings" in args
        assert args[-1] == "https://youtu.be/abc"

    def test_does_not_download(self):
        args = ytdlp.build_metadata_args("https://youtu.be/abc")
        assert "-o" not in args


class TestQualitiesFromFormats:
    def test_descending_unique_heights(self):
        assert ytdlp.qualities_from_formats(INFO) == ["1080p", "720p", "144p"]

    def test_audio_only_formats_excluded(self):
        assert "None" not in " ".join(ytdlp.qualities_from_formats(INFO))

    def test_empty_formats_yield_empty_list(self):
        assert ytdlp.qualities_from_formats({"formats": []}) == []

    def test_missing_formats_key_is_tolerated(self):
        assert ytdlp.qualities_from_formats({}) == []


class TestMetadataFromInfo:
    def test_extracts_fields_ui_needs(self):
        meta = ytdlp.metadata_from_info(INFO)
        assert meta.title == "무대 직캠 4K"
        assert meta.duration_sec == 754
        assert meta.thumbnail_url == "https://i.example/thumb.jpg"
        assert meta.uploader == "채널명"
        assert meta.qualities == ["1080p", "720p", "144p"]

    def test_parses_raw_json_text(self):
        meta = ytdlp.metadata_from_info(json.loads(json.dumps(INFO)))
        assert meta.width == 1920 and meta.height == 1080

    def test_missing_optional_fields_do_not_crash(self):
        meta = ytdlp.metadata_from_info({"title": "제목만 있음"})
        assert meta.duration_sec == 0
        assert meta.thumbnail_url is None
        assert meta.qualities == []


class TestBuildDownloadArgs:
    def test_quality_becomes_height_capped_selector(self, tmp_path):
        args = ytdlp.build_download_args("URL", "1080p", tmp_path)
        selector = args[args.index("-f") + 1]
        assert selector == "bestvideo[height<=1080]+bestaudio/best"

    def test_best_quality_has_no_height_cap(self, tmp_path):
        selector = ytdlp.build_download_args("URL", "best", tmp_path)[
            ytdlp.build_download_args("URL", "best", tmp_path).index("-f") + 1
        ]
        assert selector == "bestvideo+bestaudio/best"

    def test_output_template_preserves_original_in_work_dir(self, tmp_path):
        args = ytdlp.build_download_args("URL", "best", tmp_path)
        template = args[args.index("-o") + 1]
        assert template == str(tmp_path / "source.%(ext)s")

    def test_merges_to_mp4(self, tmp_path):
        args = ytdlp.build_download_args("URL", "best", tmp_path)
        assert args[args.index("--merge-output-format") + 1] == "mp4"

    def test_progress_is_line_buffered_and_templated(self, tmp_path):
        args = ytdlp.build_download_args("URL", "best", tmp_path)
        assert "--newline" in args
        template = args[args.index("--progress-template") + 1]
        assert template.startswith("download:")
        assert "downloaded_bytes" in template
        assert "total_bytes_estimate" in template

    def test_bundled_ffmpeg_location_is_passed(self, tmp_path):
        args = ytdlp.build_download_args("URL", "best", tmp_path, ffmpeg_dir="/app/bin")
        assert args[args.index("--ffmpeg-location") + 1] == "/app/bin"

    def test_cookie_file_is_first_class_fallback(self, tmp_path):
        args = ytdlp.build_download_args("URL", "best", tmp_path, cookie_file="/home/me/c.txt")
        assert args[args.index("--cookies") + 1] == "/home/me/c.txt"
        assert "--cookies-from-browser" not in args

    def test_browser_cookies_are_second_fallback(self, tmp_path):
        args = ytdlp.build_download_args("URL", "best", tmp_path, cookies_from_browser="safari")
        assert args[args.index("--cookies-from-browser") + 1] == "safari"

    def test_cookie_file_wins_when_both_given(self, tmp_path):
        """쿠키 파일 1순위는 아키텍처 7절 확정 사항이다."""
        args = ytdlp.build_download_args(
            "URL", "best", tmp_path, cookie_file="/c.txt", cookies_from_browser="chrome"
        )
        assert "--cookies" in args
        assert "--cookies-from-browser" not in args

    def test_player_client_fallback_is_expressed_as_extractor_args(self, tmp_path):
        args = ytdlp.build_download_args("URL", "best", tmp_path, player_client="tv")
        assert args[args.index("--extractor-args") + 1] == "youtube:player_client=tv"

    def test_url_is_last(self, tmp_path):
        assert ytdlp.build_download_args("https://youtu.be/x", "best", tmp_path)[-1] == "https://youtu.be/x"

    def test_all_args_are_strings(self, tmp_path):
        args = ytdlp.build_download_args("URL", "1080p", tmp_path, ffmpeg_dir=tmp_path)
        assert all(isinstance(a, str) for a in args)


class TestPlayerClientFallbacks:
    def test_declared_in_this_module_only(self):
        """자주 바뀌는 값이라 한 곳에만 둔다(아키텍처 15절 재심 결론)."""
        assert isinstance(ytdlp.PLAYER_CLIENT_FALLBACKS, tuple)
        assert len(ytdlp.PLAYER_CLIENT_FALLBACKS) >= 1


class TestParseProgressLine:
    def test_uses_total_bytes_when_known(self):
        assert ytdlp.parse_progress_line("download:2500/10000/NA") == pytest.approx(0.25)

    def test_falls_back_to_estimate(self):
        assert ytdlp.parse_progress_line("download:2500/NA/10000") == pytest.approx(0.25)

    def test_unknown_total_returns_none(self):
        assert ytdlp.parse_progress_line("download:2500/NA/NA") is None

    def test_non_progress_line_returns_none(self):
        assert ytdlp.parse_progress_line("[youtube] Extracting URL") is None

    def test_capped_at_one(self):
        assert ytdlp.parse_progress_line("download:12000/10000/NA") == 1.0

    def test_handles_none_literal_from_ytdlp(self):
        assert ytdlp.parse_progress_line("download:100/None/None") is None


class TestClassifyError:
    def test_bot_block(self):
        text = "ERROR: [youtube] abc: Sign in to confirm you're not a bot"
        assert ytdlp.classify_error(text) == "BOT_BLOCK"

    def test_format_unavailable(self):
        assert ytdlp.classify_error("ERROR: Requested format is not available") == "FORMAT_UNAVAILABLE"

    @pytest.mark.parametrize(
        "text",
        [
            "ERROR: unable to download video data: <urlopen error timed out>",
            "ERROR: Unable to download webpage: Connection reset by peer",
            "ERROR: HTTP Error 503: Service Unavailable",
        ],
    )
    def test_network(self, text):
        assert ytdlp.classify_error(text) == "NETWORK"

    def test_unknown_failure_is_generic(self):
        assert ytdlp.classify_error("ERROR: something entirely new") == "DOWNLOAD_FAILED"

    def test_empty_stderr_is_generic(self):
        assert ytdlp.classify_error("") == "DOWNLOAD_FAILED"


class TestBuildUpdateArgs:
    def test_self_update(self):
        assert ytdlp.build_update_args(exe="/app/bin/yt-dlp") == ["/app/bin/yt-dlp", "-U"]
