# openai-workspace-mcp

English | [中文](./README.zh-CN.md)

OpenAI Workspace MCP server for Claude — exposes the OpenAI **Admin API** (the API
Platform organization back office, distinct from ChatGPT Enterprise workspace admin) as
MCP tools: organization members, invites, projects, project members, service accounts,
project API keys, rate limits, usage, costs, and audit logs.

**Tech stack:** Python 3.12 + uv + FastMCP (Starlette/uvicorn)

关联需求：PRD-15751（ChatGPT / OpenAI Workspace）。完整调研见
`vendor-mcp-template/prd/OpenAIWorkspace.md`.

**Out of scope:** Admin API key self-management, fine-grained custom Roles/Groups (RBAC),
mTLS Certificates, Data Retention policy, Spend Limit/Alert configuration, Model
Permissions, and Hosted Tool Permissions are intentionally not implemented — see the PRD
§4.11 for rationale (mostly: high-risk security/compliance writes, or orthogonal to the
"members + usage + billing" scope this service targets).

## Quick Start

```bash
cd openai-workspace-mcp
uv sync

# stdio mode (for Claude Desktop / CLI), single shared key from env
OPENAI_ADMIN_API_KEY=sk-admin-xxxx uv run openai-workspace-mcp
```

## Authentication

This service is **stateless**: it never stores or persists the OpenAI Admin API key.
The key is either supplied once via an environment variable (local dev, `AUTH_MODE=env`),
or per-request via an HTTP header (`AUTH_MODE=gateway`, production).

Unlike some other vendor integrations in this workspace (Adobe, Bitwarden), the OpenAI
Admin API needs **no OAuth token exchange** — it's a single static Bearer token attached
directly to every request, so there's no extra Identity round trip.

### Gateway mode HTTP headers (`AUTH_MODE=gateway`)

| Header | Type | Required | Default | Enum | Description | Example |
|---|---|---|---|---|---|---|
| `x-openai-admin-key` | string | Yes | none | none | OpenAI Admin API key (`sk-admin-...`), created by an org Owner under Settings -> Admin API Keys. Distinct from a regular `sk-...` key — it cannot call model endpoints, and a regular key cannot call `/organization/*`. Used only for this request's `Authorization: Bearer` header; never persisted or logged. | `sk-admin-abc123...` |

Missing the header on a `/mcp` request returns `401` with a `required_headers` list.

### Env mode variables (`AUTH_MODE=env`, local dev only)

| Variable | Default | Description |
|---|---|---|
| `OPENAI_ADMIN_API_KEY` | — | OpenAI Admin API key |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Admin API base URL (fixed, no regional variants) |
| `AUTH_MODE` | `gateway` | `env` or `gateway` |
| `MCP_TRANSPORT` | `stdio` | `stdio` or `http` |
| `MCP_HTTP_PORT` | `8080` | HTTP server port |
| `MCP_HTTP_HOST` | `0.0.0.0` | HTTP server bind address |

Get a key: as an organization Owner, go to platform.openai.com -> **Settings** ->
**Admin API Keys** -> Create. Requires an OpenAI API Platform organization (not a personal
ChatGPT account).

## Claude Desktop Setup

```json
{
  "mcpServers": {
    "openai-workspace": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/openai-workspace-mcp", "openai-workspace-mcp"],
      "env": {
        "OPENAI_ADMIN_API_KEY": "sk-admin-xxxx"
      }
    }
  }
}
```

## Transport Modes

### stdio (Claude Desktop / CLI)
```bash
OPENAI_ADMIN_API_KEY=sk-admin-xxxx uv run openai-workspace-mcp
```

### HTTP — single-tenant (env mode)
```bash
OPENAI_ADMIN_API_KEY=sk-admin-xxxx MCP_TRANSPORT=http AUTH_MODE=env uv run openai-workspace-mcp
curl http://localhost:8080/health
```

### HTTP — gateway / multi-tenant (production)
```bash
MCP_TRANSPORT=http AUTH_MODE=gateway uv run openai-workspace-mcp
```

## Tool List

Base URL: `https://api.openai.com/v1` (fixed). List endpoints use cursor pagination
(`after`/`limit`, some also `before`) — pass the previous response's `last_id`/`next_page`
value as `after`/`page` to fetch the next batch.

### Organization Users

| Tool | Description | Parameters |
|---|---|---|
| `openai_list_users` | List organization members | `emails` (string[], optional), `after` (string, optional), `limit` (int, optional) |
| `openai_get_user` | Get a member's details | `user_id` (string, required) |
| `openai_update_user_role` | Change a member's org role | `user_id` (string, required), `role` (string, required — `owner`/`reader`) |
| `openai_remove_user` | Remove a member from the org | `user_id` (string, required) |

> No "create user" endpoint — joining the org always goes through an invite.

### Invites

| Tool | Description | Parameters |
|---|---|---|
| `openai_invite_user` | Invite a new user by email | `email` (string, required), `role` (string, required — `owner`/`reader`), `projects` (array of `{id, role}`, optional) |
| `openai_get_invite` | Get an invite's status | `invite_id` (string, required) |
| `openai_list_invites` | List all invites | `after`, `limit` (optional) |
| `openai_delete_invite` | Revoke a pending invite | `invite_id` (string, required) |

### Projects

| Tool | Description | Parameters |
|---|---|---|
| `openai_list_projects` | List projects | `include_archived` (bool, default false), `after`, `limit` (optional) |
| `openai_get_project` | Get a project's details | `project_id` (string, required) |
| `openai_create_project` | Create a project | `name` (string, required) |
| `openai_update_project` | Rename a project | `project_id` (string, required), `name` (string, required) |
| `openai_archive_project` | Archive a project (**cannot be undone** via API; projects cannot be deleted) | `project_id` (string, required) |

### Project Users

| Tool | Description | Parameters |
|---|---|---|
| `openai_list_project_users` | List members of a project | `project_id` (required), `after`, `limit` (optional) |
| `openai_get_project_user` | Get a project member's details | `project_id`, `user_id` (required) |
| `openai_add_project_user` | Add an **existing org member** to a project | `project_id`, `user_id`, `role` (required — `owner`/`member`) |
| `openai_update_project_user_role` | Change a member's project role | `project_id`, `user_id`, `role` (required) |
| `openai_remove_project_user` | Remove a member from a project | `project_id`, `user_id` (required) |

### Project Service Accounts

Service accounts are non-human, project-scoped identities. Creating one is the **only**
programmatic way to mint a new API key — there's no "create user API key" endpoint.

| Tool | Description | Parameters |
|---|---|---|
| `openai_list_service_accounts` | List service accounts in a project | `project_id` (required), `after`, `limit` (optional) |
| `openai_get_service_account` | Get a service account's details | `project_id`, `service_account_id` (required) |
| `openai_create_service_account` | Create a service account (**response includes the API key's plaintext value — shown only once**) | `project_id`, `name` (required), `create_service_account_only` (bool, default false) |
| `openai_update_service_account` | Update name/role | `project_id`, `service_account_id` (required), `name`, `role` (optional) |
| `openai_delete_service_account` | Delete a service account | `project_id`, `service_account_id` (required) |

### Project API Keys (read + revoke only)

| Tool | Description | Parameters |
|---|---|---|
| `openai_list_project_api_keys` | List API keys in a project (values always redacted) | `project_id` (required), `owner_project_access` (`active`/`inactive`/`any`, optional), `after`, `limit` (optional) |
| `openai_get_project_api_key` | Get a key's details (redacted) | `project_id`, `api_key_id` (required) |
| `openai_delete_project_api_key` | Delete a key (fails if it belongs to a service account — delete the service account instead) | `project_id`, `api_key_id` (required) |

### Project Rate Limits

| Tool | Description | Parameters |
|---|---|---|
| `openai_list_rate_limits` | List per-model rate limit configs | `project_id` (required), `after`, `before`, `limit` (optional) |
| `openai_update_rate_limit` | Update one model's rate limit | `project_id`, `rate_limit_id` (required), `max_requests_per_1_minute`, `max_tokens_per_1_minute`, `max_images_per_1_minute`, `max_audio_megabytes_per_1_minute`, `max_requests_per_1_day`, `batch_1_day_max_input_tokens` (all optional) |

### Usage & Costs

| Tool | Description | Parameters |
|---|---|---|
| `openai_get_usage` | Query time-bucketed usage for one category | `category` (required — `completions`/`embeddings`/`moderations`/`images`/`audio_speeches`/`audio_transcriptions`/`vector_stores`/`code_interpreter_sessions`/`file_search_calls`/`web_search_calls`), `start_time` (int, required, Unix seconds), `end_time`, `bucket_width` (`1m`/`1h`/`1d`, default `1d`), `group_by` (string[]), `project_ids`, `user_ids`, `api_key_ids`, `models`, `limit`, `page` (all optional) |
| `openai_get_costs` | Query daily spend breakdown | `start_time` (int, required), `end_time`, `bucket_width` (only `1d` supported), `group_by` (`project_id`/`line_item`/`api_key_id`), `project_ids`, `api_key_ids`, `limit` (1-180, default 7), `page` (all optional) |

### Audit Logs

| Tool | Description | Parameters |
|---|---|---|
| `openai_list_audit_logs` | List user actions and config changes | `effective_start_time`, `effective_end_time` (Unix seconds, optional), `actor_emails`, `actor_ids`, `event_types`, `project_ids`, `resource_ids` (string[], optional), `after`, `before`, `limit` (optional) |

**Role enums:** org — `owner`/`reader`; project & service account — `owner`/`member` (service
account also has read-only `none`). **Invite `status` (read-only):** `pending`/`accepted`/`expired`.

**Rate limits:** OpenAI has not published Admin-API-specific throttling numbers; `429`
responses are passed through as-is.

## Test Examples

### tools/list (gateway mode)
```bash
curl -X POST http://localhost:8080/mcp \
  -H "x-openai-admin-key: sk-admin-your_key" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

### tools/call — invite a member into a project
```bash
curl -X POST http://localhost:8080/mcp \
  -H "x-openai-admin-key: sk-admin-your_key" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": 2,
    "params": {
      "name": "openai_invite_user",
      "arguments": {
        "email": "user@example.com",
        "role": "reader",
        "projects": [{"id": "proj_abc123", "role": "member"}]
      }
    }
  }'
```

### tools/call — query last 7 days of completions usage
```bash
curl -X POST http://localhost:8080/mcp \
  -H "x-openai-admin-key: sk-admin-your_key" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": 3,
    "params": {
      "name": "openai_get_usage",
      "arguments": {"category": "completions", "start_time": 1735689600, "bucket_width": "1d", "limit": 7}
    }
  }'
```

### Missing header → 401
```bash
curl -i -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
# HTTP/1.1 401 Unauthorized
# {"error":"Missing credentials","required_headers":["x-openai-admin-key"]}
```

## API Reference

- [Admin APIs overview](https://developers.openai.com/api/docs/guides/admin-apis)
- [Invites](https://platform.openai.com/docs/api-reference/invite)
- [Project users](https://platform.openai.com/docs/api-reference/project-users)
- [Usage/Cost API introduction](https://community.openai.com/t/introducing-the-usage-api-track-api-usage-and-costs-programmatically/1043058)
- [Audit logs](https://help.openai.com/en/articles/9687866-admin-and-audit-logs-api-for-the-api-platform)
- Endpoint paths, params, and enums in this service were verified against the official
  `openai-node` SDK source (`src/resources/admin/organization/**`, auto-generated by
  OpenAI from their OpenAPI spec), since the interactive docs site returns 403 to non-browser
  fetches. See `vendor-mcp-template/prd/OpenAIWorkspace.md` §8 for the exact file list.

## Known Limitations

- **No "create user" or "create project API key" tools** — by design, these follow OpenAI's
  own API surface: org membership only grows via invites, and a new API key can only be
  minted by creating a service account.
- **`openai_create_service_account` returns a plaintext API key** — this is the underlying
  API's own behavior (shown once, at creation time only); the tool does not redact it.
- **Array-valued filters (`project_ids`, `event_types`, etc.) are sent as `key[]=...`
  query params**, matching OpenAI's own SDK serialization — not the plain repeated-key
  format some other vendors in this workspace use.
- **No documented Admin-API-specific rate limits** — `429` is passed through as-is.
- Requires an OpenAI **API Platform** organization with Owner access to create an Admin
  API key; a personal ChatGPT account cannot use this service.
- Advanced features intentionally out of scope: Admin API key self-management, custom
  Roles/Groups (RBAC), Certificates (mTLS), Data Retention, Spend Limit/Alerts, Model
  Permissions, Hosted Tool Permissions — see the PRD for rationale.
