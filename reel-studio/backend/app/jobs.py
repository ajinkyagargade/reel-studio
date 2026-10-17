"""Background job runner. Jobs write their progress into the store; the UI polls."""
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Callable

from . import config, store

log = logging.getLogger("reelstudio")
_pool = ThreadPoolExecutor(max_workers=config.JOB_WORKERS, thread_name_prefix="job")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def submit(fn: Callable, *args, kind: str = "", doc_id: str = "") -> None:
    """Run fn in the pool. On crash, mark the (kind, doc_id) document as failed."""
    def runner():
        try:
            fn(*args)
        except Exception as e:  # noqa: BLE001
            log.error("job failed: %s\n%s", e, traceback.format_exc())
            if kind and doc_id:
                store.update(kind, doc_id, status="failed", message=str(e)[:400], progress=0)
    _pool.submit(runner)


def recover_orphans() -> None:
    """After a restart, anything left 'processing'/'rendering' can never finish - mark it failed."""
    for kind in ("videos", "reels", "explainers", "captioned"):
        for doc in store.list_docs(kind):
            if doc.get("status") in ("processing", "rendering", "uploaded"):
                store.update(kind, doc["id"], status="failed", message="Interrupted by a server restart. Please retry.")
    for doc in store.list_docs("explainers"):  # the explanation stays valid; only an unfinished reel is lost
        if (doc.get("reel") or {}).get("status") == "processing":
            store.update("explainers", doc["id"], reel={**doc["reel"], "status": "failed", "progress": 0,
                                                         "message": "Interrupted by a server restart. Please retry."})
