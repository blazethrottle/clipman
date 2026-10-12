from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import html
import json
import re
import secrets
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from app import paths
from app.jobs.manager import InvalidTransition
from app.schemas import CaptureRequest, ExportRequest
from app.services.engine import Engine
from app.wrappers.binaries import BinaryNotFound


MANIFEST = json.loads((paths.APP_ROOT / "extension" / "manifest.json").read_text(encoding="utf-8"))
EXTENSION_ID = "".join(chr(97 + int(c, 16)) for c in hashlib.sha256(base64.b64decode(MANIFEST["key"])).hexdigest()[:32])


def create_app(engine=None, token=None, port=9000):
    engine = engine or Engine()
    token = token or secrets.token_urlsafe(32)
    authority = f"127.0.0.1:{port}"
    extension_origin = f"chrome-extension://{EXTENSION_ID}"

    @asynccontextmanager
    async def lifespan(app):
        yield
        await asyncio.to_thread(engine.close)

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.engine, app.state.token = engine, token

    def ticket(path):
        return hmac.new(token.encode(), path.encode(), hashlib.sha256).hexdigest()

    @app.middleware("http")
    async def protect(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.headers.get("host") != authority or (origin is not None and origin != extension_origin):
            return JSONResponse({"detail": "허용되지 않은 연결입니다."}, status_code=403)
        path = request.url.path
        if path.startswith("/api/"):
            media = request.method in {"GET", "HEAD"} and re.fullmatch(r"/api/jobs/[a-f0-9]{32}/(source|outputs/\d+)", path)
            valid_media = media and hmac.compare_digest(request.query_params.get("ticket", ""), ticket(path))
            valid_headers = (hmac.compare_digest(request.headers.get("x-clipman-token", ""), token)
                             and request.headers.get("x-clipman-extension") == EXTENSION_ID)
            if not valid_media and not valid_headers:
                return JSONResponse({"detail": "처리 프로그램을 다시 연결해 주세요."}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    def state(job):
        source_path = f"/api/jobs/{job.job_id}/source"
        outputs = [f"/api/jobs/{job.job_id}/outputs/{index}" for index in range(len(job.outputs))]
        return {"job_id": job.job_id, "status": job.status.value, "progress": job.progress,
                "message": job.message, "error_code": job.error_code,
                "selection": asdict(job.selection), "source_meta": asdict(job.source_meta) if job.source_meta else None,
                "source_timeline": asdict(job.source_timeline) if job.source_timeline else None,
                "origin_basis": "requested_precise_cut" if job.source_timeline else None,
                "last_edit": asdict(job.last_edit) if job.last_edit else None,
                "source_url": source_path + "?ticket=" + ticket(source_path) if job.source_path else None,
                "outputs": [{"url": path + "?ticket=" + ticket(path), "name": job.outputs[i].name} for i, path in enumerate(outputs)]}

    @app.exception_handler(KeyError)
    async def unknown(request, exc):
        return JSONResponse({"detail": "작업을 찾을 수 없습니다. 처리 프로그램이 다시 시작됐을 수 있습니다."}, status_code=404)

    @app.exception_handler(InvalidTransition)
    async def conflict(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(BinaryNotFound)
    async def missing(request, exc):
        return JSONResponse({"detail": "영상 처리 파일이 준비되지 않았습니다. 처리 프로그램 설치를 확인해 주세요."}, status_code=503)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.get("/api/connect")
    def connect():
        return {"connected": True, "extension_id": EXTENSION_ID}

    @app.post("/api/jobs", status_code=201)
    def acquire(body: CaptureRequest):
        return state(engine.acquire(body.selection(), body.quality))

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        return state(engine.manager.get(job_id))

    @app.post("/api/jobs/{job_id}/export", status_code=202)
    def export(job_id: str, body: ExportRequest):
        engine.export(job_id, body.options())
        return state(engine.manager.get(job_id))

    @app.delete("/api/jobs/{job_id}")
    def cancel(job_id: str):
        return state(engine.manager.cancel(job_id))

    @app.api_route("/api/jobs/{job_id}/source", methods=["GET", "HEAD"])
    def source(job_id: str):
        path = engine.manager.get(job_id).source_path
        if path is None or not path.is_file():
            raise HTTPException(404, "편집할 원본이 없습니다.")
        return FileResponse(path, media_type="video/mp4")

    @app.api_route("/api/jobs/{job_id}/outputs/{index}", methods=["GET", "HEAD"])
    def output(job_id: str, index: int, download: bool = False):
        outputs = engine.manager.get(job_id).outputs
        if not 0 <= index < len(outputs) or not outputs[index].is_file():
            raise HTTPException(404, "저장한 쇼츠를 찾을 수 없습니다.")
        return FileResponse(outputs[index], media_type="video/mp4", filename=outputs[index].name if download else None)

    @app.get("/connect", response_class=HTMLResponse)
    def pairing():
        code = html.escape(json.dumps({"baseUrl": f"http://{authority}", "token": token}))
        return HTMLResponse(f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>클립맨 연결</title><link rel="stylesheet" href="/connect.css"><main><span class="brand">clipman</span>
<h1>Chrome에서 보고,<br>클립맨으로 담으세요.</h1><p>로컬 처리 프로그램이 준비되었습니다. Chrome 확장 패널의 연결 화면에 아래 코드를 붙여 넣으세요.</p>
<label for="code">이 기기의 연결 코드</label><textarea id="code" readonly>{code}</textarea>
<button id="copy">연결 코드 복사</button><p id="result" role="status"></p>
<details><summary>개발용 확장 처음 열기</summary><p>Chrome 확장 관리에서 개발자 모드를 켜고 ‘압축해제된 확장 프로그램을 로드합니다’를 선택합니다. clipman의 extension/dist 폴더를 선택한 뒤 도구 모음의 클립맨 아이콘을 눌러 연결합니다.</p></details>
<p>서버가 다시 시작되면 연결 코드를 다시 복사해 주세요. 영상은 이 기기에서 처리됩니다.</p></main><script src="/connect.js"></script></html>''',
            headers={"Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; object-src 'none'"})

    @app.get("/connect.js")
    def pairing_script():
        from fastapi.responses import Response
        return Response("document.querySelector('#copy').onclick=async()=>{try{await navigator.clipboard.writeText(document.querySelector('#code').value);document.querySelector('#result').textContent='복사했습니다. 확장 패널에 붙여 넣으세요.';}catch{document.querySelector('#code').select();document.querySelector('#result').textContent='선택한 코드를 복사해 주세요.';}};", media_type="text/javascript")

    @app.get("/connect.css")
    def pairing_css():
        from fastapi.responses import Response
        return Response("body{margin:0;background:#f3f5f7;color:#18232f;font:16px/1.65 system-ui,sans-serif}main{max-width:640px;margin:8vh auto;padding:32px}.brand{font-size:24px;font-weight:750}h1{font-size:40px;line-height:1.25;margin:40px 0 24px}textarea{box-sizing:border-box;display:block;width:100%;height:110px;padding:16px;border:1px solid #dde3ea;border-radius:8px;resize:none;margin:12px 0}button{background:#356ae6;color:white;border:0;border-radius:8px;padding:14px 24px;font:inherit;cursor:pointer}details{margin-top:36px}button:focus-visible{outline:3px solid #18232f;outline-offset:3px}", media_type="text/css")
    return app
