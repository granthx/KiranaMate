"""
KiranaMate — Vercel Serverless Function Entry Point
"""
import os
import sys
import traceback
import typing

# Fix Python 3.12.4+ compatibility with older pydantic v1 / langsmith
try:
    _orig_eval = typing.ForwardRef._evaluate
    def _patched_eval(self, globalns, localns, type_params=None, *, recursive_guard=None):
        if recursive_guard is None:
            recursive_guard = frozenset()
        try:
            return _orig_eval(self, globalns, localns, type_params=type_params, recursive_guard=recursive_guard)
        except TypeError:
            try:
                return _orig_eval(self, globalns, localns, type_params=type_params)
            except TypeError:
                return _orig_eval(self, globalns, localns)
    typing.ForwardRef._evaluate = _patched_eval
except Exception:
    pass

os.environ.setdefault("VERCEL", "1")

try:
    from api.main import app
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.middleware("http")
    async def vercel_path_correction(request: Request, call_next):
        """
        Vercel's rewrite engine forwards /{path} to /api/index.py.
        In some environments, the ASGI scope['path'] is set to '/api/index.py'
        or '/api/index' while the real requested path is in the 'x-matched-path'
        or 'x-forwarded-uri' header.
        This middleware restores the original path in scope so FastAPI routes match.
        """
        matched = request.headers.get("x-matched-path") or request.headers.get("x-forwarded-uri")
        curr_path = request.scope.get("path", "")
        if matched and (curr_path.endswith("/index.py") or curr_path in ("/api/index.py", "/api/index", "/api", "/")):
            request.scope["path"] = matched
        return await call_next(request)

    @app.exception_handler(404)
    async def custom_404_handler(request: Request, exc):
        return JSONResponse(
            status_code=404,
            content={
                "detail": "Not Found",
                "path": request.url.path,
                "scope_path": request.scope.get("path"),
                "matched_header": request.headers.get("x-matched-path"),
                "forwarded_uri": request.headers.get("x-forwarded-uri"),
            }
        )

except Exception as exc:
    # If the main app fails to import, create a minimal diagnostic app
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse

    app = FastAPI()

    _error_tb = traceback.format_exc()
    _error_msg = str(exc)

    @app.get("/{path:path}")
    async def diagnostic(path: str = ""):
        return PlainTextResponse(
            f"KiranaMate import failed:\n\n"
            f"Error: {_error_msg}\n\n"
            f"Traceback:\n{_error_tb}\n\n"
            f"Python: {sys.version}\n"
            f"Platform: {sys.platform}\n",
            status_code=500
        )
