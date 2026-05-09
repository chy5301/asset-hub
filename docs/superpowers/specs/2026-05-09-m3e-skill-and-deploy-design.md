# M3e 设计文档 · SKILL.md + 部署 + 测试基建（v1.0 GA 收口）

- **日期**：2026-05-09
- **状态**：初稿，待实施
- **作者**：conghaoyangbobby@gmail.com（与 Claude 协同 brainstorm）
- **范围**：M3 第 5 个、也是最后一个子里程碑。v1.0 GA 前收口工作：CLI envelope 统一、SKILL.md 起草、Windows 部署文档、README 全量重写、v1.0 release notes、playwright e2e CI、5 态文案对齐、测试薄弱点补齐。

## 0. 背景

M3a/b/c/d 全部合并 main，v1 资产管理主线 + 状态机 + 看板 + 导出 + timeline 视觉都已就位。M3e 是 v1.0 GA 前最后一个子里程碑，**不引入新业务能力**，目标是把"对外契约 + 文档 + CI 兜底"收口，让 v1.0 可发版。

参考文档：
- M3 总览：[`2026-05-03-m3-overview-design.md`](./2026-05-03-m3-overview-design.md) §3.5（M3e 范围）+ §4（跨子里程碑约束）
- M3a 状态机基建：[`2026-05-03-m3a-state-machine-design.md`](./2026-05-03-m3a-state-machine-design.md)
- followup 分配：[`../followup-allocation.md`](../followup-allocation.md) §M3e 行 ⏳ 待启动
- simplify follow-up：[`../simplify-followups.md`](../simplify-followups.md) §5 K1（HIGH 优先级 envelope 统一）/ §7-§8（M3a/M3d 落地后新登记）
- agent-native 设计指南：`agent-native-design-guide` skill
- skill 写法标准：`skill-creator` skill

## 1. 总览

### 1.1 架构变化（仅 CLI / docs / CI 三处）

主 spec [`2026-04-15-asset-hub-design.md`](./2026-04-15-asset-hub-design.md) §3 三层架构（Web GUI / CLI → Service 唯一事实 → Repo）**不动**。改动落在三处：

```
┌────── CLI 层 ────────┐    ┌── docs / 仓库根 ───┐    ┌── .github/workflows ──┐
│ envelope.py 升级      │    │ SKILL.md 新增       │    │ e2e.yml 新增            │
│ serve/cmd.py 重写     │    │ references/ 拆 4 文件│    │ playwright 启动         │
│ serve/doctor.py 新增  │    │ docs/deployment.md  │    │ serve start --mode prod │
│                      │    │ README.md 重写      │    │ + 跑 7 spec             │
│                      │    │ release-notes-v1.0  │    │                         │
└──────────────────────┘    └────────────────────┘    └────────────────────────┘
        ↓ 不变 ↓                ↓ 不变 ↓                  ↓ 不变 ↓
   Service / Router / 前端 RHF / TanStack Router / SQLModel migration
```

**唯一例外**：5 态文案修订动到 `frontend/src/features/assets/status-labels.ts` 单 SoT 一处 + `src/asset_hub/services/export.py` `STATUS_LABELS` dict——属于展示层 string 改动，不动 service / router / model / 枚举值。

### 1.2 单 PR 4 phase 顺序（feat/m3e-ga）

| phase | 主题 | 关键 commit subject 形态 |
|---|---|---|
| **1** | envelope 升级 + serve doctor | `feat(cli): 统一 envelope error 为 {code, message}` / `feat(serve): doctor 子命令` |
| **2** | 5 态文案 + 薄弱点补测 | `refactor(frontend): 5 态文案对齐 3 字（闲置中/使用中）` / `test(asset): 5 态 filter 列表拼接` |
| **3** | SKILL.md + Windows 部署 + README + release notes | `docs(skill): 仓库根 SKILL.md (agent-native + references)` / `docs(deployment)` / `docs(readme)` / `docs(release)` |
| **4** | playwright e2e + GitHub Actions | `test(e2e): 7 个 happy path spec` / `ci: GitHub Actions e2e workflow` |

**顺序理由**：
- Phase 1 先定 envelope 形态——Phase 3 SKILL.md / references/envelope.md 要把 envelope schema 文档化，前者不定形后者写不出来
- Phase 2 5 态文案修订理论上能与 Phase 1 并行；单 PR 单 branch 走串行避免冲突
- Phase 3 文档先于 e2e——Phase 4 e2e fixtures 命令调用形态与 SKILL.md 命令速查同源
- Phase 4 最后——e2e 在 envelope/5 态/SKILL.md 都定型后写一次到位

### 1.3 包 / 不包

**包**：
1. K1 envelope 统一（`error` 字段 → `{code, message}`，主 CLI + serve 单一契约）
2. `serve doctor` 子命令（环境/版本/依赖/端口/dist 7 项诊断）
3. 5 态文案修订（IDLE → 闲置中、IN_USE → 使用中；其余 3 态不变）
4. 测试薄弱点补齐（5 态 filter 列表拼接 — 默认隐藏 RETIRED/DISPOSED + `include_retired` / `include_disposed` 独立 toggle 组合）
5. `SKILL.md`（仓库根，agent-native frontmatter + 主体 ≤ 200 行 + `references/` 拆 4 文件 progressive disclosure）
6. `docs/deployment.md` 稳定参考文档（Windows 单机首选 / 配置 / 备份 / 升级路径）
7. `README.md` 全量重写（v1.0 GA 主页面）
8. `docs/superpowers/release-notes-v1.0.md` 一次性升级指南
9. playwright e2e 5-7 happy path 脚本（实定 7 spec）
10. GitHub Actions `e2e.yml` workflow

**不包（推 v1.1 或 M4）**——完整列表见 §7.4：
- Linux 真机烟测 / Lighthouse a11y 全站扫描（v1.1）
- M2d known gap 残：多代日志轮转 / `serve build` 独立 / `--workers`（触发条件出现后）
- M3a/M3d 残：A3 dialog 合并 / §S Toggle 视觉 / §T `IllegalTransitionError.detail` 结构化 payload / §U KIND_META 跨文件合一 / §V `Settings.mode` 字段 / §W types/assets 风格统一 / §X dispose-dialog RHF / §Y findOpenCheckout 抽工具 / §Z formatRelative 小时级粒度（M4 / 触发条件）
- **envelope error 结构化升级**：`{code, message}` → `{code, message, hint, fields_missing?, ...}`（v1.1 与 §T detail 结构化同 PR）
- **`--help --json` 双模 help** / **`--fields` 字段掩码**（v1.1，agent-native 检查清单候选项）
- v1.0.0 git tag 动作（PR 合并 + 用户人工检查无残留后单独执行；不进 PR、不进 plan phase）
- SKILL.md description trigger eval（v1.1 用 skill-creator 的 description optimization loop 跑 5 iteration）

### 1.4 不破坏的契约

| 契约 | 来源 |
|---|---|
| HTTP API：`POST /api/assets/{id}/transitions` 单端点 + body shape | M3a |
| HTTP API：`GET /api/assets`、`GET /api/stats`、`GET /api/export` query 参数 | M3a/b/c |
| 5 态枚举值 `IDLE/IN_USE/MAINTENANCE/RETIRED/DISPOSED` | M3a |
| 10 transition kind 枚举值 | M3a |
| Service 层签名（`record_transition` / `list_assets` 等） | M3a |
| Alembic migration head（M3e 不新增 schema 变更） | M3a/b/c/d |
| 前端 `generated/schema.d.ts`（openapi-typescript 产物） | M3a/b/c |
| `Settings()` 现有字段 | M2d |
| `data/asset_hub.db` / `data/attachments/` 目录布局 | 全程 |

**M3e 对外契约零破坏**。改动全在 CLI 层 + 文档 + CI 配置 + 5 态文案展示层。

## 2. Phase 1 · envelope 升级 + serve doctor

### 2.0 与 agent-native-design-guide 的对齐

agent-native-design-guide 对 CLI 错误响应的硬约束是"包含错误码（机器可读）+ 错误描述 + 恢复建议"。本里程碑的 envelope 升级形态 `{code, message}` 满足前两项，**第三项（恢复建议）通过 `message` 自带自然语言修复指引承担**——例如 `IllegalTransitionError("CHECKOUT_INTERNAL 必须提供 to_holder——加上 --to-holder 选项重试")`，与现有 M3a 实现一致。

envelope 结构化升级到 `{code, message, hint, fields_missing?, ...}` 推 **v1.1**——与 simplify §T（IllegalTransitionError detail 结构化 payload）同 PR 落地，届时 message 与 hint 分离，前端 dialog 也按 hint code 渲染本地化文案。

`serve doctor` 的 `fix_hint` 字段（§2.4）是局部 hint 实现样本——它在 `data.checks[].fix_hint` 而非 `error.hint`，因为 doctor 是 success 路径下的多 issue 聚合渲染（不进 `handle_domain_errors`）。

agent-native 检查清单中的 `--help --json` 双模、`--fields` 字段掩码同样推 v1.1（YAGNI；M3e 范围已饱和）。

### 2.1 envelope error code inventory

**主 CLI（域异常自动映射，6 个）**：

| 异常类（`src/asset_hub/errors.py`） | code | HTTP map（`api/app.py` 已就位） | exit_code |
|---|---|---|---|
| `NotFoundError` | `not_found` | 404 | 3 |
| `DuplicateError` | `duplicate` | 409 | 1 |
| `ValidationError` | `validation` | 422 | 1 / 2(usage) |
| `StateError` | `state_conflict` | 409 | 1 |
| `ConflictError` | `conflict` | 409 | 1 |
| `IllegalTransitionError` | `illegal_transition` | 409 | 1 |

`StateError → state_conflict`（不裸 `state`），避免与"状态机/状态字段"歧义。

**serve（已有 dot prefix 保留，10 个）**——grep `src/asset_hub/cli/serve/lifecycle.py` 确认：

`serve.port_occupied` / `serve.dist_missing` / `serve.health_probe_timeout` / `serve.frontend_failed_to_start` / `serve.data_unwritable` / `serve.already_running` / `serve.build_failed` / `serve.kill_failed` / `serve.mode_required`

**serve doctor 新增（候选）**：

`serve.uv_missing` / `serve.pnpm_missing` / `serve.alembic_outdated` / `serve.dist_outdated` / `serve.python_version_low`

### 2.2 envelope.py 改动

`src/asset_hub/cli/envelope.py` 重写为：

```python
from asset_hub.errors import (
    AssetHubError, NotFoundError, DuplicateError, ValidationError,
    StateError, ConflictError, IllegalTransitionError,
)

_DOMAIN_ERROR_CODES: dict[type[AssetHubError], str] = {
    NotFoundError: "not_found",
    DuplicateError: "duplicate",
    ValidationError: "validation",
    StateError: "state_conflict",
    ConflictError: "conflict",
    IllegalTransitionError: "illegal_transition",
}


def success_envelope(data, count=None, took_ms=None) -> str:
    # 不变：success/data/metadata/error 形态保持，只改 error 形态
    ...


def error_envelope(message: str, *, code: str) -> str:
    return json.dumps({
        "success": False, "data": None, "metadata": {},
        "error": {"code": code, "message": message},
    }, ensure_ascii=False)


def print_error(message: str, json_output: bool, *, code: str, exit_code: int = 1) -> NoReturn:
    if json_output:
        print(error_envelope(message, code=code))
    else:
        from rich.console import Console
        Console(stderr=True).print(f"[red]错误:[/red] {message}")
    raise SystemExit(exit_code)


@contextmanager
def handle_domain_errors(json_output: bool, *, exit_2_on_validation: bool = False):
    try:
        yield
    except AssetHubError as e:
        code = _DOMAIN_ERROR_CODES[type(e)]
        exit_code = (
            3 if isinstance(e, NotFoundError)
            else (2 if (isinstance(e, ValidationError) and exit_2_on_validation) else 1)
        )
        print_error(str(e), json_output, code=code, exit_code=exit_code)
```

`print_result` / `print_dry_run` / `to_json_dict` 不变（成功路径无 error 字段）。

**`code` keyword-only 必填**——禁止裸 `print_error("失败")` 漏 code，所有 callsite 必须显式给 code。

### 2.3 serve/cmd.py 重写

5 子命令（start / stop / status / restart / logs）改造模式统一：

```python
# Before
@app.command()
def start(...):
    try:
        result = lifecycle.start_service(...)
        _emit_success(json_out=json_out, ..., data=result.to_dict(), metadata=result.metadata())
    except ServeLifecycleError as e:
        _emit_error(json_out=json_out, ..., error=e.to_dict())
        raise typer.Exit(code=1)

# After
@app.command()
def start(...):
    try:
        result = lifecycle.start_service(...)
        if json_out:
            print(success_envelope(result.to_dict(), took_ms=result.took_ms))
        else:
            print(render_plain_start(result))
    except ServeLifecycleError as e:
        print_error(e.message, json_out, code=e.code, exit_code=1)
```

**删**：
- `serve/output.py::render_json_envelope`（~15 LOC）
- `serve/output.py::ServeError` dataclass（~10 LOC）
- `serve/cmd.py::_emit_success / _emit_error`（~30 LOC）

**保留**：
- `serve/output.py::ServiceInfo / StartResult / StopResult / StatusReport` dataclass（plain renderer 仍依赖）
- `serve/output.py::render_plain_*`

`ServeLifecycleError(code, message)` 双字段保留——它是 raw payload source，`code` pass through 到 `print_error`，`serve.*` dot prefix 自然继承。

### 2.4 serve doctor 子命令

新增 `src/asset_hub/cli/serve/doctor.py` + `cmd.py::doctor` 子命令。

**检查项（v1）— 7 项**：

| # | 检查 | 通过条件 | 失败 code |
|---|---|---|---|
| 1 | uv 可用 | `uv --version` exit 0 | `serve.uv_missing` |
| 2 | pnpm 可用 | `pnpm --version` exit 0 | `serve.pnpm_missing` |
| 3 | Python 版本 | `>= 3.12` | `serve.python_version_low` |
| 4 | data dir 可写 | `Settings().data_dir` exists & writable | `serve.data_unwritable`（复用） |
| 5 | alembic head | `alembic current` 与 `alembic heads` 一致 | `serve.alembic_outdated` |
| 6 | frontend/dist 存在 | `frontend/dist/index.html` 存在（仅 prod 模式相关） | `serve.dist_missing`（复用） |
| 7 | 端口可用 | `:8000`、`:5173`（dev 模式额外）未被其他 serve start 之外进程占用 | `serve.port_occupied`（复用） |

**plain 输出**：

```
SERVICE                  STATUS
uv (>= 0.4)              ✓ 0.5.4
pnpm (>= 9)              ✓ 9.12.3
Python (>= 3.12)         ✓ 3.12.7
data dir writable        ✓ /Users/.../data
alembic head             ✓ 80f6499 (current = head)
frontend/dist            ! missing (run `pnpm --dir frontend build`)
port :8000 free          ✓
port :5173 free          ✓

1 issue. Run `uv run asset-hub serve doctor --json` for machine-readable output.
```

**JSON 输出**：

```json
{
  "success": true,
  "data": {
    "checks": [
      {"name": "uv", "ok": true, "detail": "0.5.4"},
      {"name": "pnpm", "ok": true, "detail": "9.12.3"},
      {"name": "frontend_dist", "ok": false, "detail": "missing",
       "code": "serve.dist_missing", "fix_hint": "pnpm --dir frontend build"}
    ],
    "ok": false,
    "issue_count": 1
  },
  "metadata": {"took_ms": 412},
  "error": null
}
```

**退出码**：
- 全部通过 → exit 0
- 至少一项失败 → exit 1

诊断命令本身**不抛域异常**（不进 `handle_domain_errors`），所有 check 收集后统一渲染——这是它"agent 友好可重复"的关键（不是"第一个错就 fail"）。

**doctor 不接 lifecycle**：纯 read-only 检查，不调 `start_service` / `stop_service`。

### 2.5 测试改动面（Phase 1）

**新增**：
- `tests/unit/test_envelope.py` 6 case：每个域异常 → `handle_domain_errors` → 验证 envelope shape `{code, message}` + exit_code
- `tests/unit/test_doctor.py` 8 case：7 检查项各 1 + 全通过聚合 1（用 monkeypatch mock subprocess / Path 状态）
- `tests/cli/test_serve_doctor.py` 3 case：plain 输出 / json 输出 / 至少一项失败 exit 1

**改动现有**：
- `tests/cli/test_serve_*.py` 5 文件：`error.code` / `error.message` 解析路径**不变**（已是 dict shape），仅断言改成走 `envelope.py` 的 `print_error` 调用 path
- `tests/cli/test_asset_cli.py` / `test_type_cli.py` / `test_attachment_cli.py` / `test_transition_cmds.py` / `test_stats_cli.py` 5 文件：grep `parsed["error"] == ` / `payload["error"] ==` 字面 string 断言，改成 `error.message == ...` 或 `error == {"code": ..., "message": ...}`。预估 12-18 处

**改造期辅助**：
- 一行 `git grep -nE 'parsed\["error"\]\s*==\|payload\["error"\] ==' tests/` 列出全部定位
- 单元测试改完跑 `uv run pytest tests/cli`，挂的 case 改一处过一处

### 2.6 Phase 1 验收

- [ ] `uv run pytest` 全绿（含新 envelope/doctor 测试）
- [ ] `uv run ruff check .` clean
- [ ] `uv run asset-hub asset get <无效id> --json` → `{"success": false, "error": {"code": "validation", "message": "..."}}` exit 2
- [ ] `uv run asset-hub asset get <不存在id> --json` → `error.code == "not_found"` exit 3
- [ ] `uv run asset-hub serve start --mode prod`（重复启动）→ `error.code == "serve.already_running"` exit 1
- [ ] `uv run asset-hub serve doctor --json` 在干净环境 → `data.ok == true` exit 0；缺 dist 时 → `data.ok == false` exit 1，issue 含 `code: serve.dist_missing` + `fix_hint`
- [ ] grep `render_json_envelope` / `_emit_success` / `_emit_error` 应**全部消失**

## 3. Phase 2 · 5 态文案修订 + 薄弱点补测

### 3.1 5 态文案修订

**新文案 SoT 表**：

| Status | 旧 label | 新 label |
|---|---|---|
| `IDLE` | 闲置 | **闲置中** |
| `IN_USE` | 在用 | **使用中** |
| `MAINTENANCE` | 维修中 | 维修中（不变） |
| `RETIRED` | 已退役 | 已退役（不变） |
| `DISPOSED` | 已处置 | 已处置（不变） |

只动 IDLE 与 IN_USE 两个 label。理由：M3a 决议是 IDLE→闲置 / IN_USE→在用，2-2-3-3-3 字数不齐；M3e 收口期对齐到 3 字模式（"X中" 进行态 / "已X" 终态），列表 chip / dashboard tooltip / 导出列宽 / SKILL.md 表格全部受益。

**改动点**（grep 已确认）：

| 层 | 文件 | 内容 |
|---|---|---|
| 前端 SoT | `frontend/src/features/assets/status-labels.ts` | `STATUS_META.IN_USE.label` / `IDLE.label` |
| 前端引用 | `dashboard-header.tsx` / `dashboard/empty-states/idle-empty.tsx` / `dashboard/charts/idle-top-bar-chart.tsx` / `assets/list/assets-filters.tsx` / `assets/detail/retire-alert-dialog.tsx` / `simple-transition-dialog.tsx` / `dispose-alert-dialog.tsx` | 多数引用 `STATUS_META[s].label` 自动跟随；硬编码字面量需手 grep |
| 后端 SoT | `src/asset_hub/services/export.py:28-32` `STATUS_LABELS` dict | XLSX/CSV 导出"状态"列文案 |
| 后端非 SoT | `src/asset_hub/cli/asset_cmd.py:194` docstring + L319/323 `--include-retired/disposed` help / `cli/stats_cmd.py` `"闲置 Top 10"` | 这一类是"闲置时长 / 闲置天数 / 闲置 Top 10"等名词性指标概念，**不**修订 |
| 前端测试 | `tests/components/{status-distribution-chart, idle-top-bar-chart, dashboard-motion, dashboard-header}.test.tsx` | 字面 "在用"/"闲置" 替换为 "使用中"/"闲置中" |

**修订原则**：
- 仅替换 5 态 label 本身的"在用→使用中"、"闲置→闲置中"
- 不替换"闲置时长 / 闲置天数 / 闲置 Top 10"——这些是名词性指标概念，"闲置时长 = idle 状态停留时长"语义清楚
- 不替换 CLI help 与 docstring 里的"已退役/已处置"——这两态文案没变

### 3.2 薄弱点补测 — 5 态 filter 列表拼接

**当前 API 形态**：
- `GET /api/assets?status=IDLE` 单态 filter（`AssetStatus` 枚举单值）
- `?include_retired=true` / `?include_disposed=true` 独立 toggle，默认 `false`
- 服务层 `AssetService.list_assets(status=, include_retired=, include_disposed=)` 三参数

**当前测试覆盖**：grep `tests/api/test_asset_routes.py` / `tests/unit/test_asset_service.py` 仅 status 单值 filter 主路径；`include_retired` / `include_disposed` 组合**未独立覆盖**。

**薄弱点补测计划**：

后端 `tests/unit/test_asset_service.py` 新增 6 case：
1. 默认（无 status，无 include flag）→ 不含 RETIRED/DISPOSED
2. `include_retired=True, include_disposed=False` → 含 RETIRED 不含 DISPOSED
3. `include_retired=False, include_disposed=True` → 含 DISPOSED 不含 RETIRED
4. `include_retired=True, include_disposed=True` → 全 5 态都含
5. `status=RETIRED, include_retired=False` → 显式 status RETIRED 应**强制包含**（status 显式 override 默认排除）
6. `status=DISPOSED, include_retired=False, include_disposed=False` → 同上 5 态显式 status override

后端 `tests/api/test_asset_routes.py` 新增 2 case：
- 1×4 query 组合 → JSON 响应行数与服务层匹配
- `status=RETIRED` 显式 query → 不依赖 include_retired flag

前端 `tests/hooks/` 新增 1 case：
- `assets-filters.tsx` Toggle on/off → URL search params 同步 + list query refetch（用 msw mock list endpoint 验证 query string）

**为何此处是薄弱点**：M3a PR-1 后端聚焦 transition 端点，PR-2 前端聚焦 dialog；list filter 的 5 态新组合**没专门 case 覆盖**，靠 toggle UI 手测。M3e 补这一刀关闭"5.5 → DISPOSED → 历史回看"用户路径回归风险。

### 3.3 Phase 2 commit 切分

```
refactor(frontend): 5 态文案对齐 3 字（闲置中/使用中）
refactor(backend): export STATUS_LABELS 同步 5 态新文案
test(asset): 补 5 态 filter include_retired/include_disposed 组合 6+2 case
test(frontend): assets-filters Toggle 同步 URL search params 1 case
```

### 3.4 Phase 2 验收

- [ ] `pnpm --dir frontend test` 全绿（含修订 + 新 case）
- [ ] `uv run pytest` 全绿（新增 8 后端 case + export 测试同步）
- [ ] `pnpm --dir frontend lint` clean
- [ ] `uv run ruff check .` clean
- [ ] 浏览器手测 list 页：默认隐藏 RETIRED/DISPOSED，开 toggle 后行数 +N，关 toggle 后行数恢复；chip 显示"闲置中/使用中/维修中/已退役/已处置" 5 态都正确
- [ ] dashboard `/dashboard` 4 张图 tooltip / x 轴 label 看到新文案
- [ ] `uv run asset-hub asset list --json` 返回 5 态枚举值不变（不返中文 label）

## 4. Phase 3 · 文档（SKILL.md / deployment.md / README / release-notes-v1.0.md）

### 4.1 SKILL.md（仓库根，agent-native + references/ 拆分）

按 `skill-creator` 与 `agent-native-design-guide` 标准设计。**主体 ≤ 200 行**，progressive disclosure 拆 `references/` 4 文件。

#### 4.1.1 frontmatter description

经 skill-creator "误触发风险评估"校准后的版本（删冗余具象词、加语境锚、保留关键 trigger 类别）：

```yaml
---
name: asset-hub
description: |-
  小组资产管理工具（命令 asset-hub）的 Agent 入口。
  使用此 skill 当用户在 asset-hub 项目里提到资产登记 / 状态流转（派发、归还、送修、退役、处置）/ 列表筛选 / CSV/XLSX 导出 / 看板统计 / AssetType 自定义字段 / serve 子命令（start/stop/status/restart/logs/doctor）/ 在 Windows 部署 asset-hub / asset-hub 升级，或在项目目录里直接调用 asset-hub 命令。
  包含 5 态状态机（闲置中/使用中/维修中/已退役/已处置）、10 种 transition、JSON envelope 契约、CLI 命令速查、常见任务流。
---
```

**校准要点**：
- 项目根 SKILL.md 触发面已被 cwd 锁死，不需要全局 skill 那种"pushy 防欠触发"密度
- 给宽泛词加语境锚（`AssetType 自定义字段`、`在 Windows 部署 asset-hub`、`asset-hub 升级`）
- 删冗余具象词（"4 张图"、"/api/stats" 等用户日常不说的代码细节）
- 删冗余动词列表（"变更位置/变更保管人/重新启用/维修完成/出借" 已被"状态流转"概括，靠 Claude 语义理解扩展）
- description 触发率量化校准推 v1.1（用 skill-creator 的 description optimization loop）

#### 4.1.2 SKILL.md 主体结构（≤ 200 行）

下方为 **结构骨架**——`[...]` 内的描述是 plan 期填充的章节内容形态指引，实施期写出实际表格 / 命令清单 / Gotchas 文案。

```markdown
# asset-hub

## 何时用我
- 资产 CRUD（登记 / 查询 / 编辑 / 删除）
- 状态流转（10 种 transition）
- 类型管理（自定义字段定义）
- 看板查询（4 段聚合统计）
- 数据导出（CSV / XLSX，按当前筛选透传）
- 服务生命周期（serve start/stop/status/restart/logs/doctor）

## 资产状态机（5 态总览）
[5 态精简表 1 行/态]

## 10 种 transition（总览）
[精简表 1 行/kind，含 from→to 简记]

## CLI envelope 速查
[success/error JSON 形态 + exit code 表]

## 命令速查
[按 resource 分组：asset / type / attachment / transition / stats / export / serve，每命令 1 行 + 关键 flag]

## Gotchas（含 explain the why）
- DISPOSED 是终态（不可回退）：因为对应物理处置（卖/捐/销毁），与 RETIRED（暂时退役、可复活）严格区分
- DISPOSE 必须 from RETIRED/MAINTENANCE：让"用户误点处置"成本最小化（多一步 dialog 二次确认）
- 归还后 holder/location 跟随 to_holder/to_location 不强制清空（M3a 修订）
- IN_USE → MAINTENANCE 直跳走两步（dialog 提示 + service 写两条 record）
- 5 态 UI 文案 vs 枚举值严格区分（"闲置中" UI / "IDLE" API）

## 详细参考
- 10 transition 完整规则（**何时读**：用户问 RELOCATE 与 TRANSFER_HOLDER 区别 / dialog 行为 / from-status 边界）：[references/transitions.md](./references/transitions.md)
- envelope error code 完整 inventory（**何时读**：解析 CLI error 遇到未知 code、调试 exit_code、需引用错误处理对照表）：[references/envelope.md](./references/envelope.md)
- 端到端任务流（**何时读**：用户给出"帮我登记 + 派发 + 归还"完整流程，或需要 --json 输出对照样本）：[references/workflows.md](./references/workflows.md)
- 部署 / serve doctor / 故障排查（**何时读**：`serve start` 失败、`serve doctor` 输出有 issue、用户问"在 Windows 怎么部署 / 怎么备份"）：[references/deploy.md](./references/deploy.md)
```

**为何要"何时读"指引**：skill-creator 的 progressive disclosure 标准要求"Reference files clearly from SKILL.md with guidance on when to read them"——agent 在 SKILL.md 主体 200 行内已能解决 80% 任务，剩余 20% 触发 references 加载需要明确触发条件，避免"无差别加载所有 references" 浪费 context。

#### 4.1.3 references/ 4 文件（progressive disclosure）

```
SKILL.md（≤ 200 行）
references/
├── transitions.md   # 10 transition 完整规则: from/to / 必填字段 / dialog 行为 / service 写入语义
├── envelope.md      # error code 完整 inventory + JSON 示例 + edge case + exit code 详表
├── workflows.md     # 5 端到端任务流 with --json 输出实例（登记 / checkout-return / 送修闭环 / 退役复活 / 按筛选导出）
└── deploy.md        # 部署 / serve doctor 7 检查项 / 故障排查 / 备份恢复 完整指南
```

**`references/deploy.md` 与 `docs/deployment.md` 关系**：
- `docs/deployment.md`：给人类作者读的稳定参考（独立文件）
- `references/deploy.md`：给 Agent 读的精简版 + pointer。**实施时若两者重复维护成本过高，`references/deploy.md` 改为单行 pointer：`详见 ../docs/deployment.md`**，agent 通过 pointer 拿完整内容，避免双源漂移

**写法约束**（"explain the why"）：用"为什么"代替 MUST/ALWAYS。例如不是"NEVER allow DISPOSE → IDLE"，而是"DISPOSED 是终态——一旦设置不可回退，因为它对应物理处置（卖/捐/销毁）"。让 Agent 在边界 case 上做正确判断，而非死记硬背。

**与代码同源约束**（防 staleness）：
- `references/transitions.md` 头部加：`# ⚠️ 与 src/asset_hub/services/transition.py + src/asset_hub/api/routers/transitions.py 同源约定 — 改一处必查另一处`
- `references/envelope.md` 头部加同源提示，pointer 指 `src/asset_hub/cli/envelope.py`
- `references/workflows.md` 命令调用形态与 Phase 4 e2e fixtures 同源
- 自动 staleness 检查 helper 推 v1.1

### 4.2 docs/deployment.md（稳定参考文档）

```markdown
# 部署指南

## 环境要求
- Python 3.12+ / Node.js 20+ / uv 0.4+ / pnpm 9+
- Windows 11 / Linux（v1.1 真机验证）

## 安装
1. clone 仓库
2. uv sync
3. pnpm --dir frontend install
4. cp .env.example .env（说明每个 ASSET_HUB_* 变量）
5. uv run alembic upgrade head
6. uv run asset-hub serve doctor 验证环境
7. uv run asset-hub serve start --mode prod

## 配置项（.env）
[列 Settings 所有字段：data_dir / logs_dir / database_url / backend_port / frontend_port / mode / ...（实施期对照 `src/asset_hub/config.py::Settings` 全枚举）]

## 数据维护
- 数据库：data/asset_hub.db（SQLite 单文件）
- 附件：data/attachments/<yyyy>/<mm>/<sha256>.<ext>
- 日志：data/logs/{backend,frontend}.log（+ .1 上一会话）
- 备份：cp data/asset_hub.db <date>.bak（建议每日 + 升级前）

## 升级
- git pull → uv sync → pnpm --dir frontend install → uv run alembic upgrade head
- uv run asset-hub serve doctor → uv run asset-hub serve restart --mode prod

## 故障排查
- serve doctor 各项失败的修复指引
- 端口占用 / dist 缺失 / pid 残留 / 数据库 lock
- 日志位置 + tail --follow
```

### 4.3 README.md（全量重写）

v1.0 GA 主页面：
- 定位句保留
- 核心能力列全（资产 CRUD + 类型驱动字段 + 5 态状态机 + 10 transition + 看板 + 导出 + 附件 + serve 生命周期）
- 技术栈表补 alembic / openpyxl / playwright / TanStack 全家桶
- 快速开始：删 `./scripts/dev.sh`，改 `serve start --mode dev`
- CLI 示例从 2 条扩到 7 条（type define / asset register / transition checkout / transition return / asset list filter / asset export xlsx / serve doctor）
- 路线图状态全更新（M1 ✅ / M2 ✅ / M3a-d ✅ / M3e ✅ / M4 ⏳ / M5 ⏳）
- 文档索引：[SKILL.md](./SKILL.md) / [docs/deployment.md](./docs/deployment.md) / [docs/superpowers/specs/](./docs/superpowers/specs/) / [docs/superpowers/release-notes-v1.0.md](./docs/superpowers/release-notes-v1.0.md)

### 4.4 docs/superpowers/release-notes-v1.0.md（一次性升级指南）

继承 `release-notes-m2d.md` 形态：

```markdown
# v1.0 GA 发版升级指南

## 概览（v1.0 = M2d 之后所有里程碑）

| 里程碑 | 主线交付 | merge commit |
|---|---|---|
| M3a | 5 态状态机 + 10 transition + StateTransitionRecord 重构 + CLI 9 子命令 + 7 dialog | a360e04 + bc084e5 |
| M3b | /api/stats + 看板 4 图表 + ChartTokenProvider | c21ae55 + 98052dc |
| M3c | /api/export CSV/XLSX + ExportButton | a55beec + 5c5bab0 |
| M3d | timeline Group rail + 月份分段 + 派出类型染色 + 超长派发预警 + simplify §7 | 5320804 |
| M3e | SKILL.md + envelope 统一 + serve doctor + 5 态文案对齐 + Windows 部署文档 + playwright e2e CI | `<m3e-merge>`（实施期回填） |

## Breaking changes
- HTTP API：废 `POST /api/assets/{id}/checkout` / `/return` / 散点 PATCH status；统一 `POST /api/assets/{id}/transitions { kind, ... }`（M3a）
- 数据库：drop `checkout_records` 表 + drop `Asset.current_checkout_id`；add `state_transition_records` + `Asset.status` enum 加 DISPOSED（M3a migration）
- CLI envelope：error 字段从 plain string 升级为 `{code, message}` 结构化（M3e）
- 5 态文案：在用→使用中、闲置→闲置中（M3e；前端 + 导出列文案，不影响 API 枚举值）

## 升级前
1. 备份数据库：`cp data/asset_hub.db data/asset_hub.db.<日期>.bak`
2. 备份附件：`tar czf attachments-<日期>.tgz data/attachments/`
3. 如有自定义 dev 脚本，确认调用 `uv run asset-hub serve start --mode dev`

## 升级
- git pull / git fetch && git checkout v1.0.0
- uv sync / pnpm --dir frontend install
- uv run alembic upgrade head（M3a migration 含 drop checkout_records — 单向不可回数据）
- uv run asset-hub serve doctor

## 升级后验证
1. 自动化测试：`uv run pytest` + `pnpm --dir frontend test --run`
2. CI e2e workflow 在 v1.0.0 tag push 后自动跑
3. Windows 烟测 checklist（继承 M2d 形态，扩 transition + export + stats）：
   - [ ] register / list / get
   - [ ] transition checkout/return 闭环
   - [ ] transition retire/reinstate
   - [ ] transition retire→dispose（终态锁）
   - [ ] export csv/xlsx 含 5 态
   - [ ] dashboard 加载 4 张图
   - [ ] serve doctor 全 ✓
   - [ ] serve start/stop/status/restart/logs

## 已知 gap（推 v1.1+）
- Linux 真机烟测
- Lighthouse a11y 全站扫描 + 修复
- M2d 残：多代日志轮转 / serve build 独立 / --workers
- M3 残：A3 dialog 合并 / §S/§T/§U/§V/§W/§X/§Y/§Z（详见 simplify-followups.md）
- SKILL.md description trigger eval（用 skill-creator 的 description optimization loop 在 v1.1 跑 5 iteration）

## 回滚
- git checkout <pre-v1.0-commit>
- cp data/asset_hub.db.<日期>.bak data/asset_hub.db
- 重启 serve（注意：alembic downgrade 不能恢复 drop 的 checkout_records 数据，必须用 db 备份）
```

### 4.5 Phase 3 commit 切分

```
docs(skill): 仓库根 SKILL.md (agent-native frontmatter + 5 态/10 transition/envelope/Gotchas)
docs(skill): references/ 拆 4 文件 (transitions / envelope / workflows / deploy)
docs(deployment): docs/deployment.md (Windows 单机首选 + 配置 + 备份 + 故障排查)
docs(readme): README.md 全量重写 (M3 后路线图 + 7 条 CLI 示例 + 文档索引)
docs(release): docs/superpowers/release-notes-v1.0.md (升级前/升级/验证/烟测/已知 gap/回滚)
```

### 4.6 Phase 3 验收

- [ ] SKILL.md 主体 ≤ 200 行
- [ ] SKILL.md 引 envelope schema 与 §2.1（envelope.py 实际形态）一致
- [ ] SKILL.md 引 5 态文案与 status-labels.ts 一致
- [ ] SKILL.md 引 10 transition 与 transition_kind enum 一致
- [ ] references/ 4 文件齐备 + 头部同源约定提示
- [ ] deployment.md 所有命令实际可执行（dry-run 一遍）
- [ ] README.md 路线图状态与本 spec 当前 phase 一致
- [ ] release-notes-v1.0.md 已知 gap 清单与 followup-allocation.md + simplify-followups.md 残留对账
- [ ] 全部文档 markdown 渲染干净（VSCode preview 检查）

## 5. Phase 4 · playwright e2e + GitHub Actions

### 5.1 e2e 场景集（7 条 happy path）

| # | 场景名 | 经过的 transition kind / 端点 |
|---|---|---|
| 1 | `register-and-list` | type define → asset register（含照片）→ list 页表格出现 |
| 2 | `checkout-return-internal` | CHECKOUT_INTERNAL → RETURN（带 to_holder/to_location） |
| 3 | `maintenance-cycle` | SEND_TO_MAINTENANCE → RECOVER_FROM_MAINTENANCE |
| 4 | `retire-reinstate` | RETIRE → REINSTATE（验证可复活语义） |
| 5 | `retire-then-dispose` | RETIRE → DISPOSE（验证 DISPOSED 终态锁——dispose dialog 输"处置"解锁） |
| 6 | `export-csv-xlsx` | seed 3 asset → 跳列表 → 点 export csv + 点 export xlsx，assert 下载响应 + filename + 内容首行表头 |
| 7 | `dashboard-loads` | 跳 `/dashboard` → assert 4 张图都渲染（type/status/holder/idle） + 无报错 boundary |

覆盖 7/10 transition kind。**未覆盖 3 个 kind**（CHECKOUT_EXTERNAL 与 INTERNAL 形同质 / RELOCATE / TRANSFER_HOLDER）— 靠 §3.2 单元 + API + CLI 三层覆盖。

### 5.2 playwright 引入与配置

**位置**：`frontend/e2e/`（与 `frontend/tests/` 平级，不污染 vitest 范围）

**依赖**：`pnpm --dir frontend add -D @playwright/test`

**配置**：`frontend/playwright.config.ts`（独立于 vitest 配置）

```ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,                      // 共享 db，避免并发冲突
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:8000",        // serve start --mode prod 单端口
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "uv run asset-hub serve start --mode prod --json",
    url: "http://127.0.0.1:8000/api/healthz",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,                        // 含 frontend build 时间
  },
});
```

**关键决定**：webServer 直接调 `serve start --mode prod`——这样 e2e 实际**也在测 serve 命令本身**（顺手覆盖 Phase 1 改动）。失败时报错也带 envelope 形态。

### 5.3 e2e seed / cleanup

每次 CI run：
- `ASSET_HUB_DATA_DIR=$(mktemp -d)` 临时目录，跑完销毁
- `frontend/e2e/global-setup.ts`：先 `execSync("uv run alembic upgrade head")` 在临时 db 建表，再 `execSync("uv run asset-hub type define --from frontend/e2e/fixtures/laptop.json")` seed 1 个类型。**`webServer` 启动的 `serve start --mode prod` 不会再跑 migrate**——把 db 准备职责完全集中在 global-setup
- `frontend/e2e/global-teardown.ts`：rm -rf $ASSET_HUB_DATA_DIR

**为什么不用 sqlite memory**：alembic migration + serve start 都假设文件 db；用临时目录最直接。

**为什么不放 GitHub Actions step**：alembic + seed 的逻辑放 global-setup 是为了让 **本地 dev `pnpm exec playwright test` 与 CI 共享同一启动路径**，避免漂移。

### 5.4 e2e 测试代码组织

```
frontend/e2e/
├── global-setup.ts          # alembic + seed type
├── global-teardown.ts       # rm tmpdir
├── fixtures/
│   ├── laptop.json          # seed 用 type 定义
│   └── photo-sample.png     # register 场景的附件
├── helpers/
│   ├── register-asset.ts    # 共用 helper：登记一台资产返回 id
│   └── assert-status.ts     # 共用 helper：assert chip label 匹配 5 态新文案
└── specs/
    ├── 01-register-and-list.spec.ts
    ├── 02-checkout-return-internal.spec.ts
    ├── 03-maintenance-cycle.spec.ts
    ├── 04-retire-reinstate.spec.ts
    ├── 05-retire-then-dispose.spec.ts
    ├── 06-export-csv-xlsx.spec.ts
    └── 07-dashboard-loads.spec.ts
```

每个 spec 文件单一场景；helpers 抽出 register / status assert 这两个跨场景操作。

### 5.5 GitHub Actions workflow

`.github/workflows/e2e.yml`：

```yaml
name: e2e
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with: { version: "0.5.x", enable-cache: true }
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - uses: pnpm/action-setup@v4
        with: { version: 9 }
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
          cache-dependency-path: frontend/pnpm-lock.yaml
      - run: uv sync
      - run: pnpm --dir frontend install --frozen-lockfile
      - run: pnpm --dir frontend exec playwright install --with-deps chromium
      # alembic upgrade + seed 由 frontend/e2e/global-setup.ts 统一处理（见 §5.3）
      - name: Run e2e
        run: pnpm --dir frontend exec playwright test
        env:
          ASSET_HUB_DATA_DIR: ${{ runner.temp }}/asset-hub-e2e-${{ github.run_id }}
      - if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-trace
          path: frontend/playwright-report/
          retention-days: 7
```

**触发**：PR + push to main。每次 PR 都跑，main 每次合并也跑（regression net）。

**runner**：ubuntu-latest（GitHub Actions 标准 + 价格友好）。e2e 在 Linux 跑**不等于** "Linux 真机部署烟测"——后者推 v1.1。e2e 是验证 functional flow，OS 兼容由 Windows 烟测 checklist + v1.1 Linux 真机烟测覆盖。

**预算**：单 run 4-7 分钟（3 min 依赖 + 1 min build + 2-3 min 7 spec）。

### 5.6 跨 phase 依赖

e2e 运行依赖前 3 phase 已落地：
- Phase 1 envelope：webServer 启动失败时报错形态对齐
- Phase 2 5 态文案：e2e helpers/assert-status.ts assert "闲置中/使用中/维修中/已退役/已处置"
- Phase 3 SKILL.md：e2e 命令调用复用 SKILL.md 命令速查同形态

### 5.7 Phase 4 commit 切分

```
test(e2e): playwright 安装 + 配置 + global-setup/teardown
test(e2e): 7 个 spec (register / checkout-return / maint / retire-reinstate / dispose / export / dashboard)
ci: GitHub Actions e2e workflow + ubuntu-latest + cache + trace artifact
```

### 5.8 Phase 4 验收

- [ ] 本地：`pnpm --dir frontend exec playwright test` 7 spec 全绿
- [ ] CI：PR 触发后 e2e workflow 在 GitHub Actions 跑通
- [ ] 故意 fail 一个 spec → trace artifact 上传成功
- [ ] webServer 配置实际启动 `serve start --mode prod` 并通过 `/api/healthz` 探活
- [ ] global-teardown 后 `$ASSET_HUB_DATA_DIR` 清空

## 6. 跨 phase 约束 + 风险与回滚

### 6.1 phase 顺序刚性约束

| 依赖关系 | 说明 |
|---|---|
| Phase 1 → Phase 3 | SKILL.md / references/envelope.md 引 envelope.py 实际形态 |
| Phase 2 → Phase 3 | references/transitions.md / SKILL.md 引 5 态文案表 |
| Phase 1 + 2 → Phase 4 | e2e webServer 启动报错走新 envelope；e2e helpers assert 5 态文案 |
| Phase 3 → Phase 4 | e2e fixtures 与 SKILL.md `常见任务流` 示例同源 |

phase 内部允许 atomic commit 切分；phase 间不可乱序。

### 6.2 与 hooks/约束的兼容

- **CLAUDE.md "后端任何 schema 改动都必须跑 `pnpm gen:api`"**：M3e 不动 backend schema → 不需要跑
- **auto memory "tsc -b 而非 tsc --noEmit"**：Phase 4 添加 playwright 不破坏前端 tsc -b 范围（playwright 用独立 tsconfig）
- **CLAUDE.md "frontend-design"**：Phase 2 5 态文案修订是配色/视觉中性改动；不动 design system token
- **commit message 全局规范**（Angular + 中文 subject + 不带 Co-Authored-By）：四个 phase commit 已遵循

### 6.3 风险清单

| # | 风险 | 等级 | 缓解 |
|---|---|---|---|
| R1 | envelope 重写后 12-18 个现有 CLI 测试 grep 改不全，silent regress | 中 | 改造期统一 grep 列出 case 清单；逐文件改 + 跑 `pytest tests/cli` 做 fail-list 兜底 |
| R2 | 5 态文案改动遗漏硬编码字面量（grep 没找全） | 低 | grep `"在用"` `"闲置"` 在 frontend/src + tests + frontend/e2e 三处全扫；CI 跑 vitest + e2e 双重兜底 |
| R3 | playwright e2e 在 ubuntu-latest 与本地 Windows / macOS 行为差异（字体渲染 / hit area / 中文 label 折行） | 中 | 视觉 diff 不进 e2e 断言；只 assert text content + element role |
| R4 | serve doctor 在 Windows / Linux / macOS 行为差异（`uv --version` 路径、端口探测、frontend/dist 大小写） | 中 | doctor 用 `subprocess.run([...], shell=False)` + `pathlib.Path` 跨平台；端口探测复用 `proc_mod.is_port_in_use`；CI 仅 ubuntu，Windows 留 Phase 4 完成后用户手测 |
| R5 | description optimization 推 v1.1，M3e 内 SKILL.md description 触发率未量化验证 | 低 | description 是人工校准的合理初值；v1.1 跑 5 iteration loop 校到最优；description 后续只增不删 trigger 类别（向后兼容） |
| R6 | references/ 拆分后 SKILL.md 主体 + 4 references 漂移 | 中 | references/transitions.md / envelope.md 头部加同源约定提示；M4 加 SKILL.md staleness 检查 helper（v1.1） |
| R7 | release-notes-v1.0.md 已知 gap 列表与 simplify-followups / followup-allocation 不对账 | 低 | 写时 grep 后两文件 `⏳ 待` / `🔴 暂不动` 标记交叉对账 |
| R8 | M3e PR 体量超出"docs+CI 主"预期（~50+ commit） | 低 | 单 PR 4 phase 约束；如某 phase 失控可追加内部子 commit 但不拆 PR |

### 6.4 回滚

**部分回滚**（phase 内）：phase commit 边界清晰 → 单 commit revert 即可。

**整 PR 回滚**（main 合后发现严重问题）：
- envelope 改动可单独 revert（前 3 phase 都依赖它，整体 revert）
- 5 态文案 / SKILL.md / e2e 互不依赖，可各自 revert

**v1.0 tag 后回滚**：用户人工 `git tag -d v1.0.0 && git push origin :v1.0.0` + main revert PR + 待修后再打 v1.0.0。tag 不进 PR 是这层缓冲的根源。

## 7. 验收总表 + ship 标准 + spec 落点 + followup 登记

### 7.1 全 phase 验收汇总

| Phase | 验收点 | 来源 |
|---|---|---|
| 1 | envelope.py 升级、serve doctor 落地、`pytest` + `ruff` clean、含新 envelope/doctor 测试、grep `render_json_envelope` / `_emit_*` 全消失 | §2.6 |
| 2 | 5 态新文案、`pnpm test`/`pytest` 全绿、新增 8 后端 + 1 前端 case、浏览器手测 list / dashboard / chip | §3.4 |
| 3 | SKILL.md 主体 ≤ 200 行、references/ 4 文件、deployment.md 命令可执行、README 路线图最新、release notes 已知 gap 与 followup 对账 | §4.6 |
| 4 | 本地 `playwright test` 7 spec 全绿、CI workflow 在 PR/push 跑通、failure trace 上传、webServer 走 `serve start --mode prod` | §5.8 |

### 7.2 v1.0 GA Ship 标准

合并 + tag 之间用户做的人工检查清单：

- [ ] 全部 4 phase 验收点 ✓
- [ ] CI e2e workflow 在 main 首跑绿
- [ ] Windows 烟测 checklist 全过（`docs/superpowers/release-notes-v1.0.md` 内）
- [ ] `uv run asset-hub serve doctor` 在干净环境全 ✓
- [ ] `uv run asset-hub --help` 命令清单与 SKILL.md 命令速查表一致（grep 对账）
- [ ] 浏览器手测：登记 + 派发归还 + 看板 + 导出 + 5 态 chip 文案

通过 → 用户告知 → Claude 执行 `git tag v1.0.0 && git push origin v1.0.0`。

### 7.3 spec 文件落点

- 路径：`docs/superpowers/specs/2026-05-09-m3e-skill-and-deploy-design.md`（即本文）
- 命名：`<日期>-m3e-<slug>-design.md`，slug = `skill-and-deploy`
- 撰写约束：CLAUDE.md "设计决策放在 docs/superpowers/specs/"

### 7.4 实施期 followup 登记预案

**`docs/superpowers/followup-allocation.md`** 在 M3e 落地后回填：
- 摘要表 M3e 行 ⏳ → ✅ 已完成
- 强搭车表新增（M2d 残 doctor 已闭环 / M2d K1 envelope 已闭环 / 5 态文案对齐 已闭环）

**`docs/superpowers/simplify-followups.md`** 新增 `§9 M3e 范围（2026-05-XX）`：
- K1 envelope 统一已闭环（commit ref）
- M2d serve doctor 已闭环（commit ref）
- 5 态文案对齐 已闭环
- e2e 7 spec + Actions 已闭环

**`docs/superpowers/release-notes-v1.0.md`** 已知 gap 章节登记 v1.1 候选：Linux 真机烟测 / Lighthouse a11y / SKILL.md description trigger eval / 多代日志轮转 / serve build 独立 / `--workers` / **envelope error 结构化升级 `{code, message, hint, fields_missing?}`（与 §T 同 PR）** / **`--help --json` 双模** / **`--fields` 字段掩码** / IllegalTransitionError 结构化 detail / A3 dialog 合并 / §S/§T/§U/§V/§W/§X/§Y/§Z

## 8. brainstorm 决策追踪表

| 决策点 | 选择 | 备注 |
|---|---|---|
| K1 envelope 统一形态 | A 主 envelope 升级 + serve 重写 | error → `{code, message}` 单一 schema |
| envelope code 命名 | B1 域异常 lowercase + serve.* 保留 dot | 自动 mapping 显式 dict |
| StateError code | `state_conflict` | 避与状态机 IllegalTransition 歧义 |
| e2e 场景集 | A 中额 5-7 条 | 7 spec 覆盖 7/10 transition + export + dashboard |
| M2d known gap 搭车 | 仅 serve doctor | 多代日志/serve build/--workers 推 v1.1 |
| 测试薄弱点优先级 | 5 态 filter 列表拼接 | 6 unit + 2 api + 1 frontend = 9 case |
| 5 态文案 | 全 3 字对齐（IDLE/IN_USE 改） | 闲置中/使用中/维修中/已退役/已处置 |
| PR 拆分 | 单 PR `feat/m3e-ga` | 4 phase commit 切分 |
| Phase 顺序 | C1 envelope → 5 态 → docs → e2e+CI | 文档基于稳态写 |
| release notes 形态 | 单 v1.0 集成 | git log 留中间细节 |
| v1.0 tag 动作 | PR merge + 用户检查 + 手动 tag | tag 不进 PR/plan |
| README 重写范围 | 全量重写 | v1.0 GA 主页面 |
| SKILL.md 形态 | A1 agent-native frontmatter | + references/ 4 文件 progressive disclosure |
| SKILL.md description | 平衡版（缩短 + 加语境锚） | 删冗余具象词；trigger eval 推 v1.1 |
| references/deploy.md vs docs/deployment.md | 后者 SoT 前者 pointer（如重复维护成本高） | 实施时拍板单源还是双源 |
| doctor 检查项数 | 7 项（uv/pnpm/Python/data dir/alembic/dist/ports） | 全跨平台；CI 仅 ubuntu，Windows 用户手测 |
| envelope 错误恢复建议处理 | M3e 通过 message 自承担；envelope 字段升级推 v1.1 | agent-native 检查清单 "code+message+hint" 第三项；与 §T 同 PR |
| `--help --json` / `--fields` | 推 v1.1 | agent-native 候选项；M3e 不引入（YAGNI） |
| references/ 各文件需带"何时读"指引 | 是 | skill-creator progressive disclosure 标准 |
