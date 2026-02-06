from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    ibkr_host: str = Field(
        default="127.0.0.1",
        alias="IBKR_HOST",
        min_length=1,
    )
    ibkr_port: int = Field(default=4002, alias="IBKR_PORT")
    ibkr_client_id: int = Field(default=1, alias="IBKR_CLIENT_ID")
    ibkr_account_id: str = Field(default="", alias="IBKR_ACCOUNT_ID")

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

    @property
    def IBKR_HOST(self) -> str:
        return self.ibkr_host

    @property
    def IBKR_PORT(self) -> int:
        return self.ibkr_port

    @property
    def IBKR_CLIENT_ID(self) -> int:
        return self.ibkr_client_id

    @property
    def IBKR_ACCOUNT_ID(self) -> str:
        return self.ibkr_account_id
