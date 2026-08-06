"""OpenAI project API key tools — list, retrieve, delete (read + revoke only).

Tool naming convention: openai_<action>_<resource>

There is no "create" tool here: the Admin API cannot mint a plain user API
key directly — the only programmatic way to get a new key is
openai_create_service_account (tools/service_accounts.py).
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
    async def openai_list_project_api_keys(
        project_id: str,
        owner_project_access: str | None = None,
        after: str | None = None,
        limit: int | None = None,
    ) -> str:
        """List API keys in a project. Key values are always redacted.

        Args:
            project_id: The project's ID (see openai_list_projects).
            owner_project_access: Filter by whether the key owner currently has
                project access — `active`, `inactive`, or `any`.
            after: Pagination cursor from a previous response's `last_id`.
            limit: Maximum number of keys to return per page.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            params = {
                "owner_project_access": owner_project_access,
                "after": after,
                "limit": limit,
            }
            path = f"/organization/projects/{project_id}/api_keys"
            result = await client.get(path, params=params)
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_get_project_api_key(project_id: str, api_key_id: str) -> str:
        """Get a single project API key's details (redacted value only).

        Args:
            project_id: The project's ID (see openai_list_projects).
            api_key_id: The API key's ID (see openai_list_project_api_keys).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.get(f"/organization/projects/{project_id}/api_keys/{api_key_id}")
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_delete_project_api_key(project_id: str, api_key_id: str) -> str:
        """Delete an API key from a project.

        Fails if the key belongs to a service account — delete the service
        account instead (openai_delete_service_account) to revoke that key.

        Args:
            project_id: The project's ID (see openai_list_projects).
            api_key_id: The API key's ID (see openai_list_project_api_keys).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            await client.delete(f"/organization/projects/{project_id}/api_keys/{api_key_id}")
            return f"API key {api_key_id} deleted from project {project_id}."
        except OpenAIError as e:
            return f"Error: {e}"
