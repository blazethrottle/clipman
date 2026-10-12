# 외부 도구 계약과 Windows 취소 검증

2026-10-12 Windows x64 및 Python 3.13에서 검증함. 기준은 Draft PR #2의 `96f89e707541e684ca7a3d67a0ba50fdf99560d0`임. main 기준 초기 수정은 이 개발본에 맞춰 통합했으며 Selection과 기존 Chrome 연결을 유지함.

## 변경

- yt-dlp 출력 종류 접두사와 실제 진행률 접두사를 분리하여 파서가 실제 출력을 읽도록 수정함.
- metadata 및 download에서 개인 yt-dlp 설정을 배제하고 영상 하나만 처리함. 재생목록 전용 URL을 거부함.
- 대체 포맷에도 요청한 화질 상한을 적용함.
- 명시적 trim이 없어도 원본 길이를 검증하며 음수, 역전, 원본 길이 초과, NaN과 무한대를 거부함. ffprobe도 무한 길이를 거부함.
- Windows 작업을 Job Object에 먼저 할당한 뒤 대상 실행파일을 시작함. 부모 선행 종료 후에도 자식 전체를 종료하고 active process 수 0을 기다림. 정상 해제 때도 잔여 자식과 핸들을 정리함.
- 서비스의 중복 ignore-config 삽입을 제거함. 기존 출력의 길이, 해상도 및 음성 검증과 원자적 게시를 유지함.

## 검사 결과

| 검사 | 결과 | 확인 범위 |
|---|---|---|
| 수정 전 신규 입력 회귀 검사 | 13 failed, 6 passed | 잘못된 trim, 원본 길이, 재생목록과 무한 길이 결함 재현 |
| 수정 전 Windows 부모 선행 종료 검사 | 1 failed | 부모가 종료된 뒤 자식이 실행 중임을 실제 프로세스 핸들로 확인 |
| 최종 전체 pytest | 212 passed, skipped 0 | 기본 199개 및 실제 실행파일 통합 13개 |
| pip check | 통과 | backend 의존성 |
| 실제 yt-dlp 진행률 | 통과 | 통제된 HTTP 다운로드의 실제 출력과 파서 연결 |
| 실제 yt-dlp 화질 선택 | 통과 | 결합된 720p 및 1080p 후보에서 720p 상한 유지 |
| 실제 구간 및 크롭 | 통과 | 시간과 좌우 색이 다른 합성 영상의 2~3.5초 확보, 좌/우 크롭, 시작/후반 프레임과 음성 |
| API 및 Engine 종단 검사 | 통과 | 실제 획득, export, Range 재생과 원본 재사용 |
| Windows 취소 | 통과 | 자식 트리 종료, 부모 선행 종료 후 취소, Job 할당 실패 시 대상 미실행 |

전체 실행: `backend/.venv/Scripts/python.exe -m pytest -o addopts='' -q --basetemp=../work/final-contract-check`. 기본 검사와 통합 검사를 같은 실행에서 포함함. FastAPI TestClient의 httpx 사용에 대한 StarletteDeprecationWarning 1건이 있으며 실패는 아님. 이 수정에서 의존성을 교체하지 않음.

실행파일은 yt-dlp 2026.08.19, ffmpeg/ffprobe 8.1.2 essentials이며 공급자 체크섬을 대조함. PR #2의 이전 9.0.2 검증과 구분해 binaries-manifest에 추가 기록함.

## 실제 YouTube

- `https://www.youtube.com/watch?v=aqz-KE-bpKQ`: 메타 조회 성공, 10~12초 구간 확보는 90초 제한 시간 초과임. 검수용 직접 subprocess 호출의 부모 종료 후 남은 자식을 확인하고 해당 검수 트리만 정리함. 이를 성공으로 집계하지 않음.
- `https://www.youtube.com/watch?v=jNQXAC9IVRw`: 수정한 실제 Engine으로 0~2초 확보 후 로컬 0~1초를 export함. 소스는 320x240, 2.0초, 음성 있음. 결과는 1080x1920, 1.0초, H.264 및 AAC임.
- 결과 파일: 검수 복제본의 `output/clipman-506b35ba1350-2.mp4`. 결과 JSON과 표본 프레임은 `work/youtube-engine-check/`에 있음. 표본 3프레임을 눈으로 확인했으며 전체 재생 청취나 프레임별 원본 시각 대조는 수행하지 않음.

## 한계

단일 영상의 기계 검사이며 YouTube 전반의 화질, 제한 조건과 전송량 절감은 검증하지 않음. 실제 사용자 Chrome 인수, macOS, 모바일과 frozen 패키지는 미검증임. 이번 수정은 UI를 변경하지 않았으므로 PR #2의 이전 브라우저 검사를 새로 수행한 것으로 계산하지 않음. 기기 연결 키/미디어 ticket 수명과 작업 영속화는 기존 구현 상태를 보존함.
