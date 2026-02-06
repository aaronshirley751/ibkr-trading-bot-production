from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    operator_id: str = Field(
        default="CSATSPRIM",
        alias="OPERATOR_ID",
        min_length=1,
    )

    model_config = SettingsConfigDict(
        env_file=(".env", "config/operator_id.env"),
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def OPERATOR_ID(self) -> str:
        return self.operator_id
