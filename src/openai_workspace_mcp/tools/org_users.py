"""OpenAI organization member tools — list, get, update role, remove.

Tool naming convention: openai_<action>_<resource>

There is no "create user" endpoint here — joining the organization always goes
through the invite flow (see tools/invites.py).
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
    async def openai_list_users(
        emails: list[str] | None = None,
        after: str | None = None,
        limit: int | None = None,
    ) -> str:
        """List members of the OpenAI organization.

        Args:
            emails: Filter by these email addresses.
            after: Pagination cursor from a previous response's `last_id`.
            limit: Maximum number of users to return per page.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.get(
                "/organization/users", params={"emails": emails, "after": after, "limit": limit}
            )
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_get_user(user_id: str) -> str:
        """Get a single organization member's details.

        Args:
            user_id: The member's user ID (see openai_list_users).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.get(f"/organization/users/{user_id}")
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_update_user_role(user_id: str, role: str) -> str:
        """Change a member's role in the organization.

        Args:
            user_id: The member's user ID (see openai_list_users).
            role: New organization role — `owner` or `reader`.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.post(f"/organization/users/{user_id}", {"role": role})
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_remove_user(user_id: str) -> str:
        """Remove a member from the organization.

        Args:
            user_id: The member's user ID (see openai_list_users).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            await client.delete(f"/organization/users/{user_id}")
            return f"User {user_id} removed from the organization."
        except OpenAIError as e:
            return f"Error: {e}"
