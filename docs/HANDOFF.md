# clipman 개발 핸드오프

- 갱신일: 2026-10-16, 서울 기준 (최종 QA 반영)
- 사용자 승인: 제품 목적과 초기 Chrome 확장 + 로컬 처리 프로그램 방향. 2026-10-12 후속 요청으로 로드맵 개발 착수
- 2026-10-16 사용자 결정: 개인 용도로 먼저 쓰며 고도화하고, 상업용 배포 여부는 그 뒤에 정함. Mac 검증, PR 병합, 본인 Chrome 설치까지 진행하고 **최종 QA는 별도의 새 세션에서 진행함**
- 저장소: `https://github.com/blazethrottle/clipman`, 기본 브랜치 `main`
- 이번 개발 시작 기준: `54ae8c0` (당일 핸드오프 반영 main)
- 이번 갱신은 Chrome MV3 확장, 처리 서비스/API 및 개인용 개발 릴리즈를 반영함. 일반 사용자 설치/스토어 게시의 완료는 아님

## 2026-10-16 최종 QA (Mac mini, main `025b3a3` 기준)

- 핸드오프 4절의 7개 항목을 수행함. 자동 검사 5종 통과, 실제 서버 API로 일반·4K 40초·세로 Shorts·연령 제한 영상과 확보/인코딩 취소, 재편집, 실행기 재실행을 확인함. 상세: [최종 QA 기록](verification/2026-10-16-final-qa.md), [비개발자용 QA 보고서](verification/2026-10-16-final-qa-report.html)
- 결함 1건 수정: 사용 직후 `start.command`를 다시 열면 직전 연결의 TIME_WAIT 때문에 9000 bind가 실패해 임의 포트로 열리고 확장의 저장된 연결이 끊김. `open_listener()`가 POSIX에서 `SO_REUSEADDR`를 켬(Windows 제외). 회귀 검사 `test_listener_reclaims_port_left_in_time_wait`. 기본 pytest 212 passed·2 skipped.
- 자막 실측: 자막이 박힌 가로 원본은 「화면 채우기」의 좌우 위치 어디에서도 자막이 잘리고, 「전체 화면 유지」만 보존함. 결함이 아니라 세로 크롭 폭의 한계임.
- 사용자 반복 인수(사이드 패널 UI)는 사용자 부재로 수행하지 않음. 동반 세션에서 확인함.
- 개선 후보(사용자 결정): 연령 제한 영상의 실패 메시지가 "가져오기를 제한했습니다. 다른 영상을 시도해 주세요."로 표시되어 로그인이 필요한 영상임을 알리지 않음. 문구 변경 여부는 사용자가 정함.

## 2026-10-16 macOS 실물 검증 (Mac mini, Apple Silicon)

- Mac용 yt-dlp 2026.08.19와 ffmpeg/ffprobe 9.0.2 정적 빌드를 조달하고 배포처 해시와 대조함. [manifest](binaries-manifest.md)의 macOS 표에 기록함.
- Mac에서 결함 2건을 발견해 수정함. ① 정적 ffmpeg가 시스템 인증서를 찾지 못해 실제 YouTube 구간 확보가 전부 실패함. `processes.child_env()`가 `SSL_CERT_FILE`을 전달함. ② YouTube 영상 서버의 간헐적 403(반복 3회 중 1회). 확보 단계에서 1회 재시도함.
- POSIX 프로세스 트리 취소를 실제 자식 프로세스로 검사하는 `test_posix_process_tree.py`를 추가함. 결함 주입 시 실패함을 확인함.
- pytest 224 passed, 2 skipped(Windows 전용), Node 5, 확장 빌드, Playwright MV3 1 통과. 실제 YouTube 5구간을 짧은 PATH 환경에서 1080x1920 MP4로 저장함.
- `start.command`를 Finder와 같은 짧은 환경으로 실행해 127.0.0.1:9000 연결 안내 페이지와 `logs/connection.key`(권한 600) 생성을 확인함.
- 상세: [macOS 검증 기록](verification/2026-10-16-macos-first-run.md)

## 검수 후속 보완 (별도 수정 브랜치)

Draft PR #2의 `96f89e7` 위에서 진행률, 재생목록, 화질 상한과 편집 범위 검증을 수정함. Windows는 부모가 먼저 종료해도 자식을 정리하는 Job Object 방식으로 보강함. 기존 Selection, Chrome 연결과 UI를 유지함. 기본 199개 및 실물 통합 13개를 포함해 총 212 passed, skipped 0을 확인함. 실제 YouTube 한 영상에서 구간 확보와 음성 포함 1080x1920 MP4 저장을 확인했고 다른 영상은 시간 초과함. [검증 상세](verification/2026-10-12-media-contract-review.md)와 [갱신 계약](superpowers/specs/2026-10-12-clipman-engine-contract.md)을 참조함. main 병합 및 기존 개인 배포물 재패키징은 수행하지 않음.

## 최신 연결 개발 결과

- Chrome MV3 content script, 서비스 워커, 구간 선택 패널 및 Svelte 편집 탭을 구현함. 구간 확보 -> 크롭/PAD -> MP4 저장, 재편집, 탭 변경/영상 이동, 미저장 설정의 새로고침 복원을 브라우저에서 확인함.
- FastAPI의 Host/Origin 정확 검사, 연결 키와 확장 ID 검사, 경로별 서명 미디어 및 Range 재생을 구현함. content script에는 로컬 연결 키와 API 중계를 제공하지 않으며 storage.local의 TRUSTED_CONTEXTS 제한을 먼저 완료함.
- 실제 프로세스 시작/등록과 출력 게시를 작업 잠금으로 묶고 Windows 프로세스 트리 종료를 검사함. POSIX는 부모 종료 후 잔여 그룹에도 KILL을 보내도록 보완했으나 macOS 실기기 검증은 남음.
- 실행기를 추가하고 Windows의 신규 프로세스에서 9000 점유 시 다른 실제 포트의 연결 안내가 열리는 것을 확인함. 기기 키는 logs/connection.key에 보존하며 실제 키/영상/실행파일을 커밋하지 않음.
- 기본 검사 178개, 실제 실행파일 통합 9개, 확장 순수/보안 검사 5개, 실제 MV3 브라우저 시나리오 1개 통과. [최신 검증 기록](verification/2026-10-12-chrome-first-connection.md)을 참조함.
- 실제 YouTube `jNQXAC9IVRw`에서 0~2초 구간 확보 후 0~1초를 1080x1920 MP4로 변환했고 음성 스트림을 확인함. 단일 공개 영상의 기계 검사이며 실제 장면 시각/고화질/제한 영상/쿠키 및 전체 UX의 일반 검증이 아님.
- [릴리즈 경로와 개인 설치 안내](RELEASE.md)를 작성함. 현재 추천은 스토어 없이 개인 개발자 모드로 로드하는 것임. 개인용 ZIP을 준비하며 독립 로컬 처리 프로그램은 별도 필요함. 스토어 Private/Unlisted도 같은 심사를 받으며 등록/심사/공개 게시를 하지 않음.

## 이전 기반 착수 결과 (f97bdc3 이력)

- [Chrome 발췌 구현 계획](superpowers/plans/2026-10-12-clipman-capture-implementation-plan.md)을 작성하고 아키텍처 1절에 localhost 연결과 선택/확보/편집 시각 계약을 개정함.
- `backend/app/capture.py`: YouTube ID/URL 일치, 원본 선택 범위, 확보 파일의 로컬 시각을 원본 시각으로 변환함. 유한값과 범위를 검사함.
- `wrappers/ytdlp.py`: 선택 구간 및 정밀 컷 옵션을 추가함. 기존 전체 다운로드 호출과 쿠키 옵션을 유지함. 긴 영상의 소수점 시각 반올림 결함을 회귀 테스트로 수정함.
- `jobs/manager.py`: 상태 사본, 잠금, 단조 진행률, 실행별 generation, Popen 종료 확인, 원본 보존과 재편집을 구현함. 취소 뒤 완료/오류 신호와 이전 실행의 신호를 무효화함. 완성 출력은 작업 정리 폴더 밖의 파일만 등록함.
- Windows x64의 번들 3종 조달 및 체크섬 검사를 완료함. manifest에 버전과 해시를 기록함. 다른 기기의 bin으로 배포한 것은 아님.
- 기본 검사 153 passed, 통합 검사 6 passed, skipped 0, pip check 통과. [검증 기록](verification/2026-10-12-capture-foundation.md)을 참조함.
- 통합 검사의 구간 획득은 소유한 합성 HTTP 영상임. 실제 YouTube, 전송량/대기 비교, Chrome UI, macOS 및 모바일은 아직 미검증임. M2의 Popen 종료는 직접 프로세스에 한함. 다운로드 자식 프로세스 트리 종료 및 실행 전 취소와 Popen 등록의 경합은 M3의 종단 관문으로 남음.

## 1. 현재 승인된 방향

클립맨은 **YouTube 시청 중 마음에 든 구간을 발췌하고 인용해 쇼츠로 재편집하는 도구**임. 팬덤 또는 한국어 콘텐츠 특화가 아님. 다운로드는 구간 확보 수단이며 전체 원본 다운로드를 필수 선행 단계로 두지 않음.

**초기 제품은 Chrome 확장 + 로컬 영상 처리 프로그램으로 진행함.** Chrome에서 영상을 보며 시작과 끝을 표시하고, 구간과 세로 구도를 확인한 뒤 쇼츠를 저장함. 확장 외에 최초 로컬 프로그램 설치가 필요함을 숨기지 않음. 로컬 엔진은 macOS 우선 및 Windows 호환을 유지함.

**최종 모바일 목표는 iOS와 Android에서 발췌, 편집과 저장까지 완료하는 것임.** URL을 PC로 전달하는 기능으로 축소하지 않음. 모바일 출시 순서와 최소 OS 버전은 아직 결정하지 않았고 실제 영상 및 음성 확보는 미검증임.

UI는 가볍고 쾌적하며 단순하지만 깔끔하고 예뻐야 함. 시청 중에는 구간 표시, 편집 시에는 미리보기, 구간과 구도 조절, 쇼츠 만들기에 집중함. 색과 서체, 패널 및 탭의 상세 배치는 시안으로 확인할 항목임.

## 2. 읽기 순서와 문서 우선순위

1. 이 문서
2. [최신 승인 설계](superpowers/specs/2026-10-12-clipman-capture-first-design.md)
3. [레퍼런스와 적용 조건](research/2026-10-12-reference-review.md)
4. [구간 확보 및 플랫폼 검토](research/2026-10-12-capture-options.md)
5. 구현할 부분에 해당하는 기존 아키텍처, 계획, 테스트와 코드

제품 의도와 초기 형태는 **2026-10-12 설계가 정본**임. 9월 설계의 팬덤 시나리오, URL 입력 우선, 전체 다운로드 선행, 독립 로컬 웹앱 3화면과 더블클릭 단독 진입은 최신 결정을 덮어쓸 수 없음.

9월 아키텍처의 로컬 엔진과 API는 구현 참고임. 이번에 1절의 Chrome 연결 계약과 선택 구간 시각 모델을 개정하고 [새 계획](superpowers/plans/2026-10-12-clipman-capture-implementation-plan.md)으로 M2 이후를 재배치함. 이미 승인된 목적과 초기 형태를 다시 승인받지 않음. 일반 구현 선택은 근거를 기록해 진행하고 목적이나 사용자 경험을 바꾸는 선택만 합의함.

기기의 공통 지침과 필요한 관련 지식을 사용하되, 이 공개 저장소만 읽어도 승인과 다음 작업을 이해할 수 있어야 함. 과거 프로젝트 입구 문서가 최신 사용자 정정을 대신하지 않음.

## 3. 실제 완료 및 미완료

| 항목 | 상태 | 근거 |
|---|---|---|
| M0 초기 설계와 계획 | 완료 이력 | 2026-09-03. 최신 방향으로 개정 필요 |
| M1-1 경로 및 테스트 스캐폴딩 | 구현 완료 | `backend/app/paths.py`, requirements 및 pytest 설정 |
| M1-2 바이너리 경로 | 구현 완료 | `wrappers/binaries.py` |
| M1-3 메타 정보 파싱 | 구현 완료 | `wrappers/ffprobe.py`, 회전 및 음성 유무 |
| M1-4 트림과 CROP/PAD 명령 | 구현 완료 | `wrappers/ffmpeg.py`, 진행률 파싱 |
| M1-5 다운로드 명령과 오류 파싱 | 구현 완료 | `wrappers/ytdlp.py` |
| M1-0 바이너리 조달 | Windows, macOS arm64 완료 | manifest의 버전/체크섬 기록 |
| M1-6 실제 변환 검증 | Windows, macOS 완료 | 실물 통합 13개 통과, 실제 YouTube 5구간(macOS) |
| 구간 자료형 및 명령 | 구현 및 합성 HTTP 검사 완료 | capture.py와 test_section_integration.py |
| M2 작업 관리자 | 기반 구현 완료 | jobs/manager.py, 상태/보존/취소/경합 검사 |
| M3 서비스 및 M4 API | 초기 연결 구현 및 Windows 검사 완료 | services/engine.py, main.py 및 실물 흐름 검사 |
| M5 Chrome 확장과 편집 UI | 개발 연결 구현 및 실제 MV3 시험 완료 | extension/, frontend/, 합성 페이지 브라우저 시나리오 |
| 실행기와 개인용 ZIP | Windows 실행기, macOS `start.command` 기동·재실행 및 확장 패키지 검사 완료 | start.cmd, start.command, tools/package_extension.py. 2026-10-16 QA에서 재실행 시 포트 유지 결함을 수정함. ZIP 사본의 Gatekeeper 경고와 일반 설치는 미검증 |
| 모바일 앱 | 미구현 | iOS 및 Android 구현 및 실기기 검증 없음 |

기존 어댑터 코드는 PR #1로 **2026-10-11 08:37 서울 기준** main에 병합됨. 이번 착수 전 기본 테스트 107개 통과를 재확인함. 이번 결과는 위 착수 결과 및 검증 기록을 따름.

Mac mini의 `~/Projects/clipman`에는 `bin/`(macOS 실행파일 3종), `backend/.venv`, `frontend/node_modules`와 빌드된 `extension/dist`가 준비돼 있음. 다시 조달하거나 설치하지 않음.

## 4. 최종 QA 세션의 작업 (2026-10-16 기준)

QA 세션은 구현을 다시 만들지 않고 아래를 확인함. 결함은 재현 절차와 함께 기록하고, 고칠 때는 회귀 검사를 먼저 추가함.

1. **상태 확인:** PR #2·#3의 병합 여부, 현재 브랜치, 미커밋 변경을 확인함. 병합 전이면 `fix/media-contracts-pr2-20261012` 브랜치가 최신 코드임.
2. **자동 검사 재현:** `backend`에서 기본 pytest(`python -m pytest -q`, 통합 제외)와 통합 pytest(`-m integration`)를 따로 실행함. `frontend`에서 `npm test`, `npm run build`, `npx playwright test`. 기대값은 기본 212 passed·2 skipped·13 deselected, 통합 13 passed, Node 5, 빌드 통과, Playwright 1 passed임(2026-10-16 QA 기준). Playwright 브라우저 캐시(`~/Library/Caches/ms-playwright`)가 없으면 `npx playwright install chromium`을 먼저 실행함.
3. **본인 Chrome 인수(사용자와 함께):** 2026-10-16 첫 인수에서 설치, 연결, 저장까지 1회 성공함([기록](verification/2026-10-16-macos-first-run.md)). 2026-10-16 최종 QA는 사용자 부재로 기계 경로(API)만 검증했고, 사용자 반복 인수는 동반 세션에서 확인함. 원본에 자막이 박힌 가로 영상은 「화면 채우기」에서 자막 좌우가 잘림. QA 실측에서 자막 폭이 세로 크롭 폭보다 넓어 「좌우 위치」를 어디에 두어도 잘렸고 「전체 화면 유지」만 자막을 보존함([최종 QA 기록](verification/2026-10-16-final-qa.md)).
   - 기존 항목: 사용자의 Chrome 프로필에서 실제 사이드 패널로 YouTube 시청 → 시작/끝 표시 → 이 구간 편집하기 → 세로 구도(화면 채우기·좌우 위치 또는 전체 화면 유지) → 쇼츠 만들기 → MP4 저장까지 진행함. 저장 파일을 재생해 장면, 음성, 구도를 확인함.
4. **여러 영상:** 일반 영상, 고화질(4K) 영상, 세로 원본(Shorts), 연령 제한 또는 로그인 필요 영상, 긴 구간(30초 이상)을 각각 시도함. 확보 시간과 실패 메시지를 기록함. 구간 확보가 JavaScript runtime 관련 메시지로 실패하면, Finder 실행 환경의 PATH에 `/opt/homebrew/bin`(deno 위치)이 없는지 먼저 확인함. 2026-10-16 검사는 짧은 PATH에서 통과했으나 영상 2개의 표본임.
5. **취소와 재편집:** 확보 중 취소, 인코딩 중 취소, 같은 구간 재편집 후 원본 보존을 확인함. 취소 뒤 `ps`로 yt-dlp·ffmpeg 잔여 프로세스가 없는지 확인함.
6. **실행기:** Finder에서 `start.command`를 더블클릭함. 연결 코드가 재실행 뒤에도 유지되는지는 2026-10-16 QA에서 확인함(TIME_WAIT 포트 결함 수정 뒤 9000 유지). ZIP으로 내려받은 사본은 격리 속성이 붙으므로 처음 실행 시 macOS 보안 경고가 나오는지 확인함. git clone 체크아웃은 경고가 없음을 확인함.
7. **결과 기록:** `docs/verification/`에 QA 기록을 남기고 이 문서 3·4절을 갱신함.

QA 이후의 개발 후보(개인 사용 단계): 일반 사용자용 설치/업데이트 정리, 탭 부분 녹화 비교, 모바일 발췌/편집/저장. 상업용 배포는 사용자가 개인 사용 뒤에 결정하며, 결정 전에 `docs/RELEASE.md`의 스토어 정책(다운로드 기능), ffmpeg 라이선스(GPL 빌드), YouTube 약관을 검토함.

## 5. 구현할 때 보존할 계약

- 선택 구간 가져오기를 우선 검증하고 부분 녹화를 대안으로 비교함. 전체 다운로드는 반복 재편집 등의 선택 경로임.
- 부분 녹화로 지나간 장면을 자동 복구할 수 없음. 재재생 또는 사전 버퍼가 필요하며 항상 녹화하는 버퍼는 초기 범위에 포함하지 않음.
- 잘라 받은 파일의 로컬 0초와 YouTube 원본 시각을 별도로 저장함. 컷과 출처 시각이 어긋나지 않아야 함.
- 미리보기와 출력이 같은 트림 및 크롭 설정을 사용함. 표시 좌표를 원본 픽셀로 환산하고 화면 크기가 달라도 결과 위치가 일치해야 함.
- 소스 URL과 원본 시작 및 끝을 작업 자료에 보존함. 출처 자막 삽입은 선택 후보이며 필수화하지 않음.
- 실제 작업 취소는 Popen 프로세스를 종료함. 인코딩 취소 시 확보한 구간 원본을 보존하고 임시 결과만 정리함.
- 확장 UI에서 내부 도구와 코덱을 전면 노출하지 않음. 로컬 연결 실패와 음성 누락은 다음 행동이 명확한 메시지로 안내함.
- 실행파일 이름의 플랫폼 분기는 `binaries.py`, 경로는 pathlib를 사용함. 새 연결 계층에 플랫폼 분기가 필요하면 위치를 문서화함.
- 설치를 사용자가 터미널에서 해결해야 하는 흐름으로 만들지 않음. 개발 세션의 에이전트가 첫 설치를 대행함.
- 클라우드 처리, 계정, 자동 추천 중심 서비스로 범위를 바꾸지 않음. 모바일 목표는 유지하되 구현됐다고 표시하지 않음.

## 6. 재심 및 실제 검증 항목

실제 사용자 Chrome의 반복 사용 UX, 로그인·쿠키가 필요한 영상, 전송량, 탭 녹화 음성, 일반 설치와 모바일 전체는 미검증임. 연령 제한 영상의 실패 메시지와 40초 구간은 2026-10-16 QA에서 확인함. Mac 바이너리와 변환, Windows 개발 연결과 YouTube 획득/변환은 위 최신 기록을 따름. 특히 녹화가 항상 더 가볍거나 구간 요청이 선택 길이만큼만 전송된다고 가정하지 않음.

참고 코드와 주의 사항:

- yt_clipper: YouTube 구간 표시, 크롭 좌표 및 드래그 복구.
- Clipcillo: 원본 재사용, 편집 상태와 내보내기. yt-dlp 라이브러리 다운로드를 그대로 이식해 프로세스 취소 모델을 잃지 않음.
- Chopify: 인코더 검사와 저해상도 초안. 추천 점수를 시청 성과로 읽지 않음.
- Reframe: 설정 복원. 설정에 따라 외부 지표 전송이 있으므로 전체 복사보다 작은 함수 단위를 검토함.
- Screenity: Chrome 녹화 흐름. 자체 코드 GPL-3.0이며 이번에는 이식하지 않음.
- 한국어 자막은 일반 기능 도입 시의 참고임. 한국어 매칭 결함 발견을 제품 타깃의 근거로 사용하지 않음.

## 7. 시작 명령

새 복제본이 필요할 때만 clone함.

```bash
git clone git@github.com:blazethrottle/clipman.git
cd clipman
git status --short
git remote -v
git branch --show-current
```

기존 복제본은 미커밋과 스테이징 변경이 없는 경우만 갱신함.

```bash
git pull --ff-only origin main
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m pytest -q
./.venv/bin/python -m pytest -m integration -q -rs
```

기존 가상환경이 있으면 먼저 확인하고 그대로 사용함. Windows는 `.venv/Scripts/python.exe`로 실행함. `bin/`이 없으면 통합 검사는 skip이 예상되며 성공 판정은 실제 passed 수와 출력 검사임.

## 8. 다음 세션에 전달할 시작 요청

> clipman의 사용자 동반 인수를 진행해줘. Mac mini의 ~/Projects/clipman에서 docs/HANDOFF.md와 docs/verification/2026-10-16-final-qa.md를 먼저 읽어. 최종 QA는 2026-10-16에 끝났고 결함 1건(재실행 시 포트 유지)은 수정돼 있어. 남은 일은 ① 내 Chrome 프로필에서 사이드 패널 → 편집 → 저장을 반복하는 인수(4절 3항)와 ② 결정 2건(연령 제한 영상 안내 문구를 나눌지, ZIP 사본의 Gatekeeper 경고를 언제 확인할지)이야. 구현은 다시 만들지 말고, 결함이 나오면 재현 절차와 회귀 검사를 먼저 추가해서 고쳐줘. 지금은 개인 용도이며 상업용 배포는 나중에 결정해.
