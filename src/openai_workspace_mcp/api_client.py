from typing import Any

import httpx

DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"OpenAI Admin API error {status_code}: {message}")


class OpenAIAdminClient:
    """Async httpx client wrapping the OpenAI Admin API (`/organization/*`).

    Auth is a single static Bearer token (the Admin API key) — unlike Bitwarden/Adobe,
    there is no OAuth token exchange hop, so every call is a plain one-shot HTTP request
    with the caller-supplied key attached directly.
    """

    def __init__(self, admin_api_key: str, base_url: str = DEFAULT_BASE_URL):
        self._admin_api_key = admin_api_key
        self._base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._admin_api_key}",
            "Content-Type": "application/json",
        }

    def _clean_params(self, params: dict | None) -> list[tuple[str, Any]]:
        """Drop None values and serialize list values as repeated `key[]` params.

        This matches the OpenAI SDK's own query serialization (`arrayFormat:
        "brackets"`) — plain repeated `key=a&key=b` (httpx's default for list
        values) is not what the Admin API expects for array filters like
        `project_ids`/`event_types`.
        """
        if not params:
            return []
        pairs: list[tuple[str, Any]] = []
        for k, v in params.items():
            if v is None:
                continue
            if isinstance(v, list):
                pairs.extend((f"{k}[]", item) for item in v)
            else:
                pairs.append((k, v))
        return pairs

    async def get(self, path: str, params: dict | None = None) -> Any:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}{path}",
                headers=self._headers(),
                params=self._clean_params(params),
            )
            self._raise_for_status(resp)
            return resp.json() if resp.status_code != 204 and resp.content else None

    async def post(self, path: str, body: Any = None) -> Any:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}{path}",
                headers=self._headers(),
                json=body,
            )
            self._raise_for_status(resp)
            return resp.json() if resp.status_code != 204 and resp.content else None

    async def delete(self, path: str) -> Any:
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{self._base_url}{path}",
                headers=self._headers(),
            )
            self._raise_for_status(resp)
            return resp.json() if resp.status_code != 204 and resp.content else None

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise OpenAIError(resp.status_code, str(detail))
