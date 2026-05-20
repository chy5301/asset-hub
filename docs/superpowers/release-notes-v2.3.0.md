# v2.3.0 发版升级指南

> 发布日期：2026-05-20
> 闭环 [issue #24](https://github.com/chy5301/asset-hub/issues/24)：新增 `asset undo` 元命令；MINOR bump（新功能、向后兼容）。

## 概览

v2.3.0 在 v2.2.1 patch 基础上新增 `asset-hub asset undo <id>` 元命令，用于无痕撤销资产最后一条流转记录。元操作绕过状态机：物理删除最后一条 transition + 重置 asset 三字段（status/holder/location）到该 transition 的 `from_*`。Agent / 人类误操作（如手滑 checkout、误手 dispose）从此可以单步回退，而不必走"反向 transition + 历史多两条脚印"的旧路径。

## 升级路径

另一台设备直接：

```bash
git fetch --tags
git checkout v2.3.0
uv sync
# 无 db migration / 前端构建产物 / 配置文件变化
uv run asset-hub serve restart --mode prod   # 已起服务的话
```

无需 `uv run alembic upgrade head`（无 schema 变化），无需 `pnpm install` / `pnpm build`（前端无改动）。

## Breaking changes

**无**。

- DB schema 不变
- API contract 不变（无新增 endpoint）
- 前端不变
- 既有 12 种 transition 行为不变
- envelope error code 集合不变

新功能完全增量。

## 改动详情

### #24 新增 `asset undo` 元命令（PR #25）

CLI 入口：

```bash
asset undo <asset_id> [--dry-run] [--fields ...] [--json]
```

**行为：**

- 物理删除该资产最后一条 transition（按 `created_at DESC LIMIT 1`），重置 `Asset.status` / `Asset.holder` / `Asset.location` 到该 transition 的 `from_*`，并把 `Asset.updated_at` 推到 now
- **不**走 `validate_transition` / 状态机；元操作，与 12 种 transition kind 解耦
- DB 零脚印（历史里看不出曾经撤过）；service 层 `logger.info` 留运行日志做事后追溯（`serve logs --tail` 可查 `undo transition asset_id=... record_id=... kind=...`）
- **DISPOSE 也可被 undo**：v1 工具无外部合规约束，元操作不受状态机终态约束
- `--dry-run` 输出 `{would_undo: <被删 transition>, would_restore: {status, holder, location}}`，exit 10，不改 DB
- 错误码：UUID 非法 → `validation` exit 2；asset 不存在 → `not_found` exit 3；asset 存在但无 transition → `state_conflict` exit 1（hint 引导用户用 `asset delete`）

**`closes_transition_id` 副作用：**

- 删 `RETURN` / `DISMISS` 后，原 `CHECKOUT_*` 自然被 `find_open_checkout_id` 重新认作 OPEN（恢复派出状态）
- 删 `CHECKOUT_*` 本身：它不闭合任何记录，无悬挂
- 删 `REPORT_BROKEN`：原 `CHECKOUT_*` 仍保持 OPEN（`REPORT_BROKEN` 本来就不闭合 CHECKOUT，因 IN_USE / BROKEN 都属 `PERSISTED_CHECKOUT_STATES`）

**与反向 transition 的语义差异：**

| 维度 | `undo` | 反向 transition（如 `return` 反 `checkout`） |
|---|---|---|
| 历史记录 | 零脚印（物理删除）| 多一条记录 |
| 语义 | "我没派发，只是手滑" | "派出后归还" |
| 适用 | 误操作回退 | 真实业务往返 |
| 终态 DISPOSE | 可撤 | 无反向 transition，无法救回 |

**实现关键点：**

- service 层在 `delete` / `commit` 之前 `TransitionRead.model_validate(last)` 快照为 DTO 返回，避免后续访问 detached ORM 实例触发 lazy-load
- 元操作不复用 `record_transition` 路径，直接 `repo.delete(last)` + 三字段重置
- CLI dry-run 走 `tx_svc.repo.find_last(uid)` 而非 `undo_last_transition`，确保预览不改 DB

### 配套文档

- `SKILL.md` 命令速查 transition 段加 `asset undo` 一行；新增 `## 常见任务流` → `### 撤销最后一条流转记录（手滑回退）`
- `references/transitions.md` 底部加 §undo（元操作，不在 12 kind 内）

### 测试覆盖补全（PR #26）

PR #25 终审遗留的 3 个测试覆盖缺口在 PR #26 中补齐（test-only follow-up，无实现改动）：

- 多步连续 undo 链路（`checkout → return → undo → undo`）
- `REPORT_BROKEN` undo（验证不闭合 CHECKOUT 的特殊语义在 undo 路径也成立）
- `DECLARE_UNREPAIRABLE` undo（回 MAINTENANCE，keep holder/location）

## 测试覆盖

- `tests/unit/test_transition_undo.py`：15 用例（3 repo + 4 happy + 5 edge/error + 3 follow-up 补全）
- `tests/cli/test_asset_undo_cmd.py`：6 用例（成功 / dry-run 含 DB 不变性验证 / 非法 UUID / 不存在 asset / 无 transition / fields 过滤）
- 后端全测 **692 passed / 1 skipped**
- 前端 / e2e 无影响

15 条手动烟测（主路径 / 错误路径 / DISPOSE undo 路径）全部通过；DISPOSE → undo → RETIRED 闭合 Q1=B 设计决策（spec §3）。

## 回滚

```bash
git fetch --tags
git checkout v2.2.1
uv sync
uv run asset-hub serve restart --mode prod
```

无数据变更，回滚安全。已经用过 `asset undo` 的资产在 v2.2.1 上**不会**异常——撤销后的 asset 状态本来就是合法状态机状态，回滚不影响数据完整性。

## SemVer

MINOR = **v2.3.0**。新增 CLI 命令 + service 方法，向后兼容，无 schema / API / contract 变化。

## 来源

- GitHub issue [#24](https://github.com/chy5301/asset-hub/issues/24)（CLOSED via PR #25）
- Spec: `docs/superpowers/specs/2026-05-20-issue24-asset-undo-design.md`
- Plan: `docs/superpowers/plans/2026-05-20-issue24-asset-undo.md`
- PRs: [#25](https://github.com/chy5301/asset-hub/pull/25) 主功能、[#26](https://github.com/chy5301/asset-hub/pull/26) 测试覆盖补全
