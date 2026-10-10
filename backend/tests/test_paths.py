"""app.paths: 앱 루트 기준 경로 상수.

경로가 틀리면 번들 실행파일도 결과물도 엉뚱한 곳을 가리키므로 가장 먼저 고정한다.
"""

from pathlib import Path

from app import paths


def test_app_root_is_repository_root():
    """APP_ROOT는 저장소 루트여야 한다(backend/의 부모)."""
    assert (paths.APP_ROOT / "backend").is_dir()
    assert (paths.APP_ROOT / "README.md").is_file()


def test_runtime_dirs_are_under_app_root():
    for d in (paths.BIN_DIR, paths.WORK_DIR, paths.OUTPUT_DIR, paths.LOGS_DIR):
        assert d.parent == paths.APP_ROOT
        assert isinstance(d, Path)


def test_runtime_dir_names_match_gitignore():
    """.gitignore가 제외하는 이름과 일치해야 한다. 어긋나면 산출물이 커밋된다."""
    assert paths.BIN_DIR.name == "bin"
    assert paths.WORK_DIR.name == "work"
    assert paths.OUTPUT_DIR.name == "output"
    assert paths.LOGS_DIR.name == "logs"


def test_job_dir_is_under_work_dir():
    job_dir = paths.job_dir("abc123")
    assert job_dir == paths.WORK_DIR / "abc123"
    assert paths.job_tmp_dir("abc123") == job_dir / "tmp"


def test_job_dir_rejects_path_traversal():
    """job_id는 외부 입력에서 오지 않지만, 경로 조립 지점은 방어해 둔다."""
    import pytest

    for bad in ("../escape", "a/b", "", "."):
        with pytest.raises(ValueError):
            paths.job_dir(bad)


def test_ensure_runtime_dirs_creates_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "WORK_DIR", tmp_path / "work")
    monkeypatch.setattr(paths, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(paths, "LOGS_DIR", tmp_path / "logs")

    paths.ensure_runtime_dirs()

    assert (tmp_path / "work").is_dir()
    assert (tmp_path / "output").is_dir()
    assert (tmp_path / "logs").is_dir()
