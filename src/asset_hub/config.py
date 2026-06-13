from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from asset_hub import runtime


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ASSET_HUB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Field(default_factory=runtime.data_root)
    backend_port: int = 8000
    frontend_port: int = 5173
    backend_host: str | None = None

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.data_dir / 'asset_hub.db'}"

    @property
    def attachments_dir(self) -> Path:
        return self.data_dir / "attachments"

    @property
    def pids_dir(self) -> Path:
        return self.data_dir / "pids"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    def resolve_backend_host(self, mode: Literal["dev", "prod"]) -> str:
        if self.backend_host is not None:
            return self.backend_host
        return "127.0.0.1" if mode == "dev" else "0.0.0.0"
