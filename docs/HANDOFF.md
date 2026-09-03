# clipman 핸드오프 (Windows 기획 세션 -> macOS 개발 세션)

- 작성일: 2026-09-01 (KST) / 갱신: 2026-09-03 (M0 착수 관문 판정 반영)
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

## 3. 진행 상태 (2026-09-03 갱신)

M0(착수 관문) 완료. 관문 4개가 모두 닫혔다.

| 관문 | 상태 | 산출물 |
|---|---|---|
| 사용자 사인오프 | **완료** | design/architecture 문서 상태 줄 갱신 |
| macOS 재심 전제 7건 판정 | **완료** | 이 문서 4절 확정 판정 열 |
| 아키텍처 정본 크로스플랫폼 정정 | **완료** | architecture 1, 2, 3, 7, 9, 13절 |
| 구현 계획 수립(writing-plans) | **완료** | `docs/superpowers/plans/2026-09-03-clipman-v1-implementation-plan.md` |

구현 순서는 계획서가 정본이며, 원 권장안(첫 수직 슬라이스: `wrappers/` 순수 어댑터 TDD -> `jobs/manager.py` -> `services/` -> FastAPI 라우터 -> Svelte UI)을 그대로 승계했다.

M1 wrappers 계층도 완료했다(단위 테스트 107개 통과, 번들 바이너리 없이).

| 마일스톤 | 상태 | 비고 |
|---|---|---|
| M1-1 스캐폴딩 (`requirements.txt`, `pyproject.toml`, `paths.py`) | **완료** | 의존성 버전 고정 |
| M1-2 `wrappers/binaries.py` | **완료** | 실행파일 이름의 플랫폼 분기 단일 지점 |
| M1-3 `wrappers/ffprobe.py` | **완료** | 회전 메타 처리, 오디오 유무 판정 |
| M1-4 `wrappers/ffmpeg.py` | **완료** | CROP/PAD 조립, 자동 PAD 전환, 진행률 파싱 |
| M1-5 `wrappers/ytdlp.py` | **완료** | 메타 조회, 다운로드 인자, 폴백 순서, 에러 4종 분류 |
| M1-0 바이너리 조달 | **미완료** | 실사용 기기에서만 가능 |
| M1-6 통합 검증 | **미완료** | 테스트는 작성됨(`tests/integration/`), 실행은 바이너리 조달 후 |
| M2 이후 | 미착수 | `jobs/manager.py`부터 |

**중요: 이 작업은 아직 main에 없다.** 브랜치 `claude/clipman-product-progress-wlaf5v`에 있고 드래프트 PR로 열려 있다(`blazethrottle/clipman#1`). 이어받는 세션은 그 브랜치에서 시작하거나 PR을 먼저 병합해야 한다.

### 이어받는 즉시 할 일

1. `bin/`에 실행파일 3종 조달 (M1-0). 절차는 `docs/binaries-manifest.md`.
2. `./.venv/bin/pytest -m integration` 실행 (M1-6). 세 모드의 오디오 유지가 여기서 처음 실측된다.
3. 통과하면 M2 `jobs/manager.py` 착수.

## 4. 재심 대상 전제 (판정 완료, 2026-09-03)

아키텍처 문서 결론은 제약이 아니라 재심 가능한 상태로 물려받았고, 2026-09-03에 7건 전부를 단일 답으로 확정했다. **대상 플랫폼 확정: macOS 1순위 + Windows 병행(크로스플랫폼 유지).** 근거는 원 PC(Windows)와의 왕복 가능성이고, 비용은 `binaries.py`의 `sys.platform` 분기와 실행기 파일 2개뿐이다.

| 전제 | Windows 결정 | 확정 판정 (2026-09-03) |
|---|---|---|
| 번들 바이너리 이름 | `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe` | **확정**: `binaries.py`가 `sys.platform`으로 분기. `win32`면 `.exe` 접미, 그 외(darwin/linux)는 확장자 없음. 이름 상수는 단일 지점에만 둔다 |
| ffmpeg 번들 소스 | gyan.dev/BtbN 정적 빌드(Windows) | **확정**: 조달 우선순위를 1순위 정적 빌드 다운로드, 2순위 Homebrew 설치본 복사로 고정. 조달 스크립트가 `uname -m`으로 arm64/x86_64를 판별한다. 조달 결과(출처 URL, 버전, SHA256)는 `bin/`이 gitignore이므로 `docs/binaries-manifest.md`에 기록한다 |
| 실행기 | `start.cmd` (더블클릭) | **확정**: `start.command`(macOS, `chmod +x` 필요)와 `start.cmd`(Windows) 두 파일을 모두 저장소 루트에 둔다. Gatekeeper 첫 실행은 우클릭 열기 1회 안내로 처리 |
| 이벤트 루프 함정 | ProactorEventLoop 주의(Windows 전용) | **확정(변경 없음)**: macOS 해당 없음. `run_in_executor` + 동기 `subprocess.Popen` 실행 모델은 크로스플랫폼이므로 그대로 유지 |
| 쿠키 폴백 | `--cookies-from-browser chrome` + App-Bound Encryption 회피 | **확정**: 폴백 순서를 (1) `--cookies FILE`(사용자가 내보낸 쿠키 파일), (2) `--cookies-from-browser`(macOS는 chrome, safari 순), (3) `player_client` 교체, (4) yt-dlp 업데이트 안내로 고정. Keychain 권한 프롬프트는 실측 대상으로 M1에 남긴다 |
| 경로 처리 | 일부 역슬래시/`.exe` 하드코딩 | **확정**: 내부 경로는 전부 `pathlib.Path`. 문자열 결합 금지, subprocess 인자로 넘길 때만 `str()` 변환. `.exe` 하드코딩은 아키텍처 9절에서 제거 완료 |
| v2 패키징 | PyInstaller onefile(Windows) | **확정(보류 유지)**: macOS `.app` 번들 + 코드서명/공증은 v2 범위. v1에서는 다루지 않는다 |

아키텍처 문서 15절의 기존 재심 항목(번들 ffmpeg 실제 버전에서 필터/컷/오디오 유지 통합 테스트, `player_client` 조합 변동, 포트 자동 선택 배선)은 여전히 실측 대상이며, 구현 계획(`docs/superpowers/plans/2026-09-03-clipman-v1-implementation-plan.md`)의 명시적 검증 태스크로 편입했다.

## 5. 관련 파일 인덱스

- `README.md` : 프로젝트 개요, 로드맵
- `docs/superpowers/plans/2026-09-03-clipman-v1-implementation-plan.md` : v1 구현 계획(읽기 1순위, 무엇을 어떤 순서로 만드는지)
- `docs/superpowers/specs/2026-09-01-clipman-architecture.md` : 개발 아키텍처 확정본(읽기 2순위, **API 계약과 폴더 구조의 정본**)
- `docs/superpowers/specs/2026-09-01-clipman-design.md` : 서비스/UI/UX 기획 정본(읽기 3순위, 제품 의도와 화면 흐름)
- `docs/binaries-manifest.md` : 번들 실행파일 조달 기록(출처, 버전, SHA256). `bin/`이 gitignore이므로 이 파일이 유일한 추적 수단
- `docs/cobalt-analysis.html` : 벤치마크 분석(참고)
- `.gitignore` : `bin/`, `work/`, `output/`, `logs/`, venv, node_modules 제외

## 6. 작업 원칙

이 계정의 방법론(설계 먼저, 계획 합의 후 실행, TDD, 완료 전 검증, 서브에이전트 티어링, 적대적 검증, 한국어 출력 품질)은 글로벌 CLAUDE.md와 스킬이 강제하므로 여기 재서술하지 않는다. macOS 허브 세션은 그 규범을 이미 로드한다. 프로젝트 고유 원칙만 남긴다.

- 개인 로컬 전용 도구다. 공개 서비스용 복잡성(터널 서명, 다층 인증, Redis)은 넣지 않는다.
- 편집이 유일한 차별점이다. 다운로드는 검증된 도구(yt-dlp)에 위임하고 편집 UX에 투자한다.
- v1은 최소(다운로드 + 자르기 + 세로 변환). blur_pad(흐린 배경)는 v1.1, 자막은 v2, 하이라이트는 v3.
- 비개발자 사용자다. 설치와 실행은 Claude가 대행하고 사용자는 더블클릭만 한다.

## 7. macOS 세션 시작 방법 (2026-09-03 갱신)

M0가 끝났으므로 시작 절차가 바뀌었다.

```bash
git clone git@github.com:blazethrottle/clipman.git
cd clipman
git checkout claude/clipman-product-progress-wlaf5v   # 작업은 main이 아니라 이 브랜치에 있다

cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/pytest                                    # 107 passed 확인 (바이너리 불필요)
```

1. 위 명령으로 브랜치를 받고 단위 테스트 통과를 확인한다. 여기서 실패하면 환경 문제이므로 먼저 해결한다.
2. 이 문서 -> 구현 계획서 -> architecture 순으로 읽는다(R1 선행자료 게이트). design spec은 제품 의도 확인용으로 필요할 때 읽는다.
3. **바이너리 조달이 첫 물리 작업이다.** 계획서 M1-0 절차대로 `bin/`에 `yt-dlp`, `ffmpeg`, `ffprobe`를 배치하고 `docs/binaries-manifest.md`에 출처와 버전, SHA256을 기록한다.
4. `./.venv/bin/pytest -m integration`으로 M1-6을 실측한다. 세 모드의 오디오 유지 검증이 여기서 처음 실행된다. 통과 후 M2로 넘어간다.
