import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from asset_hub.api.routers import (
    assets,
    attachments,
    health,
    stats,
    transitions,
    types,
)
from asset_hub.errors import (
    AssetHubError,
    ConflictError,
    DuplicateError,
    IllegalTransitionError,
    NotFoundError,
    StateError,
    ValidationError,
)

_FRONTEND_DIST = Path("frontend/dist")

_EXC_STATUS: dict[type[AssetHubError], int] = {
    ConflictError: 409,
    DuplicateError: 409,
    IllegalTransitionError: 409,
    NotFoundError: 404,
    StateError: 409,
    ValidationError: 422,
}


def _make_handler(status: int):
    async def handler(request: Request, exc: Exception):
        return JSONResponse(status_code=status, content={"detail": str(exc)})

    return handler


def create_app() -> FastAPI:
    app = FastAPI(title="asset-hub", version="0.1.0")
    app.include_router(types.router, prefix="/api/types", tags=["types"])
    app.include_router(assets.router, prefix="/api/assets", tags=["assets"])
    app.include_router(transitions.router, prefix="/api/assets", tags=["transitions"])
    app.include_router(attachments.router, prefix="/api", tags=["attachments"])
    app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
    app.include_router(health.router, prefix="/api", tags=["health"])

    for exc_cls, status in _EXC_STATUS.items():
        app.add_exception_handler(exc_cls, _make_handler(status))

    # prod 模式 SPA 托管：dist 存在时挂载到根路径，404 fallback 到 index.html
    # 让 TanStack Router 客户端路由刷新可工作。dev 模式（ASSET_HUB_MODE=dev）跳过挂载，
    # 避免 :8000 兜底回旧 dist SPA 覆盖 Vite :5173 热更——lifecycle.py 启 backend 前注入。
    #
    # 路径冲突：vite assetsDir="assets" 与前端 SPA 路由 /assets/{id} 同前缀；hash 资产
    # 永远带扩展名（index-B7-2Mqlb.js），SPA 路由不带扩展名（UUID/"new"），靠 suffix 区分。
    _is_dev_mode = os.environ.get("ASSET_HUB_MODE") == "dev"
    if not _is_dev_mode and _FRONTEND_DIST.is_dir() and (_FRONTEND_DIST / "index.html").exists():
        index_html = _FRONTEND_DIST / "index.html"

        @app.exception_handler(404)
        async def _spa_fallback(request: Request, _exc: Exception):
            if _classify_path(request.url.path) != "spa_route":
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            return FileResponse(
                index_html,
                headers={"Cache-Control": "no-cache, must-revalidate"},
            )

        # SPA 缓存策略：无 Cache-Control 时浏览器对 HTML 走 heuristic 缓存
        # （约 (Date - Last-Modified) / 10），prod 启动 build 新 dist 后浏览器仍可能从
        # 本地缓存返回旧 HTML（连带加载旧 JS hash 引用），表现为'prod 启动旧前端'。
        @app.middleware("http")
        async def _add_static_cache_headers(request: Request, call_next):
            response = await call_next(request)
            kind = _classify_path(request.url.path)
            if kind == "static_asset":
                response.headers.setdefault(
                    "Cache-Control", "public, max-age=31536000, immutable"
                )
            elif kind == "spa_route":
                response.headers.setdefault(
                    "Cache-Control", "no-cache, must-revalidate"
                )
            return response

        app.mount(
            "/",
            StaticFiles(directory=str(_FRONTEND_DIST), html=True),
            name="spa",
        )

    return app


def _classify_path(path: str) -> Literal["api", "static_asset", "spa_route"]:
    """SPA 部署下的请求路径分类——cache 策略 + SPA fallback 共用此分类。"""
    if path.startswith("/api/"):
        return "api"
    if path.startswith("/assets/") and Path(path).suffix:
        return "static_asset"
    return "spa_route"


app = create_app()
