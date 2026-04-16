# src/asset_hub/config.py
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ASSET_HUB_")

    data_dir: Path = Path("data")

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.data_dir / 'asset_hub.db'}"
