# envelope reference

> ⚠️ 与 `src/asset_hub/cli/envelope.py` + `src/asset_hub/cli/serve/lifecycle.py` + `src/asset_hub/cli/serve/doctor.py` 同源约定 — 改一处必查另一处。

CLI envelope error code 完整 inventory + JSON 示例 + edge case。

## envelope 形态

成功：

```json
{ "success": true, "data": <任意>, "metadata": { "took_ms": 12, "count": 5 }, "error": null }
```

错误：

```json
{ "success": false, "data": null, "metadata": {}, "error": { "code": "<error_code>", "message": "<中文 detail>" } }
```

dry-run（破坏性命令的预览）：

```json
{ "success": true, "data": { "would_delete": true, ... }, "metadata": {}, "error": null }
```

dry-run 退出码 = 10（语义化区分"成功执行"与"成功预览不执行"）。

## error code 完整清单

### 域异常（主 CLI）

来源：`src/asset_hub/cli/envelope.py` `_DOMAIN_ERROR_CODES` 映射。

| code | 来源异常 | HTTP map | exit_code |
|---|---|---|---|
| `not_found` | `NotFoundError` | 404 | 3 |
| `duplicate` | `DuplicateError` | 409 | 1 |
| `validation` | `ValidationError` | 422 | 1（默认）/ 2（UUID parse 场景，via `exit_2_on_validation=True`） |
| `state_conflict` | `StateError`（业务规则冲突） | 409 | 1 |
| `conflict` | `ConflictError`（跨对象引用冲突，如 type 被资产引用时删除） | 409 | 1 |
| `illegal_transition` | `IllegalTransitionError` | 409 | 1 |
| `cancelled` | 用户在 dry-run 后取消操作（见 `type_cmd.py:123`） | — | 1 |

> **注**：`cancelled` 是 v1.0 现有行为（`type delete` dry-run 后用户拒绝确认），规范化为 v1.1 正式 formalize candidate（与 release-notes-v1.0.md 已知 gap 关联）。

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
| 1 | 一般错误（duplicate / validation / conflict / state_conflict / illegal_transition / cancelled / serve.*） |
| 2 | 用法错误（UUID 格式非法、参数缺失）|
| 3 | 资源不存在（not_found） |
| 10 | dry-run 预览（非错误；`success=true`） |

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

### 恢复建议（v1.0 状态 / v1.1 计划）

当前 `error.message` 自带恢复建议（如 `"CHECKOUT_INTERNAL 必须提供 to_holder"`）。v1.1 计划升级为 `{code, message, hint, fields_missing?, ...}` 结构化，届时 message 与 hint 分离。

`serve doctor` 的 `data.checks[].fix_hint` 是局部 hint 实现样本——不在 `error.hint` 而在 `data.checks[]`，因为 doctor 在 success 路径下多 issue 聚合渲染。
