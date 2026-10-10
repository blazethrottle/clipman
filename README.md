# clipman

YouTube 영상을 받아 세로 9:16 쇼츠로 편집하는 개인용 로컬 도구입니다. 다운로드부터 쇼츠 완성까지 툴을 갈아타지 않고 한 흐름으로 처리하는 것이 목적입니다.

현재 상태: 설계 사인오프 완료(2026-09-03). 구현 계획 수립 후 v1 구현에 착수했습니다.

## 개요

- 형태: 로컬 웹앱. 브라우저 화면 + 로컬 파이썬 서버가 번들 실행파일을 호출해 처리
- 스택: Python + FastAPI 백엔드, yt-dlp와 ffmpeg(번들 실행파일), Svelte + Vite 프론트엔드
- 사용 흐름: URL 미리보기 -> 다운로드(원본 보존) -> 편집(구간 자르기 + 세로 9:16 변환) -> 내보내기
- 원칙: 개인 로컬 전용. 본인 권리 보유 및 개인 용도 콘텐츠에 한해 사용

## 로드맵

- v1: 다운로드 + 구간 자르기 + 세로 변환(중앙 크롭 / 단색 여백)
- v2: 자동 자막(음성인식)
- v3: 자동 하이라이트 구간 추천

## 문서

- 구현 계획(v1): `docs/superpowers/plans/2026-09-03-clipman-v1-implementation-plan.md`
- 개발 아키텍처(정본. API 계약과 폴더 구조): `docs/superpowers/specs/2026-09-01-clipman-architecture.md`
- 서비스 및 UI/UX 기획: `docs/superpowers/specs/2026-09-01-clipman-design.md`
- 번들 실행파일 조달 기록: `docs/binaries-manifest.md`
- 인수인계와 플랫폼 판정: `docs/HANDOFF.md`
- 벤치마크 분석(cobalt.tools): `docs/cobalt-analysis.html`

## 개발

대상 플랫폼은 macOS 1순위, Windows 병행입니다. 플랫폼 분기는 `backend/app/wrappers/binaries.py`와 실행기 파일에만 존재합니다.

```bash
cd backend
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/pytest            # 기본 스위트는 bin/ 실행파일 없이도 전부 통과합니다
./.venv/bin/pytest -m integration   # 실물 바이너리 필요 (bin/ 조달 후)
```

## 라이선스

미정 (개인 프로젝트).
