import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from asset_hub.api.routers import (
    assets,
    attachments,
    health,
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
    app.include_router(health.router, prefix="/api", tags=["health"])

    for exc_cls, status in _EXC_STATUS.items():
        app.add_exception_handler(exc_cls, _make_handler(status))

    # prod 模式 SPA 托管：dist 存在时挂载到根路径，并对未命中的非 /api、非静态
    # 资产路径 fallback 到 index.html（TanStack Router 客户端路由刷新需此 fallback）。
    # dev 模式 dist 不存在 → 不挂载，浏览器走 Vite 5173；测试环境同样跳过。
    #
    # 路径冲突：vite 默认 assetsDir="assets"，与前端 SPA 路由 /assets/{id} 同前缀；
    # 静态资产名永远带 hash + 扩展名（如 index-B7-2Mqlb.js），SPA 路由不带扩展名
    # （UUID 或 "new"），靠 Path.suffix 区分。
    #
    # ASSET_HUB_MODE=dev 时跳过挂载——避免 backend :8000 兜底回旧 dist SPA，
    # 让用户访问 :8000 看到的是过期 build；dev 模式应只走 Vite :5173 拿热更代码。
    # lifecycle.py 启 backend 前注入此变量；测试 / 直跑 uvicorn 不设变量则按原行为。
    _is_dev_mode = os.environ.get("ASSET_HUB_MODE") == "dev"
    if not _is_dev_mode and _FRONTEND_DIST.is_dir() and (_FRONTEND_DIST / "index.html").exists():
        index_html = _FRONTEND_DIST / "index.html"

        @app.exception_handler(404)
        async def _spa_fallback(request: Request, _exc: Exception):
            path = request.url.path
            looks_like_static_asset = bool(Path(path).suffix)
            if path.startswith("/api/") or looks_like_static_asset:
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            return FileResponse(
                index_html,
                headers={"Cache-Control": "no-cache, must-revalidate"},
            )

        # SPA 缓存策略 middleware：
        # - /assets/* 是 vite hash 文件名（如 index-Csgk9Ll1.js），1 年 immutable
        # - / 与其他无扩展名 SPA 路由 → no-cache, must-revalidate（强制 conditional
        #   request 比对 ETag → 304 不下载，但保证版本鲜度）
        #
        # 没有此 middleware 时浏览器对无 Cache-Control 的 HTML 走 heuristic 缓存
        # （约 (Date - Last-Modified) / 10），prod 启动后用户改前端代码 + dist 重新
        # build + backend 也挂载新 dist，但浏览器仍可能从本地缓存返回旧 HTML（连带
        # 加载到旧 JS hash 引用）——表现为 'prod 启动旧前端'。
        @app.middleware("http")
        async def _add_static_cache_headers(request: Request, call_next):
            response = await call_next(request)
            path = request.url.path
            if path.startswith("/api/"):
                return response
            if path.startswith("/assets/") and "." in path:
                response.headers.setdefault(
                    "Cache-Control", "public, max-age=31536000, immutable"
                )
            elif path == "/" or not Path(path).suffix:
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


app = create_app()
