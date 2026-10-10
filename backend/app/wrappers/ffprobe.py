"""ffprobe 어댑터: 소스 메타(해상도, 길이, 오디오 유무) 조회.

인자 조립과 JSON 파싱만 담당한다. 실행은 services/가 한다.
회전 메타 처리가 핵심이다. 세로로 찍힌 영상이 가로로 보고되면
이미 세로인 소스에 세로 크롭을 걸어 ffmpeg가 실패한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class ProbeError(RuntimeError):
    """소스 메타를 신뢰할 수 없을 때. 편집을 시작하면 안 되는 상태다."""


@dataclass(frozen=True)
class SourceMeta:
    width: int
    height: int
    duration: float
    has_audio: bool

    @property
    def is_wider_than_9_16(self) -> bool:
        """9:16보다 넓어야 세로 크롭에 잘라낼 여백이 있다. 정확히 9:16이면 없다."""
        return self.width * 16 > self.height * 9


def build_probe_args(src: Path | str, exe: Path | str = "ffprobe") -> list[str]:
    return [
        str(exe),
        "-v",
        "error",  # stdout이 순수 JSON이어야 파싱이 깨지지 않는다
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(src),
    ]


def _rotation_degrees(stream: dict) -> int:
    for side_data in stream.get("side_data_list") or []:
        if "rotation" in side_data:
            try:
                return int(round(float(side_data["rotation"])))
            except (TypeError, ValueError):
                continue
    legacy = (stream.get("tags") or {}).get("rotate")
    if legacy is not None:
        try:
            return int(round(float(legacy)))
        except (TypeError, ValueError):
            return 0
    return 0


def _duration_seconds(data: dict, video: dict) -> float:
    for raw in ((data.get("format") or {}).get("duration"), video.get("duration")):
        if raw in (None, "", "N/A"):
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    raise ProbeError("영상 길이를 읽을 수 없습니다. 손상된 파일이거나 지원하지 않는 형식입니다.")


def parse_probe_json(text: str) -> SourceMeta:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ProbeError("ffprobe 출력을 해석할 수 없습니다.") from exc

    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise ProbeError("영상 스트림이 없습니다. 오디오 전용 파일일 수 있습니다.")

    try:
        width = int(video["width"])
        height = int(video["height"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ProbeError("영상 해상도를 읽을 수 없습니다.") from exc

    # 90도나 270도 회전은 표시 해상도가 뒤바뀐다. 180도는 그대로다.
    if abs(_rotation_degrees(video)) % 180 == 90:
        width, height = height, width

    return SourceMeta(
        width=width,
        height=height,
        duration=_duration_seconds(data, video),
        has_audio=any(s.get("codec_type") == "audio" for s in streams),
    )
