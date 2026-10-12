"""브라우저 검사 전용 서버. 실제 YouTube 대신 소유한 합성 파일만 확보한다."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import uvicorn
from app.jobs.manager import JobManager
from app.main import create_app
from app.services.engine import Engine
from app.wrappers import binaries, ytdlp

workspace = tempfile.TemporaryDirectory(prefix="clipman-browser-")
root = Path(workspace.name)
fixture = root / "fixture.mp4"
subprocess.run([str(binaries.require(binaries.FFMPEG)), "-v", "error", "-y",
    "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30:duration=2",
    "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(fixture)],
    check=True, capture_output=True)
def test_download(url, quality, work_dir, **kwargs):
    script = "import shutil,sys;shutil.copyfile(sys.argv[1],sys.argv[2]);print('download:1/1/NA')"
    # Engine가 앞에 넣는 --ignore-config를 Python 자체가 소비하지 않도록 exec 인자를 둔다.
    return [sys.executable, "-c", script, str(fixture), str(Path(work_dir) / "source.mp4")]
ytdlp.build_download_args = test_download
engine = Engine(JobManager(root / "work"), root / "output")
# 합성 획득은 Python 명령이므로 yt-dlp 설정 플래그를 테스트 하네스 안에서만 제거한다.
real_run = engine._run
def test_run(job_id, generation, args, parser=None):
    if args[0] == sys.executable and args[1] == "--ignore-config":
        args = [args[0], *args[2:]]
    return real_run(job_id, generation, args, parser)
engine._run = test_run
token = "browser-test-key-only-not-production-123456789"
app = create_app(engine, token, 9019)
@app.get("/ready")
def ready():
    return {"ready": True}
(ROOT / "logs").mkdir(exist_ok=True)
shutil.copyfile(fixture, ROOT / "logs/browser-source.mp4")
(ROOT / "logs/browser-fixture.json").write_text(json.dumps({"baseUrl": "http://127.0.0.1:9019", "token": token}), encoding="utf-8")
try:
    uvicorn.run(app, host="127.0.0.1", port=9019, access_log=False)
finally:
    workspace.cleanup()
