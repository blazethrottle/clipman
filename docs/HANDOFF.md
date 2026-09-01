# clipman 핸드오프 (Windows 기획 세션 -> macOS 개발 세션)

- 작성일: 2026-09-01 (KST)
- 배경: 기획과 개발 아키텍처 확정까지를 Windows PC에서 완료했고, 이후 개발은 macOS(맥북)에서 이어간다.
- 진본 위치: GitHub `blazethrottle/clipman` (SSH). macOS에서 `git clone` 후 아래 순서로 읽고 시작한다.

## 1. 프로젝트 개요

YouTube 영상을 받아 세로 9:16 쇼츠로 편집하는 개인용 로컬 도구. 다운로드부터 쇼츠 완성까지 한 흐름으로 통합하는 것이 존재 이유다. 형태는 로컬 웹앱(브라우저 UI + 로컬 파이썬 서버가 번들 실행파일 호출), 스택은 Python + FastAPI + yt-dlp + ffmpeg + Svelte/Vite.

## 2. 완료 작업

- 서비스 기획, UI/UX 기획: `docs/superpowers/specs/2026-09-01-clipman-design.md`
- 개발 아키텍처 확정본(스택 검증 + 4개 렌즈 적대적 리뷰 반영): `docs/superpowers/specs/2026-09-01-clipman-architecture.md`
- 벤치마크(cobalt.tools) 코드 분석: `docs/cobalt-analysis.html`
- Web vs App 판단: 로컬 웹앱 확정. yt-dlp/ffmpeg는 번들 실행파일 + subprocess 호출로 확정(취소, 자체 업데이트, 실행 모델 통일 때문)
- git 초기화 + 최초 커밋 + GitHub 푸시 완료

## 3. 미완료 작업 (다음 즉시 착수 지점)

1. **구현 계획 수립(writing-plans)이 아직 안 됨.** 맥 세션의 첫 작업으로 권장. 아키텍처 문서를 입력으로 파일별 작업 순서와 TDD 단위를 만든다.
2. 그 전에 아래 "재심 대상 전제"의 macOS 적응을 먼저 판정할 것(구현 세부가 Windows에 맞춰져 있음).
3. 구현 착수 시 첫 수직 슬라이스 권장 순서: (a) `wrappers/`(binaries 경로 해석 -> ffprobe 메타 -> yt-dlp 다운로드 -> ffmpeg 크롭) 순수 어댑터부터 TDD, (b) `jobs/manager.py` 인메모리 레지스트리, (c) `services/`, (d) FastAPI 라우터, (e) Svelte UI.

## 4. 재심 대상 전제 (macOS 세션이 반드시 의심하고 확인할 것)

아키텍처 문서 결론은 제약이 아니라 재심 가능한 상태로 물려준다. 특히 아래는 Windows 전제라 macOS에서 반드시 바꾸거나 재검증해야 한다.

| 전제 | Windows 결정 | macOS에서 할 일 |
|---|---|---|
| 번들 바이너리 이름 | `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe` | 확장자 없는 `yt-dlp`, `ffmpeg`, `ffprobe`. `binaries.py`에서 `sys.platform` 분기로 이름 결정(크로스플랫폼) |
| ffmpeg 번들 소스 | gyan.dev/BtbN 정적 빌드(Windows) | macOS 정적 빌드(evermeet.cx 등) 또는 Homebrew. Apple Silicon(arm64)/Intel 구분 확인 |
| 실행기 | `start.cmd` (더블클릭) | `start.command` 또는 shell 스크립트 + `chmod +x`. Gatekeeper 첫 실행 경고 감안 |
| 이벤트 루프 함정 | ProactorEventLoop 주의(Windows 전용) | macOS엔 해당 없음. 단 `run_in_executor + subprocess.Popen` 실행 모델 자체는 크로스플랫폼이라 그대로 유지 |
| 쿠키 폴백 | `--cookies-from-browser chrome` + App-Bound Encryption 회피 | macOS는 Safari/Chrome 대상, Keychain 접근 권한 프롬프트 발생 가능. `--cookies` 파일 폴백 우선은 동일 |
| 경로 처리 | 일부 역슬래시/`.exe` 하드코딩 | `pathlib`/`os.path`로 통일, 하드코딩 제거 |
| v2 패키징 | PyInstaller onefile(Windows) | macOS는 `.app` 번들 + 코드서명/공증(notarization) 이슈. v2 범위라 지금은 보류 |

아키텍처 문서 15절의 기존 재심 항목(번들 ffmpeg 실제 버전에서 필터/컷/오디오 유지 통합 테스트, `player_client` 조합 변동, 포트 자동 선택 배선)도 그대로 유효하다.

**권장 방향:** 지금 구조는 `binaries.py`의 `sys.platform` 분기와 실행기 파일만 OS별로 두면 크로스플랫폼이 된다. macOS 전용으로 좁히기보다 크로스플랫폼으로 두는 편이 Windows 원 PC와의 왕복에도 유리하다.

## 5. 관련 파일 인덱스

- `README.md` : 프로젝트 개요, 로드맵
- `docs/superpowers/specs/2026-09-01-clipman-design.md` : 서비스/UI/UX/개념 아키텍처(읽기 1순위)
- `docs/superpowers/specs/2026-09-01-clipman-architecture.md` : 개발 아키텍처 확정본(읽기 2순위, 구현의 근거)
- `docs/cobalt-analysis.html` : 벤치마크 분석(참고)
- `.gitignore` : `bin/`, `work/`, `output/`, `logs/`, venv, node_modules 제외

## 6. 작업 원칙

이 계정의 방법론(설계 먼저, 계획 합의 후 실행, TDD, 완료 전 검증, 서브에이전트 티어링, 적대적 검증, 한국어 출력 품질)은 글로벌 CLAUDE.md와 스킬이 강제하므로 여기 재서술하지 않는다. macOS 허브 세션은 그 규범을 이미 로드한다. 프로젝트 고유 원칙만 남긴다.

- 개인 로컬 전용 도구다. 공개 서비스용 복잡성(터널 서명, 다층 인증, Redis)은 넣지 않는다.
- 편집이 유일한 차별점이다. 다운로드는 검증된 도구(yt-dlp)에 위임하고 편집 UX에 투자한다.
- v1은 최소(다운로드 + 자르기 + 세로 변환). blur_pad(흐린 배경)는 v1.1, 자막은 v2, 하이라이트는 v3.
- 비개발자 사용자다. 설치와 실행은 Claude가 대행하고 사용자는 더블클릭만 한다.

## 7. macOS 세션 시작 방법

1. `git clone git@github.com:blazethrottle/clipman.git` 후 폴더 진입.
2. 이 문서 -> design spec -> architecture 순으로 읽는다(R1 선행자료 게이트).
3. 4절 재심 전제(특히 바이너리/실행기/경로)를 먼저 판정한다.
4. writing-plans로 구현 계획을 만든 뒤 사용자와 합의하고 착수한다.
