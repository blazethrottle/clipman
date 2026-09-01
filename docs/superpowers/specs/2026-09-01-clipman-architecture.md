# clipman 개발 아키텍처 (Development Architecture)

- 작성일: 2026-09-01 (KST), 적대적 리뷰(4개 렌즈) 반영 확정본
- 상태: 확정안 (스택 사실 검증 + 적대적 리뷰 완료, 사용자 사인오프 대기)
- 상위 문서: `2026-09-01-clipman-design.md` (서비스/UI/UX/개념 아키텍처)
- 근거: 스택 5개 영역 병렬 검증(공식 문서 확인) + 4개 렌즈 적대적 리뷰. 버전과 명령은 2026-09 시점 확인값

---

## 0. 확정 스택 (검증된 버전)

| 계층 | 선택 | 버전(2026-09) | 확정 근거 |
|---|---|---|---|
| 백엔드 언어 | Python | 3.11+ | yt-dlp, whisper(v2)와 동일 생태계 |
| 웹 프레임워크 | FastAPI + uvicorn | 최신 | 비동기, response_model 스키마 자동화 |
| 검증 모델 | Pydantic v2 | 2.13.x | Literal 기반 enum, OpenAPI 자동 생성 |
| 다운로드 | yt-dlp (**번들 실행파일, subprocess 호출**) | >=2026.8.19 | 취소 가능(프로세스 종료), 자체 업데이트, ffmpeg와 실행 모델 통일 |
| 미디어 처리 | ffmpeg + ffprobe (번들 실행파일) | gyan.dev/BtbN 정적 8.x | ffprobe 동봉, 오프라인 견고, 버전 고정 |
| 프론트엔드 | Svelte 5 + Vite (순수 SPA) | Vite 7.x 고정 권장 | 단일 화면에 SvelteKit은 과잉 |
| 테스트 | pytest + httpx(TestClient) + pytest-subprocess | 최신 | subprocess 모킹, 엔드포인트 통합 |

**핵심 전환(리뷰 반영):** yt-dlp를 파이썬 라이브러리가 아니라 번들 실행파일(`yt-dlp.exe`)로 subprocess 호출한다. 이유는 세 가지가 한 번에 해결되기 때문이다. (1) 취소: 라이브러리를 스레드에서 돌리면 `task.cancel()`로 실제 다운로드를 멈출 수 없지만, 실행파일은 프로세스 핸들을 `terminate()`하면 즉시 멈춘다. (2) 업데이트: `yt-dlp.exe -U` 한 줄로 자체 갱신된다(봇 차단 대응의 핵심). (3) 통일: ffmpeg와 동일한 subprocess + Popen + 진행률 파싱 + 취소 모델을 공유해 코드가 단순해진다. 메타데이터도 `yt-dlp -J`(JSON 덤프)로 제목, 길이, 썸네일, 화질 목록을 한 번에 얻는다.

거부한 대안: yt-dlp 라이브러리(취소 불가, 업데이트 복잡), imageio-ffmpeg(ffprobe 미포함), static-ffmpeg(최초 실행 온라인 다운로드), BackgroundTasks(핸들/취소/진행률 없음), asyncio.create_subprocess_exec(Windows 이벤트 루프 함정), SvelteKit(단일 화면에 과잉), pydantic-settings(고정 경로 도구에 과한 설정 계층).

---

## 1. 시스템 개요

전부 사용자 Windows PC 안에서 동작하는 로컬 3계층이다. 브라우저는 화면만, 로컬 파이썬 서버가 번들 실행파일을 호출해 무거운 처리를 한다.

```
[브라우저 SPA]  --HTTP(127.0.0.1:PORT)-->  [FastAPI 서버]  --subprocess-->  [번들 실행파일]
  Svelte 빌드(dist)      /api 폴링              라우터/서비스/래퍼         yt-dlp.exe / ffmpeg.exe / ffprobe.exe
  (FastAPI가 서빙)                             인메모리 Job 레지스트리
                                                     |
                                     [로컬 파일시스템]  work/<job>/ (원본 보존)   output/ (쇼츠 결과물)
```

cobalt에서 걷어낸 것: 서명 터널, 다층 인증, Redis, 인스턴스 분리(전부 공개 멀티유저용). 그 예산을 편집 기능과 UX에 쓴다.

---

## 2. 폴더와 모듈 구조

계층(레이어)별로 나눈다. 핵심은 `router -> service -> wrapper` 3계층 경계다.

```
clipman/
├─ backend/
│  ├─ app/
│  │  ├─ main.py            # 앱 생성, 라우터/예외핸들러 등록, dist 서빙, 포트 선택, 브라우저 열기, 로깅
│  │  ├─ paths.py           # 앱 루트 기준 경로 상수(bin/work/output/logs). 단순 모듈(pydantic-settings 미사용)
│  │  ├─ schemas.py         # 요청/응답 Pydantic 모델
│  │  ├─ errors.py          # 소수의 동작-분기 에러 코드 + 한국어 메시지 룩업
│  │  ├─ routers/
│  │  │  ├─ metadata.py     # POST /api/metadata
│  │  │  ├─ jobs.py         # 다운로드/상태/취소/export/source/reveal
│  │  │  └─ system.py       # POST /api/system/update-ytdlp
│  │  ├─ services/
│  │  │  ├─ download.py     # yt-dlp 오케스트레이션(유스케이스)
│  │  │  └─ edit.py         # ffmpeg 오케스트레이션(유스케이스)
│  │  ├─ jobs/
│  │  │  └─ manager.py      # 인메모리 Job 레지스트리, 상태/진행률, 취소
│  │  └─ wrappers/          # 외부 실행파일 저수준 어댑터 (순수, 테스트 쉬움)
│  │     ├─ ytdlp.py        # yt-dlp 인자 조립 + Popen 실행 + 진행률 파싱
│  │     ├─ ffmpeg.py       # ffmpeg 필터그래프 조립 + Popen 실행 + 진행률 파싱
│  │     ├─ ffprobe.py      # 소스 메타(해상도/길이) 조회
│  │     └─ binaries.py     # 번들 실행파일 경로 해석
│  └─ requirements.txt
├─ frontend/                # Svelte + Vite 소스
│  └─ dist/                 # Vite 빌드 산출물 → FastAPI가 서빙 (배포 전 1회 빌드 필요)
├─ bin/                     # 번들 실행파일: yt-dlp.exe, ffmpeg.exe, ffprobe.exe
├─ work/                    # 작업별 폴더 work/<job_id>/ : 다운로드 원본 보존 + 인코딩 임시
├─ output/                  # 최종 쇼츠 결과물 (사용자가 얻는 곳)
├─ logs/                    # clipman.log (진단용)
└─ start.cmd                # 더블클릭 실행기 (실패 시 콘솔 유지)
```

3계층 책임: `wrappers/`는 실행파일을 어떻게 부르는가(인자, 진행률 파싱)만, `services/`는 무엇을 어떤 순서로(유스케이스), `routers/`는 HTTP 껍데기. 이 경계가 로드맵(v2 자막, v3 하이라이트)을 국소 추가로 흡수한다.

---

## 3. 런타임 실행 모델 (Windows 검증 반영)

1. **uvicorn 단일 워커, reload 없음.**
   ```python
   uvicorn.run(app, host="127.0.0.1", port=chosen_port, workers=1, reload=False)
   ```
   인메모리 Job 레지스트리를 쓰므로 워커 2개 이상이면 폴링이 작업을 못 찾는다. 단일 워커는 타협 불가. 이 구성이 Windows 기본 ProactorEventLoop도 보장한다.

2. **장시간 작업 = `asyncio.create_task` + `run_in_executor`(스레드) + 동기 `subprocess.Popen`.**
   `asyncio.create_subprocess_exec`은 Windows에서 uvicorn이 SelectorEventLoop를 고르면(누군가 --reload를 켜면) NotImplementedError로 조용히 깨진다. 스레드풀 + 동기 Popen은 이벤트 루프 종류와 무관하게 항상 동작한다. **취소는 스레드 취소가 아니라 프로세스 종료로 한다**(아래 6절): 스레드에 얹은 블로킹 작업은 `task.cancel()`로 멈지 않으므로, JobState에 보관한 `Popen` 핸들을 `terminate()`/`kill()` 해서 실제로 멈춘다.

3. **서빙 모델(모순 정정).** v1도 프론트엔드는 배포 전 1회 빌드가 필요하다(`npm run build`가 `frontend/dist/`를 만든다). "빌드 단계 없음"은 파이썬 쪽에만 해당한다. FastAPI는 API를 `/api` 접두어로 먼저 등록하고, `StaticFiles(directory=dist, html=True)`를 `/`에 마운트해 그 dist를 서빙한다(마운트가 하위 경로를 삼키므로 접두어 분리 필수). 개발 중에는 Vite dev 서버가 `/api`를 FastAPI로 proxy한다.

4. **포트 선택.** 9000을 우선 시도하되 점유돼 있으면 빈 포트를 찾아 쓰고, 그 실제 포트로 `webbrowser.open`한다(하드코딩 실패 방지).

5. **로깅.** 서버는 `logs/clipman.log`에 기록한다. `start.cmd`는 실패 시 콘솔 창을 닫지 않고(`pause`) 오류를 보이게 한다.

---

## 4. REST API 계약

`/api` 접두어. Pydantic v2 모델, enum은 `Literal`. UX(가져오기 -> 편집 -> 내보내기)와 "한 번 받아 여러 번 편집"을 반영해 다운로드(원본 확보)와 export(쇼츠 렌더링)를 분리한다.

| 메서드 | 경로 | 역할 | 요청 | 응답 |
|---|---|---|---|---|
| POST | `/api/metadata` | 미리보기(잡 생성 안 함) | `{url}` | `{title, duration_sec, width, height, thumbnail_url, uploader, qualities[]}` |
| POST | `/api/jobs` | 다운로드 작업 생성 | `{url, quality}` | `201 {job_id}` |
| GET | `/api/jobs/{id}` | 상태 폴링 | - | `JobStatus` |
| GET | `/api/jobs/{id}/source` | **편집 화면용 원본 재생/스크럽 (Range 지원)** | - | 비디오 스트림 |
| POST | `/api/jobs/{id}/export` | 편집(자르기+세로변환) 실행 | `EditOptions` | `202 JobStatus` |
| DELETE | `/api/jobs/{id}` | 현재 단계 취소 + 정리 | - | `200 JobStatus` / `409` |
| POST | `/api/jobs/{id}/reveal` | 결과물 폴더를 탐색기로 열기 | - | `204` |
| POST | `/api/system/update-ytdlp` | `yt-dlp.exe -U` 실행(봇차단 대응) | - | `{updated, version}` |

리뷰 반영: (1) `GET .../source` 신설: 편집 화면은 다운로드한 원본을 브라우저에서 재생하며 트림 지점과 9:16 크롭 오버레이를 잡아야 하므로 원본을 Range로 서빙하는 엔드포인트가 필수다. (2) `GET .../result`(브라우저 다운로드)는 제거: 결과물은 이미 `output/`에 있고 사용자는 `reveal`로 폴더를 연다. (3) `/api/metadata`가 `qualities[]`(실제 사용 가능 화질 목록, `yt-dlp -J`의 formats에서 도출)를 반환해 UI가 진짜 선택지를 준다. `quality`는 그 목록의 값 또는 `"best"`.

---

## 5. 데이터 모델

`JobPhase`는 제거했다(리뷰: `JobStatus`의 순수 파생값이라 동기화 부담만 만든다). 진행바 라벨은 status에서 파생한다.

```python
class JobStatus(str, Enum):
    QUEUED = "queued"            # 접수, 시작 전
    DOWNLOADING = "downloading"  # yt-dlp 실행 중
    DOWNLOADED = "downloaded"    # 원본 확보, 편집 옵션 대기 (clipman 고유 단계)
    ENCODING = "encoding"        # ffmpeg 실행 중
    DONE = "done"                # 결과물 완성
    ERROR = "error"
    CANCELED = "canceled"
    # v3 예약: ANALYZING (하이라이트 분석). v1에서는 미사용

@dataclass
class JobState:
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0            # 0.0~1.0, 현재 status 기준
    message: str = ""                # 사람이 읽는 한국어 문구
    error_code: str | None = None
    input_url: str = ""
    work_dir: str = ""               # work/<job_id>/ : 원본 보존 + 인코딩 임시
    source_path: str | None = None   # 다운로드 원본 (export 간 재사용)
    source_meta: dict | None = None  # duration, width, height (ffprobe)
    outputs: list[str] = field(default_factory=list)  # 이 원본에서 만든 쇼츠들(여러 개 가능)
    last_edit: "EditOptions | None" = None
    created_at: int = field(default_factory=time.time_ns)
    updated_at: int = field(default_factory=time.time_ns)
    _proc: subprocess.Popen | None = None   # 취소용 프로세스 핸들, API 직렬화 제외
```

`outputs`를 리스트로 둔 것은 "한 원본에서 여러 쇼츠"를 실제로 추적하기 위함이다(리뷰 반영). 재편집은 원본을 지우지 않고 새 결과를 `outputs`에 추가한다.

편집 옵션(v1 필터에서 실제로 쓰는 필드만):

```python
class EncodeMode(str, Enum):
    CROP = "crop"   # 9:16 영역만 잘라내기 (기본)
    PAD = "pad"     # 원본 유지 + 단색 레터박스
    # BLUR_PAD = "blur_pad"  # 흐린 배경. v1.1 (설계 문서 결정 존중). 8절에 정확한 명령 명시

@dataclass
class EditOptions:
    trim_start: float | None = None   # 초. None이면 처음부터
    trim_end: float | None = None     # 초. None이면 끝까지
    mode: EncodeMode = EncodeMode.CROP
    crop_x: int | None = None         # mode=CROP의 가로 오프셋(원본 픽셀). None이면 중앙
    target_w: int = 1080
    target_h: int = 1920
```

리뷰 반영: v1 크롭 필터가 `crop=ih*9/16:ih:X:0`로 폭/높이/y가 고정이고 사용자가 조절하는 값은 가로 오프셋 하나뿐이므로, 죽은 필드(crop_y/w/h)를 제거하고 `crop_x`만 남겼다. 임의 사각 크롭이 실제 요구로 등장하면 그때 확장한다.

### 상태 전이

```
QUEUED --start--> DOWNLOADING --(성공)--> DOWNLOADED --(편집 제출)--> ENCODING --(성공)--> DONE
                       |                                                  |
                       +--(실패)ERROR  취소 CANCELED                      +--(실패)ERROR

재편집: DONE --(새 EditOptions)--> ENCODING   # 같은 source_path 재사용, 다운로드 생략, outputs에 추가
```

`DOWNLOADED`에서 사용자 입력을 기다리는 단계가 clipman의 핵심이다. 한 번 받은 원본으로 여러 쇼츠를 뽑을 때 재다운로드가 불필요하다.

---

## 6. 작업 수명주기, 진행률, 취소, 정리

- **진행률: 폴링.** `GET /api/jobs/{id}`를 500ms~1s 간격. 단일 사용자 로컬 앱에 가장 단순하고 견고하다. progress는 status별로 0~1(UI에 "다운로드 40%", "인코딩 70%").
- **취소(정정).** JobState의 `_proc`(Popen)를 `terminate()` 후 응답 없으면 `kill()` 한다. yt-dlp도 ffmpeg도 실행파일이라 프로세스 핸들이 있으므로 다운로드/인코딩 모두 실제로 멈춘다(라이브러리였다면 다운로드 취소가 불가능했다).
- **정리(정정).** 폴더 구조를 둘로 나눈다. 다운로드 원본은 `work/<job_id>/source.*`에 **보존**하고, 인코딩 중간물만 `work/<job_id>/tmp/`에 두어 export마다 정리한다. 취소/실패 시 삭제 범위: 다운로드 단계 취소면 그 job 폴더 통째로, 인코딩 단계 취소면 `tmp/`와 미완성 출력만(원본은 보존해 재편집이 재다운로드를 강제하지 않게). 완성된 쇼츠는 `output/`로 원자적 이동(`os.replace`). Windows에서 핸들 잔류로 삭제가 실패할 수 있으므로 `rmtree(ignore_errors=True)` + 시작 시 오래된 job 폴더 스윕을 병행한다.

---

## 7. 다운로드 설계 (yt-dlp.exe subprocess)

- **미리보기:** `yt-dlp -J --no-warnings <url>`로 JSON을 받아 title, duration, thumbnail, formats를 파싱한다. formats에서 height별로 정리한 `qualities[]`를 `/api/metadata`가 반환해 UI가 실제 화질 목록을 준다.
- **다운로드:** `yt-dlp -f "bestvideo[height<=1080]+bestaudio/best" --merge-output-format mp4 --ffmpeg-location <bin> -o "<work>/source.%(ext)s" --newline --progress-template "download:%(progress.downloaded_bytes)s/%(progress.total_bytes)s/%(progress.total_bytes_estimate)s" <url>`. stdout을 줄 단위로 읽어 진행률을 계산한다(total_bytes 부재 시 estimate로 폴백).
- **취소:** Popen 핸들 terminate.
- **봇 차단 폴백(로컬 강점):** stdout/stderr에 `Sign in to confirm you're not a bot`가 뜨면 순서대로 재시도: (1) `--cookies-from-browser chrome` (2) `--extractor-args "youtube:player_client=tv"` 또는 `web_safari` (3) 업데이트 안내.
- **업데이트:** `POST /api/system/update-ytdlp`가 `yt-dlp.exe -U`를 실행한다. 실행파일 자체 갱신이라 파이썬 재시작이 필요 없다(라이브러리 방식 대비 이점).

쿠키 주의(리뷰 반영): clipman이 기동 시 기본 브라우저(대개 Chrome)를 자동으로 여는데, `--cookies-from-browser chrome`는 Chrome 실행 중 쿠키 DB 잠금과 App-Bound Encryption으로 실패할 수 있다. 그래서 쿠키 폴백은 (a) 사용자가 내보낸 쿠키 파일(`--cookies FILE`)을 1순위로 두거나, (b) UI에서 "브라우저를 닫고 다시 시도" 안내를 제공하는 이중화를 둔다. 쿠키는 민감정보이므로 로컬에만 두고 로그/전송에 넣지 않는다.

---

## 8. 편집 설계 (ffmpeg)

구간 컷은 재인코딩 경로로 통일한다(세로 변환이 이미 재인코딩을 요구). 명령은 `-ss START -i input -t DURATION`로 고정해 빠른 시크와 프레임 정확성을 함께 얻고, `-to` 대신 `-t`로 버전별 타임라인 혼선을 차단한다.

```bash
# 공통 인코딩 꼬리
ENC="-c:v libx264 -crf 23 -preset veryfast -pix_fmt yuv420p -movflags +faststart -c:a aac -b:a 128k -progress pipe:1"

# (1) v1 기본: 중앙 크롭 (오디오는 -vf라 자동 매핑됨)
ffmpeg -ss S -i src -t D -vf "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920,setsar=1" $ENC out.mp4

# (1') 위치 조절 크롭: X는 0 ~ (iw - ih*9/16)로 클램프
ffmpeg -ss S -i src -t D -vf "crop=ih*9/16:ih:X:0,scale=1080:1920,setsar=1" $ENC out.mp4

# (2) v1: 단색 레터박스
ffmpeg -ss S -i src -t D -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,setsar=1" $ENC out.mp4

# (3) v1.1: 흐린 배경. filter_complex는 오디오 자동 매핑이 꺼지므로 반드시 명시 매핑
ffmpeg -ss S -i src -t D -filter_complex \
 "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=luma_radius=20:luma_power=2[bg];\
  [0:v]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]" \
 -map "[v]" -map 0:a? $ENC out.mp4
```

리뷰 반영(중요):
- **오디오 누락 방지(critical).** `filter_complex`(흐린 배경)는 라벨 없는 출력이면 오디오 자동 매핑이 꺼져 무음 mp4가 나온다. 최종 출력을 `[v]`로 라벨링하고 `-map "[v]" -map 0:a?`(원본에 오디오 없을 수 있어 `?`)를 명시한다. `-vf` 모드(크롭/패드)는 오디오가 자동 매핑되지만, 통합 테스트로 세 모드 모두 오디오 유지를 확인한다.
- **blur_pad는 v1.1로 연기.** 상위 설계 문서가 v1을 단색 여백으로, 흐린 배경을 v1.1로 정한 결정을 존중한다. v1 기본은 중앙 크롭(CROP), 대안은 단색 패드(PAD). 흐린 배경 명령은 위에 정확히 명시해 두되 v1.1에서 활성화한다.
- **세로/좁은 소스 가드.** 크롭 폭 `ih*9/16`이 원본 폭 `iw`보다 크면(이미 세로이거나 좁은 소스) ffmpeg가 실패한다. 인코딩 전 ffprobe로 소스 종횡비를 확인해, 9:16보다 넓지 않으면 CROP 대신 PAD로 자동 전환한다.
- **진행률.** `-progress pipe:1`의 stdout에서 `out_time_us / (clip_len*1_000_000)`로 계산한다. `out_time_ms`는 이름과 달리 마이크로초이므로 쓰지 않고 `out_time_us`를 1차값, `out_time` 문자열을 폴백으로 둔다. `N/A` 초기값을 방어한다.
- **좌표 환산.** 브라우저 오버레이 좌표는 표시 크기가 아니라 영상 실제 해상도(`videoWidth/clientWidth` 비율)로 환산해 crop 인자에 넘긴다.

---

## 9. 번들 실행파일 경로

`bin/`에 `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe`를 동봉한다(gyan.dev/BtbN 정적 빌드 + yt-dlp 릴리스). 최초 실행 다운로드가 없어 오프라인에도 견고하다.

```python
# wrappers/binaries.py
# v1(.cmd + venv): 앱 루트 기준 bin/
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/ -> backend/ -> clipman/
BIN = os.path.join(BASE, "bin")
# v2(PyInstaller onefile): 자원은 sys._MEIPASS에 풀리므로 그때는 아래로 교체
# if getattr(sys, "frozen", False): BIN = os.path.join(sys._MEIPASS, "bin")
FFMPEG  = os.path.join(BIN, "ffmpeg.exe")
FFPROBE = os.path.join(BIN, "ffprobe.exe")
YTDLP   = os.path.join(BIN, "yt-dlp.exe")
```

리뷰 반영: v1은 frozen이 아니므로 venv 경로만 둔다. PyInstaller onefile(v2)에서는 `--add-binary`로 넣은 자원이 `sys.executable` 옆이 아니라 `sys._MEIPASS`에 풀리므로, 그 시점에 위 주석 분기를 활성화한다. 라이선스: gyan.dev는 GPL 빌드로 개인 로컬 사용에는 무관하고 제3자 배포 시에만 의무가 생긴다(필요 시 BtbN LGPL 빌드).

---

## 10. 에러 분류 (동작-분기 우선, 성장식)

리뷰 반영: 번들 바이너리를 돌려보기 전 오류 문자열을 예측한 12코드 격식을 걷어내고, **실제로 동작을 분기시키는 소수 코드**만 v1에 둔다. 나머지는 generic 버킷 + stderr 상세로 시작하고, 관측되면 그때 코드를 추가한다.

다운로드(yt-dlp): stdout/stderr 문자열 매칭으로 판정.

| 감지 | error_code | 동작 | 사용자 메시지 |
|---|---|---|---|
| `not a bot` | BOT_BLOCK | 쿠키 -> player_client -> 갱신 폴백 | 자동 접속 의심 차단. 로그인 정보로 재시도합니다. |
| `Requested format is not available` | FORMAT_UNAVAILABLE | 포맷 완화 재시도 | 화질을 찾을 수 없어 다른 화질로 재시도합니다. |
| `timed out`, `Connection`, `5xx` | NETWORK | 지수 백오프 재시도 | 네트워크 문제로 재시도합니다. |
| 그 외 실패 | DOWNLOAD_FAILED | 없음(즉시 실패) | 다운로드 실패. (stderr 마지막 N줄 접힌 상세) |

편집(ffmpeg): 성공/실패는 종료코드로만(0=성공, 그 외 실패), 종류는 stderr 패턴으로. `-hide_banner -loglevel error`로 오류 라인만 남긴다. v1은 크롭 범위 초과만 별도 처리(사용자가 고칠 수 있으므로), 나머지는 generic.

| stderr 패턴 | error_code | 사용자 메시지 |
|---|---|---|
| `Invalid too big or non positive size` | CROP_OUT_OF_RANGE | 자를 영역이 영상 크기를 벗어났습니다. 크롭을 줄이세요. |
| 그 외 실패 | ENCODE_FAILED | 편집 실패. (stderr 마지막 N줄 접힌 상세) |

추가 판정: 종료코드 0이어도 출력 파일이 없거나 크기 0이면 실패로 본다(항상 재검증).

---

## 11. 프론트엔드 설계 (Svelte + Vite)

- **순수 Svelte + Vite SPA:** `npm create vite@latest clipman-ui -- --template svelte-ts`. 단일 화면이라 SvelteKit 어댑터/SSR 개념이 불필요하다.
- **개발 프록시:** `vite.config.js`의 `server.proxy`로 `/api`를 `http://localhost:9000`에 넘긴다(CORS 불필요).
- **화면(3단계):** 가져오기(URL 입력 -> `/api/metadata` 미리보기, 화질 목록 표시) -> 편집(`GET .../source`로 원본 재생, 타임라인 트림, 9:16 크롭 오버레이, 모드 선택) -> 내보내기(진행률 폴링 -> `reveal`로 결과 폴더 열기).
- **트림/크롭 UI:** 재생 위치는 `video.currentTime`과 `timeupdate`, 프레임 정밀이 필요할 때만 `requestVideoFrameCallback`(과설계 회피). 타임라인 핸들과 크롭 오버레이는 절대 위치 div를 `pointerdown/move/up`으로 드래그해 상태로 관리하고 ffmpeg 인자로 환산한다.
- **버전:** create-vite가 설치하는 버전을 쓰되, Vite 8(신 메이저) 플러그인 호환 문제 시 Vite 7.x로 고정.

---

## 12. 테스트 전략

| 대상 | 방법 |
|---|---|
| FastAPI 엔드포인트 | `fastapi.testclient.TestClient`(httpx). 동기 `def test_...` |
| subprocess 의존 코드 | 실제 실행 금지. `pytest-mock`/`pytest-subprocess`로 위조 |
| 명령 조립 로직 | 순수 함수로 분리해 반환 인자 리스트 단위 비교(바이너리 없이) |
| 실제 인코딩 통합 | `ffmpeg -f lavfi -i testsrc=... -f lavfi -i sine=...`로 **오디오 포함** 합성 영상 생성(리뷰 반영: 무음 결함을 잡으려면 픽스처에 오디오 필수), 출력 해상도/길이/**오디오 스트림 존재**를 검증 |
| 봇차단/네트워크 실패 | subprocess 모킹으로 비정상 returncode+stderr 위조, 사용자 친화 오류 검증 |
| 실제 YouTube 접속 | `@pytest.mark.network`로 격리, 상시 스위트 제외 |

리뷰 반영: 세로 변환 통합 테스트 픽스처는 반드시 오디오를 포함한다(`sine` 입력 추가). 오디오 없는 testsrc만 쓰면 blur_pad류 오디오 누락을 원리적으로 못 잡는다. 세 모드 모두 결과물의 오디오 스트림 존재를 ffprobe로 단언한다.

---

## 13. 패키징과 첫 설치 (비개발자 현실 반영)

리뷰 반영: 사용자는 비개발자다. "개발 PC라 마찰 0" 전제는 성립하지 않는다. 따라서 첫 설치는 사용자가 아니라 **Claude가 대신 수행**한다(전 계정 실행 위임 원칙: 사용자가 하는 일이 말 한마디면 Claude가 처리한다). 절차:

1. Claude가 이 PC에 Python 확인/설치를 돕고, `backend/`에 venv 생성 후 `pip install -r requirements.txt`.
2. Claude가 `bin/`에 `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe`를 내려받아 배치.
3. Claude가 `frontend/`에서 `npm install && npm run build`로 `dist/`를 1회 생성.
4. 이후 사용자는 `start.cmd` 더블클릭만 하면 된다: venv 활성화 -> `python -m app.main`(내부에서 빈 포트 선택 + uvicorn 단일 워커 실행 + 브라우저 자동 열기). 실패 시 콘솔을 닫지 않고 오류와 `logs/clipman.log` 위치를 보여준다.

- **v2(남에게 배포):** PyInstaller onefile. `dist/`를 `--add-data`, `bin/`을 `--add-binary`로 동봉하고 `sys._MEIPASS` 기준 경로. `uvicorn.run(app, ...)`에 문자열 아닌 app 객체 전달. 미서명 exe 백신 오탐과 기동 지연을 감안.

---

## 14. 로드맵 확장 지점 (정직한 표현)

리뷰 반영: "기존 코드를 전혀 안 건드린다"는 과장이다. 정확히는 **국소 확장(새 모듈 추가 + 기존 모델의 하위호환 필드 추가)으로 흡수하며, 전면 재작성은 없다**. 구체적으로:

- **v2 자동 자막:** `wrappers/whisper.py` + `services/subtitle.py` 신설. `EditOptions`에 자막 옵션 필드 추가(하위호환, 기본 off). 진행률은 status에 자막 단계를 얇게 추가하거나 인코딩 진행률에 흡수. ffmpeg 자막 렌더링 명령을 `wrappers/ffmpeg.py`에 추가. 기존 다운로드/크롭 경로는 불변.
- **v3 자동 하이라이트:** `services/highlight.py` 신설(음성 에너지/장면 전환 분석). `JobStatus.ANALYZING`(이미 예약)과 JobState에 추천 구간 필드 추가. 결과가 타임라인 UI에 추천 구간으로 표시된다.
- **확장 후보:** 다중 플랫폼(yt-dlp가 이미 지원), 배치 처리, 프리셋 저장.

3계층 경계와 하위호환 필드 추가 원칙 덕에 확장이 국소적이지만, EditOptions/JobStatus/상태기계에 필드가 더해지는 것은 사실이므로 v1 모델을 확장 가능하게(리스트, optional 필드) 설계해 둔다.

---

## 15. 확정 결정과 재심 대상 전제

확정: (1) yt-dlp/ffmpeg 모두 번들 실행파일 + subprocess + Popen 취소, (2) 단일 워커 + 폴링, (3) gyan.dev 정적 번들, (4) 다운로드/export 분리 + 원본 보존으로 "한 번 받아 여러 번 편집", (5) filter_complex 오디오 명시 매핑, (6) v1 세로 모드는 CROP/PAD, blur_pad는 v1.1, (7) 동작-분기 우선 성장식 에러, (8) 첫 설치는 Claude가 대행, 이후 더블클릭.

재심 대상 전제(구현 착수 시 실측):
- 번들 ffmpeg 실제 버전에서 세 필터와 컷 정확도, 세 모드의 오디오 유지를 통합 테스트로 1회 검증.
- Windows 최신 Chrome App-Bound Encryption으로 `--cookies-from-browser`가 막힐 수 있음. 자동 브라우저 열기와의 충돌 때문에 `--cookies` 파일 폴백을 1순위로 검토.
- yt-dlp `player_client` 유효 조합은 자주 바뀜. 설정으로 빼 폴백으로만 사용.
- 포트 자동 선택 시 브라우저에 전달할 실제 포트 배선을 확인.

---

## 다음 단계 (이 문서 범위 밖)

이 문서로 개발 아키텍처를 확정한다. 사용자 사인오프 후 다음 단계는 구현 계획 수립(writing-plans: 파일별 작업 순서, TDD 단위)이며 별도 착수 대상이다.
