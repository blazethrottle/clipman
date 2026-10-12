import math

import pytest

from app import capture
from app.wrappers import ytdlp


VIDEO_ID = "BaW_jenozKc"


@pytest.mark.parametrize("url", [
    f"https://www.youtube.com/watch?v={VIDEO_ID}&list=ignore",
    f"https://youtu.be/{VIDEO_ID}?t=120",
    f"https://www.youtube.com/shorts/{VIDEO_ID}",
])
def test_selection_preserves_video_and_original_times(url):
    selected = capture.Selection(VIDEO_ID, url, 120.25, 135.5)
    assert selected.url == f"https://www.youtube.com/watch?v={VIDEO_ID}"
    assert selected.duration_sec == 15.25


@pytest.mark.parametrize("url", [
    "https://www.youtube.com.evil.test/watch?v=BaW_jenozKc",
    "file:///tmp/video.mp4", "http://localhost/watch?v=BaW_jenozKc",
    "https://user:pass@www.youtube.com/watch?v=BaW_jenozKc",
    "https://www.youtube.com:444/watch?v=BaW_jenozKc",
    "https://www.youtube.com/watch?v=abcdefghijk",
    "https://youtu.be/BaW_jenozKc/extra",
])
def test_invalid_or_mismatched_video_is_rejected(url):
    with pytest.raises(ValueError):
        capture.Selection(VIDEO_ID, url, 0, 10)


@pytest.mark.parametrize("start,end", [(-1, 1), (1, 1), (3, 1), (math.nan, 1), (0, math.inf)])
def test_invalid_selection_times_are_rejected(start, end):
    with pytest.raises(ValueError):
        capture.Selection(VIDEO_ID, f"https://youtu.be/{VIDEO_ID}", start, end)


def test_local_times_map_to_original_instead_of_youtube_zero():
    timeline = capture.SourceTimeline(origin_start_sec=120.25, duration_sec=15.25)
    assert timeline.original_range(2, 5) == (122.25, 125.25)
    assert timeline.original_range(None, None) == (120.25, 135.5)


@pytest.mark.parametrize("start,end", [(-1, 2), (5, 2), (2, 2), (0, 16), (math.nan, 2), (0, math.inf)])
def test_edit_cannot_escape_acquired_file(start, end):
    with pytest.raises(ValueError):
        capture.SourceTimeline(120, 15).original_range(start, end)


@pytest.mark.parametrize("origin,duration", [(-1, 15), (math.nan, 15), (0, 0), (0, math.inf)])
def test_invalid_acquired_timeline_is_rejected(origin, duration):
    with pytest.raises(ValueError):
        capture.SourceTimeline(origin, duration)


def test_section_download_uses_canonical_video_and_precise_cut(tmp_path):
    selected = capture.Selection(VIDEO_ID, f"https://youtu.be/{VIDEO_ID}", 120.25, 135.5)
    args = ytdlp.build_download_args(selected.url, "1080p", tmp_path, selection=selected)
    assert args[args.index("--download-sections") + 1] == "*120.25-135.5"
    assert "--force-keyframes-at-cuts" in args
    assert "--no-playlist" in args
    assert args[-1] == selected.url


def test_section_cannot_be_used_with_another_video(tmp_path):
    selected = capture.Selection(VIDEO_ID, f"https://youtu.be/{VIDEO_ID}", 1, 2)
    with pytest.raises(ValueError):
        ytdlp.build_download_args("https://youtu.be/abcdefghijk", "best", tmp_path, selection=selected)


def test_existing_whole_download_does_not_gain_a_section(tmp_path):
    args = ytdlp.build_download_args("URL", "best", tmp_path)
    assert "--download-sections" not in args


def test_long_video_section_keeps_fractional_seconds(tmp_path):
    selected = capture.Selection(VIDEO_ID, f"https://youtu.be/{VIDEO_ID}", 12345.125, 12346.875)
    args = ytdlp.build_download_args(selected.url, "best", tmp_path, selection=selected)
    assert args[args.index("--download-sections") + 1] == "*12345.125-12346.875"
