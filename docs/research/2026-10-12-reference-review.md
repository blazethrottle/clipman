# 클립맨 공개 저장소 레퍼런스 조사

이 문서는 조사 및 사용자 정정의 기록임. 초기 Chrome 확장 + 로컬 처리 프로그램은 이후 사용자 승인됐으며 제품 방향의 정본은 [최신 승인 설계](../superpowers/specs/2026-10-12-clipman-capture-first-design.md)임.

2026년 10월 12일 서울 기준 조사 결과임. 최초 조사에서는 개인용 로컬 웹앱과 수동 구간 선택, 세로 9:16 변환을 기준으로 GitHub 공개 저장소 16개를 선별하고, 그중 12개의 기본 브랜치 코드를 대조함. 조사 시점과 커밋, 라이선스 파일은 [출처 목록](2026-10-12-reference-sources.json)에 기록함. 이후 사용자가 제품 정체성과 사용 환경을 명확히 해 아래 방향을 정정함. 획득 방식, Chrome 초기 버전과 모바일 목표는 [보완 검토](2026-10-12-capture-options.md)가 최신 기준임.

**클립맨의 정체성은 YouTube에서 마음에 드는 영상의 특정 부분을 발췌하고 인용해 쇼츠로 재편집하는 도구임.** 팬덤 영상이나 한국어 콘텐츠에 특화하는 결정은 없으며, 이전의 해당 제안은 철회함. Clipcillo는 편집 구조, yt_clipper는 재생 중 구간 표시와 크롭 조작, dawn-cut은 자막 기능을 도입할 때의 한국어 처리 참고임. 영상 획득을 전체 다운로드로 고정하지 않고 구간 획득과 부분 녹화도 검토함.

## 현재 설계에서 바꿔야 할 전제

클립맨의 main은 `636341d8a3843313e50d46cff8ee8fac5cba46c0`이며 영상 도구 어댑터 구현 후 작업 관리와 서비스, API 및 화면 개발이 남은 상태임. [인계 문서](https://github.com/blazethrottle/clipman/blob/636341d8a3843313e50d46cff8ee8fac5cba46c0/docs/HANDOFF.md)

기존 cobalt 분석에서 편집을 클립맨의 차별점으로 본 것은 cobalt와의 비교로는 유효함. 다만 다운로드와 편집의 통합 자체가 다른 도구와 구별되는 기능이라는 해석은 이번 조사로 유지하기 어려워짐. Clipcillo는 URL 입력, 로컬 원본, 구간 선택, 세로 편집과 MP4 출력의 연결 코드를 이미 갖고 있음. 사용자가 밝힌 우선 경험은 YouTube를 보다가 바로 발췌하는 것이며, 목적은 가볍고 쾌적하고 단순하면서 깔끔하고 예쁜 UI와 UX임. 전체 다운로드는 제품 정체성이 아니라 구간을 얻는 여러 수단 중 하나임. [Clipcillo](https://github.com/Fierillo/clipcillo/tree/3c1a587b1748d864527699ddc21adbef49032b8c)

음성 전사 중심의 자동 하이라이트 추천은 모든 영상에서 마음에 드는 장면을 고르는 문제와 다름. 음성이 없거나 음악, 스포츠와 시각적 사건 중심인 영상에서는 자막의 문장 품질과 얼굴 크기만으로 선택 기준을 만들 수 없음. 클립맨은 사용자가 마음에 드는 구간을 직접 선택하는 경험을 중심에 둠. [shortsgen의 제한](https://github.com/kakha13/youtube-shorts-generator/blob/48e780647f95e290f92694ea60cafc4bea0acd25/README.md)

## 참고할 저장소와 적용 범위

아래 12개 저장소는 LICENSE 본문에서 자체 코드의 MIT 표기를 확인함. 라이브러리, 모델, 폰트와 번들 실행파일의 권리까지 MIT라는 뜻은 아님. 표의 기능은 코드 존재를 확인한 내용이며 완성된 앱의 실사용 품질을 보증하지 않음.

| 저장소 | 실제로 참고할 부분 | 클립맨 적용 범위 | 이식할 때의 제약 |
|---|---|---|---|
| [Fierillo/clipcillo](https://github.com/Fierillo/clipcillo/tree/3c1a587b1748d864527699ddc21adbef49032b8c) | FastAPI와 브라우저 편집, 원본 재사용, 파형, 상태 복원, 비동기 출력 | v1 화면과 서비스의 가장 가까운 참고 | 프런트는 일반 JavaScript임. 다운로드는 yt-dlp 라이브러리이므로 클립맨의 실행파일과 프로세스 취소 계약에 맞춰야 함 |
| [exwm/yt_clipper](https://github.com/exwm/yt_clipper/tree/02318b0f5ba6b23c8d11eaa13d4581cf83794f77) | YouTube 재생 중 구간 표시, 영상 좌표 환산, 크롭 오버레이, 회전과 드래그 복구 | 초기 Chrome 진입 UX, 크롭 조작과 테스트 | userscript와 CLI 구조임. 전역 화면 상태에 연결된 부분을 분리하고 확장 UI에 맞춰야 함 |
| [reframe-oss/reframe](https://github.com/reframe-oss/reframe/tree/4af01e56ecc9f8740bcf51e503ce671519f13d7f) | 화면비 선택, 편집 설정 저장과 복원, 잘못된 설정 방어 | v1 화면과 설정 복원 | Next.js와 FFmpeg.wasm 구조이므로 네이티브 FFmpeg 엔진 대체에는 부적합함. 설정에 따라 Datadog 지표 전송 코드가 활성화됨 |
| [mehbul/chopify](https://github.com/mehbul/chopify/tree/99fa3e3d81be7ce35debf1e302a5c5da75f53f62) | 시작 전 환경 검사, 저해상도 초안, 후보를 고른 뒤 출력 | 설치 진단과 후속 초안 검토 | CLI임. 기본 추천 점수는 영어 표현과 단어 밀도를 사용하는 규칙이며 실제 시청 성과를 검증한 점수가 아님 |
| [kwakseongjae/dawn-cut](https://github.com/kwakseongjae/dawn-cut/tree/7de68fce41505d8092ec227806b8d4bea4127675) | 한국어 어절 복원, 자막 타이밍과 구간 편집 후 시간 변환, 한국어 자막 스타일 | v2 자막의 핵심 참고 | Electron과 React 기반임. whisper.cpp의 토큰 형식이 전제이므로 faster-whisper 출력에 그대로 적용할 수 없음 |
| [SysAdminDoc/Vertigo](https://github.com/SysAdminDoc/Vertigo/tree/a3d84ed733959496c4b4ec3f220565498fbd4156) | 수동 크롭, 흐린 배경, 장면 경계에 따른 크롭 경로, 자막 안전 영역 경고 | v1.1과 자동 추적 확장 | PyQt6 데스크톱 앱임. 일반 인물과 발화자 추적은 무대의 지정 멤버 추적과 다름 |
| [RishikeshAluguvelli/VerticalMaker](https://github.com/RishikeshAluguvelli/VerticalMaker/tree/a725a37f921c73677fc7fcc150da6aa64770e8a3) | 발화 구간별 고정 크롭, 장면 전환 시 추적 초기화, 다인 분할 화면 | 인터뷰 영상의 후속 추적 기능 | CPU 기반 CLI이며 모델 조달이 필요함. 발화자 판정과 무대에서의 멤버 선택은 별도 문제임 |
| [kakha13/youtube-shorts-generator](https://github.com/kakha13/youtube-shorts-generator/tree/48e780647f95e290f92694ea60cafc4bea0acd25) | 추천 문장을 원문에 찾아 시각을 복구, 후보 이유와 메타데이터 저장, ASS 자막 | v2 자막과 v3 추천 | 한국어 매칭 결함을 직접 재현함. 얼굴 추적도 클립 전체의 고정 위치를 구하는 방식임 |
| [Gutsken/Autoclip](https://github.com/Gutsken/Autoclip/tree/5d0eac36fa615b79dd2104083bf273a96f8d68bb) | 단일 작업 큐, 재시작 시 중단 작업 처리, 후보 검토 화면 | v1 작업 관리 패턴, 후속 작업 복구 | SQLite와 이벤트 전달에 연결된 전체 큐의 이식 비용이 큼. 클립맨 v1의 인메모리 계획을 자동으로 변경하지 않음 |
| [fralapo/clippyme](https://github.com/fralapo/clippyme/tree/724233ec6147a38b9bfd02078c30d2b01cae0fd2) | 원자적 작업 기록 저장, 취소와 중단의 분리, 재프레이밍 파이프라인 | 작업 복구가 필요해질 때 참고 | 전사와 추천에 외부 API 경로가 있음. 취소 시 출력 폐기 정책이 클립맨의 보존 계약과 다름 |
| [Anil-matcha/AI-Youtube-Shorts-Generator](https://github.com/Anil-matcha/AI-Youtube-Shorts-Generator/tree/3d11f2e6ecbbb9757d788e1bd05695c01f3e6c6c) | 후보 중복 제거, 추천 이유와 구간 자료형 | v3 추천의 작은 함수 참고 | 기본은 MuAPI 경로임. local 모드도 OpenAI 또는 Gemini에 추천을 요청하므로 완전 오프라인이 아님 |
| [S07K/cutaway](https://github.com/S07K/cutaway/tree/e9c6cc06b549d7fa857bb8f43f02c47a39368e33) | 시간과 픽셀 환산, 스냅 테스트, 미리보기와 출력이 같은 장면 정의 사용 | v1 조작과 검증 원칙 | Pixi와 WebCodecs 엔진 전체는 과도함. Whisper 최초 모델 다운로드와 브라우저 오디오 인코더 지원 조건이 있음 |

추가로 [Prekzursil/Reframe](https://github.com/Prekzursil/Reframe), [WyattBlue/auto-editor](https://github.com/WyattBlue/auto-editor), [sanyo4ever/local-shorts-studio](https://github.com/sanyo4ever/local-shorts-studio), [imputnet/cobalt](https://github.com/imputnet/cobalt)를 1차 선별함. 이 네 저장소는 위 12개와 같은 깊이의 구현 검토를 하지 않았으므로 코드 이식 후보로 확정하지 않음. `reframe-oss/reframe`과 `Prekzursil/Reframe`은 이름이 비슷한 별개 제품임.

## 가져올 코드와 아이디어

| 적용 시점 | 후보 코드 | 적용 내용 | 필요한 조정과 완료 조건 |
|---|---|---|---|
| v1 크롭 UI | yt_clipper의 [`getVideoScaledCropComponents`](https://github.com/exwm/yt_clipper/blob/02318b0f5ba6b23c8d11eaa13d4581cf83794f77/src/markup/crop-utils.ts#L50)와 [`crop-utils.test.ts`](https://github.com/exwm/yt_clipper/blob/02318b0f5ba6b23c8d11eaa13d4581cf83794f77/src/markup/crop-utils.test.ts) | 표시 좌표를 원본 해상도에 맞게 환산하고 회전 상태를 분리 | 클립맨의 가로 오프셋 `crop_x`만 남김. 화면 크기와 원본 해상도가 달라도 같은 위치를 출력하는지 검증 |
| v1 드래그 | yt_clipper의 [`registerActiveDragCleanup`](https://github.com/exwm/yt_clipper/blob/02318b0f5ba6b23c8d11eaa13d4581cf83794f77/src/markup/util/drag-recovery.ts) | 창 전환과 드래그 중단 후 조작 상태 복구 | Svelte 컴포넌트 종료 시 정리 연결. 창 전환 후 타임라인이나 크롭 프레임이 계속 따라오지 않아야 함 |
| v1 설치 진단 | Chopify의 [`check_environment`](https://github.com/mehbul/chopify/blob/99fa3e3d81be7ce35debf1e302a5c5da75f53f62/chopify.py#L49) | 파일 존재뿐 아니라 실제 실행, H.264와 AAC 인코더 지원 검사 | 시스템 PATH 대신 클립맨 `bin/` 경로 사용. v2에서는 자막에 필요한 libass 필터와 한국어 폰트를 추가 검사 |
| v1 편집 설정 | Reframe의 [`loadPersistedRecipe`와 `migrateRecipe`](https://github.com/reframe-oss/reframe/blob/4af01e56ecc9f8740bcf51e503ce671519f13d7f/src/lib/editorPersistence.ts) | 화면 새로고침 때 트림과 크롭 설정 복원, 잘못된 JSON과 범위 방어 | 현재 job과 원본 존재를 다시 확인해야 함. 브라우저 설정 저장만으로 서버 재시작 후 작업 복구까지 된다고 표시하지 않음 |
| v1 다운로드 보호 | Clipcillo의 [`download_video`](https://github.com/Fierillo/clipcillo/blob/3c1a587b1748d864527699ddc21adbef49032b8c/app/services/download.py#L65) | 단일 영상 처리 옵션과 진행률 표시 참고 | `noplaylist=True`에 대응하는 실행파일 옵션 검토. 라이브러리 다운로드 구현은 복사하지 않고 기존 Popen 취소 모델 유지 |
| 후속 원본 캐시 | Clipcillo의 [`normalize_url`, `cache_key_for_url`, `materialize_for_job`](https://github.com/Fierillo/clipcillo/blob/3c1a587b1748d864527699ddc21adbef49032b8c/app/services/cache.py) | 주소 표기가 달라도 같은 원본 재사용, 임시 파일과 보존 자료 구분 | 클립맨은 화질 선택이 있으므로 URL만 캐시 키로 쓰면 부족함. 화질과 실제 포맷을 함께 관리하거나 보유 원본이 요청 품질을 만족하는지 검사 |
| v1.1 출력 검토 | Chopify의 [`PREVIEW_DIMS`와 `--preview`](https://github.com/mehbul/chopify/blob/99fa3e3d81be7ce35debf1e302a5c5da75f53f62/render_clips.py#L37) | 저해상도 초안을 보고 확정본 생성 | 초안과 최종본에 같은 구간과 크롭 설정 사용. 출력 속도 이점은 Mac에서 별도 측정 |
| v2 한국어 자막 | dawn-cut의 [`whisperNaturalToWords`](https://github.com/kwakseongjae/dawn-cut/blob/7de68fce41505d8092ec227806b8d4bea4127675/packages/core/src/whisper.ts#L97), [`whisper.test.ts`](https://github.com/kwakseongjae/dawn-cut/blob/7de68fce41505d8092ec227806b8d4bea4127675/packages/core/src/whisper.test.ts), [`transcriptToCues`](https://github.com/kwakseongjae/dawn-cut/blob/7de68fce41505d8092ec227806b8d4bea4127675/packages/core/src/subtitles.ts#L40) | 한국어 어절과 조사 복원, 구두점 처리, 잘라낸 뒤 자막 시간 재배치 | 엔진 출력 자료형에 맞춰 적용. 한글과 영문 혼용, 이름, 숫자와 반복 문장의 회귀 검사 필요 |
| 후속 자동 크롭 | Vertigo의 [`_scene_clamp`와 `build_plan`](https://github.com/SysAdminDoc/Vertigo/blob/a3d84ed733959496c4b4ec3f220565498fbd4156/core/reframe.py), VerticalMaker의 [`segment_crop_xy`](https://github.com/RishikeshAluguvelli/VerticalMaker/blob/a725a37f921c73677fc7fcc150da6aa64770e8a3/verticalmaker/modes/track.py#L30) | 장면 전환을 가로질러 크롭 창이 움직이지 않도록 하고 구간별 위치 유지 | 가장 큰 얼굴이나 발화자가 사용자가 원하는 피사체라는 보장은 없음. 대상 지정과 검출 실패 시 수동 위치 유지 규칙 필요 |
| v3 추천 시각 | shortsgen의 [`find_quote`와 `resolve_span`](https://github.com/kakha13/youtube-shorts-generator/blob/48e780647f95e290f92694ea60cafc4bea0acd25/shortsgen/anchor.py) | LLM이 제시한 숫자보다 원문 인용 구절로 실제 시각 계산 | ASCII 전용 정규화 수정, 반복 문장에 앞뒤 문맥 추가, 매칭 실패 시 사용자가 구간을 확인하도록 안내 |

위키에서 제안한 장면 캡처와 프레임 검사도 좌표 환산 검증에 연결할 수 있음. 해상도와 길이만 검사하면 잘못된 인물 위치를 자른 출력은 통과할 수 있으므로, 화면 미리보기와 실제 결과를 여러 시점에서 비교하는 검사를 함께 두는 것이 적절함.

## 그대로 가져오면 생기는 문제

**한국어 문장 매칭 실패를 재현함.** shortsgen은 `normalize`에서 영문 소문자와 숫자 외의 문자를 제거함. `안녕하세요`는 빈 문자열이 되고 `안녕하세요 오늘` 인용 구절은 매칭되지 않음. 같은 스냅샷의 기존 테스트 80개는 모두 통과했으므로 테스트 통과와 한국어 지원을 구분해야 함. 인용 구절로 실제 시각을 찾는 아이디어는 유용하지만 함수의 원문 복사는 부적합함. [anchor.py](https://github.com/kakha13/youtube-shorts-generator/blob/48e780647f95e290f92694ea60cafc4bea0acd25/shortsgen/anchor.py#L25)

**얼굴 검출이 사용자가 원하는 피사체 추적을 뜻하지 않음.** shortsgen의 `find_crop_center`는 24개 표본 프레임에서 가장 큰 얼굴을 찾고 중앙값 하나로 클립의 위치를 고정함. 사람이 이동하거나 다른 사람이 카메라에 가까워지는 상황을 해결하지 않음. VerticalMaker의 입 움직임과 음성 기반 발화자 추정도 모든 유형의 영상에 적합하다는 검증은 없음. [faces.py](https://github.com/kakha13/youtube-shorts-generator/blob/48e780647f95e290f92694ea60cafc4bea0acd25/shortsgen/faces.py), [VerticalMaker 분석 코드](https://github.com/RishikeshAluguvelli/VerticalMaker/blob/a725a37f921c73677fc7fcc150da6aa64770e8a3/verticalmaker/analysis.py)

**local이라는 소개가 외부 전송 부재를 뜻하지 않음.** Anil-matcha 생성기의 local 모드도 OpenAI 또는 Gemini API를 호출함. clippyme에는 Gemini 추천과 클라우드 전사 경로가 있음. reframe-oss는 설정 값이 있을 때 Datadog 지표와 오류 수집을 활성화하며 세션 화면 녹화는 비활성화함. 이 코드를 참고하더라도 클립맨의 개인 로컬 사용과 외부 서비스 선택 조건을 유지해야 함. [local LLM](https://github.com/Anil-matcha/AI-Youtube-Shorts-Generator/blob/3d11f2e6ecbbb9757d788e1bd05695c01f3e6c6c/shorts_generator/local/llm.py), [clippyme 파이프라인](https://github.com/fralapo/clippyme/blob/724233ec6147a38b9bfd02078c30d2b01cae0fd2/src/clippyme/pipeline/main.py), [DatadogInit](https://github.com/reframe-oss/reframe/blob/4af01e56ecc9f8740bcf51e503ce671519f13d7f/src/components/DatadogInit.tsx)

**추천 점수를 실제 반응 예측으로 읽으면 안 됨.** Chopify 기본 점수는 영어 표현과 단어 밀도 등의 규칙이며 shortsgen 점수는 모델이 매긴 항목별 평가임. 시청 지속이나 조회수를 검증한 점수로 볼 근거는 확인되지 않음. 클립맨에서는 사용자의 직접 구간 선택을 중심에 두고 자동 추천은 후속 참고로 둠. [Chopify 점수 계산](https://github.com/mehbul/chopify/blob/99fa3e3d81be7ce35debf1e302a5c5da75f53f62/score_clips.py#L112)

**취소와 보존 계약이 다름.** clippyme는 취소, 작업 중단과 일시 정지를 별도 상태로 관리함. `cancelled`는 출력 폐기, `stopped`는 이미 생성한 출력 보존, `paused`는 일시 정지임. 클립맨은 인코딩 취소 시 원본을 보존해야 하므로 상태 기계와 파일 삭제 범위를 그대로 이식할 수 없음. [취소 계약](https://github.com/fralapo/clippyme/blob/724233ec6147a38b9bfd02078c30d2b01cae0fd2/src/clippyme/jobs/job_control.py#L19)

**브라우저 엔진 전체 교체는 v1의 검증 범위를 넓힘.** Reframe의 FFmpeg.wasm과 Cutaway의 WebCodecs는 클립맨의 네이티브 FFmpeg 실행 모델과 다름. Cutaway는 일부 브라우저에서 오디오 인코더가 없으면 영상만 출력할 수 있음. 클립맨의 음성 유지 기준을 고려하면 화면과 좌표 처리 아이디어를 참고하고 기존 출력 엔진을 유지하는 편이 적절함. [오디오 지원 조건](https://github.com/S07K/cutaway/blob/e9c6cc06b549d7fa857bb8f43f02c47a39368e33/apps/web/src/features/export/capabilities.ts#L111)

## 라이선스와 참고 방식

12개 코드 검토 대상의 자체 코드는 MIT이며 재사용한 코드의 저작권과 허가문을 보존해야 함. `reframe-oss/reframe`은 GitHub API의 라이선스 값이 비어 있으나 저장소의 `MIT LICENSE` 파일에서 실제 조건을 확인함. API 표시 부재를 라이선스 부재로 해석하지 않음. [Reframe 라이선스](https://github.com/reframe-oss/reframe/blob/4af01e56ecc9f8740bcf51e503ce671519f13d7f/MIT%20LICENSE), [MIT 조건](https://choosealicense.com/licenses/mit/)

cobalt는 루트와 웹 코드의 라이선스가 다름. 루트는 AGPL-3.0이며 웹은 CC BY-NC-SA 4.0임. 이번 적용안에서는 cobalt 화면의 단순한 입력 흐름만 참고하고 코드를 이식할 후보에는 포함하지 않음. [루트 라이선스](https://github.com/imputnet/cobalt/blob/main/LICENSE), [웹 라이선스](https://github.com/imputnet/cobalt/blob/main/web/LICENSE)

실제 코드 이식이 시작되면 출처 저장소, 커밋, 파일, 수정 내용과 라이선스를 별도 기록해야 함. 라이선스 고지를 제품 화면 하단에 추가할 필요는 없으며 저장소의 라이선스 및 출처 문서로 관리할 수 있음. 클립맨 자체 라이선스는 현재 미정이므로 공개 배포 범위를 정할 때 함께 결정할 사항임.

## 기존 로컬 앱 계획의 대안 검토

아래는 최초 조사에서 검토한 로컬 앱 대안임. Chrome 초기 버전, 구간 획득과 모바일 완주 목표를 반영한 최신 대안은 [보완 검토](2026-10-12-capture-options.md)의 비교를 따름.

| 대안 | 장점 | 부담과 조건 | 판단 |
|---|---|---|---|
| 기존 클립맨에 작은 단위로 적용 | 수동 편집 중심의 간단한 UI와 Popen 취소, 원본 보존 계약 유지 | API와 화면 구현은 계속 필요함 | 추천. v1의 조작과 설치 검증부터 참고 |
| Clipcillo를 기반으로 개조 | URL부터 출력까지 구현된 흐름을 실사용 후보로 검토 가능 | Svelte 계획 변경, 여섯 단계의 화면 축소, ML 의존성 정리와 취소 방식 조정 필요 | 바로 쓸 도구가 우선일 때 별도 실행 비교 후보 |
| 자동 쇼츠 생성기를 기반으로 확장 | 자막과 추천 및 추적의 연결 구조 확보 | 외부 API, 모델, 라이브러리와 품질 검증 범위가 v1보다 커짐 | v2와 v3 참고. v1 기반 교체는 보류 |

## 기존 로컬 구현 계획에 참고할 항목

아래 항목은 기존 로컬 처리 계획의 보완 후보임. 초기 출시 형태를 Chrome 확장으로 선택할 경우 입력과 구간 획득 경로를 먼저 검증하고 계획을 다시 구성해야 함.

1. M1 실물 검증에 시작 전 실행파일과 인코더 진단을 추가하고 Mac 실제 변환을 확인함.
2. M2와 M3의 다운로드, 취소, 원본 보존을 기존 계약대로 구현함. 단일 영상 보호 옵션과 결과 파일 검사를 포함함.
3. M5 편집 화면에서 yt_clipper의 좌표 테스트와 드래그 복구를 먼저 참고함. 구간 숫자 입력과 프레임 오버레이를 같은 설정에서 계산함.
4. 화면 새로고침 때 현재 job과 편집 설정을 복원함. 서버 재시작 복구와 전역 원본 캐시는 별도 후속 범위로 남김.
5. v1 완주 후 저해상도 초안과 흐린 배경을 검토함. v2는 한국어 어절 및 자막 처리, v3는 후보 이유와 실제 문장 시각 복구를 참고함.

## 직접 검증한 범위

- shortsgen `48e7806`: 기존 테스트 80개 통과. 별도 한국어 문장 매칭에서 빈 문자열과 매칭 실패를 재현함.
- Chopify `99fa3e3`: 순수 로직 테스트 57개 통과. FFmpeg 출력과 추천 품질의 실사용 검증은 아님.
- Vertigo `a3d84ed`: 세 테스트 파일 실행을 시도했으나 OpenCV 패키지 미설치로 수집 중 오류 발생함. 앱 결함으로 판정하지 않음.
- 나머지 앱은 README, 실제 함수, 테스트 파일과 LICENSE를 정적으로 대조함. 전체 UI와 실제 영상 내보내기는 실행하지 않음.
- 별점과 갱신 날짜는 후보 탐색 자료로만 사용함. 검증된 수요, 안정성이나 코드 품질의 증거로 사용하지 않음.
- 클립맨 코드는 수정하지 않음. 이 보고서의 제품 방향 해석을 사용자 설명에 따라 정정했으며 기존 GitHub 계획은 아직 개정하지 않음. 기능과 구현 방식의 제안은 후속 검토 후보임.
