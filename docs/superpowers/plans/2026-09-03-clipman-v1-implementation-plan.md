# clipman v1 구현 계획 (Implementation Plan)

- 작성일: 2026-09-03 (KST)
- 상태: 확정. 사인오프 완료된 설계 문서 2건을 입력으로 작성
- 입력 문서: `docs/superpowers/specs/2026-09-01-clipman-architecture.md`(구현 정본), `docs/superpowers/specs/2026-09-01-clipman-design.md`(제품 의도), `docs/HANDOFF.md` 4절(플랫폼 판정)
- 범위: v1 = 다운로드 + 구간 자르기 + 세로 9:16 변환(CROP/PAD) + 내보내기

---

## 0. 이 계획의 규칙

1. **정본 우선.** 구현 중 설계를 바꿔야 하면 코드가 아니라 아키텍처 문서를 먼저 고친다. 계획서는 순서만 소유한다.
2. **TDD.** 각 작업 단위는 테스트를 먼저 쓴다. 테스트가 없는 단위는 완료로 보지 않는다.
3. **바이너리 독립 원칙.** 기본 테스트 스위트(`pytest`)는 `bin/`이 비어 있어도 100% 통과해야 한다. 실물 실행파일이 필요한 검증은 `tests/integration/`에 `@pytest.mark.integration`으로 격리한다. 이 원칙 덕분에 코드 작성은 어느 기기에서든 가능하고, 실측만 실사용 기기(macOS)에서 한다.
4. **순수 함수 분리.** 외부 실행파일 호출 코드는 "인자를 조립하는 순수 함수"와 "프로세스를 돌리는 얇은 실행부"로 나눈다. 조립 함수는 인자 리스트를 반환하므로 바이너리 없이 문자열 단위로 검증된다.
5. **완료 정의(DoD) 없는 작업은 착수하지 않는다.**

---

## 1. 마일스톤 개요

| ID | 이름 | 산출물 | 실물 바이너리 필요 | 추정 |
|---|---|---|---|---|
| M1 | wrappers 계층 + 바이너리 조달 | `binaries.py`, `ffprobe.py`, `ffmpeg.py`, `ytdlp.py` + 테스트 | M1-0, M1-6만 | 3~4 세션 |
| M2 | 작업 레지스트리 | `jobs/manager.py`, 상태 전이 테스트 | 아니오 | 1~2 세션 |
| M3 | 유스케이스 계층 | `services/download.py`, `edit.py`, `files.py`, `errors.py` | M3-3만 | 2 세션 |
| M4 | HTTP 계층 | `schemas.py`, `routers/` 3종, `main.py` | 아니오 | 2 세션 |
| M5 | UI와 실행기 | Svelte 3화면, `start.command`/`start.cmd`, 종단 검증 | 예 | 3~4 세션 |

추정치이며 실측 이력이 없다. 1세션 = 집중 2~4시간.

---

## 2. M1: wrappers 계층

### M1-0 바이너리 조달 (실사용 기기에서 수행)

- 절차: `bin/`에 `yt-dlp`, `ffmpeg`, `ffprobe` 배치(Windows는 `.exe`). macOS는 `uname -m`으로 arm64/x86_64 판별 후 정적 빌드 1순위, Homebrew 설치본 복사 2순위. `chmod +x` 및 `xattr -d com.apple.quarantine` 확인.
- DoD: 세 실행파일이 `-version`에 응답하고, 출처 URL·버전·SHA256이 `docs/binaries-manifest.md`에 기록됨.
- 왜 별도 단위인가: `bin/`이 gitignore이므로 커밋 이력으로는 진척이 보이지 않는다. manifest 파일이 유일한 추적 수단이다.

### M1-1 스캐폴딩

- 대상: `backend/requirements.txt`, `backend/pyproject.toml`(pytest 마커 설정), `app/__init__.py` 외 패키지 표식, `app/paths.py`.
- 첫 테스트: `paths.APP_ROOT`가 저장소 루트를 가리키고 `BIN_DIR`/`WORK_DIR`/`OUTPUT_DIR`/`LOGS_DIR`가 그 하위를 가리킨다.
- DoD: `pytest`가 수집 0건이 아니라 실제 통과. 의존성 버전이 파일로 고정됨.

### M1-2 `wrappers/binaries.py`

- 테스트 먼저: (1) `win32`에서 `.exe` 접미가 붙는다, (2) `darwin`/`linux`에서는 붙지 않는다, (3) 경로가 `BIN_DIR` 하위다, (4) 파일이 없으면 명확한 예외(`BinaryNotFound`)를 던지고 메시지에 조달 안내가 있다.
- 플랫폼 분기는 `monkeypatch`로 `sys.platform`을 위조해 검증한다. 실제 OS와 무관하게 3개 플랫폼 경로가 전부 테스트된다.
- DoD: **실행파일 이름**의 플랫폼 분기가 이 모듈에만 존재함을 `grep sys.platform`으로 확인. 예외는 M3-4의 `services/files.py`(폴더 열기 명령 분기) 하나뿐이며, 그 외 코드는 `sys.platform`을 보지 않는다.

### M1-3 `wrappers/ffprobe.py`

- 책임: 소스 메타(가로, 세로, 길이, 오디오 스트림 유무) 조회.
- 순수 함수: `build_probe_args(src) -> list[str]`, `parse_probe_json(text) -> SourceMeta`.
- 테스트: 실제 ffprobe JSON 형태 픽스처로 파싱 검증. 비디오 스트림 없음, 회전 메타 존재, `duration` 누락(format에서 폴백) 같은 비정상 입력 포함.
- DoD: 오디오 스트림 유무가 정확히 판정됨(8절 오디오 누락 방지의 전제).

### M1-4 `wrappers/ffmpeg.py`

- 순수 함수 3개: `resolve_mode(meta, requested)`(9:16보다 넓지 않은 소스는 CROP을 PAD로 자동 전환), `build_encode_args(src, out, opts, meta)`(CROP/PAD 필터그래프 조립), `parse_progress_line(line, clip_len)`(`out_time_us` 1차, `out_time` 문자열 폴백, `N/A` 방어).
- 테스트: 아키텍처 8절의 명령 원문과 문자열 단위 대조. `crop_x` 클램프(0 ~ `iw - ih*9/16`), `-ss`/`-t` 순서, 공통 인코딩 꼬리 존재, PAD 모드 필터, 진행률 0~1 범위와 단조성.
- DoD: 8절 (1), (1'), (2) 명령이 테스트로 고정됨. blur_pad는 v1.1이므로 구현하지 않는다.

### M1-5 `wrappers/ytdlp.py`

- 순수 함수: `build_metadata_args(url)`(`-J`), `qualities_from_formats(info)`(height별 정리), `build_download_args(url, quality, work_dir, ffmpeg_dir, cookie_opts)`, `parse_progress_line(line)`(`total_bytes` 없으면 `total_bytes_estimate` 폴백), `classify_error(stderr)`(BOT_BLOCK / FORMAT_UNAVAILABLE / NETWORK / DOWNLOAD_FAILED).
- `PLAYER_CLIENT_FALLBACKS` 모듈 상수를 이 파일에만 둔다(아키텍처 15절 재심 결론의 이행 지점).
- 테스트: 실제 `-J` 출력 축약 픽스처에서 title/duration/thumbnail/qualities 도출, 진행률 파싱, 4개 에러 분기.
- DoD: 봇 차단 문자열이 BOT_BLOCK으로, 포맷 없음이 FORMAT_UNAVAILABLE로 분기됨.

### M1-6 통합 검증 (실물 바이너리 필요, 아키텍처 15절 재심 1번)

- `ffmpeg -f lavfi -i testsrc -f lavfi -i sine`으로 **오디오 포함** 합성 영상을 만들고 CROP/PAD 두 모드를 실제 인코딩.
- 단언: 출력 해상도 1080x1920, 클립 길이 오차 허용범위, **오디오 스트림 존재**.
- DoD: 세 단언이 통과. 실패하면 M2 이후로 넘어가지 않는다(무음 결함은 v1 품질의 하한선).

---

## 3. M2: 작업 레지스트리

- 대상: `jobs/manager.py`. `JobStatus` 7값, `JobState` 데이터클래스(아키텍처 5절 정의 그대로), 인메모리 딕셔너리 레지스트리.
- 테스트: 상태 전이(QUEUED → DOWNLOADING → DOWNLOADED → ENCODING → DONE), 재편집 경로(DONE → ENCODING, 같은 `source_path` 재사용, `outputs` 누적), 취소(`_proc.terminate()` 호출 여부를 위조 객체로 검증), 실패 전이.
- 정리 규칙 테스트: 다운로드 단계 취소는 job 폴더 통째 삭제, 인코딩 단계 취소는 `tmp/`만 삭제하고 원본 보존.
- DoD: "한 번 받아 여러 번 편집"이 테스트로 고정됨. 이것이 clipman의 핵심 차별점이다.

---

## 4. M3: 유스케이스 계층

- **M3-1 `services/download.py`**: 메타 조회, 다운로드 오케스트레이션, 봇 차단 폴백 4단계(쿠키 파일 → 브라우저 쿠키 → player_client → 업데이트 안내), NETWORK 지수 백오프.
- **M3-2 `services/edit.py`**: ffprobe로 소스 확인 → 모드 자동 전환 판정 → 인코딩 → 종료코드 0이어도 출력 파일 부재나 0바이트면 실패 처리 → `output/`으로 원자적 이동(`os.replace`).
- **M3-3 쿠키 폴백 실측** (아키텍처 15절 재심 2번, 실사용 기기): macOS에서 `--cookies-from-browser`가 Keychain 프롬프트를 띄우는지, 브라우저 실행 중 실패하는지 1회 확인하고 결과를 아키텍처 7절에 기록.
- **M3-4 `services/files.py`**: 결과 폴더 열기(macOS `open`, Windows `explorer`, Linux `xdg-open`), 경로 검증(작업 폴더 밖 접근 차단).
- DoD: subprocess 모킹으로 각 폴백 분기가 실제로 갈라짐이 검증됨. 사용자 메시지가 전부 한국어.

---

## 5. M4: HTTP 계층

- **M4-1** `schemas.py`(Pydantic v2, enum은 `Literal`), `errors.py`(에러 코드 6종 + 한국어 메시지 룩업).
- **M4-2** `routers/metadata.py`, `routers/jobs.py`, `routers/system.py`. 아키텍처 4절 8개 엔드포인트 전부. `GET /api/jobs/{id}/source`는 Range 요청 지원(편집 화면 스크럽의 전제).
- **M4-3** `main.py`: `/api` 라우터 먼저 등록 후 `StaticFiles(dist, html=True)`를 `/`에 마운트, uvicorn 단일 워커 고정, 9000 우선 후 빈 포트 자동 선택, **그 실제 포트로 브라우저 열기**(아키텍처 15절 재심 4번), `logs/clipman.log` 기록.
- 테스트: `TestClient`로 8개 엔드포인트 통합 테스트. 포트 선택 로직은 소켓 점유를 위조해 단위 테스트.
- DoD: 8개 엔드포인트가 계약대로 응답하고, 마운트 순서 때문에 `/api`가 정적 파일에 삼켜지지 않음이 테스트로 고정됨.

---

## 6. M5: UI와 실행기

- **M5-1** Vite + Svelte 프로젝트 생성, `/api` 개발 프록시.
- **M5-2** 가져오기 화면: URL 입력 → `/api/metadata` → 영상 카드와 실제 화질 목록.
- **M5-3** 편집 화면: `GET .../source` 재생, 타임라인 트림 핸들, 9:16 크롭 오버레이 드래그. **좌표는 표시 크기가 아니라 `videoWidth` 기준 실제 해상도로 환산**해 `crop_x`로 보낸다.
- **M5-4** 내보내기 화면: 진행률 폴링(500ms~1s), 완료 후 결과 폴더 열기.
- **M5-5** `start.command`(macOS) / `start.cmd`(Windows) 실행기. 실패 시 창 유지.
- **M5-6 종단 검증**: URL 붙여넣기부터 쇼츠 mp4 내보내기까지 다른 툴 이탈 없이 1회 완주(설계 문서 1.6 성공 지표 1차 검증).
- 리스크: M5-3의 드래그와 좌표 환산이 v1 최대 난제다. M5 착수 시 이 부분을 가장 먼저 만들어 조기에 검증한다.

---

## 7. 검증 태스크 편입 대장 (아키텍처 15절 재심 항목)

| 재심 항목 | 편입 위치 | 검증 방법 |
|---|---|---|
| 번들 ffmpeg 필터/컷/오디오 유지 | M1-6 | 합성 영상(testsrc + sine) 실인코딩 후 ffprobe 단언 |
| 쿠키 폴백 실동작 | M3-3 | macOS 실기기 1회 실행, 결과를 아키텍처 7절에 기록 |
| `player_client` 조합 변동 | M1-5 | 모듈 상수 단일화 + 폴백 순서 테스트 |
| 포트 자동 선택 배선 | M4-3 | 9000 점유 상태에서 실제 열린 포트로 브라우저가 열리는지 확인 |

---

## 8. 지금 세션에서 가능한 범위와 불가능한 범위

이 계획을 실행하는 환경이 실사용 기기(macOS)가 아닐 수 있다. 구분은 다음과 같다.

- **어느 기기에서든 가능**: M1-1 ~ M1-5, M2, M3-1/3-2/3-4, M4 전체, M5-1 ~ M5-4의 코드 작성과 단위 테스트.
- **실사용 기기에서만 가능**: M1-0(바이너리 조달), M1-6(실인코딩), M3-3(쿠키 실측), M5-5/5-6(더블클릭 실행과 종단 검증).

이 분리가 "바이너리 독립 원칙"의 실질적 이유다.
