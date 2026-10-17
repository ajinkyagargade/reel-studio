"""Vercel entrypoint: exposes the ASGI app as a top-level `app` (see vercel.json, entrypoint "index:app").

Importing through the `app` package keeps the relative imports inside app/*.py working.
Locally you still run:  uvicorn app.main:app --port 8000
"""
from app.main import app  # noqa: F401
