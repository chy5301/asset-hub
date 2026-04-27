from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request

from asset_hub.api.routers import assets, attachments, checkouts, types
from asset_hub.errors import (
    AssetHubError,
    DuplicateError,
    NotFoundError,
    StateError,
    ValidationError,
)

_EXC_STATUS: dict[type[AssetHubError], int] = {
    NotFoundError: 404,
    DuplicateError: 409,
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
    app.include_router(checkouts.router, prefix="/api/assets", tags=["checkouts"])
    app.include_router(attachments.router, prefix="/api", tags=["attachments"])

    for exc_cls, status in _EXC_STATUS.items():
        app.add_exception_handler(exc_cls, _make_handler(status))

    return app


app = create_app()
