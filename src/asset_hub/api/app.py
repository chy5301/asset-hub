from fastapi import FastAPI

from asset_hub.api.routers import types


def create_app() -> FastAPI:
    app = FastAPI(title="asset-hub", version="0.1.0")
    app.include_router(types.router, prefix="/api/types", tags=["types"])
    return app


app = create_app()
