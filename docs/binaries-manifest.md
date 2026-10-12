# 번들 실행파일 조달 기록 (binaries manifest)

`bin/`은 `.gitignore` 대상이라 커밋 이력으로 조달 여부를 확인할 수 없다. 이 파일이 유일한 추적 수단이다.
조달 직후 아래 표를 채우고 커밋한다. 비어 있으면 저장소에 조달이 기록되지 않은 상태다. 실제 기기의 `bin/`은 별도로 확인하고, 이미 배치된 실행파일이 있으면 출처, 버전과 SHA256을 검증해 표를 갱신한다.

## 현재 상태

| 실행파일 | 조달 여부 | 플랫폼 / 아키텍처 | 버전 | 출처 URL | SHA256 | 조달일 |
|---|---|---|---|---|---|---|
| yt-dlp | 이 Windows 기기에 조달 | Windows / x64 | 2026.08.19 | https://github.com/yt-dlp/yt-dlp/releases/download/2026.08.19/yt-dlp.exe | `66674953fe251b89f4d08c5f0e35e0728679bd67ab3d7d05c0562af101dd3e7a` | 2026-10-12 |
| ffmpeg | 이 Windows 기기에 조달 | Windows / x64 | 9.0.2 essentials | https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip | `3256173f3f8bffd7df12227c68adf68025edb1832273a9530688a7bb1ed8edec` | 2026-10-12 |
| ffprobe | 이 Windows 기기에 조달 | Windows / x64 | 9.0.2 essentials | 위 ffmpeg archive와 동일 | `f0d36ecbbdd3bcfac3efa078c96c7271c2e68b3810595552ac3b7f17e9a65c52` | 2026-10-12 |

yt-dlp의 release `SHA2-256SUMS`와 실행파일 해시를 대조함. ffmpeg archive는 공급자 `.sha256`의 `60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba`와 대조 후 두 실행파일을 추출함. 공급자 체크섬 대조이며 별도 서명 검증은 수행하지 않음. 위 gyan URL은 가변 URL이므로 재조달 시 같은 파일인지 해시로 확인함.

기존 변환 검사 5개를 이 기기의 실제 실행파일로 통과함. 통제된 로컬 HTTP 합성 영상으로 구간 가져오기 1개도 실행함. YouTube 네트워크 획득, 전송량, 브라우저 쿠키와 macOS 바이너리는 아직 미검증임. `bin/`은 gitignore이며 다른 기기로 자동 배포되지 않음.

## 조달 절차

1. 플랫폼 판별: macOS는 `uname -m`으로 `arm64`(Apple Silicon) / `x86_64`(Intel)를 확인한다.
2. 조달 우선순위
   - 1순위: 정적 빌드 다운로드(단일 파일, 의존성 없음, 오프라인에 견고)
   - 2순위: Homebrew 설치본을 `bin/`으로 복사(`brew install ffmpeg yt-dlp` 후 `readlink -f $(which ffmpeg)`)
   - Windows: gyan.dev 또는 BtbN 정적 빌드
3. 실행 권한과 격리 해제(macOS)
   ```bash
   chmod +x bin/yt-dlp bin/ffmpeg bin/ffprobe
   xattr -d com.apple.quarantine bin/* 2>/dev/null || true
   ```
4. 검증과 기록
   ```bash
   ./bin/ffmpeg -version | head -1
   ./bin/ffprobe -version | head -1
   ./bin/yt-dlp --version
   shasum -a 256 bin/*        # macOS. Linux는 sha256sum
   ```
   출력값을 위 표에 옮겨 적고 커밋한다.

## 주의

- ffmpeg 정적 빌드가 GPL 빌드인 경우 개인 로컬 사용에는 의무가 없고, 제3자 배포 시에만 소스 제공 의무가 생긴다. 배포 계획이 서면 LGPL 빌드로 교체를 검토한다.
- yt-dlp는 YouTube 변경에 따라 자주 깨진다. `POST /api/system/update-ytdlp`가 `yt-dlp -U`로 자체 갱신하므로, 갱신 후 버전이 바뀌면 이 표도 함께 갱신한다.
