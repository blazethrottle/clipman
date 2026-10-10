"""yt-dlp 어댑터: 메타 조회, 다운로드 명령 조립, 진행률 파싱, 에러 분류.

명령의 정본은 아키텍처 7절, 에러 분류의 정본은 10절이다.
에러 코드는 "동작을 분기시키는 것"만 둔다. 관측되지 않은 오류를 미리 코드화하지 않는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# yt-dlp가 stdout에 찍을 진행률 형식. 세 값 모두 없을 수 있어 파서가 방어한다.
PROGRESS_TEMPLATE = (
    "download:%(progress.downloaded_bytes)s"
    "/%(progress.total_bytes)s"
    "/%(progress.total_bytes_estimate)s"
)

# 봇 차단 폴백에서 시도할 player_client 목록.
# YouTube 변경에 따라 자주 바뀌므로 저장소에서 이 한 곳에만 둔다(아키텍처 15절 재심 결론).
PLAYER_CLIENT_FALLBACKS: tuple[str, ...] = ("tv", "web_safari")

# 브라우저 쿠키 추출 순서. 쿠키 파일이 없을 때만 쓰는 2순위 폴백이다.
BROWSER_COOKIE_SOURCES: dict[str, tuple[str, ...]] = {
    "darwin": ("chrome", "safari"),
    "win32": ("chrome",),
    "linux": ("chrome", "firefox"),
}

_QUALITY_PATTERN = re.compile(r"^(\d{2,4})p?$")
_HTTP_5XX_PATTERN = re.compile(r"http error 5\d\d")
_EMPTY_VALUES = {"", "na", "n/a", "none", "null"}


@dataclass(frozen=True)
class VideoMeta:
    title: str
    duration_sec: int
    width: int | None = None
    height: int | None = None
    thumbnail_url: str | None = None
    uploader: str | None = None
    qualities: list[str] = field(default_factory=list)


def build_metadata_args(url: str, exe: Path | str = "yt-dlp") -> list[str]:
    """-J는 JSON 덤프 1회로 제목, 길이, 썸네일, 화질 목록을 모두 준다. 다운로드는 하지 않는다."""
    return [str(exe), "-J", "--no-warnings", str(url)]


def qualities_from_formats(info: dict) -> list[str]:
    """UI가 진짜 선택지를 주도록 실제 사용 가능한 화질만 추린다(오디오 전용 포맷 제외)."""
    heights: set[int] = set()
    for fmt in info.get("formats") or []:
        if (fmt.get("vcodec") or "none") == "none":
            continue
        height = fmt.get("height")
        if not height:
            continue
        try:
            heights.add(int(height))
        except (TypeError, ValueError):
            continue
    return [f"{h}p" for h in sorted(heights, reverse=True)]


def metadata_from_info(info: dict) -> VideoMeta:
    return VideoMeta(
        title=info.get("title") or "",
        duration_sec=int(info.get("duration") or 0),
        width=info.get("width"),
        height=info.get("height"),
        thumbnail_url=info.get("thumbnail"),
        uploader=info.get("uploader"),
        qualities=qualities_from_formats(info),
    )


def format_selector(quality: str | None) -> str:
    if not quality or quality == "best":
        return "bestvideo+bestaudio/best"
    match = _QUALITY_PATTERN.match(str(quality))
    if not match:
        raise ValueError(f"알 수 없는 화질 값입니다: {quality!r}")
    return f"bestvideo[height<={match.group(1)}]+bestaudio/best"


def build_download_args(
    url: str,
    quality: str | None,
    work_dir: Path | str,
    ffmpeg_dir: Path | str | None = None,
    cookie_file: Path | str | None = None,
    cookies_from_browser: str | None = None,
    player_client: str | None = None,
    exe: Path | str = "yt-dlp",
) -> list[str]:
    """원본을 work/<job>/source.<ext>로 받는다. 원본 보존이 재편집의 전제다."""
    args = [
        str(exe),
        "-f",
        format_selector(quality),
        "--merge-output-format",
        "mp4",
        "-o",
        str(Path(work_dir) / "source.%(ext)s"),
        "--newline",
        "--progress-template",
        PROGRESS_TEMPLATE,
        "--no-warnings",
    ]
    if ffmpeg_dir:
        args += ["--ffmpeg-location", str(ffmpeg_dir)]

    # 쿠키 파일이 1순위다. 브라우저 추출은 실행 중 잠금과 권한 프롬프트 때문에 2순위다.
    if cookie_file:
        args += ["--cookies", str(cookie_file)]
    elif cookies_from_browser:
        args += ["--cookies-from-browser", str(cookies_from_browser)]

    if player_client:
        args += ["--extractor-args", f"youtube:player_client={player_client}"]

    args.append(str(url))
    return args


def build_update_args(exe: Path | str = "yt-dlp") -> list[str]:
    """실행파일 자체 갱신. 파이썬 재시작이 필요 없다."""
    return [str(exe), "-U"]


def _to_number(raw: str) -> float | None:
    value = (raw or "").strip()
    if value.lower() in _EMPTY_VALUES:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_progress_line(line: str) -> float | None:
    """진행률(0.0~1.0). total_bytes가 없으면 total_bytes_estimate로 폴백한다."""
    text = (line or "").strip()
    if not text.startswith("download:"):
        return None

    parts = text[len("download:") :].split("/")
    if len(parts) != 3:
        return None

    downloaded = _to_number(parts[0])
    total = _to_number(parts[1])
    if total is None:
        total = _to_number(parts[2])
    if downloaded is None or not total:
        return None

    return max(0.0, min(1.0, downloaded / total))


def classify_error(text: str) -> str:
    """stdout/stderr 문자열에서 동작 분기용 에러 코드를 뽑는다(아키텍처 10절)."""
    lowered = (text or "").lower()

    if "not a bot" in lowered or "sign in to confirm" in lowered:
        return "BOT_BLOCK"
    if "requested format" in lowered and "not available" in lowered:
        return "FORMAT_UNAVAILABLE"
    if (
        any(
            token in lowered
            for token in ("timed out", "timeout", "connection", "network is unreachable")
        )
        or _HTTP_5XX_PATTERN.search(lowered)
    ):
        return "NETWORK"
    return "DOWNLOAD_FAILED"
