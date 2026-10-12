# Chrome 개발 연결과 개인 릴리즈 검증

2026-10-12 Windows x64, Python 3.13.5, Node 22.17.1 및 Playwright Chrome for Testing 156.0.8078.4에서 수행함. 개인 Chrome 프로필을 변경하지 않고 독립 시험 프로필을 사용함.

## 결과

| 검사 | 결과 | 범위 |
|---|---|---|
| 기본 pytest | 178 passed, 9 deselected | 기존 기반, API 출처/키/요청/경로, 프로세스 경합/트리, 기기 키 보존, POSIX 그룹 대역 검사 |
| pytest -m integration | 9 passed, skipped 0 | 실제 인코딩, 합성 HTTP 구간 및 장면/음성, API 확보/출력/재편집, 좌우 크롭 장면 |
| npm test | 5 passed | loopback 연결, 허용 API, 영상 ID/탭 변경, 네이티브 픽셀 및 content script 중계 거부 |
| npm run test:browser | 1 passed | 실제 MV3 로드, 영상 표시, 실제 MP4 디코딩/출력/다운로드/재편집, 미저장 상태 복원, 영상 이동, 폭 430px, 저장소 키 격리 |
| npm run build | 통과 | CSP 아래에서 번들 Svelte 패널/편집 및 로컬 확장 파일 생성 |
| pip check | 통과 | 고정 backend 의존성 |
| 신규 실행기 프로세스 | 통과 | 9000 점유 시 다른 실제 포트, 연결 안내 200, URL에 키 없음 |
| 개인 ZIP | 내용/압축/해시 및 압축해제본 확장 검사 | 최신 artifact 명세 참조 |

Starlette가 기존 httpx 기반 TestClient의 향후 변경을 안내하는 경고 1개를 냄. 검사 실패는 아니며 이번 기능과 무관한 의존성 교체는 하지 않음. Playwright 실행 시 환경의 NO_COLOR/FORCE_COLOR 경고도 있었음.

## 실제 YouTube 단일 영상

`https://www.youtube.com/watch?v=jNQXAC9IVRw`의 0~2초를 실제 서비스로 확보함. 결과는 320x240, 2.0초, 음성 있음. 같은 원본의 로컬 0~1초를 중앙 크롭하여 출력한 결과는 1080x1920, 1.0초, 음성 있음, 279668 bytes, SHA256 `395fd4ad881e06837d258f6048df880e5a44d4544e75c62b2d36374cefbf67ae`임. 확보와 출력 상태는 downloaded 및 done임. 영상 자체는 임시 시험 폴더에서 검사 후 정리했고 공개 저장소에 포함하지 않음.

기존 테스트 영상 BaW_jenozKc는 현재 unavailable 응답을 받아 성공 근거로 쓰지 않음. yt-dlp가 지원 JavaScript 런타임 미설정 경고를 냈으나 위 다른 영상은 확보/변환에 성공함. 다양한 화질 및 제한 영상, 쿠키, 런타임 조건은 후속 관문임. 단일 성공에서 범용 성공률을 추정하지 않음.

## 브라우저 시나리오의 의미

합성 영상이 있는 YouTube 모양의 시험 페이지를 제공하고 content script의 실제 isolated world와 MV3 서비스 워커를 실행함. 브라우저 시나리오의 확보 파일은 시험 하네스에서 소유한 합성 파일로 대체함. 구간 확보의 실제 yt-dlp 호출은 별도 통합 검사 및 위 YouTube 단일 검사로 확인함.

패널은 확장 페이지를 탭으로 열어 검사함. 실제 Chrome 사이드 패널의 화면 경계와 도구 모음에서 여는 UX는 사용자 Chrome의 인수 관문으로 남김. 화면은 logs/chrome-panel.png, chrome-editor.png, chrome-editor-narrow.png로 생성하고 시각 확인함. 화면 폭별 네이티브 crop_x 및 실제 좌우 색상 출력도 분리해 검사함.

## 독립 리뷰 반영

리뷰어 1명이 쓰기 없이 핵심 경계를 검토함. storage.local 기본 content script 노출을 지적받아 TRUSTED_CONTEXTS 설정을 모든 키 처리 전에 await하도록 수정함. CDP로 실제 content isolated world에서 키 읽기 실패를 확인함. POSIX 부모 종료 뒤 SIGTERM 무시 자식이 남을 수 있는 경로는 부모 poll과 무관하게 그룹 KILL을 보내도록 수정하고 2개 대역 검사로 확인함. Windows 실제 부모/자식 종료는 별도 통과함. macOS 실물 검증은 아님.

미저장 편집 복원의 Svelte 초기화 반응성 오류와 편집 탭 왕복 후 마커 소실도 브라우저 실패로 확인 후 수정함. 한글 시험 페이지 및 Range 영상 응답의 하네스 결함을 고친 후 실제 디코딩으로 검증함.

## 남은 관문

본인 Chrome에서 로컬 확장/처리 프로그램을 최초 설치하고 실제 YouTube 시청부터 저장까지 인수, 다양한 영상의 장면 시각/품질/전송량, Mac/모바일 실기기, 일반 설치/업데이트, 스토어 정책 심사와 등록/게시가 남음. 릴리즈 방식은 docs/RELEASE.md를 따름.

## GitHub 기록용 패키지 보완

개인 ZIP을 docs/artifacts에 기록하기 전에 번들 제3자 런타임의 라이선스 고지를 추가함. 기존 브라우저 검사 패키지의 JavaScript/HTML/CSS/manifest 및 설치 안내가 새 빌드와 바이트 단위로 동일함을 확인함. 변경은 정적 고지 파일 1개이며 전체 ZIP의 압축 검사, 내용 대조와 해시를 새로 확인함. 새 해시는 personal-package.json을 따름. 화면 3개는 logs의 검토본을 docs/screenshots/2026-10-12로 복사하고 바이트 일치를 확인함.
