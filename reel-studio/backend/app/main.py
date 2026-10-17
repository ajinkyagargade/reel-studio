"""Reel Studio API (Starlette). Run: uvicorn app.main:app --port 8000"""
import logging
import shutil
from contextlib import asynccontextmanager
import uuid
from pathlib import Path

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import assets, captions, config, explainer, jobs, llm, media, options, pipeline, render, reels, store, transcribe, tts

logging.basicConfig(level=logging.INFO)
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".flv", ".wmv", ".mpeg", ".mpg", ".3gp"}


def ok(data, status=200):
    return JSONResponse(data, status_code=status)


def need(kind: str, doc_id: str, label: str):
    doc = store.get(kind, doc_id)
    if not doc:
        raise HTTPException(404, f"{label} not found")
    return doc


def public_video(v: dict) -> dict:
    return {k: val for k, val in v.items() if k != "path"}


async def body(request: Request) -> dict:
    try:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# ------------------------------------------------------------------ system
async def health(request: Request):
    return ok({
        "ok": True,
        "ffmpeg": media.ffmpeg_available(),
        "whisper": transcribe.available(),
        "whisperModel": config.WHISPER_MODEL,
        "claude": llm.available(),
        "claudeModel": config.CLAUDE_MODEL if llm.available() else None,
        "aiVoice": _edge_available(),
    })


def _edge_available() -> bool:
    try:
        import edge_tts  # noqa: F401
        return True
    except Exception:
        return False


async def get_options(request: Request):
    return ok(options.catalog())


# ------------------------------------------------------------------ videos
async def upload(request: Request):
    form = await request.form()
    f = form.get("file")
    if f is None or not hasattr(f, "filename"):
        raise HTTPException(400, "No file was uploaded")
    ext = Path(f.filename or "").suffix.lower()
    if ext not in VIDEO_EXT and not (f.content_type or "").startswith("video/"):
        raise HTTPException(400, "Please upload a video file (mp4, mov, mkv, webm...)")
    if not media.ffmpeg_available():
        raise HTTPException(500, "ffmpeg is not installed on the server")
    video_id = uuid.uuid4().hex[:12]
    dest = config.UPLOAD_DIR / f"{video_id}{ext or '.mp4'}"
    limit, size = int(config.MAX_UPLOAD_GB * 1024 ** 3), 0
    with dest.open("wb") as out:
        while chunk := await f.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"File is larger than {config.MAX_UPLOAD_GB:g} GB")
            out.write(chunk)
    try:
        await run_in_threadpool(media.probe, dest)
    except Exception:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, "That file could not be read as a video")
    language = str(form.get("language") or "auto")
    doc = {
        "id": video_id, "filename": dest.name, "originalName": f.filename, "path": str(dest), "status": "uploaded",
        "progress": 1, "message": "Queued", "duration": None, "createdAt": jobs.now_iso(), "thumbnailUrl": None,
        "language": language, "meta": {},
    }
    store.put("videos", video_id, doc)
    jobs.submit(pipeline.process_video, video_id, kind="videos", doc_id=video_id)
    return ok({"id": video_id, "message": "Upload complete. Processing started."})


async def list_videos(request: Request):
    return ok([public_video(v) for v in store.list_docs("videos")])


async def get_video(request: Request):
    return ok(public_video(need("videos", request.path_params["video_id"], "Video")))


async def delete_video(request: Request):
    vid = request.path_params["video_id"]
    v = need("videos", vid, "Video")
    if v["status"] == "processing":
        raise HTTPException(409, "Video is still processing")
    for r in store.list_docs("reels", {"videoId": vid}):
        reels.delete_reel(r["id"])
    Path(v["path"]).unlink(missing_ok=True)
    shutil.rmtree(config.WORK_DIR / vid, ignore_errors=True)
    (config.OUTPUT_DIR / f"captioned_{vid}.mp4").unlink(missing_ok=True)
    store.delete("captioned", vid)
    store.delete("analysis", vid)
    store.delete("videos", vid)
    return ok({"message": "Deleted"})


async def stream_video(request: Request):
    v = need("videos", request.path_params["video_id"], "Video")
    return FileResponse(v["path"])  # Starlette handles HTTP Range requests (seeking)


async def thumbnail(request: Request):
    p = config.WORK_DIR / request.path_params["video_id"] / "thumb.jpg"
    if not p.exists():
        raise HTTPException(404, "No thumbnail yet")
    return FileResponse(p, media_type="image/jpeg")


async def get_transcript(request: Request):
    vid = request.path_params["video_id"]
    need("videos", vid, "Video")
    if not reels.transcript_path(vid).exists():
        raise HTTPException(404, "Transcript not ready")
    return ok(reels.load_transcript(vid))


async def get_analysis(request: Request):
    vid = request.path_params["video_id"]
    v = need("videos", vid, "Video")
    a = store.get("analysis", vid)
    if not a:
        raise HTTPException(404, "Analysis not ready")
    return ok({**a, "metadata": {**v.get("meta", {}), "fileName": v["originalName"], "uploadedAt": v["createdAt"]}})


# ------------------------------------------------------------------ reels
async def list_reels(request: Request):
    vid = request.path_params["video_id"]
    need("videos", vid, "Video")
    return ok(store.list_docs("reels", {"videoId": vid}))


async def create_reel(request: Request):
    vid = request.path_params["video_id"]
    need("videos", vid, "Video")
    data = await body(request)
    try:
        reel = await run_in_threadpool(
            reels.create_reel, vid, float(data.get("targetSeconds") or 60), data.get("numPoints"), data.get("settings"))
    except (LookupError, RuntimeError) as e:
        raise HTTPException(409, str(e))
    if data.get("render"):
        reel = reels.start_render(reel["id"])
    return ok(reel, 201)


async def get_reel(request: Request):
    return ok(need("reels", request.path_params["reel_id"], "Reel"))


async def put_reel(request: Request):
    rid = request.path_params["reel_id"]
    data = await body(request)
    try:
        reel = reels.update_reel(rid, data)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))
    return ok(reel)


async def replan_reel(request: Request):
    rid = request.path_params["reel_id"]
    reel = need("reels", rid, "Reel")
    data = await body(request)
    video, analysis = need("videos", reel["videoId"], "Video"), need("analysis", reel["videoId"], "Analysis")
    target = float(data.get("targetSeconds") or reel["settings"]["targetSeconds"])
    settings = options.normalize_settings({"targetSeconds": target}, base=reel["settings"])
    pts = reels.plan_points(analysis, video["duration"], target, data.get("numPoints"))
    return ok(store.update("reels", rid, settings=settings, points=pts, stale=True, message="Re-planned - render to apply"))


async def render_reel(request: Request):
    rid = request.path_params["reel_id"]
    need("reels", rid, "Reel")
    data = await body(request)
    try:
        if "settings" in data or "points" in data:
            reels.update_reel(rid, data)
        return ok(reels.start_render(rid))
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))


async def reel_video(request: Request):
    rid = request.path_params["reel_id"]
    reel = need("reels", rid, "Reel")
    p = config.OUTPUT_DIR / f"reel_{rid}.mp4"
    if not p.exists():
        raise HTTPException(404, "This reel has not been rendered yet")
    if request.query_params.get("download"):
        name = Path(store.get("videos", reel["videoId"])["originalName"]).stem[:40] + "-reel.mp4"
        return FileResponse(p, media_type="video/mp4", filename=name, content_disposition_type="attachment")
    return FileResponse(p, media_type="video/mp4")


async def delete_reel(request: Request):
    rid = request.path_params["reel_id"]
    need("reels", rid, "Reel")
    reels.delete_reel(rid)
    return ok({"message": "Deleted"})


# ------------------------------------------------------------------ fonts & logos
async def read_upload(request: Request, max_mb: int):
    form = await request.form()
    f = form.get("file")
    if f is None or not hasattr(f, "filename"):
        raise HTTPException(400, "No file was uploaded")
    data = await f.read()
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {max_mb} MB")
    return f.filename or "file", data


async def list_fonts(request: Request):
    return ok(assets.list_fonts())


async def upload_font(request: Request):
    name, data = await read_upload(request, 20)
    try:
        return ok(assets.save_font(name, data), 201)
    except ValueError as e:
        raise HTTPException(400, str(e))


async def font_file(request: Request):
    p = assets.font_path(request.path_params["filename"])
    if not p:
        raise HTTPException(404, "Font not found")
    return FileResponse(p, headers={"Cache-Control": "public, max-age=86400"})


async def delete_font(request: Request):
    if not assets.delete_font(request.path_params["filename"]):
        raise HTTPException(404, "Only uploaded fonts can be removed")
    return ok({"message": "Deleted"})


async def list_logos(request: Request):
    return ok(assets.list_logos())


async def upload_logo(request: Request):
    name, data = await read_upload(request, 10)
    try:
        return ok(assets.save_logo(name, data), 201)
    except ValueError as e:
        raise HTTPException(400, str(e))


async def logo_file(request: Request):
    p = assets.logo_path(request.path_params["logo_id"])
    if not p:
        raise HTTPException(404, "Logo not found")
    return FileResponse(p, media_type="image/png")


async def delete_logo(request: Request):
    if not assets.delete_logo(request.path_params["logo_id"]):
        raise HTTPException(404, "Logo not found")
    return ok({"message": "Deleted"})


# ------------------------------------------------------------------ live captions: files + burned video
async def caption_file(request: Request):
    vid, fmt = request.path_params["video_id"], request.path_params["fmt"]
    v = need("videos", vid, "Video")
    if fmt not in ("srt", "vtt"):
        raise HTTPException(404, "Use srt or vtt")
    tr = reels.load_transcript(vid)
    if not tr["words"]:
        raise HTTPException(404, "Transcript not ready")
    name = Path(v["originalName"]).stem[:40] + "." + fmt
    return PlainTextResponse(captions.subtitle_file(tr["words"], fmt), media_type="text/plain; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'} if request.query_params.get("download") else None)


def burn_job(video_id: str) -> None:
    doc = store.get("captioned", video_id)
    v = store.get("videos", video_id)
    tr = reels.load_transcript(video_id)
    out = config.OUTPUT_DIR / f"captioned_{video_id}.mp4"
    work = config.WORK_DIR / video_id / "burn"
    shutil.rmtree(work, ignore_errors=True)
    render.burn_captions(Path(v["path"]), tr["words"], doc["settings"], out, work, {**v["meta"], "duration": v["duration"]},
                         lambda f, m: store.update("captioned", video_id, progress=int(1 + 98 * f), message=m))
    shutil.rmtree(work, ignore_errors=True)
    store.update("captioned", video_id, status="ready", progress=100, message="Done",
                 outputUrl=f"/api/videos/{video_id}/captioned/video?v={int(out.stat().st_mtime)}",
                 downloadUrl=f"/api/videos/{video_id}/captioned/video?download=1")


async def start_captioned(request: Request):
    vid = request.path_params["video_id"]
    v = need("videos", vid, "Video")
    cur = store.get("captioned", vid)
    if cur and cur["status"] == "rendering":
        raise HTTPException(409, "Already rendering")
    data = await body(request)
    settings = options.normalize_settings({k: data.get("settings", {}).get(k) for k in ("captions", "logo", "quality")
                                           if data.get("settings", {}).get(k) is not None})
    store.put("captioned", vid, {"id": vid, "videoId": vid, "status": "rendering", "progress": 0, "message": "Queued",
                                 "settings": settings, "outputUrl": None, "downloadUrl": None})
    jobs.submit(burn_job, vid, kind="captioned", doc_id=vid)
    return ok(store.get("captioned", vid))


async def get_captioned(request: Request):
    doc = store.get("captioned", request.path_params["video_id"])
    return ok(doc or {"status": "none", "progress": 0})


async def captioned_video(request: Request):
    vid = request.path_params["video_id"]
    v = need("videos", vid, "Video")
    p = config.OUTPUT_DIR / f"captioned_{vid}.mp4"
    if not p.exists():
        raise HTTPException(404, "Not rendered yet")
    if request.query_params.get("download"):
        return FileResponse(p, media_type="video/mp4", filename=Path(v["originalName"]).stem[:40] + "-captioned.mp4",
                            content_disposition_type="attachment")
    return FileResponse(p, media_type="video/mp4")


# ------------------------------------------------------------------ explainer
async def create_explainer(request: Request):
    data = await body(request)
    topic = str(data.get("topic") or "").strip()
    if not topic:
        raise HTTPException(400, "Please enter a topic")
    if not llm.available():
        raise HTTPException(503, "The topic explainer needs ANTHROPIC_API_KEY set in backend/.env")
    job = explainer.start(topic[:200])
    return ok({"id": job["id"]})


async def get_explainer(request: Request):
    return ok(need("explainers", request.path_params["job_id"], "Explainer"))


async def explainer_video(request: Request):
    jid = request.path_params["job_id"]
    job = need("explainers", jid, "Explainer")
    p = config.OUTPUT_DIR / f"explainer_{jid}.mp4"
    if not p.exists():
        raise HTTPException(404, "Video not ready")
    if request.query_params.get("download"):
        return FileResponse(p, media_type="video/mp4", filename=f"{job['topic'][:40]}.mp4", content_disposition_type="attachment")
    return FileResponse(p, media_type="video/mp4")


# ------------------------------------------------------------------ app
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


async def server_error(request: Request, exc: Exception):
    logging.getLogger("reelstudio").exception("unhandled error")
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


class SPAStatic(StaticFiles):
    """Serve the built React app; unknown paths fall back to index.html for react-router."""
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as e:
            if e.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


api_routes = [
    Route("/health", health), Route("/options", get_options),
    Route("/upload", upload, methods=["POST"]),
    Route("/videos", list_videos),
    Route("/videos/{video_id}", get_video), Route("/videos/{video_id}", delete_video, methods=["DELETE"]),
    Route("/videos/{video_id}/status", get_video),
    Route("/videos/{video_id}/stream", stream_video), Route("/videos/{video_id}/thumbnail", thumbnail),
    Route("/videos/{video_id}/transcript", get_transcript), Route("/videos/{video_id}/analysis", get_analysis),
    Route("/videos/{video_id}/reels", list_reels), Route("/videos/{video_id}/reels", create_reel, methods=["POST"]),
    Route("/reels/{reel_id}", get_reel), Route("/reels/{reel_id}", put_reel, methods=["PUT"]),
    Route("/reels/{reel_id}", delete_reel, methods=["DELETE"]),
    Route("/reels/{reel_id}/replan", replan_reel, methods=["POST"]),
    Route("/reels/{reel_id}/render", render_reel, methods=["POST"]),
    Route("/reels/{reel_id}/video", reel_video),
    Route("/fonts", list_fonts), Route("/fonts", upload_font, methods=["POST"]),
    Route("/fonts/file/{filename}", font_file), Route("/fonts/{filename}", delete_font, methods=["DELETE"]),
    Route("/logos", list_logos), Route("/logos", upload_logo, methods=["POST"]),
    Route("/logos/{logo_id}/file", logo_file), Route("/logos/{logo_id}", delete_logo, methods=["DELETE"]),
    Route("/videos/{video_id}/captions/{fmt}", caption_file),
    Route("/videos/{video_id}/captioned", get_captioned), Route("/videos/{video_id}/captioned", start_captioned, methods=["POST"]),
    Route("/videos/{video_id}/captioned/video", captioned_video),
    Route("/explainer", create_explainer, methods=["POST"]),
    Route("/explainer/{job_id}", get_explainer), Route("/explainer/{job_id}/video", explainer_video),
]

routes = [Mount("/api", routes=api_routes)]
if (config.FRONTEND_BUILD / "index.html").exists():
    routes.append(Mount("/", app=SPAStatic(directory=str(config.FRONTEND_BUILD), html=True)))


@asynccontextmanager
async def lifespan(app):
    jobs.recover_orphans()
    yield


app = Starlette(
    routes=routes,
    middleware=[Middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])],
    exception_handlers={HTTPException: http_error, Exception: server_error},
    lifespan=lifespan,
)
