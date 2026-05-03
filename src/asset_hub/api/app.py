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
    if _FRONTEND_DIST.is_dir() and (_FRONTEND_DIST / "index.html").exists():
        index_html = _FRONTEND_DIST / "index.html"

        @app.exception_handler(404)
        async def _spa_fallback(request: Request, _exc: Exception):
            path = request.url.path
            looks_like_static_asset = bool(Path(path).suffix)
            if path.startswith("/api/") or looks_like_static_asset:
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            return FileResponse(index_html)

        app.mount(
            "/",
            StaticFiles(directory=str(_FRONTEND_DIST), html=True),
            name="spa",
        )

    return app


app = create_app()
