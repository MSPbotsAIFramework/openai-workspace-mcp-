"""OpenAI organization invite tools — invite, list, retrieve, revoke.

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
    async def openai_invite_user(
        email: str,
        role: str,
        projects: list[dict] | None = None,
    ) -> str:
        """Invite a new user to the OpenAI organization by email.

        The invite must be accepted by the user before they gain access. Its
        "status" starts at `pending` until accepted.

        Args:
            email: Email address to invite.
            role: Organization role to grant — `owner` or `reader`.
            projects: Optional list of `{"id": <project_id>, "role": "owner"|"member"}`
                to grant project membership at the same time the invite is accepted.
                If omitted, the user is invited to the default project (legacy
                behavior). Pass an empty list to invite them to no projects at all.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        body: dict = {"email": email, "role": role}
        if projects is not None:
            body["projects"] = projects
        try:
            result = await client.post("/organization/invites", body)
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_get_invite(invite_id: str) -> str:
        """Get a single invite's details, including its status.

        Args:
            invite_id: The invite's ID (see openai_list_invites).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.get(f"/organization/invites/{invite_id}")
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_list_invites(after: str | None = None, limit: int | None = None) -> str:
        """List all invites in the organization.

        Each invite's "status" is one of `pending`, `accepted`, or `expired`.

        Args:
            after: Pagination cursor from a previous response's `last_id`.
            limit: Maximum number of invites to return per page.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.get(
                "/organization/invites", params={"after": after, "limit": limit}
            )
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_delete_invite(invite_id: str) -> str:
        """Revoke a pending invite. Invites that have already been accepted cannot be deleted.

        Args:
            invite_id: The invite's ID (see openai_list_invites).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            await client.delete(f"/organization/invites/{invite_id}")
            return f"Invite {invite_id} deleted."
        except OpenAIError as e:
            return f"Error: {e}"
