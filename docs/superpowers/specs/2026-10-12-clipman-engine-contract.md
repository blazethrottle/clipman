# Chrome 연결과 영상 처리 계약

2026-10-12 검수 후속 설계. 제품 목적은 capture-first-design을 따른다. 이 문서는 구현 계약이며 Chrome, API와 취소 관리자가 이미 구현됐다는 뜻이 아니다.

## 1. 연결 선택

| 방식 | 장점 | 비용 |
|---|---|---|
| localhost HTTP | 기존 FastAPI와 Range 영상 재생 계약을 유지함. 작업이 확장 화면 수명과 독립적임 | 세션 인증, Origin 및 Host 검증과 연결 초기화가 필요함 |
| Native Messaging | 허용 확장 ID를 호스트 등록으로 제한함 | OS별 호스트 등록이 필요하고 대용량 영상 재생에는 별도 전달 경로가 필요함 |

초기 구현은 localhost HTTP를 사용한다. Native Messaging 계층을 함께 도입하지 않는다. 첫 설치 도구가 확장 ID와 로컬 실행기를 함께 설정하며 임의 웹사이트의 요청을 신뢰하지 않는다.

- 서버는 `127.0.0.1` 한 곳에만 바인딩하며 단일 worker로 실행한다. 실제 선택한 포트만 연결 정보로 사용하고 다른 로컬 포트를 탐색하지 않는다.
- 시작 시 `secrets.token_urlsafe(32)`로 세션 토큰을 생성한다. 설치 도구가 등록한 확장의 연결 탭을 Chrome에서 열고 포트와 토큰은 URL fragment로 전달한다. 연결 탭은 즉시 fragment를 지우고 확장 session storage에 보관한다. 설치된 Chrome 실행 경로와 확장 ID를 모르면 연결 실패로 안내하며 일반 웹 URL에 토큰을 전달하지 않는다.
- API 요청은 Authorization Bearer 토큰을 요구한다. 허용 Origin은 등록된 `chrome-extension://<id>` 하나이며 Host도 `127.0.0.1:<port>`로 제한한다. 와일드카드 CORS, 쿠키 인증과 일반 웹페이지의 직접 접근은 허용하지 않는다. 토큰 비교는 상수 시간 비교를 사용한다.
- content script는 영상 ID와 구간만 확장에 전달하고 토큰을 받지 않는다. service worker가 sender의 tab URL과 video ID를 검사한다. 페이지에서 온 메시지로 임의 URL, 명령, 파일 경로를 실행하지 않는다.
- 영상 element의 Range 요청에는 API가 발급한 짧은 수명의 작업별 재생 URL을 사용한다. 이 권한은 해당 source/result 읽기에만 유효하며 다른 API에는 사용할 수 없다. URL과 토큰을 로그에 기록하지 않고 만료되면 확장이 새 권한을 요청한다. 응답은 no-store로 제공한다.
- 확장 화면 종료는 작업 취소가 아니다. 서버가 실행을 소유하고 확장은 job_id로 다시 조회한다. 서버 재시작 후에는 새 세션 토큰으로 다시 연결한다. 작업 manifest로 원본 및 완료 결과를 복구하되 실행 중이던 작업은 interrupted로 표시하며 자동 재다운로드하지 않는다.

구현 검증: 미등록 Origin, 잘못된 Host, 토큰 누락 및 오답, 만료된 미디어 권한은 거부한다. Chrome 재연결과 Range 재생은 실제 브라우저에서 별도로 검증해야 한다.

## 2. 영상 식별과 시각

| 필드 | 의미 |
|---|---|
| source_video_id, source_url | 선택 당시 영상의 식별자와 정규화한 시청 URL |
| requested_start, requested_end | YouTube 원본 기준 요청 구간. 초 단위 유한 실수이며 시작 포함, 끝 제외 |
| source_origin_seconds | 확보 파일의 로컬 0초에 대응하는 원본 시각 |
| actual_duration | ffprobe로 확인한 확보 파일 길이 |
| trim_start, trim_end | 확보 파일 안에서 편집하는 로컬 시각 |
| crop_x | 회전이 적용된 원본 표시 해상도의 가로 픽셀 좌표 |

원본 80~90초가 로컬 0~10초로 확보됐다면 source_origin_seconds는 80이다. 원본 82~85초 편집은 로컬 2~5초를 사용한다. 원본 시각에 로컬 trim을 다시 더해 저장할 수 있어야 한다. 구간 확보 요청값을 실제 시작 시각으로 무조건 복사하지 않는다. 구간 정확성을 확인한 획득 경로에만 이 매핑을 부여하며 불확실하면 편집 준비 완료로 표시하지 않는다.

시청 URL에 list가 있어도 영상 하나만 확보한다. 재생목록 전용 주소는 거부한다. 영상 이동 시 기존 마커를 새 영상에 적용하지 않는다. content script 메시지의 영상 ID와 제출 시 영상 ID가 다르면 제출을 거부한다.

부분 획득은 yt-dlp `--download-sections`와 정밀 컷 재인코딩을 사용해 검증한다. 원본 전체 받기는 명시적 별도 선택이다. 범위 획득 실패 시 전체 다운로드나 녹화로 조용히 전환하지 않는다. 실제 네트워크 전송량이 선택 구간 길이에 비례한다고 표시하지 않는다.

## 3. 중복 실행, 취소와 저장

- request_id로 생성 요청을 중복 제거한다. 같은 작업의 export와 cancel은 작업별 lock 안에서 상태를 바꾼다. 초기 엔진은 무거운 획득 또는 인코딩을 한 번에 하나만 실행하고 추가 요청은 대기시킨다.
- spawn 전에 취소 플래그와 상태를 확인하고, 프로세스 등록 직후에도 확인한다. cancel과 spawn이 겹쳐 취소 후 새 프로세스가 남는 경우를 막는다.
- macOS는 새 세션/프로세스 그룹으로 실행하고 그룹 전체에 TERM, 제한 시간 후 KILL을 보낸다. Windows는 Job Object에 할당한 뒤 실행을 재개해 자식 생성 전부터 트리를 소유한다. Job Object 종료와 active process 수 0 확인 후 취소 완료로 표시한다. 플랫폼 구현은 `jobs/processes.py` 한 곳에 둔다.
- stdout 및 stderr는 동시에 비우고 보존 로그 크기에 상한을 둔다. 프로세스와 출력 reader 종료를 기다린 뒤 파일을 정리한다. 부모 Popen.terminate 호출만으로 취소를 완료 처리하지 않는다.
- 획득 취소는 해당 작업의 미완성 확보 파일만 정리한다. export 취소는 tmp와 해당 미완성 출력만 정리하고 source와 이전 완료 결과를 보존한다. 정리에 실패하면 실패 경로를 기록하고 재시도 대상으로 남긴다.
- 인코딩 종료 후 ffprobe로 유효한 영상 스트림, 양수인 유한 길이, 출력 해상도와 기대 음성 유지를 확인한다. 길이는 요청 구간과 허용 오차 안에서 맞아야 한다. 확인된 파일만 같은 볼륨에서 os.replace로 최종 경로에 옮긴다. 실패하면 성공 상태나 outputs 목록에 추가하지 않는다.
- 작업 manifest는 임시 JSON을 쓴 뒤 원자적으로 교체한다. 원본의 만료 및 일괄 정리는 사용자에게 보존 정책을 보여 주기 전까지 자동 적용하지 않는다.

## 4. 다음 구현 및 관문

1. 순수 wrapper 수정과 회귀 검사를 완료한다.
2. Windows 번들로 기존 변환 검사와 외부 yt-dlp 계약 검사를 실제 실행한다. 합성 원본의 시점과 좌우 색을 검사해 잘못된 컷과 크롭을 검출한다.
3. 로컬 HTTP 합성 영상으로 구간 확보, 원본 시각 매핑, CROP/PAD 출력 및 음성 유지를 검사한다. 이 결과는 YouTube 접속 성공이나 대역폭 절감 증거가 아니다.
4. 프로세스 트리 관리자와 상태 복구를 구현하고 실제 자식 프로세스 및 파일 쓰기를 사용해 취소를 검사한다.
5. 위 인증 계약의 API와 Chrome 최소 UI를 연결한다. YouTube 영상 이동, 중복 클릭, 새로고침, 취소 및 재편집을 실제 Chrome에서 검사한다.
6. macOS 번들과 설치, 실제 YouTube 구간 시각과 음성을 별도로 확인한다. 실패 시 실패 원인과 실제 실행 범위를 남긴다.

근거: https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging , https://docs.python.org/3/library/subprocess.html , https://github.com/yt-dlp/yt-dlp . 구현 범위에 따라 각 플랫폼의 공식 API 계약을 다시 대조한다.
