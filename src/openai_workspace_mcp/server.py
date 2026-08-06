import contextvars
import sys

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .api_client import OpenAIAdminClient
from .config import Settings

# ─────────────────────────────────────────────────────────────────────────────
# Per-request Admin API key contextvar for gateway mode.
# GatewayKeyMiddleware sets this before the MCP handler runs.
# Python asyncio copies context per task, so concurrent requests are isolated.
# ─────────────────────────────────────────────────────────────────────────────
_gateway_key_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "openai_gateway_admin_key", default=None
)


def get_client_from_context(settings: Settings) -> OpenAIAdminClient | None:
    """Resolve the active OpenAIAdminClient for the current request context."""
    if settings.auth_mode == "gateway":
        key = _gateway_key_var.get()
    else:
        key = settings.openai_admin_api_key

    if not key:
        return None
    return OpenAIAdminClient(key, settings.openai_base_url)


class GatewayKeyMiddleware:
    """ASGI middleware for gateway mode.

    Reads the configured Admin API key header from each request and stores it in
    the contextvar for the duration of that request. Returns 401 if the header
    is missing on /mcp requests.
    """

    def __init__(self, app: ASGIApp, settings: Settings):
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not path.startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        # Header lookup is case-insensitive in Starlette
        key = request.headers.get(self.settings.openai_admin_key_header.lower())
        if not key:
            response = JSONResponse(
                {
                    "error": "Missing credentials",
                    "message": (
                        f"Gateway mode requires the {self.settings.openai_admin_key_header} header"
                    ),
                    "required_headers": [self.settings.openai_admin_key_header],
                },
                status_code=401,
            )
            await response(scope, receive, send)
            return

        ctx_token = _gateway_key_var.set(key)
        try:
            await self.app(scope, receive, send)
        finally:
            _gateway_key_var.reset(ctx_token)


def create_mcp_server(settings: Settings) -> FastMCP:
    """Build the FastMCP server instance and register all tools."""
    # DNS-rebinding protection is disabled because the container runs behind
    # mcp-gateway on an internal Docker network and is never publicly exposed.
    mcp = FastMCP(
        name="openai-workspace-mcp",
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    def client_factory() -> OpenAIAdminClient | None:
        return get_client_from_context(settings)

    if not settings.has_credentials:
        # Graceful degradation: register only a diagnostic tool when no credentials are available.
        @mcp.tool()
        async def openai_test_connection() -> str:
            """Test OpenAI Admin API connection.

            Shows configuration requirements when credentials are missing.
            """
            return (
                "Error: Missing OpenAI Admin API key.\n\n"
                "Set the required environment variable:\n"
                "  OPENAI_ADMIN_API_KEY=sk-admin-...\n\n"
                "Or use gateway mode (per-request key):\n"
                "  AUTH_MODE=gateway\n"
                f"  Send header: {settings.openai_admin_key_header}: sk-admin-..."
            )

        print(
            "Warning: No OpenAI Admin API key found. Only the diagnostic tool is available.",
            file=sys.stderr,
        )
        return mcp

    from .tools import (
        audit_logs,
        invites,
        org_users,
        project_api_keys,
        project_users,
        projects,
        rate_limits,
        service_accounts,
        usage_costs,
    )

    org_users.register(mcp, client_factory)
    invites.register(mcp, client_factory)
    projects.register(mcp, client_factory)
    project_users.register(mcp, client_factory)
    service_accounts.register(mcp, client_factory)
    project_api_keys.register(mcp, client_factory)
    rate_limits.register(mcp, client_factory)
    audit_logs.register(mcp, client_factory)
    usage_costs.register(mcp, client_factory)

    return mcp
