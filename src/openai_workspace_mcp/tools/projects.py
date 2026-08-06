"""OpenAI project tools — create, list, retrieve, rename, archive.

Tool naming convention: openai_<action>_<resource>

Projects cannot be deleted, only archived (see openai_archive_project).
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
    async def openai_list_projects(
        include_archived: bool = False,
        after: str | None = None,
        limit: int | None = None,
    ) -> str:
        """List projects in the organization.

        Args:
            include_archived: If True, also return archived projects (excluded by default).
            after: Pagination cursor from a previous response's `last_id`.
            limit: Maximum number of projects to return per page.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.get(
                "/organization/projects",
                params={"include_archived": include_archived, "after": after, "limit": limit},
            )
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_get_project(project_id: str) -> str:
        """Get a single project's details.

        Args:
            project_id: The project's ID (see openai_list_projects).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.get(f"/organization/projects/{project_id}")
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_create_project(name: str) -> str:
        """Create a new project in the organization.

        Args:
            name: The project's friendly name (appears in usage/cost reports).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.post("/organization/projects", {"name": name})
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_update_project(project_id: str, name: str) -> str:
        """Rename a project.

        Args:
            project_id: The project's ID (see openai_list_projects).
            name: The new project name.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.post(f"/organization/projects/{project_id}", {"name": name})
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_archive_project(project_id: str) -> str:
        """Archive a project. Archived projects cannot be used or modified further,
        and this action cannot be undone via the API.

        Args:
            project_id: The project's ID (see openai_list_projects).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.post(f"/organization/projects/{project_id}/archive")
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"
