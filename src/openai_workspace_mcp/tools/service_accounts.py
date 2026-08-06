"""OpenAI project service account tools — create, list, retrieve, update, delete.

Tool naming convention: openai_<action>_<resource>

Service accounts are non-human, project-scoped identities for programmatic
access. Creating one is the only way this Admin API can mint a new API key
(there is no endpoint to create a plain user API key).
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
    async def openai_list_service_accounts(
        project_id: str, after: str | None = None, limit: int | None = None
    ) -> str:
        """List service accounts in a project.

        Args:
            project_id: The project's ID (see openai_list_projects).
            after: Pagination cursor from a previous response's `last_id`.
            limit: Maximum number of service accounts to return per page.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.get(
                f"/organization/projects/{project_id}/service_accounts",
                params={"after": after, "limit": limit},
            )
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_get_service_account(project_id: str, service_account_id: str) -> str:
        """Get a single service account's details.

        Args:
            project_id: The project's ID (see openai_list_projects).
            service_account_id: The service account's ID (see openai_list_service_accounts).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.get(
                f"/organization/projects/{project_id}/service_accounts/{service_account_id}"
            )
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_create_service_account(
        project_id: str, name: str, create_service_account_only: bool = False
    ) -> str:
        """Create a new service account in a project.

        By default this also creates a `member`-role project membership and an
        API key for the account. IMPORTANT: the response contains the API key's
        PLAINTEXT value — this is the only time it is ever shown. Surface it to
        the user immediately so they can store it; it cannot be retrieved again.

        Args:
            project_id: The project's ID (see openai_list_projects).
            name: Name for the new service account.
            create_service_account_only: If True, skip creating the default role/API key.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        body: dict = {"name": name, "create_service_account_only": create_service_account_only}
        try:
            path = f"/organization/projects/{project_id}/service_accounts"
            result = await client.post(path, body)
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_update_service_account(
        project_id: str,
        service_account_id: str,
        name: str | None = None,
        role: str | None = None,
    ) -> str:
        """Update a service account's name and/or role.

        Args:
            project_id: The project's ID (see openai_list_projects).
            service_account_id: The service account's ID (see openai_list_service_accounts).
            name: New name for the service account.
            role: New project role — `owner` or `member`.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        body: dict = {}
        if name is not None:
            body["name"] = name
        if role is not None:
            body["role"] = role
        try:
            result = await client.post(
                f"/organization/projects/{project_id}/service_accounts/{service_account_id}", body
            )
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_delete_service_account(project_id: str, service_account_id: str) -> str:
        """Delete a service account from a project. Fails if the project is archived.

        Args:
            project_id: The project's ID (see openai_list_projects).
            service_account_id: The service account's ID (see openai_list_service_accounts).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            await client.delete(
                f"/organization/projects/{project_id}/service_accounts/{service_account_id}"
            )
            return f"Service account {service_account_id} deleted from project {project_id}."
        except OpenAIError as e:
            return f"Error: {e}"
