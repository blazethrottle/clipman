"""wrappers.binaries: 번들 실행파일 경로 해석.

이 모듈이 저장소에서 실행파일 이름의 플랫폼 분기를 담당하는 유일한 지점이다.
실제 OS와 무관하게 세 플랫폼을 전부 검증한다.
"""

import pytest

from app.wrappers import binaries


class TestExeSuffix:
    def test_windows_gets_exe_suffix(self):
        assert binaries.exe_suffix("win32") == ".exe"

    @pytest.mark.parametrize("platform", ["darwin", "linux"])
    def test_unix_has_no_suffix(self, platform):
        assert binaries.exe_suffix(platform) == ""

    def test_defaults_to_current_platform(self, monkeypatch):
        monkeypatch.setattr(binaries.sys, "platform", "win32")
        assert binaries.exe_suffix() == ".exe"
        monkeypatch.setattr(binaries.sys, "platform", "darwin")
        assert binaries.exe_suffix() == ""


class TestBinaryPath:
    @pytest.mark.parametrize(
        "name,platform,expected",
        [
            ("ffmpeg", "darwin", "ffmpeg"),
            ("ffmpeg", "win32", "ffmpeg.exe"),
            ("ffprobe", "linux", "ffprobe"),
            ("yt-dlp", "win32", "yt-dlp.exe"),
            ("yt-dlp", "darwin", "yt-dlp"),
        ],
    )
    def test_filename_per_platform(self, name, platform, expected, tmp_path):
        path = binaries.binary_path(name, platform=platform, bin_dir=tmp_path)
        assert path.name == expected

    def test_path_is_under_bin_dir(self, tmp_path):
        assert binaries.binary_path("ffmpeg", platform="darwin", bin_dir=tmp_path).parent == tmp_path

    def test_defaults_to_paths_bin_dir(self):
        from app import paths

        assert binaries.binary_path("ffmpeg").parent == paths.BIN_DIR

    def test_unknown_name_rejected(self):
        with pytest.raises(ValueError):
            binaries.binary_path("rm")


class TestRequire:
    def test_returns_path_when_present(self, tmp_path):
        (tmp_path / "ffmpeg").write_text("")
        assert binaries.require("ffmpeg", platform="darwin", bin_dir=tmp_path).exists()

    def test_raises_with_korean_guidance_when_missing(self, tmp_path):
        with pytest.raises(binaries.BinaryNotFound) as exc:
            binaries.require("ffmpeg", platform="darwin", bin_dir=tmp_path)

        message = str(exc.value)
        assert "ffmpeg" in message
        assert "bin" in message
        # 사용자가 다음 행동을 알 수 있어야 한다(조달 문서 안내).
        assert "binaries-manifest" in message


class TestMissing:
    def test_lists_all_when_bin_dir_empty(self, tmp_path):
        assert set(binaries.missing(platform="darwin", bin_dir=tmp_path)) == set(binaries.NAMES)

    def test_lists_only_absent_ones(self, tmp_path):
        (tmp_path / "ffmpeg").write_text("")
        (tmp_path / "ffprobe").write_text("")
        assert binaries.missing(platform="darwin", bin_dir=tmp_path) == ["yt-dlp"]
