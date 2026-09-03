"""ffmpeg 어댑터: 세로 9:16 변환 명령 조립과 진행률 파싱.

명령의 정본은 아키텍처 8절이다. 이 모듈은 그 명령을 문자열로 재현할 뿐이고,
바뀔 때는 문서를 먼저 고친다.

v1 모드는 CROP과 PAD 둘뿐이다. blur_pad(흐린 배경)는 v1.1 범위이므로 넣지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import gcd
from pathlib import Path

from .ffprobe import SourceMeta


class EncodeMode(str, Enum):
    CROP = "crop"  # 9:16 영역만 잘라내기 (기본)
    PAD = "pad"  # 원본 유지 + 단색 레터박스


@dataclass
class EditOptions:
    trim_start: float | None = None  # 초. None이면 처음부터
    trim_end: float | None = None  # 초. None이면 끝까지
    mode: EncodeMode = EncodeMode.CROP
    crop_x: int | None = None  # CROP의 가로 오프셋(원본 픽셀). None이면 중앙
    target_w: int = 1080
    target_h: int = 1920


# 아키텍처 8절 "공통 인코딩 꼬리"
ENCODE_TAIL: tuple[str, ...] = (
    "-c:v", "libx264",
    "-crf", "23",
    "-preset", "veryfast",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    "-c:a", "aac",
    "-b:a", "128k",
    "-progress", "pipe:1",
)


def _target_ratio(target_w: int, target_h: int) -> tuple[int, int]:
    """1080x1920 -> (9, 16). 필터 문자열을 문서 원문과 같은 모양으로 유지한다."""
    divisor = gcd(target_w, target_h)
    return target_w // divisor, target_h // divisor


def resolve_mode(
    meta: SourceMeta,
    requested: EncodeMode,
    target_w: int = 1080,
    target_h: int = 1920,
) -> EncodeMode:
    """좁은 소스에 CROP을 걸면 ffmpeg가 실패하므로 PAD로 자동 전환한다(아키텍처 8절 가드)."""
    if requested is EncodeMode.PAD:
        return EncodeMode.PAD
    is_wider_than_target = meta.width * target_h > meta.height * target_w
    return EncodeMode.CROP if is_wider_than_target else EncodeMode.PAD


def crop_width(meta: SourceMeta, target_w: int = 1080, target_h: int = 1920) -> int:
    """잘라낼 가로 폭(픽셀). ffmpeg는 표현식으로 계산하지만 X 클램프에는 수치가 필요하다."""
    ratio_w, ratio_h = _target_ratio(target_w, target_h)
    return int(meta.height * ratio_w // ratio_h)


def clamp_crop_x(
    crop_x: int | None,
    meta: SourceMeta,
    target_w: int = 1080,
    target_h: int = 1920,
) -> int | None:
    """None은 중앙 정렬을 뜻하므로 그대로 둔다. 값이 있으면 화면 밖으로 나가지 않게 가둔다."""
    if crop_x is None:
        return None
    max_x = max(0, meta.width - crop_width(meta, target_w, target_h))
    clamped = max(0, min(int(crop_x), max_x))
    return clamped - (clamped % 2)  # 크로마 정렬을 위해 짝수로 내린다


def clip_duration(meta: SourceMeta, opts: EditOptions) -> float:
    start = opts.trim_start or 0.0
    end = meta.duration if opts.trim_end is None else opts.trim_end
    if end <= start:
        raise ValueError(f"끝 지점({end})이 시작 지점({start})보다 뒤여야 합니다.")
    return round(end - start, 6)


def _filtergraph(mode: EncodeMode, meta: SourceMeta, opts: EditOptions) -> str:
    ratio_w, ratio_h = _target_ratio(opts.target_w, opts.target_h)
    if mode is EncodeMode.CROP:
        crop_x = clamp_crop_x(opts.crop_x, meta, opts.target_w, opts.target_h)
        offset = f"(iw-ih*{ratio_w}/{ratio_h})/2" if crop_x is None else str(crop_x)
        return (
            f"crop=ih*{ratio_w}/{ratio_h}:ih:{offset}:0,"
            f"scale={opts.target_w}:{opts.target_h},setsar=1"
        )
    return (
        f"scale={opts.target_w}:{opts.target_h}:force_original_aspect_ratio=decrease,"
        f"pad={opts.target_w}:{opts.target_h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
    )


def build_encode_args(
    src: Path | str,
    dst: Path | str,
    opts: EditOptions,
    meta: SourceMeta,
    exe: Path | str = "ffmpeg",
) -> list[str]:
    """구간 컷 + 세로 변환 명령. -ss를 -i 앞에 두어 빠른 시크와 프레임 정확성을 함께 얻는다."""
    mode = resolve_mode(meta, opts.mode, opts.target_w, opts.target_h)
    args = [str(exe), "-hide_banner", "-loglevel", "error", "-y"]

    if opts.trim_start:
        args += ["-ss", str(float(opts.trim_start))]
    args += ["-i", str(src)]
    if opts.trim_start is not None or opts.trim_end is not None:
        # -to가 아니라 -t를 쓴다. 버전별 타임라인 해석 차이를 피하기 위해서다.
        args += ["-t", str(float(clip_duration(meta, opts)))]

    args += ["-vf", _filtergraph(mode, meta, opts)]
    args += list(ENCODE_TAIL)
    args.append(str(dst))
    return args


def _hms_to_seconds(value: str) -> float | None:
    parts = value.split(":")
    if len(parts) != 3:
        return None
    try:
        hours, minutes, seconds = (float(p) for p in parts)
    except ValueError:
        return None
    return hours * 3600 + minutes * 60 + seconds


def parse_progress_line(line: str, clip_len: float) -> float | None:
    """-progress pipe:1 출력 한 줄에서 진행률(0.0~1.0)을 얻는다.

    out_time_ms는 이름과 달리 마이크로초라 1000배 어긋난다. 쓰지 않는다.
    """
    text = (line or "").strip()
    if text == "progress=end":
        return 1.0

    key, separator, raw = text.partition("=")
    if not separator or key not in ("out_time_us", "out_time"):
        return None
    if clip_len <= 0:
        return None

    raw = raw.strip()
    if not raw or raw.upper() == "N/A":
        return None

    if key == "out_time_us":
        try:
            seconds = float(raw) / 1_000_000
        except ValueError:
            return None
    else:
        seconds = _hms_to_seconds(raw)
        if seconds is None:
            return None

    return max(0.0, min(1.0, seconds / clip_len))
