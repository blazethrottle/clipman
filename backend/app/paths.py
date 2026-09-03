"""앱 루트 기준 경로 상수.

설정 계층(pydantic-settings)을 두지 않는 대신 이 모듈이 경로의 단일 출처다.
모든 경로는 pathlib.Path이며, subprocess로 넘길 때만 str()로 바꾼다.
"""

from __future__ import annotations

import re
from pathlib import Path

# app/paths.py -> app/ -> backend/ -> clipman/
APP_ROOT = Path(__file__).resolve().parents[2]

BIN_DIR = APP_ROOT / "bin"
WORK_DIR = APP_ROOT / "work"
OUTPUT_DIR = APP_ROOT / "output"
LOGS_DIR = APP_ROOT / "logs"
LOG_FILE = LOGS_DIR / "clipman.log"

# job_id는 서버가 생성하지만, 경로 조립 지점은 어떤 경우에도 상위 폴더로 새지 않게 막는다.
_JOB_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def job_dir(job_id: str) -> Path:
    """work/<job_id>/ : 다운로드 원본을 보존하는 작업 폴더."""
    if not isinstance(job_id, str) or not _JOB_ID_PATTERN.match(job_id):
        raise ValueError(f"허용되지 않는 job_id입니다: {job_id!r}")
    return WORK_DIR / job_id


def job_tmp_dir(job_id: str) -> Path:
    """work/<job_id>/tmp/ : 인코딩 중간물. export마다 정리 대상이다."""
    return job_dir(job_id) / "tmp"


def ensure_runtime_dirs() -> None:
    """런타임 폴더를 만든다. bin/은 조달 대상이므로 여기서 만들지 않는다."""
    for directory in (WORK_DIR, OUTPUT_DIR, LOGS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
