"""OpenAI organization usage and cost tools.

Tool naming convention: openai_<action>_<resource>

One tool covers all 10 usage sub-endpoints (selected via `category`) instead
of registering 10 near-identical tools; costs get their own tool since the
params differ slightly (no `models`/`user_ids`, capped bucket_width).
"""

import json
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..api_client import OpenAIAdminClient, OpenAIError

_NO_CREDENTIALS = (
    "Error: No OpenAI Admin API key configured. Set OPENAI_ADMIN_API_KEY or use AUTH_MODE=gateway."
)

_USAGE_CATEGORIES = (
    "completions",
    "embeddings",
    "moderations",
    "images",
    "audio_speeches",
    "audio_transcriptions",
    "vector_stores",
    "code_interpreter_sessions",
    "file_search_calls",
    "web_search_calls",
)


def register(mcp: FastMCP, client_factory: Callable[[], OpenAIAdminClient | None]) -> None:
    @mcp.tool()
    async def openai_get_usage(
        category: str,
        start_time: int,
        end_time: int | None = None,
        bucket_width: str = "1d",
        group_by: list[str] | None = None,
        project_ids: list[str] | None = None,
        user_ids: list[str] | None = None,
        api_key_ids: list[str] | None = None,
        models: list[str] | None = None,
        limit: int | None = None,
        page: str | None = None,
    ) -> str:
        """Query time-bucketed API usage for the organization.

        `limit` caps the number of time buckets returned, with different
        defaults/maximums per bucket_width: 1d -> default 7, max 31; 1h ->
        default 24, max 168; 1m -> default 60, max 1440.

        Args:
            category: Which usage type to query — one of: completions,
                embeddings, moderations, images, audio_speeches,
                audio_transcriptions, vector_stores, code_interpreter_sessions,
                file_search_calls, web_search_calls.
            start_time: Start of the query range, inclusive (Unix seconds).
            end_time: End of the query range, exclusive (Unix seconds).
            bucket_width: Time bucket size — `1m`, `1h`, or `1d` (default `1d`).
            group_by: Fields to group by, e.g. project_id, user_id, api_key_id,
                model, batch, service_tier (supported fields vary by category).
            project_ids: Only include usage for these projects.
            user_ids: Only include usage for these users.
            api_key_ids: Only include usage for these API keys.
            models: Only include usage for these models.
            limit: Number of time buckets to return.
            page: Pagination cursor from a previous response's `next_page`.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        if category not in _USAGE_CATEGORIES:
            valid = ", ".join(_USAGE_CATEGORIES)
            return f"Error: unknown category '{category}'. Must be one of: {valid}"
        params = {
            "start_time": start_time,
            "end_time": end_time,
            "bucket_width": bucket_width,
            "group_by": group_by,
            "project_ids": project_ids,
            "user_ids": user_ids,
            "api_key_ids": api_key_ids,
            "models": models,
            "limit": limit,
            "page": page,
        }
        try:
            result = await client.get(f"/organization/usage/{category}", params=params)
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def openai_get_costs(
        start_time: int,
        end_time: int | None = None,
        bucket_width: str = "1d",
        group_by: list[str] | None = None,
        project_ids: list[str] | None = None,
        api_key_ids: list[str] | None = None,
        limit: int | None = None,
        page: str | None = None,
    ) -> str:
        """Query the organization's daily spend breakdown.

        Args:
            start_time: Start of the query range, inclusive (Unix seconds).
            end_time: End of the query range, exclusive (Unix seconds).
            bucket_width: Time bucket size — only `1d` is currently supported.
            group_by: Fields to group by — project_id, line_item, api_key_id.
            project_ids: Only include costs for these projects.
            api_key_ids: Only include costs for these API keys.
            limit: Number of buckets to return (1-180, default 7).
            page: Pagination cursor from a previous response's `next_page`.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        params = {
            "start_time": start_time,
            "end_time": end_time,
            "bucket_width": bucket_width,
            "group_by": group_by,
            "project_ids": project_ids,
            "api_key_ids": api_key_ids,
            "limit": limit,
            "page": page,
        }
        try:
            result = await client.get("/organization/costs", params=params)
            return json.dumps(result, indent=2)
        except OpenAIError as e:
            return f"Error: {e}"
