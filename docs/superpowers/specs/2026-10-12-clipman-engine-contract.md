# Chrome 연결과 영상 처리 검수 계약

2026-10-12 검수 후속. 개발 기준은 Draft PR #2의 `96f89e7`이며 제품 목적은 capture-first-design을 따른다. 기존 API, Selection과 Chrome 연결을 유지하고 외부 도구 계약 및 Windows 취소를 보강한다. main만 검수한 이전 결과와 이 개발본의 구현 상태를 구분한다.

## 연결과 시각

- 기존 localhost HTTP 연결을 유지한다. Native Messaging을 추가하지 않는다. 실행기는 실제 선택한 포트와 기기 연결 키를 사용한다. 키는 gitignore 파일에 보관하고 사용자는 연결 안내의 코드를 확장에 등록한다.
- 서버는 정확한 Host와 확장 Origin, `X-Clipman-Token` 및 `X-Clipman-Extension`을 검사한다. 기존 TRUSTED_CONTEXTS 설정과 content script에 키를 전달하지 않는 경계를 유지한다.
- 미디어는 경로별 HMAC 읽기 ticket으로 Range 재생한다. ticket을 변경 요청 인증으로 사용할 수 없다. 현재 ticket에는 만료가 없으며 만료나 키 회전은 별도 설계 대상이다. 이번 수정이 단기 토큰과 자동 페어링을 구현했다고 표시하지 않는다.
- `Selection(video_id, url, start_sec, end_sec)`은 원본 영상 식별과 선택 시각을 보존한다. `SourceTimeline(origin_start_sec, duration_sec)`은 확보 파일의 로컬 시각을 원본 시각으로 환산한다. 기존 자료형을 대체하는 중복 구간 모델을 만들지 않는다.
- 원본 80~90초를 확보한 파일에서 2~5초 편집은 원본 82~85초다. 모든 구간은 유한값이며 `0 <= 시작 < 끝 <= 확보 길이`를 만족한다. wrapper에서도 이 조건을 확인해 API 외의 호출을 보호한다.
- origin_basis는 기존 `requested_precise_cut`이다. 요청 시작을 실제 장면 시각의 측정값으로 표시하지 않는다. 실제 장면 정확도는 별도 검증한다.
- 화면 종료는 작업 취소가 아니다. 확장이 job_id로 다시 조회한다. 현재 작업 레지스트리는 메모리이므로 서버 재시작 후 작업 복구는 미구현이다. manifest 영속화나 자동 만료 정리를 이번 수정에 추가하지 않는다.

## 외부 도구와 결과

- metadata와 download 모두 `--ignore-config --no-playlist`를 사용한다. 재생목록 전용 URL은 거부하며 Selection 경로는 기존 정규화된 단일 watch URL을 사용한다.
- yt-dlp 진행률 템플릿은 `download:download:%(...)`다. 첫 접두사는 출력 종류이고 두 번째가 실제 파서 입력이다. 실제 CLI 출력으로 검사한다.
- 제한 화질의 대체 포맷에도 높이 상한을 적용한다. 720p 결합 포맷이 있으면 1080p 결합 포맷으로 조용히 넘어가지 않는다.
- `--download-sections`와 `--force-keyframes-at-cuts`의 기존 Selection 호출을 유지한다. 전체 다운로드와 구간 다운로드의 API를 중복 추가하지 않는다.
- Engine의 기존 출력 검증을 유지한다. ffprobe의 영상 스트림, 양수인 유한 길이, 1080x1920과 필요한 음성 유지가 맞아야 최종 파일을 게시한다. 양수 파일 크기와 종료코드 0만으로 성공을 판정하지 않는다.
- 영상 길이와 좌우 색이 구별되는 합성 원본으로 선택 장면과 크롭을 확인한다. 로컬 HTTP 획득 결과를 YouTube 접속 성공이나 전송량 절감의 근거로 사용하지 않는다.

## 취소 계약

- 작업 관리자의 기존 잠금과 generation으로 실행 등록, 취소, 게시 순서를 보호한다. 취소 이후 새 프로세스나 완료 결과가 등록될 수 없다.
- POSIX는 기존 전용 프로세스 그룹 종료를 유지한다. 실제 macOS 검증은 별도다.
- Windows는 Job Object로 작업의 전체 프로세스 트리를 소유한다. Python 부트스트랩이 stdin에서 대기하는 동안 Job에 먼저 할당하고, 할당 후에만 대상 실행파일을 시작한다. 부모 시작과 Job 할당 사이에 자식이 생기는 경합을 막는다.
- 취소는 Job 전체를 종료하고 active process 수가 0인지 확인한 후 완료한다. 부모가 먼저 종료돼도 자식이 포함된 Job을 종료한다. 정상 프로세스 해제 때도 남은 자식과 Job 핸들을 정리한다.
- Job 핸들이 닫히거나 처리 프로그램이 종료되면 남은 자식도 종료하도록 KILL_ON_JOB_CLOSE를 사용한다. 현재 venv Python 실행 전용 부트스트랩이며 frozen 배포 시에는 부트스트랩 실행 경로를 다시 설계해야 한다.
- 종료 후에만 작업 파일을 정리한다. 인코딩 취소는 확보 원본과 이전 완료 결과를 보존한다. stdout/stderr를 합친 기존 bounded log를 유지한다.

## 검증 및 남은 관문

Windows 실제 부모/자식 프로세스로 부모 선행 종료 후 취소를 검사한다. API -> 서비스 -> 실행파일 -> 출력, Range 재생과 재편집을 기존 통합 검사로 재확인한다. 기본 테스트, 통합 테스트와 YouTube 외부 접속 결과는 따로 기록한다. Chrome 화면과 패키지에 변경이 없으면 기존 브라우저 검사를 이번 작업의 새 검증으로 계산하지 않는다.

근거: https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects , https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject , https://github.com/yt-dlp/yt-dlp .
