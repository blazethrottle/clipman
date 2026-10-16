"""YouTube 원본 선택과 확보 파일의 로컬 시각을 구분한다."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit


def canonical_video_url(video_id: str, url: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("영상 식별자가 올바르지 않습니다.")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.username or parsed.password
            or parsed.port not in (None, 443)):
        raise ValueError("YouTube HTTPS 영상 주소가 필요합니다.")
    if parsed.hostname == "youtu.be":
        actual_id = parsed.path.removeprefix("/")
    elif parsed.hostname in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            values = parse_qs(parsed.query).get("v", [])
            actual_id = values[0] if len(values) == 1 else ""
        elif parsed.path.startswith("/shorts/"):
            actual_id = parsed.path.removeprefix("/shorts/")
        else:
            actual_id = ""
    else:
        actual_id = ""
    if actual_id != video_id:
        raise ValueError("주소와 선택한 영상이 일치하지 않습니다.")
    return f"https://www.youtube.com/watch?v={video_id}"


def _validate_range(start: float, end: float) -> None:
    if not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end:
        raise ValueError("구간은 유한한 초 단위이며 0 <= 시작 < 끝이어야 합니다.")


@dataclass(frozen=True)
class Selection:
    video_id: str
    url: str
    start_sec: float
    end_sec: float

    def __post_init__(self) -> None:
        _validate_range(self.start_sec, self.end_sec)
        object.__setattr__(self, "url", canonical_video_url(self.video_id, self.url))

    @property
    def duration_sec(self) -> float:
        return self.end_sec - self.start_sec


@dataclass(frozen=True)
class SourceTimeline:
    origin_start_sec: float
    duration_sec: float

    def __post_init__(self) -> None:
        _validate_range(self.origin_start_sec, self.origin_start_sec + self.duration_sec)

    def original_range(
        self, start: float | None, end: float | None
    ) -> tuple[float, float]:
        start = 0.0 if start is None else start
        end = self.duration_sec if end is None else end
        _validate_range(start, end)
        if end > self.duration_sec:
            raise ValueError("편집 구간이 확보한 영상 길이를 초과합니다.")
        return self.origin_start_sec + start, self.origin_start_sec + end
