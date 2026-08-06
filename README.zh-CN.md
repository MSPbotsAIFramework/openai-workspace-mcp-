# openai-workspace-mcp

[English](./README.md) | 中文

面向 Claude 的 OpenAI Workspace MCP 服务——将 OpenAI **Admin API**（API Platform 组织后台，
不同于 ChatGPT Enterprise 的工作区管理后台）暴露为 MCP Tool：组织成员、邀请、项目、项目成员、
服务账号、项目 API Key、速率限制、用量与花费、审计日志。

**技术栈：** Python 3.12 + uv + FastMCP（Starlette/uvicorn）

关联需求：PRD-15751（ChatGPT / OpenAI Workspace）。完整调研见
`vendor-mcp-template/prd/OpenAIWorkspace.md`。

**不在本次范围内：** Admin API Key 自身的管理、细粒度自定义角色/用户组（RBAC）、mTLS 客户端证书、
数据保留策略、花费限额/告警的写操作、模型访问权限、内置工具权限——均未实现，原因见 PRD 第 4.11
节（多数属于高风险的安全/合规类写操作，或超出本服务聚焦的"成员 + 用量 + 账单"范围）。

## 快速开始

```bash
cd openai-workspace-mcp
uv sync

# stdio 模式（Claude Desktop / CLI），从环境变量读取单一共享 Key
OPENAI_ADMIN_API_KEY=sk-admin-xxxx uv run openai-workspace-mcp
```

## 认证

本服务**无状态**：从不存储或持久化 OpenAI Admin API Key。Key either 通过环境变量一次性配置
（本地开发，`AUTH_MODE=env`），或按请求通过 HTTP Header 传入（`AUTH_MODE=gateway`，生产环境）。

与本工作区内其他部分厂商集成（Adobe、Bitwarden）不同，OpenAI Admin API **无需 OAuth token 交换**——
是一个直接附加在每次请求上的静态 Bearer Token，没有额外的 Identity 往返延迟。

### Gateway 模式 HTTP Header（`AUTH_MODE=gateway`）

| Header | 类型 | 是否必填 | 默认值 | 枚举值 | 字段描述 | Example |
|---|---|---|---|---|---|---|
| `x-openai-admin-key` | string | 必填 | 无 | 无 | OpenAI Admin API Key（`sk-admin-...`），由组织 Owner 在 Settings → Admin API Keys 创建。与普通 `sk-...` Key 不通用——Admin Key 不能调用模型接口，普通 Key 不能调用 `/organization/*`。仅用于本次请求的 `Authorization: Bearer` header，不持久化、不写日志。 | `sk-admin-abc123...` |

`/mcp` 请求缺少该 Header 返回 `401`，并附带 `required_headers` 列表。

### Env 模式变量（`AUTH_MODE=env`，仅本地开发使用）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `OPENAI_ADMIN_API_KEY` | — | OpenAI Admin API Key |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Admin API Base URL（固定，无区域变体） |
| `AUTH_MODE` | `gateway` | `env` 或 `gateway` |
| `MCP_TRANSPORT` | `stdio` | `stdio` 或 `http` |
| `MCP_HTTP_PORT` | `8080` | HTTP 服务端口 |
| `MCP_HTTP_HOST` | `0.0.0.0` | HTTP 服务绑定地址 |

获取 Key：以组织 Owner 身份登录 platform.openai.com → **Settings** → **Admin API Keys** →
创建。需要一个 OpenAI **API Platform** 组织（不是个人 ChatGPT 账号）。

## Claude Desktop 配置

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

## 传输模式

### stdio（Claude Desktop / CLI）
```bash
OPENAI_ADMIN_API_KEY=sk-admin-xxxx uv run openai-workspace-mcp
```

### HTTP —— 单租户（env 模式）
```bash
OPENAI_ADMIN_API_KEY=sk-admin-xxxx MCP_TRANSPORT=http AUTH_MODE=env uv run openai-workspace-mcp
curl http://localhost:8080/health
```

### HTTP —— gateway / 多租户（生产环境）
```bash
MCP_TRANSPORT=http AUTH_MODE=gateway uv run openai-workspace-mcp
```

## Tool List

Base URL：`https://api.openai.com/v1`（固定）。列表类接口使用游标分页（`after`/`limit`，部分
还支持 `before`）——把上一次响应的 `last_id`/`next_page` 传给 `after`/`page` 即可翻页。

### 组织成员（Organization Users）

| Tool | 说明 | 参数 |
|---|---|---|
| `openai_list_users` | 列出组织成员 | `emails`（string[]，可选）、`after`（可选）、`limit`（可选） |
| `openai_get_user` | 获取成员详情 | `user_id`（必填） |
| `openai_update_user_role` | 修改成员的组织角色 | `user_id`（必填）、`role`（必填，`owner`/`reader`） |
| `openai_remove_user` | 将成员从组织移除 | `user_id`（必填） |

> 没有"创建用户"接口——加入组织必须走邀请流程。

### 邀请（Invites）

| Tool | 说明 | 参数 |
|---|---|---|
| `openai_invite_user` | 按邮箱邀请新用户 | `email`（必填）、`role`（必填，`owner`/`reader`）、`projects`（`{id, role}` 数组，可选） |
| `openai_get_invite` | 获取邀请状态 | `invite_id`（必填） |
| `openai_list_invites` | 列出所有邀请 | `after`、`limit`（可选） |
| `openai_delete_invite` | 撤销未接受的邀请 | `invite_id`（必填） |

### 项目（Projects）

| Tool | 说明 | 参数 |
|---|---|---|
| `openai_list_projects` | 列出项目 | `include_archived`（默认 false）、`after`、`limit`（可选） |
| `openai_get_project` | 获取项目详情 | `project_id`（必填） |
| `openai_create_project` | 创建项目 | `name`（必填） |
| `openai_update_project` | 重命名项目 | `project_id`（必填）、`name`（必填） |
| `openai_archive_project` | 归档项目（API 层面**不可撤销**；项目不可删除，只能归档） | `project_id`（必填） |

### 项目成员（Project Users）

| Tool | 说明 | 参数 |
|---|---|---|
| `openai_list_project_users` | 列出项目内成员 | `project_id`（必填）、`after`、`limit`（可选） |
| `openai_get_project_user` | 获取项目成员详情 | `project_id`、`user_id`（必填） |
| `openai_add_project_user` | 将**已在组织中**的成员加入项目 | `project_id`、`user_id`、`role`（必填，`owner`/`member`） |
| `openai_update_project_user_role` | 修改成员的项目角色 | `project_id`、`user_id`、`role`（必填） |
| `openai_remove_project_user` | 将成员从项目移除 | `project_id`、`user_id`（必填） |

### 项目服务账号（Service Accounts）

服务账号是非人的项目级身份。创建服务账号是**唯一**能程序化获得新 API Key 的方式——没有"创建用户
API Key"接口。

| Tool | 说明 | 参数 |
|---|---|---|
| `openai_list_service_accounts` | 列出项目内服务账号 | `project_id`（必填）、`after`、`limit`（可选） |
| `openai_get_service_account` | 获取服务账号详情 | `project_id`、`service_account_id`（必填） |
| `openai_create_service_account` | 创建服务账号（**返回体含明文 API Key，仅此一次**） | `project_id`、`name`（必填）、`create_service_account_only`（默认 false） |
| `openai_update_service_account` | 修改名称/角色 | `project_id`、`service_account_id`（必填）、`name`、`role`（可选） |
| `openai_delete_service_account` | 删除服务账号 | `project_id`、`service_account_id`（必填） |

### 项目 API Key（只读 + 删除）

| Tool | 说明 | 参数 |
|---|---|---|
| `openai_list_project_api_keys` | 列出项目内的 API Key（值始终脱敏） | `project_id`（必填）、`owner_project_access`（`active`/`inactive`/`any`，可选）、`after`、`limit`（可选） |
| `openai_get_project_api_key` | 获取 Key 详情（脱敏） | `project_id`、`api_key_id`（必填） |
| `openai_delete_project_api_key` | 删除 Key（属于服务账号的 Key 会报错，需删除该服务账号） | `project_id`、`api_key_id`（必填） |

### 项目速率限制（Rate Limits）

| Tool | 说明 | 参数 |
|---|---|---|
| `openai_list_rate_limits` | 列出各模型的速率限制配置 | `project_id`（必填）、`after`、`before`、`limit`（可选） |
| `openai_update_rate_limit` | 修改指定模型的速率限制 | `project_id`、`rate_limit_id`（必填）、`max_requests_per_1_minute`、`max_tokens_per_1_minute`、`max_images_per_1_minute`、`max_audio_megabytes_per_1_minute`、`max_requests_per_1_day`、`batch_1_day_max_input_tokens`（均可选） |

### 用量与花费（Usage & Costs）

| Tool | 说明 | 参数 |
|---|---|---|
| `openai_get_usage` | 查询指定类别的分时段用量 | `category`（必填，`completions`/`embeddings`/`moderations`/`images`/`audio_speeches`/`audio_transcriptions`/`vector_stores`/`code_interpreter_sessions`/`file_search_calls`/`web_search_calls`）、`start_time`（必填，Unix 秒）、`end_time`、`bucket_width`（`1m`/`1h`/`1d`，默认 `1d`）、`group_by`（string[]）、`project_ids`、`user_ids`、`api_key_ids`、`models`、`limit`、`page`（均可选） |
| `openai_get_costs` | 查询每日花费明细 | `start_time`（必填）、`end_time`、`bucket_width`（仅支持 `1d`）、`group_by`（`project_id`/`line_item`/`api_key_id`）、`project_ids`、`api_key_ids`、`limit`（1-180，默认 7）、`page`（均可选） |

### 审计日志（Audit Logs）

| Tool | 说明 | 参数 |
|---|---|---|
| `openai_list_audit_logs` | 列出组织内的用户操作与配置变更 | `effective_start_time`、`effective_end_time`（Unix 秒，可选）、`actor_emails`、`actor_ids`、`event_types`、`project_ids`、`resource_ids`（string[]，可选）、`after`、`before`、`limit`（可选） |

**角色枚举：** 组织级 `owner`/`reader`；项目与服务账号级 `owner`/`member`（服务账号还有只读态
`none`）。**邀请 `status`（只读）：** `pending`/`accepted`/`expired`。

**限流：** OpenAI 未公开 Admin API 专用的限流数值，`429` 原样透传。

## 测试示例

### tools/list（gateway 模式）
```bash
curl -X POST http://localhost:8080/mcp \
  -H "x-openai-admin-key: sk-admin-your_key" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

### tools/call —— 邀请成员并加入项目
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

### tools/call —— 查询近 7 天的 completions 用量
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

### 缺少 Header → 401
```bash
curl -i -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
# HTTP/1.1 401 Unauthorized
# {"error":"Missing credentials","required_headers":["x-openai-admin-key"]}
```

## API 参考

- [Admin APIs 总览](https://developers.openai.com/api/docs/guides/admin-apis)
- [Invites](https://platform.openai.com/docs/api-reference/invite)
- [Project users](https://platform.openai.com/docs/api-reference/project-users)
- [Usage/Cost API 介绍](https://community.openai.com/t/introducing-the-usage-api-track-api-usage-and-costs-programmatically/1043058)
- [Audit logs](https://help.openai.com/en/articles/9687866-admin-and-audit-logs-api-for-the-api-platform)
- 本服务的端点路径、参数与枚举值均已对照官方 `openai-node` SDK 源码（`src/resources/admin/organization/**`，
  由 OpenAI 用自己的 OpenAPI 规范自动生成）逐个核实——因为交互式文档站点对非浏览器请求返回 403。
  精确文件列表见 `vendor-mcp-template/prd/OpenAIWorkspace.md` 第 8 节。

## 已知限制

- **没有"创建用户"或"创建项目 API Key"的 Tool**——按设计对齐 OpenAI 自身的 API 能力边界：组织成员
  只能通过邀请增加，新 API Key 只能通过创建服务账号获得。
- **`openai_create_service_account` 会返回明文 API Key**——这是底层 API 本身的行为（仅创建时一次性
  可见），本 Tool 不做脱敏改写。
- **数组类过滤参数（`project_ids`、`event_types` 等）以 `key[]=...` 形式发送**，与 OpenAI 官方 SDK
  的序列化方式一致——不是本工作区其他厂商常见的"重复裸键"格式。
- **未见 Admin API 专用限流文档**——`429` 原样透传。
- 需要一个拥有 Owner 权限的 OpenAI **API Platform** 组织才能创建 Admin API Key；个人 ChatGPT 账号
  无法使用本服务。
- 以下高级能力有意排除在本次范围外：Admin API Key 自身管理、自定义角色/用户组（RBAC）、mTLS 证书、
  数据保留策略、花费限额/告警、模型访问权限、内置工具权限——原因见 PRD。
