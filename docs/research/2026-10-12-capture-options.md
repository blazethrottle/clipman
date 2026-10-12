# 클립맨 발췌 방식과 UI 방향 검토

승인 전 비교를 보존한 조사 기록임. 이후 초기 Chrome 확장 + 로컬 처리 프로그램 방향이 승인됨. [최신 승인 설계](../superpowers/specs/2026-10-12-clipman-capture-first-design.md)와 [핸드오프](../HANDOFF.md)가 실제 다음 작업의 기준임.

2026년 10월 12일 사용자 설명을 반영한 검토안임. 제품 목적과 사용 환경은 사용자 설명을 기준으로 확정하고, 출시 형태와 획득 방식 및 시각 디자인은 아래 제안으로 구분함. 실제 앱이나 확장 기능을 구현한 문서는 아님.

## 사용자 설명으로 확정한 기준

- 제품 정체성: YouTube에서 마음에 드는 영상의 특정 부분을 발췌하고 인용해 쇼츠로 재편집하는 도구임.
- 팬덤 영상에 국한하지 않음. 한국어 팬덤 특화라는 이전 제안은 철회함.
- 주 사용 순간: YouTube를 보다가 마음에 드는 구간을 발견했을 때 바로 발췌함.
- 다운로드를 유일한 수단으로 고정하지 않음. 부분 녹화와 다른 구간 획득 방식도 고려함.
- 경험 목표: 가볍고 쾌적하며 단순하지만 깔끔하고 예쁜 UI와 UX임.
- 사용 환경: 데스크톱은 Chrome, 모바일은 iOS YouTube 앱이며 Android도 고려함.
- 모바일 목표: 모바일에서 발췌, 편집과 저장까지 완료함. URL을 PC에 전달하는 기능만으로 축소하지 않음.
- 초기 버전 후보: 사용자가 Chrome 확장을 제안함. Chrome 초기 출시는 검토 후보이며 출시 범위 확정으로 표시하지 않음.

## 초기 출시 형태 비교

| 대안 | 사용 경험 | 장점 | 부담과 확인 조건 |
|---|---|---|---|
| Chrome 확장 단독 | YouTube에서 구간 선택 또는 탭 녹화 후 확장 편집 화면에서 쇼츠 저장 | 별도 로컬 프로그램 설치를 줄일 수 있음. 보는 화면에서 시작 가능 | 확장에서 기존 Python, yt-dlp와 ffmpeg 실행파일을 직접 실행하는 구조는 성립하지 않음. 탭 녹화와 브라우저 영상 처리 중심의 검증 필요. 녹화는 해당 구간을 재생하는 시간이 필요함 |
| Chrome 확장과 로컬 처리 프로그램 | 확장은 구간 선택과 편집 화면, 로컬 프로그램은 구간 획득과 인코딩 담당 | 기존 영상 도구 코드를 활용하고 원본 기반 정확한 편집을 검증하기 좋음. 처리 중 화면 반응을 분리할 수 있음 | 확장 외에 최초 로컬 프로그램 설치가 필요함. 실행과 연결 실패를 단순하게 처리하는 UX 필요 |
| 데스크톱과 모바일 앱 동시 개발 | Chrome 진입과 iOS 및 Android 공유 진입에서 같은 발췌 경험 제공 | 사용자의 최종 기기 범위를 한 번에 다룸 | 세 플랫폼의 구간 획득, 음성, 인코딩과 저장을 함께 검증해야 함. 초기 검증 범위가 가장 큼 |

**초기 후보로는 Chrome 확장과 로컬 처리 프로그램을 추천함.** 화면은 YouTube에서 바로 발췌하도록 바꾸되, 기존 처리 엔진을 사용하여 선택 구간의 영상 및 음성 품질을 먼저 검증할 수 있기 때문임. 무설치가 최우선 기준으로 추가되면 확장 단독 녹화 안을 다시 평가할 수 있음. 설치 부담과 개발 속도는 실측하지 않았으며 더 빠르거나 더 가볍다고 확정하지 않음.

Chrome Native Messaging은 확장과 설치된 네이티브 프로그램의 통신 수단임. 설치와 등록이 필요하므로 Chrome 확장을 설치하는 것만으로 기존 실행파일까지 자동 실행 가능하다고 표시할 수 없음. 현재의 localhost 연결 방식도 대안이므로 실제 연결 구현은 별도 선택 사항임. [공식 Native Messaging 문서](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)

## 영상 구간 획득 방식 비교

| 방식 | 적합한 순간 | 장점 | 제약 |
|---|---|---|---|
| 선택 구간 가져오기 | 이미 본 장면의 시작과 끝을 정해 원본 기반 편집 | 전체 파일을 먼저 저장하는 단계를 줄일 가능성 있음 | yt-dlp와 ffmpeg가 구간 기능을 지원하나 실제 전송량과 시크 정확도는 영상별 실측 필요. 선택 구간만큼만 네트워크를 쓴다고 보장하지 않음 |
| Chrome 탭 부분 녹화 | 재생되는 화면을 구간으로 담음 | 원본 URL 추출과 다른 경로를 제공하며 시청 화면에서 시작 가능 | 선택 구간 재생과 녹화 시간 필요. 지나간 구간은 다시 재생해야 함. 재생 품질, 버퍼링과 영상 UI가 결과에 영향을 줄 수 있음. 탭 음성도 확인 필요 |
| 전체 원본 확보 | 여러 구간을 반복해서 고르거나 재편집 | 원하는 시점으로 돌아가 편집하기 쉬움 | 다운로드 대기와 저장 공간 부담 가능. 기본 사용 흐름의 필수 선행 단계로 두지 않음 |

yt-dlp는 `--download-sections`로 시각 범위를 지정하고 ffmpeg를 통해 구간을 얻는 기능을 제공함. 정확한 컷을 위해 재인코딩이 필요한 경우가 있으므로 선택 구간의 앞뒤 여유를 확보하고 최종 편집에서 정밀하게 자르는 안을 검토할 수 있음. 여유 구간의 크기와 실제 전송량은 실측 후 결정함. [다운로드 옵션](https://github.com/yt-dlp/yt-dlp#download-options), [정밀 컷 FAQ](https://github.com/yt-dlp/yt-dlp-wiki/blob/master/FAQ.md)

Chrome의 `tabCapture`는 사용자 조작 후 현재 탭의 영상과 음성 스트림을 얻는 기능임. 캡처한 탭의 소리를 계속 사용자에게 재생하려면 오디오 연결을 유지해야 함. Chrome 서비스 워커와 offscreen document를 사용하는 공식 녹화 사례도 있음. 화면 공유용 `getDisplayMedia`는 매번 사용자 선택이 필요하고 음성 지원이 브라우저와 OS에 따라 다르므로, Chrome 확장과 일반 웹앱의 녹화를 같은 것으로 취급하지 않음. [tabCapture](https://developer.chrome.com/docs/extensions/reference/api/tabCapture), [공식 녹화 사례](https://developer.chrome.com/docs/extensions/how-to/web-platform/screen-capture), [getDisplayMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia)

현재는 구간 가져오기를 우선 검증하고 부분 녹화를 별도 대안으로 비교하는 것이 적절함. 녹화 실패가 구간 가져오기 성공을 의미하지 않고 그 반대도 아니므로, 결과 품질과 사용자 대기를 각각 측정해야 함. 항상 녹화하는 과거 구간 버퍼는 메모리, 저장과 개인정보 관련 UX를 추가하므로 초기 범위에 자동 편입하지 않음.

## YouTube를 보다가 바로 발췌하는 흐름

1. YouTube 영상 재생 중 확장의 시작 표시와 끝 표시로 구간을 지정함. 끝을 표시한 뒤 시작을 앞쪽으로 옮겨 방금 본 장면을 선택하는 조작도 제공하는 안임.
2. 재생 화면 옆 패널에서 선택 구간의 시작, 끝과 길이를 확인함. 영상 이동과 시작 및 끝 마커를 맞추고 선택 구간만 다시 재생함.
3. 구간이 확보되면 같은 작업에서 세로 결과 미리보기와 크롭 위치를 조정함. 소스 전체를 먼저 확보하는 단계를 사용자에게 강제하지 않음.
4. 쇼츠 만들기를 누르면 처리 상태를 표시하고 완료한 MP4를 저장함. 다시 크롭을 바꿔 출력할 수 있도록 확보한 구간은 필요한 동안 유지함.

Chrome Side Panel은 웹 콘텐츠 옆에 확장 UI를 유지할 수 있는 수단임. 패널을 닫거나 YouTube 내에서 다른 영상으로 이동해도 현재 구간의 영상 식별자와 선택 시각을 혼동하지 않도록 해야 함. [Side Panel 문서](https://developer.chrome.com/docs/extensions/reference/api/sidePanel)

임베드 플레이어를 대안으로 쓸 경우 YouTube IFrame API의 `getCurrentTime`과 `seekTo`는 재생 제어를 제공함. 이를 원본 영상 프레임이나 파일에 직접 접근하는 API로 해석하지 않음. 임베드를 허용하지 않는 영상도 있으므로 YouTube 시청 화면의 구간 표시와 로컬 편집 미리보기는 다른 단계로 설계함. [YouTube 플레이어 API](https://developers.google.com/youtube/iframe_api_reference)

## 단순하고 깔끔한 화면의 제안

- YouTube 시청 중에는 구간 표시 조작만 보임. 사용자 영상 위에 큰 도구 모음이나 대시보드를 덮지 않음.
- 좁은 패널에는 구간과 상태를 표시하고 정밀 편집이 필요할 때 확장 편집 탭을 사용함. 작은 폭에 원본과 세로 미리보기를 억지로 나란히 넣지 않음.
- 편집 화면은 영상 미리보기, 선택 구간과 세로 구도, 쇼츠 만들기의 세 부분으로 구성함.
- 전체 라이브러리, AI 점수와 고급 코덱 설정을 첫 화면에 두지 않음. 획득 방식 선택은 필요할 때 열고 내부 도구 이름은 사용자 흐름에 노출하지 않음.
- 소스 URL과 원래 선택 시각은 작업 데이터에 보존함. 출처 링크 복사나 영상에 넣을 출처 문구는 선택 기능 후보임. 모든 영상에 출처 자막을 강제로 넣는 결정은 하지 않음.

시각 방향의 첫 후보는 밝은 앱 배경과 영상 영역의 어두운 바탕을 함께 쓰는 편집 화면임. 색은 흰색 `#FFFFFF`, 옅은 회색 `#F3F5F7`, 본문색 `#18232F`, 강조색 `#356AE6`, 구분선 `#DDE3EA`를 제안함. 서체는 Pretendard와 시스템 서체를 사용하고 시각 숫자는 자리 폭을 맞춤. 여백과 정렬, 명확한 선택 상태로 질서를 만들며 장식 카드와 반복 애니메이션을 늘리지 않음. 색과 서체는 사용자 승인 전 시안 후보임.

구간 선택, 크롭, 처리 중과 완료 상태를 공통 스타일로 먼저 비교한 뒤 세부 장식을 다듬는 순서를 적용함. 이는 스타일 기준을 먼저 정하고 여러 상태를 함께 비교하는 검토 원칙을 적용한 제안임.

## iOS와 Android의 최종 목표

모바일에서도 YouTube 앱의 공유 메뉴에서 클립맨으로 진입해 구간 선택, 세로 편집과 기기 저장까지 완료하는 목표를 유지함. Chrome 확장으로 이 모바일 목표까지 구현했다고 표시하지 않음.

iOS는 Share Extension, Android는 `ACTION_SEND`를 받는 앱 진입점이 후보임. URL 공유만으로 현재 재생 시각이나 원하는 구간이 항상 전달되는 것은 보장되지 않으므로 공유된 내용에 시각이 없으면 사용자가 구간을 지정하는 화면이 필요함. [Apple 공유 확장](https://developer.apple.com/library/archive/documentation/General/Conceptual/ExtensibilityPG/Share.html), [Android 공유 수신](https://developer.android.com/training/sharing/receive)

모바일 편집 엔진 후보는 iOS AVFoundation과 Android Media3 Transformer임. 같은 구간과 크롭 설정을 공유할 수 있어도 기존 Python 서버와 실행파일을 모바일에 그대로 이식할 수 있다고 가정하지 않음. [AVAssetExportSession](https://developer.apple.com/documentation/avfoundation/avassetexportsession), [Media3 Transformer](https://developer.android.com/media/media3/transformer)

Android의 앱 화면 캡처는 MediaProjection을 사용하며 Android 14 이상에서는 캡처 세션마다 동의와 한 번만 쓰는 토큰 규칙을 적용해야 함. 다른 앱의 소리 캡처는 Android 10의 AudioPlaybackCapture 이후 가능하지만 대상 앱의 캡처 허용 정책과 권한 조건에 좌우됨. 모든 YouTube 영상의 소리를 녹화할 수 있다고 보장하지 않음. [MediaProjection](https://developer.android.com/media/grow/media-projection), [음성 캡처 조건](https://developer.android.com/media/platform/av-capture)

iOS의 녹화는 ReplayKit과 시스템 녹화 기능을 검토하되 다른 앱의 영상과 음성을 확보하는 실제 경로는 기기에서 검증해야 함. Apple은 ReplayKit과 AVPlayer 콘텐츠의 비호환을 명시하므로 이를 모든 영상 앱에 적용할 수 있는 녹화 엔진으로 가정하지 않음. 이 설명만으로 YouTube 앱의 내부 구현이나 모든 녹화 가능 여부를 단정하지 않음. 아직 iOS YouTube 앱에서 발췌용 영상과 음성을 확보하는 방식은 검증되지 않았으며, Chrome 방식으로 대체했다고 볼 수 없음. [ReplayKit](https://developer.apple.com/documentation/replaykit)

## 추가 녹화 레퍼런스

| 저장소 | 확인 범위 | 참고 내용 | 한계 |
|---|---|---|---|
| [Screenity](https://github.com/alyssaxuu/screenity/tree/dddeeb668ad285155a48fa89298f0fe2ef273579) | README, 메타데이터와 녹화 시작 및 발신 탭 전달 코드 | 확장 녹화 시작, 사용자 상태, 기록 탭과 편집 탭의 연결 | 자체 코드 GPL-3.0임. 전체 앱을 실행하거나 클립맨에 복사하지 않음. 클라우드 경로까지 초기 제품에 도입하지 않음 |
| [Kap](https://github.com/wulkano/Kap/tree/c42692fa63ac71ed192e01684beb78a1b864aa88) | README와 편집 타임바 코드 | 구간 선택과 녹화 후 편집의 단순한 UX | 자체 코드 MIT임. 기본 브랜치 확인 커밋은 2024년이며 최근 OS에서 정상 동작한다고 검증하지 않음 |
| [Aperture](https://github.com/wulkano/Aperture/tree/7591bb540c844fe6c47edeac34b17c25e92a717f) | README와 라이선스 메타데이터 | Mac 화면 영역 및 시스템 음성 녹화의 네이티브 대안 | 자체 코드 MIT임. Mac 전용 참고이며 iOS와 Android 지원 근거가 아님 |

## 다음 검증에서 해결할 질문

- 구간 획득과 탭 녹화 각각의 실제 대기, 결과 영상과 음성, 저장 공간을 같은 클립으로 비교함.
- Chrome 확장 단독의 브라우저 인코딩과 로컬 프로그램의 최초 설치 부담을 실제 사용 흐름에서 비교함.
- 구간 표시가 재생과 탐색을 방해하지 않는지, 패널과 편집 탭 전환이 과하지 않은지 시안으로 확인함.
- 모바일의 영상 구간 확보와 음성 유지 가능성을 iOS와 Android에서 별도로 실측함.
- 초기 Chrome 출시 범위와 모바일 출시 순서는 미확정임. 사용자의 제품 목적을 바꾸지 않고 구현 경로만 결정할 사항임.

정체성과 사용자 환경을 제외한 위 항목은 검토안임. 구현 코드, Chrome 확장 설치, 모바일 앱과 실제 녹화 또는 영상 획득은 이번 단계에서 수행하지 않음.
