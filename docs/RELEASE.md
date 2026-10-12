# clipman의 개인 설치와 릴리즈 경로

확인일: 2026-10-12, 서울 기준. 현재 추천은 **본인용 로컬 설치로 먼저 사용성을 검증하는 것**임. Chrome Web Store 등록은 개인용 개발자 모드 설치의 필수 조건이 아님.

## 선택지

| 방식 | 설치와 업데이트 | 비용 및 관문 | 이번 단계 판정 |
|---|---|---|---|
| 개인용 로컬 폴더 | 개발자 모드에서 압축해제된 확장 폴더를 로드함. 변경 후 확장과 YouTube 탭을 새로고침함 | 스토어 계정/등록비/심사 없음. 최초 수동 로드와 업데이트 필요 | 추천. 개발용 ZIP 및 이 PC의 빌드 폴더 준비 |
| 스토어 Private 또는 Unlisted | Private는 지정한 Google 계정/그룹, Unlisted는 링크를 아는 누구나 설치 가능함 | 개발자 등록 및 일회성 등록비, 정책 심사와 배포 설정 필요 | 후속 후보. 심사 제출 전 요구 자료와 정책 검토 필요 |
| 스토어 Public | 일반 검색과 설치, 스토어를 통한 업데이트 | 위 등록/심사와 공개 설명/지원/개인정보 선언, 로컬 처리 프로그램의 설치 배포 필요 | 일반 공개 배포는 아직 미준비 |

Unlisted는 비공개 접근 제어가 아니며 링크가 공유되면 다른 사람도 설치할 수 있음. Private/Unlisted/Public는 같은 정책 심사를 받음. [공식 배포 설정](https://developer.chrome.com/docs/webstore/cws-dashboard-distribution)

Windows와 macOS에서 임의 CRX 파일이나 자체 서버를 이용한 일반 외부 자동 설치를 개인용 ZIP의 대체로 약속하지 않음. Chrome의 공식 외부 설치는 이 플랫폼에서 스토어 경로를 요구함. 기업 관리 정책은 별도 경로이며 이번 개인 설치에는 적용하지 않음. [공식 외부 설치 문서](https://developer.chrome.com/docs/extensions/how-to/distribute/install-extensions)

## 이 PC에서 처음 사용하기

1. `C:/Users/DREAMUS/Documents/clipman/start.cmd`를 열면 로컬 처리 프로그램과 연결 안내 페이지가 실행됨. 개발 환경과 Windows 바이너리는 이 PC에 준비됨.
2. Chrome의 퍼즐 모양 확장 메뉴에서 **확장 프로그램 관리**를 열고 **개발자 모드**를 켬.
3. **압축해제된 확장 프로그램을 로드합니다**를 누르고 `C:/Users/DREAMUS/Documents/clipman/extension/dist` 폴더를 선택함.
4. 퍼즐 메뉴에서 clipman을 도구 모음에 고정함. 설치 전에 열려 있던 YouTube 탭은 새로고침함.
5. clipman 아이콘을 누르고 로컬 안내 페이지의 **연결 코드 복사**로 얻은 코드를 패널에 붙여 넣음.
6. 영상에서 시작과 끝을 표시한 뒤 **이 구간 편집하기**, 구도 조절과 **쇼츠 만들기**, **MP4 저장** 순서로 사용함.

업데이트 시 기존 빌드 폴더 위치와 manifest의 공개 key를 유지하고 확장 관리의 새로고침 버튼을 누름. 코드가 바뀐 YouTube 탭도 새로고침함. 같은 포트에서 다시 실행하면 기기 연결 키를 보존하므로 기존 연결을 유지함. 포트 또는 키가 달라진 경우 연결 코드를 다시 복사함. 로컬 폴더를 삭제하거나 옮기면 설치 경로를 다시 지정해야 함. [공식 개인용 로드 및 새로고침 절차](https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world#load-unpacked)

## 설치용 ZIP의 의미

`release/clipman-extension-0.2.0-personal.zip`은 확장만 포함함. 압축을 풀어 계속 유지할 폴더를 로드하는 개인 시험용 패키지임. Python 서버, ffmpeg와 yt-dlp 또는 이 PC의 연결 키는 포함하지 않음. 이번 패키지를 다른 기기에서 여는 것만으로 로컬 영상 처리가 설치되는 것은 아님.

이 PC에서는 기존 clipman 작업 폴더의 로컬 처리 프로그램을 함께 사용함. 다른 Windows PC나 Mac에서의 첫 설치는 환경 및 해당 플랫폼 실행파일 조달이 필요함. 일반 사용자용 독립 설치 프로그램, 자동 업데이트와 macOS 서명/공증은 후속 작업이며 완료됐다고 표시하지 않음. macOS 실행기 코드는 추가했으나 실기기 실행은 미검증임.

## 스토어 제출 전에 확인할 사항

개발자 등록과 일회성 등록비가 필요함. 등록비의 실제 금액은 결제 화면에서 확인해야 하며 이번 문서는 금액을 추정하지 않음. ZIP을 올린 뒤 소개, 개인정보/권한 설명, 배포 대상과 시험 절차를 작성하고 심사에 제출함. [등록](https://developer.chrome.com/docs/webstore/register), [첫 제출 절차](https://developer.chrome.com/docs/webstore/publish)

스토어는 저작권이 있는 콘텐츠의 **무단 접근, 다운로드 또는 스트리밍을 돕는 기능**을 금지함. clipman의 구간 획득이 실제로 어떤 권한과 콘텐츠 범위에서 제공되는지 심사 전 확인이 필요함. 개인용이라는 표기나 로컬 처리만으로 스토어 승인을 보장하지 않음. 이번 조사로 등록 불가 또는 승인 확정을 선언하지 않으며 현재 승인은 미확인임. [직접 적용되는 공식 정책 5항](https://developer.chrome.com/docs/webstore/program-policies/malicious-and-prohibited)

확장의 실행 JavaScript는 패키지에 포함하고 외부 JavaScript를 실행하지 않음. 로컬 프로그램은 데이터와 영상을 처리하는 별도 구성요소이며 설치 필요와 기능을 설명하고 심사자가 실행할 수 있는 절차를 제공해야 함. 스토어용 확장 ID/공개 key가 결정되면 로컬 프로그램의 허용 확장 ID도 일치시켜 재검증해야 함. 개인용 ID로 한 검사가 스토어 ID 연결 검증까지 대신하지 않음. [MV3 요건](https://developer.chrome.com/docs/webstore/program-policies/mv3-requirements)

업로드, 등록비 결제, 심사 제출, 공개 게시, GitHub Release 게시와 제3자 바이너리 재배포는 이번에 수행하지 않음.
