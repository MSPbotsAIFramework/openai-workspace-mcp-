"""OpenAI project rate limit tools — list, update.

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
    async def openai_list_rate_limits(
        project_id: str,
        after: str | None = None,
        before: str | None = None,
        limit: int | None = None,
    ) -> str:
        """List per-model rate limit configs for a project.

        Args:
            project_id: The project's ID (see openai_list_projects).
            after: Pagination cursor from a previous response's `last_id`.
            before: Pagination cursor to fetch the previous page.
            limit: Maximum number of rate limit entries to return per page.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.get(
                f"/organization/projects/{project_id}/rate_limits",
                params={"after": after, "before": before, "limit": limit},
            )
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_update_rate_limit(
        project_id: str,
        rate_limit_id: str,
        max_requests_per_1_minute: int | None = None,
        max_tokens_per_1_minute: int | None = None,
        max_images_per_1_minute: int | None = None,
        max_audio_megabytes_per_1_minute: int | None = None,
        max_requests_per_1_day: int | None = None,
        batch_1_day_max_input_tokens: int | None = None,
    ) -> str:
        """Update a project's rate limit for one model.

        Each `max_*` field only applies to relevant model types (e.g.
        max_images_per_1_minute only matters for image models) — check
        openai_list_rate_limits first to see which fields are present for the
        target model before changing them.

        Args:
            project_id: The project's ID (see openai_list_projects).
            rate_limit_id: The rate limit entry's ID (see openai_list_rate_limits).
            max_requests_per_1_minute: New requests-per-minute limit.
            max_tokens_per_1_minute: New tokens-per-minute limit.
            max_images_per_1_minute: New images-per-minute limit.
            max_audio_megabytes_per_1_minute: New audio-megabytes-per-minute limit.
            max_requests_per_1_day: New requests-per-day limit.
            batch_1_day_max_input_tokens: New batch max input tokens per day.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        body = {
            "max_requests_per_1_minute": max_requests_per_1_minute,
            "max_tokens_per_1_minute": max_tokens_per_1_minute,
            "max_images_per_1_minute": max_images_per_1_minute,
            "max_audio_megabytes_per_1_minute": max_audio_megabytes_per_1_minute,
            "max_requests_per_1_day": max_requests_per_1_day,
            "batch_1_day_max_input_tokens": batch_1_day_max_input_tokens,
        }
        body = {k: v for k, v in body.items() if v is not None}
        try:
            result = await client.post(
                f"/organization/projects/{project_id}/rate_limits/{rate_limit_id}", body
            )
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"
