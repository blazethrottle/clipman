from fastapi.testclient import TestClient
import pytest

from app.capture import Selection, SourceTimeline
from app.jobs.manager import JobManager
from app.main import create_app, EXTENSION_ID
from app.wrappers.ffprobe import SourceMeta


class StubEngine:
    def __init__(self, root):
        self.manager = JobManager(root / "work")
        self.exports = []
    def acquire(self, selection, quality):
        return self.manager.create(selection, quality)
    def export(self, job_id, options):
        self.exports.append(options)
        self.manager.begin_encode(job_id, options)
    def close(self):
        pass


@pytest.fixture
def api(tmp_path):
    engine = StubEngine(tmp_path)
    app = create_app(engine=engine, token="test-key", port=9000)
    with TestClient(app, base_url="http://127.0.0.1:9000") as client:
        yield client, engine


HEADERS = {"X-Clipman-Token": "test-key", "X-Clipman-Extension": EXTENSION_ID}
PAYLOAD = {"video_id": "BaW_jenozKc", "url": "https://youtu.be/BaW_jenozKc", "start_sec": 120, "end_sec": 135}


def test_valid_extension_can_create_and_poll(api):
    client, engine = api
    response = client.post("/api/jobs", json=PAYLOAD, headers=HEADERS)
    assert response.status_code == 201
    job_id = response.json()["job_id"]
    state = client.get(f"/api/jobs/{job_id}", headers=HEADERS).json()
    assert state["selection"]["start_sec"] == 120
    assert "work_dir" not in state and "_proc" not in state


@pytest.mark.parametrize("headers", [
    {}, {"X-Clipman-Token": "wrong", "X-Clipman-Extension": EXTENSION_ID},
    {**HEADERS, "Origin": "https://evil.test"},
    {**HEADERS, "Origin": "http://127.0.0.1.evil.test"},
    {**HEADERS, "X-Clipman-Extension": "a" * 32},
    {**HEADERS, "Host": "evil.test:9000"},
])
def test_untrusted_web_requests_are_rejected(api, headers):
    client, _ = api
    assert client.post("/api/jobs", json=PAYLOAD, headers=headers).status_code == 403


def test_arbitrary_cors_preflight_is_rejected(api):
    client, _ = api
    assert client.options("/api/jobs", headers={"Origin": "https://evil.test", "Access-Control-Request-Method": "POST"}).status_code == 403


@pytest.mark.parametrize("extra", [{"end_sec": 110}, {"video_id": "abcdefghijk"}, {"quality": "invalid"}, {"url": "http://127.0.0.1/private"}])
def test_invalid_job_never_reaches_engine(api, extra):
    client, engine = api
    assert client.post("/api/jobs", json={**PAYLOAD, **extra}, headers=HEADERS).status_code == 422
    assert engine.manager._jobs == {}


def test_unknown_job_is_404(api):
    client, _ = api
    assert client.get("/api/jobs/missing", headers=HEADERS).status_code == 404


def ready_source(engine):
    job = engine.manager.create(Selection(**{k: v for k, v in PAYLOAD.items() if k != "quality"}))
    token = engine.manager.begin_download(job.job_id)
    source = job.work_dir / "source.mp4"
    source.write_bytes(b"0123456789")
    engine.manager.downloaded(job.job_id, token, source, SourceMeta(1920, 1080, 15, True), SourceTimeline(120, 15))
    return job


def test_signed_media_supports_range_but_not_another_job(api):
    client, engine = api
    job = ready_source(engine)
    state = client.get(f"/api/jobs/{job.job_id}", headers=HEADERS).json()
    media = state["source_url"]
    response = client.get(media, headers={"Range": "bytes=2-5"})
    assert response.status_code == 206
    assert response.content == b"2345"
    assert response.headers["Content-Range"] == "bytes 2-5/10"
    assert client.get(media.replace(job.job_id, "other")).status_code == 403
    assert client.get(f"/api/jobs/{job.job_id}/source").status_code == 403
    assert client.post(f"/api/jobs/{job.job_id}/export?ticket=" + media.split("ticket=")[1], json={}).status_code == 403


def test_export_uses_local_seconds_and_rejects_duplicate_or_invalid_edits(api):
    client, engine = api
    job = ready_source(engine)
    path = f"/api/jobs/{job.job_id}/export"
    assert client.post(path, json={"trim_start": 2, "trim_end": 5, "mode": "pad"}, headers=HEADERS).status_code == 202
    assert engine.exports[-1].trim_start == 2
    assert client.post(path, json={}, headers=HEADERS).status_code == 409
    assert client.post(path, json={"crop_x": -5}, headers=HEADERS).status_code == 422
    assert client.post(path, json={"target_w": 10}, headers=HEADERS).status_code == 422


def test_connection_page_cannot_be_framed_and_api_disallows_query_key(api):
    client, _ = api
    response = client.get("/connect")
    assert response.status_code == 200
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Cache-Control"] == "no-store"
    assert client.get("/api/connect?token=test-key").status_code == 403
