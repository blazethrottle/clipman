"""2026-10-12 검수에서 재현한 입력 및 외부 도구 계약 회귀 검사."""
import json

import pytest

from app.wrappers import ffmpeg, ffprobe, ytdlp


@pytest.mark.parametrize("start,end", [(-1, 1), (3, 4), (1, 3), (0, 0), (float('nan'), 1), (0, float('inf'))])
def test_invalid_trim_never_reaches_encoder(start, end):
    with pytest.raises(ValueError):
        ffmpeg.build_encode_args('in.mp4', 'out.mp4', ffmpeg.EditOptions(trim_start=start, trim_end=end), ffprobe.SourceMeta(640, 360, 2, True))


@pytest.mark.parametrize("duration", [0, -1, float('nan'), float('inf')])
def test_invalid_source_duration_rejected_without_explicit_trim(duration):
    with pytest.raises(ValueError):
        ffmpeg.build_encode_args('in.mp4', 'out.mp4', ffmpeg.EditOptions(), ffprobe.SourceMeta(640, 360, duration, True))


def test_valid_clip_keeps_subsecond_precision():
    assert ffmpeg.clip_duration(ffprobe.SourceMeta(640, 360, 2, True), ffmpeg.EditOptions(trim_start=0.25, trim_end=1.75)) == 1.5


@pytest.mark.parametrize('url', ['https://www.youtube.com/playlist?list=PLabc', 'https://youtube.com/watch?list=PLabc'])
def test_playlist_only_url_is_rejected(url, tmp_path):
    with pytest.raises(ValueError):
        ytdlp.build_metadata_args(url)
    with pytest.raises(ValueError):
        ytdlp.build_download_args(url, 'best', tmp_path)


def test_watch_url_with_playlist_stays_single_video(tmp_path):
    url = 'https://www.youtube.com/watch?v=abcdefghijk&list=PLabc'
    for args in (ytdlp.build_metadata_args(url), ytdlp.build_download_args(url, 'best', tmp_path)):
        assert '--no-playlist' in args
        assert '--ignore-config' in args
        assert args[-1] == url


@pytest.mark.parametrize('duration', ['inf', 'nan', '0', '-1'])
def test_probe_rejects_invalid_duration(duration):
    with pytest.raises(ffprobe.ProbeError):
        ffprobe.parse_probe_json(json.dumps({'format': {'duration': duration}, 'streams': [{'codec_type': 'video', 'width': 640, 'height': 360}]}))


def test_probe_rejects_header_without_streams():
    with pytest.raises(ffprobe.ProbeError):
        ffprobe.parse_probe_json('{"streams": [], "format": {"size": "261"}}')
