"""
KiranaMate — Vercel Serverless Function Entry Point

Vercel's @vercel/python runtime expects a WSGI/ASGI `app` at module scope.
This file re-exports the FastAPI app from api.main.
"""
import os
os.environ.setdefault("VERCEL", "1")

from api.main import app  # noqa: F401

# Vercel expects `app` or `handler` at module level — that's it.
