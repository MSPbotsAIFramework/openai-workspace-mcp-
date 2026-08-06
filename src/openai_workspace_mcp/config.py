from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Transport
    mcp_transport: Literal["stdio", "http"] = "stdio"
    mcp_http_port: int = 8080
    mcp_http_host: str = "0.0.0.0"

    # Auth mode:
    # "gateway" — production/SOP-compliant: Admin API key from HTTP header per request
    #             (no global state, no cached credential).
    # "env"     — local dev only: shared Admin API key from OPENAI_ADMIN_API_KEY env var.
    auth_mode: Literal["env", "gateway"] = "gateway"

    # OpenAI Admin API key (only required in env mode). Distinct from a regular
    # sk-... API key — created by an org Owner under Settings -> Admin API Keys.
    openai_admin_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"

    # Header name used to pass the Admin API key in gateway mode.
    openai_admin_key_header: str = "x-openai-admin-key"

    @property
    def has_credentials(self) -> bool:
        """Returns True if the server can serve API calls.

        Gateway mode always returns True — each request carries its own key.
        Env mode requires OPENAI_ADMIN_API_KEY to be set.
        """
        if self.auth_mode == "gateway":
            return True
        return self.openai_admin_api_key is not None


def get_settings() -> Settings:
    return Settings()
