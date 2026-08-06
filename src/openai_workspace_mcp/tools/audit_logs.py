"""OpenAI organization audit log tool — list.

Tool naming convention: openai_<action>_<resource>
"""

import json
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..api_client import OpenAIAdminClient, OpenAIError

_NO_CREDENTIALS = (
    "Error: No OpenAI Admin API key configured. Set OPENAI_ADMIN_API_KEY or use AUTH_MODE=gateway."
)


def register(mcp: FastMCP, client_factory: Callable[[], OpenAIAdminClient | None]) -> None:
    @mcp.tool()
    async def openai_list_audit_logs(
        effective_start_time: int | None = None,
        effective_end_time: int | None = None,
        actor_emails: list[str] | None = None,
        actor_ids: list[str] | None = None,
        event_types: list[str] | None = None,
        project_ids: list[str] | None = None,
        resource_ids: list[str] | None = None,
        after: str | None = None,
        before: str | None = None,
        limit: int | None = None,
    ) -> str:
        """List user actions and configuration changes in the organization.

        Args:
            effective_start_time: Only events at/after this Unix timestamp (seconds).
            effective_end_time: Only events before this Unix timestamp (seconds).
            actor_emails: Only events performed by users with these emails.
            actor_ids: Only events performed by these actors (user, service
                account, or API key tracking IDs).
            event_types: Only events of these types, e.g. `project.created`,
                `user.added`, `api_key.deleted`, `invite.sent`. See
                https://platform.openai.com/docs/api-reference/audit-logs/object
                for the full enum.
            project_ids: Only events scoped to these projects.
            resource_ids: Only events affecting these resource IDs.
            after: Pagination cursor from a previous response's `last_id`.
            before: Pagination cursor to fetch the previous page.
            limit: Maximum number of events to return per page.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        params: dict = {
            "actor_emails": actor_emails,
            "actor_ids": actor_ids,
            "event_types": event_types,
            "project_ids": project_ids,
            "resource_ids": resource_ids,
            "after": after,
            "before": before,
            "limit": limit,
        }
        if effective_start_time is not None:
            params["effective_at[gte]"] = effective_start_time
        if effective_end_time is not None:
            params["effective_at[lt]"] = effective_end_time
        try:
            result = await client.get("/organization/audit_logs", params=params)
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"
