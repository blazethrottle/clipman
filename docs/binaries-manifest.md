# 번들 실행파일 조달 기록 (binaries manifest)

`bin/`은 `.gitignore` 대상이라 커밋 이력으로 조달 여부를 확인할 수 없다. 이 파일이 유일한 추적 수단이다.
조달 직후 아래 표를 채우고 커밋한다. 비어 있으면 아직 조달되지 않은 것이다.

## 현재 상태

| 실행파일 | 조달 여부 | 플랫폼 / 아키텍처 | 버전 | 출처 URL | SHA256 | 조달일 |
|---|---|---|---|---|---|---|
| yt-dlp | 미조달 | | | | | |
| ffmpeg | 미조달 | | | | | |
| ffprobe | 미조달 | | | | | |

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
