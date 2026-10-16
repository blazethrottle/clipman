# 구간 처리 기반 검증

환경: Windows x64, Python 3.13.5, 프로젝트 `backend/.venv`. 변경 전 기본 107개 통과 확인 후 개발함.

## 실제 검사

- `.venv/Scripts/python.exe -m pytest -q`: 153 passed, 6 deselected.
- `.venv/Scripts/python.exe -m pytest -m integration -q -rs`: 6 passed, 153 deselected, skipped 0.
- `.venv/Scripts/python.exe -m pip check`: No broken requirements found.
- `git diff --check`: 공백 오류 없음.

새 capture/jobs 모듈을 구현하기 전 해당 모듈이 없어 테스트 수집이 실패하는 것을 확인함. 긴 영상의 소수점 시각 손실과 tmp 출력을 완성본으로 등록하는 문제는 각각 실제 실패 단언을 확인 후 수정함.

## 검증 범위

기본 153개는 기존 107개, 구간 및 시각 30개, 작업 관리 16개임. 실제 프로세스 취소 2개는 Python 자식 프로세스를 띄워 종료와 정리를 확인함. 종료 무응답 및 권한 실패는 위조 프로세스로 검사함. 동시 인코딩 시작은 스레드 16개 요청에서 1개만 허용되는지 확인함.

통합 6개는 기존 합성 ffmpeg 변환 5개와 새 합성 HTTP 구간 다운로드 1개임. 새 검사에서는 빨강 0~2초, 파랑 2~4초와 사인파 음성을 가진 영상을 생성하고 2.25~3.75초를 yt-dlp/ffmpeg로 확보함. 길이 1.5초(허용 오차 0.15초), 음성 스트림과 파랑 장면 픽셀을 검사함. 타임라인 API가 YouTube URL만 받는 계약은 기본 검사로 유지하고 통합 검사 내부에서만 입력 URL을 로컬 합성 영상으로 교체함.

통합 검사 최초 실행에서 테스트 하네스의 잘못된 `--no-proxy` 옵션을 발견함. 배포 실행파일의 `--help`로 `--proxy ""` 문법을 확인하고 수정함. 제품 다운로드 명령에는 이 하네스 옵션을 추가하지 않음.

## 미검증

실제 YouTube 영상의 시작 장면, 접근/쿠키/봇 차단과 전송량/대기, Chrome 확장 및 API, UI 미리보기와 크롭 출력 일치, 설치/종단 UX, macOS 및 모바일은 아직 미검증임. 프로세스 트리 종료와 실행/등록 전 취소 경합은 M3 서비스의 필수 후속 관문임. 프레임 색상 검사와 합성 인코딩 성공을 실제 YouTube 품질 검증으로 해석하지 않음.
