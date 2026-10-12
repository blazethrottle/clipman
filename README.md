# clipman

YouTube를 보다가 마음에 드는 영상의 특정 부분을 발췌하고 인용해 세로 9:16 쇼츠로 재편집하는 개인용 도구입니다. 시작과 끝을 표시하고 구도를 조정해 저장하는 단순하고 깔끔한 경험을 목표로 합니다.

현재 상태: **2026-10-12 Chrome 확장 + 로컬 영상 처리 프로그램 방향으로 기반 개발 착수.** 선택 구간 자료형, 구간 다운로드 명령과 작업 관리자(M2)를 구현했습니다. Windows에서 단위 테스트 153개와 실제 실행파일 통합 검사 6개를 통과했습니다. 확장, 서비스, API와 편집 UI는 미구현이며 실제 YouTube 획득 및 macOS 검증은 남아 있습니다.

새 세션은 [핸드오프](docs/HANDOFF.md)와 [최신 승인 설계](docs/superpowers/specs/2026-10-12-clipman-capture-first-design.md)를 먼저 읽습니다. 9월의 독립 로컬 웹앱 계획을 변경 없이 실행하지 않습니다.

## 개요

- 형태: 초기 데스크톱 Chrome 확장 + 로컬 영상 처리 프로그램. 확장 외에 최초 로컬 프로그램 설치 필요
- 스택: Python + FastAPI 백엔드, yt-dlp와 ffmpeg(번들 실행파일), Svelte + Vite 프론트엔드
- 사용 흐름: YouTube 시청 -> 시작과 끝 표시 -> 선택 구간 확보 -> 세로 구도 조정 -> 쇼츠 저장
- 구간 확보: 전체 다운로드를 필수로 두지 않음. 선택 구간 가져오기를 우선 검증하고 탭 부분 녹화를 대안으로 비교
- 제품 대상: 팬덤 또는 한국어 콘텐츠에 국한하지 않음
- 원칙: 개인 로컬 전용. 본인 권리 보유 및 개인 용도 콘텐츠에 한해 사용

## 로드맵

- 초기 제품: Chrome에서 구간 선택부터 세로 편집과 저장까지 연결
- 모바일 목표: iOS 및 Android에서도 발췌, 편집과 저장까지 완료. 출시 순서와 최소 OS 버전은 미정
- 후속 후보: 흐린 배경, 자막, 자동 하이라이트 및 자동 피사체 추적. 이전 v2/v3 일정은 새 구현 계획에서 재정리

## 문서

- 최신 승인 설계: [2026-10-12 제품 및 초기 형태](docs/superpowers/specs/2026-10-12-clipman-capture-first-design.md)
- 레퍼런스 조사: [공개 코드와 적용 조건](docs/research/2026-10-12-reference-review.md)
- 영상 확보와 플랫폼 검토: [구간 확보 및 녹화](docs/research/2026-10-12-capture-options.md)
- 구현 계획: [Chrome 발췌 흐름](docs/superpowers/plans/2026-10-12-clipman-capture-implementation-plan.md)
- 9월 구현 계획: `docs/superpowers/plans/2026-09-03-clipman-v1-implementation-plan.md` (M1 및 이전 계획 이력)
- 아키텍처: `docs/superpowers/specs/2026-09-01-clipman-architecture.md` (1절에 Chrome 연결과 시각 계약 개정)
- 9월 서비스 기획: `docs/superpowers/specs/2026-09-01-clipman-design.md` (최신 사용자 정정 우선)
- 번들 실행파일 조달 기록: `docs/binaries-manifest.md`
- 인수인계와 플랫폼 판정: `docs/HANDOFF.md`
- 벤치마크 분석(cobalt.tools): `docs/cobalt-analysis.html`

## 개발

로컬 처리 엔진은 macOS 우선, Windows 호환을 유지합니다. 모바일 구현은 별도입니다. 실행파일 이름 분기는 `backend/app/wrappers/binaries.py`에서 처리합니다.

```bash
cd backend
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/pytest            # 기본 스위트는 bin/ 실행파일 없이도 전부 통과합니다
./.venv/bin/pytest -m integration   # 실물 바이너리 필요 (bin/ 조달 후)
```

Windows에서는 `.venv/Scripts/python.exe -m pytest`를 사용합니다. 통합 검사가 전부 skipped이면 실물 검증 완료가 아닙니다. 새 세션의 작업 및 검증 순서는 핸드오프를 따릅니다.

## 라이선스

미정 (개인 프로젝트).
