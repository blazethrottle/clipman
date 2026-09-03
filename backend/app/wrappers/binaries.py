"""번들 실행파일 경로 해석.

이 모듈이 실행파일 이름의 플랫폼 분기를 담당하는 유일한 지점이다(HANDOFF 4절 확정).
다른 코드는 sys.platform을 보지 않고 이 함수들만 쓴다.
"""

from __future__ import annotations

import sys
from pathlib import Path

from app import paths

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"
YTDLP = "yt-dlp"
NAMES: tuple[str, ...] = (FFMPEG, FFPROBE, YTDLP)


class BinaryNotFound(RuntimeError):
    """번들 실행파일이 bin/에 없을 때. 메시지에 조달 경로를 담는다."""


def exe_suffix(platform: str | None = None) -> str:
    """Windows만 .exe 접미를 갖는다. macOS와 Linux는 확장자가 없다."""
    current = sys.platform if platform is None else platform
    return ".exe" if current == "win32" else ""


def binary_path(
    name: str,
    platform: str | None = None,
    bin_dir: Path | str | None = None,
) -> Path:
    if name not in NAMES:
        raise ValueError(f"알 수 없는 실행파일 이름입니다: {name!r}. 허용: {', '.join(NAMES)}")
    base = paths.BIN_DIR if bin_dir is None else Path(bin_dir)
    return base / f"{name}{exe_suffix(platform)}"


def require(
    name: str,
    platform: str | None = None,
    bin_dir: Path | str | None = None,
) -> Path:
    """실행 직전에 호출한다. 없으면 사용자가 다음 행동을 알 수 있는 메시지로 실패한다."""
    path = binary_path(name, platform=platform, bin_dir=bin_dir)
    if not path.exists():
        raise BinaryNotFound(
            f"번들 실행파일을 찾을 수 없습니다: {path}\n"
            f"bin/ 폴더에 {name}을(를) 배치한 뒤 출처와 버전을 "
            f"docs/binaries-manifest.md에 기록하세요."
        )
    return path


def missing(
    platform: str | None = None,
    bin_dir: Path | str | None = None,
) -> list[str]:
    """조달되지 않은 실행파일 목록. 서버 기동 시 진단에 쓴다."""
    return [
        name
        for name in NAMES
        if not binary_path(name, platform=platform, bin_dir=bin_dir).exists()
    ]
