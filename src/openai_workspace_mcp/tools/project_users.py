"""OpenAI project member tools — add, list, retrieve, update role, remove.

Tool naming convention: openai_<action>_<resource>

Users must already be members of the organization (see openai_invite_user)
before they can be added to a project.
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
    async def openai_list_project_users(
        project_id: str, after: str | None = None, limit: int | None = None
    ) -> str:
        """List members of a project.

        Args:
            project_id: The project's ID (see openai_list_projects).
            after: Pagination cursor from a previous response's `last_id`.
            limit: Maximum number of users to return per page.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            params = {"after": after, "limit": limit}
            result = await client.get(f"/organization/projects/{project_id}/users", params=params)
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_get_project_user(project_id: str, user_id: str) -> str:
        """Get a single project member's details.

        Args:
            project_id: The project's ID (see openai_list_projects).
            user_id: The member's user ID (see openai_list_project_users).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.get(f"/organization/projects/{project_id}/users/{user_id}")
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_add_project_user(project_id: str, user_id: str, role: str) -> str:
        """Add an existing organization member to a project.

        The user must already be a member of the organization (see
        openai_invite_user / openai_list_users) — this call cannot invite
        someone new to the org.

        Args:
            project_id: The project's ID (see openai_list_projects).
            user_id: The organization member's user ID (see openai_list_users).
            role: Project role to grant — `owner` or `member`.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.post(
                f"/organization/projects/{project_id}/users", {"user_id": user_id, "role": role}
            )
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_update_project_user_role(project_id: str, user_id: str, role: str) -> str:
        """Change a member's role within a project.

        Args:
            project_id: The project's ID (see openai_list_projects).
            user_id: The member's user ID (see openai_list_project_users).
            role: New project role — `owner` or `member`.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.post(
                f"/organization/projects/{project_id}/users/{user_id}", {"role": role}
            )
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_remove_project_user(project_id: str, user_id: str) -> str:
        """Remove a member from a project. Fails if the project is archived.

        Args:
            project_id: The project's ID (see openai_list_projects).
            user_id: The member's user ID (see openai_list_project_users).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            await client.delete(f"/organization/projects/{project_id}/users/{user_id}")
            return f"User {user_id} removed from project {project_id}."
        except OpenAIError as e:
            return f"Error: {e}"
