#!/usr/bin/env python3
"""
MutationRx — backend service.

A small FastAPI app that turns the triage engine into an actual tool: the researcher asks about a
tumor, the server runs (or retrieves) a triage job with honest staged progress, and streams back a
verdict-first result. Precomputed genotypes resolve instantly; a never-seen point mutation is a real
GPU docking job. Serves the single-page assistant workspace in app/static/.

Run:
    python app/server.py            # http://localhost:8800
    (or: uvicorn server:app --app-dir app --port 8800)

The demo runs entirely on cache — no GPU needed. Configure a GPU backend (RunPod / your own) to
compute genotypes that aren't precomputed; see docs/bring_your_own_tumor.md.
"""
import os
import sys

from fastapi import FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import triage  # noqa: E402
import tcga  # noqa: E402
from jobs import JobStore  # noqa: E402
from engine import resolve, TARGET_WT  # noqa: E402

PRODUCT = "MutationRx"
FREE_RUNS = 3  # real GPU runs allowed before a user must bring their own GPU

# No GPU backend wired by default -> the demo is fully cache-driven and cannot hang. A real backend
# (app/gpu.py) is attached here when configured; requests that need compute then run for real.
try:
    from gpu import make_backend  # noqa: E402
    _gpu = make_backend()  # returns None unless env/config provides a GPU target
except Exception:
    _gpu = None

app = FastAPI(title=f"{PRODUCT} API")
store = JobStore(gpu=_gpu)
_run_counts = {}   # client_id -> number of real compute runs used
_chat_counts = {}  # client_id -> chat messages sent (soft cap to bound live-API cost on a public demo)
CHAT_LIMIT = 40


@app.middleware("http")
async def revalidate_assets(request: Request, call_next):
    """Make the browser revalidate the page + static assets (cheap via etag) so a redeploy is picked
    up on a normal refresh, never a stale cached app.js."""
    resp = await call_next(request)
    p = request.url.path
    if p == "/" or p.startswith("/static"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


def _client(x_client_id, request):
    return x_client_id or (request.client.host if request.client else "anon")


@app.get("/api/bootstrap")
def bootstrap():
    """Everything the frontend needs on load: registry, real-tumor examples, targets, limits.

    Cache-only and cheap: it maps each tumor's mutations onto in-scope genotypes WITHOUT running the
    triage bootstrap (that heavy stats work happens per-request when a tumor is actually opened). This
    keeps page load instant even on a small CPU.
    """
    tumors = []
    try:
        for s in tcga.list_samples():
            sample = tcga.load_sample(s["sample_id"])
            matched = tcga.map_to_targets(sample["mutations"])
            if matched["matched_genotypes"]:
                tumors.append(dict(sample_id=s["sample_id"], n_mutations=s["n_mutations"],
                                   in_scope_variants=matched["in_scope_variants"],
                                   primary_genotype=matched["matched_genotypes"][0]))
    except FileNotFoundError:
        pass
    return dict(
        product=PRODUCT,
        cancer_types=triage.CANCER_TYPES,
        mutations=list(triage.MUTATIONS),
        targets=sorted(TARGET_WT),
        tumors=tumors,
        free_runs=FREE_RUNS,
    )


@app.post("/api/triage")
async def submit(request: Request, x_client_id: str = Header(default=None)):
    req = await request.json()
    client = _client(x_client_id, request)
    plan = resolve(req)
    if "error" in plan:
        return JSONResponse({"error": plan["error"], "known": plan.get("known")}, status_code=400)

    # Rate-limit only REAL compute, and only COUNT a run when there's actually a GPU to execute it.
    # (No GPU configured -> we consume nothing; the job simply surfaces the bring-your-own-GPU gate.)
    if plan.get("needs_compute"):
        provider_gpu = store.gpu is not None and not getattr(store.gpu, "client_owned", False)
        if provider_gpu:
            used = _run_counts.get(client, 0)
            if used >= FREE_RUNS:
                return JSONResponse(
                    {"error": "free_runs_exhausted",
                     "message": f"You've used your {FREE_RUNS} free compute runs. Connect your own GPU "
                                f"(RunPod key or SSH) to keep triaging new genotypes.",
                     "used": used, "limit": FREE_RUNS},
                    status_code=429)
            _run_counts[client] = used + 1  # only the shared provider GPU is metered

    job_id = store.submit(req, client)
    return {"job_id": job_id, "cached": not plan.get("needs_compute", False),
            "label": plan.get("label")}


@app.get("/api/job/{job_id}")
def job(job_id: str):
    j = store.get(job_id)
    if not j:
        return JSONResponse({"error": "unknown job"}, status_code=404)
    return j


@app.post("/api/gpu/connect")
async def gpu_connect(request: Request):
    """Connect a GPU for real compute. Accepts a RunPod endpoint id + key (server-side only, never
    stored/logged). Validates it, then routes de-novo genotypes to it."""
    from gpu import backend_from_credentials
    body = await request.json()
    backend, err = backend_from_credentials((body.get("key") or "").strip(),
                                            (body.get("endpoint") or "").strip())
    if err:
        return JSONResponse({"error": err}, status_code=400)
    store.gpu = backend
    return {"connected": True, "mode": backend.label}


@app.get("/api/usage")
def usage(request: Request, x_client_id: str = Header(default=None)):
    client = _client(x_client_id, request)
    return {"used": _run_counts.get(client, 0), "limit": FREE_RUNS,
            "gpu_connected": store.gpu is not None,
            "gpu_mode": getattr(store.gpu, "label", None)}


@app.post("/api/chat")
async def chat(request: Request, x_client_id: str = Header(default=None)):
    """Grounded, multi-turn conversation about the result currently on screen. Reuses the triage
    interpretation agent (app/chat.py). Needs an Anthropic key at runtime; without one it returns a
    clear 503 so the UI can say 'live chat needs a key' while the cached results stay fully usable."""
    body = await request.json()
    label = (body.get("label") or "").strip()
    sample_id = (body.get("sample_id") or "").strip() or None
    messages = body.get("messages") or []
    if not label:
        return JSONResponse({"error": "bad_request", "message": "missing result label"}, status_code=400)

    client = _client(x_client_id, request)
    used = _chat_counts.get(client, 0)
    if used >= CHAT_LIMIT:
        return JSONResponse(
            {"error": "chat_limit", "message": f"You've reached the {CHAT_LIMIT}-message limit for this "
             "session. Start a new triage to continue the conversation."}, status_code=429)

    try:
        import chat as chat_agent  # local import so a missing anthropic dep never breaks the whole app
        reply = chat_agent.answer(label, sample_id, messages)
    except ValueError as e:
        return JSONResponse({"error": "bad_request", "message": str(e)}, status_code=400)
    except Exception as e:  # noqa: BLE001
        # anthropic.AuthenticationError (and any credential/SDK issue) -> friendly, non-fatal message
        if "authentication" in f"{type(e).__name__} {e}".lower() or "api_key" in f"{e}".lower():
            return JSONResponse(
                {"error": "no_api_key",
                 "message": "Live chat needs an ANTHROPIC_API_KEY configured on the server. The triage "
                            "results and Claude's read above are fully available without it."},
                status_code=503)
        return JSONResponse({"error": "chat_failed", "message": f"{type(e).__name__}: {e}"}, status_code=500)

    _chat_counts[client] = used + 1
    return {"reply": reply, "used": used + 1, "limit": CHAT_LIMIT}


@app.api_route("/healthz", methods=["GET", "HEAD"], include_in_schema=False)
def healthz():
    """Zero-work liveness probe for an uptime pinger (e.g. UptimeRobot) that keeps the free Render
    instance warm. Accepts GET and HEAD so a HEAD-by-default monitor never gets a 405."""
    return {"status": "ok"}


# ---- static single-page app ----
app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(HERE, "static", "index.html"))


if __name__ == "__main__":
    import uvicorn
    # PORT/HOST from env so the same entrypoint works locally (127.0.0.1:8800) and on a host (0.0.0.0:$PORT).
    uvicorn.run(app, host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8800")))
