# envelope reference

> ⚠️ 与 `src/asset_hub/cli/envelope.py` + `src/asset_hub/cli/serve/lifecycle.py` + `src/asset_hub/cli/serve/doctor.py` 同源约定 — 改一处必查另一处。

CLI envelope error code 完整 inventory + JSON 示例 + edge case。

## envelope 形态

成功：

```json
{ "success": true, "data": <任意>, "metadata": { "took_ms": 12, "count": 5 }, "error": null }
```

错误（CLI envelope；v2.0 加结构化可选字段，exclude None）：

```json
{
  "success": false,
  "data": null,
  "metadata": {},
  "error": {
    "code": "<error_code>",
    "message": "<中文 detail>",
    "hint": "<下一步建议，可选>",
    "fields_missing": ["<可选>"],
    "fields_invalid": {"<field>": "<reason>"},
    "affected_resource_id": "<可选 uuid>"
  }
}
```

> ⚠️ **API vs CLI shape 差异**（v2.0 backward compat）：HTTP API 响应保留 `{ "detail": <message>, "code": ..., "hint?", "fields_missing?", "fields_invalid?", "affected_resource_id?" }` **平铺**形态（前端 `lib/error.ts` 兼容）；CLI envelope 是上述嵌套 `error: {...}` 形态。两端字段集相同、exclude None 行为一致，仅 top-level shape 不同。详见 §v2.0 envelope error 深度结构化 章节。

dry-run（破坏性命令的预览）：

```json
{ "success": true, "data": { "would_delete": true, ... }, "metadata": {}, "error": null }
```

dry-run 退出码 = 10（语义化区分"成功执行"与"成功预览不执行"）。

## error code 完整清单

### 域异常（主 CLI）

来源：`src/asset_hub/errors.py` 6 子类的 `code` 类属性（v2.0 从 cli/envelope.py 的旧 `_DOMAIN_ERROR_CODES` dict 改造，子类 `type(exc).code` 取代字典查询）。

| code | 来源异常 | HTTP map | exit_code |
|---|---|---|---|
| `not_found` | `NotFoundError` | 404 | 3 |
| `duplicate` | `DuplicateError` | 409 | 1 |
| `validation` | `ValidationError` | 422 | 1（默认）/ 2（UUID parse 场景，via `exit_2_on_validation=True`） |
| `state_conflict` | `StateError`（业务规则冲突） | 409 | 1 |
| `conflict` | `ConflictError`（跨对象引用冲突，如 type 被资产引用时删除） | 409 | 1 |
| `illegal_transition` | `IllegalTransitionError` | 409 | 1 |
| `cancelled` | 用户在 dry-run 后取消操作（见 `type_cmd.py:123`） | — | 10 |

> **注**：`cancelled` 是 v1.0 现有行为（`type delete` dry-run 后用户拒绝确认），v2.0 正式化为 exit_code=10，与 dry-run 预览同档（用户主动取消非错误）。

### serve 子命令（dot prefix namespace）

来源：`src/asset_hub/cli/serve/lifecycle.py` (`ServeLifecycleError`) + `src/asset_hub/cli/serve/doctor.py` (`DoctorCheck.code`)。

**lifecycle 错误（serve start / stop / restart）**：

| code | 触发场景 |
|---|---|
| `serve.usage` | `--mode` / `--service` 等参数取值非法（如 `--mode staging`、`--service db` 等用法错误），exit_code 2 |
| `serve.port_occupied` | `:8000` / `:5173` 被占（`start` / `restart` 前置检查） |
| `serve.dist_missing` | `prod` 模式 + `--skip-build` 时 `frontend/dist` 缺失 |
| `serve.health_probe_timeout` | `start` 后 `/api/healthz` 多次重试仍未 200（约 10s 超时） |
| `serve.frontend_failed_to_start` | dev 模式 Vite 进程无法在 `:5173` 响应 |
| `serve.data_unwritable` | `pids_dir` / `logs_dir` 不可写（包括 mkdir 失败和权限不足两种原因） |
| `serve.already_running` | `start` 时检测到 active PID（backend 或 frontend 已在运行） |
| `serve.build_failed` | `pnpm build` 返回非零退出码，或 `pnpm` 不在 PATH |
| `serve.kill_failed` | `stop` 时 SIGTERM/SIGKILL 都失败（手动清理必需） |
| `serve.mode_required` | `restart` 无法从 PID 文件推断 mode 且未提供 `--mode` |

**doctor 检查项错误**（`serve doctor --json` 时出现在 `data.checks[].code`，不在 `error.code`）：

| code | 检查项名称 | 触发条件 |
|---|---|---|
| `serve.uv_missing` | `uv (>= 0.4)` | uv 不在 PATH |
| `serve.pnpm_missing` | `pnpm (>= 9)` | pnpm 不在 PATH |
| `serve.python_version_low` | `Python (>= 3.12)` | Python < 3.12 |
| `serve.data_unwritable` | `data dir writable` | data dir 不存在或无写权 |
| `serve.alembic_outdated` | `alembic head` | `alembic current` ≠ `alembic heads` |
| `serve.dist_missing` | `frontend/dist` | `frontend/dist/index.html` 不存在 |
| `serve.port_occupied` | `port :8000 free` / `port :5173 free` | 端口被占 |

> **doctor 输出结构**：`code` 和 `fix_hint` **只在 `ok=false` 的检查项才出现**（由 `DoctorCheck.to_dict()` 的 `if not self.ok` 分支控制）。doctor 本身成功 (`success=true`) 时聚合在 `data.checks[]`，不用 `error.code`。

## exit_code 速查

| exit_code | 含义 |
|---|---|
| 0 | 成功执行 |
| 1 | 一般错误（duplicate / validation / conflict / state_conflict / illegal_transition / serve.*） |
| 2 | 用法错误（UUID 格式非法、参数缺失）|
| 3 | 资源不存在（not_found） |
| 10 | 用户主动取消或 dry-run 预览（非错误；`success=true`） |

## edge case

### dry-run 退出码

`asset delete --dry-run` / `type delete --dry-run` / `asset retire --dry-run` 返回 `success=true` + 退出码 10。在 shell 脚本里：

```bash
uv run asset-hub asset delete <id> --dry-run --json
case $? in
  10) echo "dry-run preview, no change made" ;;
  0)  echo "delete completed" ;;
  3)  echo "asset not found" ;;
  1)  echo "general failure" ;;
esac
```

### usage error vs validation error

```bash
# UUID 格式非法 → validation + exit 2（usage 错误）
uv run asset-hub asset show "not-a-uuid" --json
# error.code == "validation", exit 2

# UUID 格式合法但不存在 → not_found + exit 3
uv run asset-hub asset show "00000000-0000-0000-0000-000000000000" --json
# error.code == "not_found", exit 3
```

区分通过 `handle_domain_errors(json_output, exit_2_on_validation=True)` 在 `cli/deps.py::parse_uuid()` 内启用。

### metadata.count 与 metadata.took_ms

- `count` 仅在集合返回时出现（如 `asset list`、`type list`）；单体返回（`asset show`）无此字段
- `took_ms` 在有明确计时的命令中出现（如 `serve status`、`serve doctor`）；快速命令的 `metadata` 可能是 `{}`

### v2.0 envelope error 深度结构化

v2.0 起 error 字段从 `{code, message}` 升级为 `{code, message, hint?, fields_missing?, fields_invalid?, affected_resource_id?}` 结构化，agent 优先读 hint 与 fields_* 字段做下一步行动。**向后兼容**：可选字段 exclude None，旧消费者只读 code/message 不破。

| 字段 | 类型 | 用途 |
|---|---|---|
| `code` | str | 必填，错误分类码（见上 inventory） |
| `message` | str | 必填，人类可读中文 detail |
| `hint` | str? | Agent 可执行的下一步建议（如"传入 to_holder 或 to_location 至少一项"） |
| `fields_missing` | list[str]? | 缺哪些字段（field name list） |
| `fields_invalid` | dict[str,str]? | 字段名 → 失败原因 |
| `affected_resource_id` | str? | 涉及资源 id（如失败 transition 的 asset_id） |

实施层：
- `src/asset_hub/errors.py`：`AssetHubError` base 加 4 个 keyword-only optional kwargs；6 子类各 `code = "..."` 类属性
- `src/asset_hub/api/app.py::_api_error_payload`：API 响应平铺新字段 + 保留 `detail`（前端兼容）
- `src/asset_hub/cli/envelope.py::_cli_error_payload`：CLI envelope `error` 字典内嵌新字段
- 两端均 exclude None：未设值字段不出现在响应

示例（agent 收到完整 hint 后可结构化下一步）：

```json
{
  "success": false,
  "error": {
    "code": "illegal_transition",
    "message": "REASSIGN 必须改 holder 或 location 至少一项",
    "hint": "传入 to_holder 或 to_location 至少一项（CLI: --to-holder / --to-location）",
    "fields_missing": ["to_holder", "to_location"]
  }
}
```

```json
{
  "success": false,
  "error": {
    "code": "validation",
    "message": "未知字段: foobar",
    "hint": "合法字段：id, name, status, holder, ...",
    "fields_invalid": {"foobar": "未知字段"}
  }
}
```

```json
{
  "success": false,
  "error": {
    "code": "illegal_transition",
    "message": "资产无未归还的派发记录: abc-123",
    "hint": "此资产当前不在 IN_USE 状态，无 OPEN CHECKOUT 可关闭。先检查 asset show 看当前 status。",
    "affected_resource_id": "abc-123"
  }
}
```

`serve doctor` 的 `data.checks[].fix_hint` 是另一类 hint——不在 `error.hint` 而在 `data.checks[]`，因为 doctor 多 issue 聚合渲染（success 路径）；语义与 `error.hint` 互补。
