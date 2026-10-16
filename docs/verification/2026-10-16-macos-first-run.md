# macOS 첫 실물 검증

2026-10-16, 서울 기준. Mac mini(Apple Silicon, macOS 27.0.1), Python 3.12.13, Node 26.8.1. 기준은 PR #3 브랜치 `1ba42ee`이며 아래 수정을 더했다.

## Mac에서 발견해 수정한 결함

| 결함 | 재현 | 수정 | 회귀 검사 |
|---|---|---|---|
| 정적 ffmpeg가 시스템 인증서를 찾지 못함 | 실제 YouTube 3구간 모두 6~8초 만에 `DOWNLOAD_FAILED`. 원인 출력 `certificate verify failed` | `processes.child_env()`가 macOS에서 `SSL_CERT_FILE=/etc/ssl/cert.pem` 전달. 사용자가 지정한 값은 유지 | `tests/test_process_env.py` 6개(macOS 실물 1개 포함) |
| YouTube 영상 서버의 간헐적 403 | 같은 구간을 앱 실행 경로로 3회 반복하면 1회 `HTTP error 403 Forbidden`, 2회 성공 | `classify_error`에 `HTTP_403` 분류 추가. 확보 단계에서 이 오류만 부분 파일을 지우고 1회 재시도. 재실패하면 "잠시 후 다시 시도" 안내 | `tests/test_engine_retry.py` 5개 |

## Mac 프로세스 정리 실물 검사

기존 POSIX 검사(`test_posix_process_group.py`)는 `killpg`를 가짜 함수로 바꾼 대역 검사였다. `tests/test_posix_process_tree.py`를 추가해 실제 자식 프로세스로 두 경우를 확인했다.

- 부모가 먼저 종료된 뒤 취소: 남아 있던 자식이 종료됨
- 부모 실행 중 취소: 자식이 종료됨

그룹 종료를 부모 pid 종료로 바꾸는 결함을 주입하면 두 검사가 모두 실패했다(검사가 결함을 잡는다는 확인).

## 검사 결과

| 검사 | 결과 |
|---|---|
| pytest 전체(기본 + 실물 통합) | 223 passed, 2 skipped. skip 2개는 Windows Job Object 전용 검사 |
| 실물 통합 검사만 | 13 passed |
| pip check | 통과 |
| Node 검사(`npm test`) | 5 passed |
| 확장 빌드(`npm run build`) | 통과 |
| 실제 MV3 확장 브라우저 시나리오(Playwright) | 1 passed |

## 실제 YouTube 종단 검사

Engine을 직접 호출했다. 실행 환경은 Finder 실행과 같은 짧은 PATH(`/usr/bin:/bin:/usr/sbin:/sbin`)다. 기본 화질 `best`, 결과는 로컬 0~1.5초 중앙 크롭이다.

| 영상 | 구간(초) | 원본 | 확보 시간 | 결과 |
|---|---|---|---|---|
| jNQXAC9IVRw | 0~2 | 320x240, 2.0초, 음성, 88KB | 5.5초 | 1080x1920 H.264/AAC 1.53초 |
| jNQXAC9IVRw | 5~8 | 320x240, 3.0초, 음성, 122KB | 6.0초 | 1080x1920 H.264/AAC 1.53초 |
| aqz-KE-bpKQ | 10~12 | 3840x2160, 2.0초, 음성, 3.6MB | 12.1초 | 1080x1920 H.264/AAC 1.5초 |
| aqz-KE-bpKQ | 60~63 | 3840x2160, 3.0초, 음성, 1.7MB | 10.1초 | 1080x1920 H.264/AAC 1.5초 |
| aqz-KE-bpKQ | 300~305 | 3840x2160, 5.0초, 음성, 4.3MB | 14.1초 | 1080x1920 H.264/AAC 1.5초 |

aqz-KE-bpKQ 10~12초는 Windows 검수에서 90초 시간 초과였던 구간이다. Mac에서는 수정 전 1회 403으로 실패했고, 수정 후 성공했다. 결과 프레임 3장씩을 눈으로 확인했으며 선택 장면의 중앙이 세로로 잘렸다. 전체 재생 청취와 프레임별 원본 시각 대조는 하지 않았다.

## 남은 미검증

- `start.command` 더블클릭 실행과 본인 Chrome 프로필에서의 실제 사이드 패널 사용
- 로그인이나 연령 제한이 있는 영상, 쿠키, 긴 구간, 실제 전송량 측정
- 403 재시도 후에도 실패하는 빈도. 이번 표본은 반복 3회와 종단 5회다
