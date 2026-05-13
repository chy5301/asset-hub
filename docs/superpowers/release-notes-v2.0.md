# v2.0.0 发版升级指南（草稿）

> ⏳ **状态**：草稿。v2.0.0 GA 待 PR-2（[#4](https://github.com/chy5301/asset-hub/pull/4)）merge 后由维护者打 tag。本 doc 内容稳定，merge commit / tag 日期合并后回填。

v2.0 GA 收口两大主线，由两个独立 PR 顺序合入 main 后发 `v2.0.0`：

1. **状态机扩展**（PR-1 BC，merge commit `b689148`）：5 态 → 6 态（加 `BROKEN` 故障态）；10 → 12 transition kind；引入 `keep` rule（解决 v1.0 "调用方不传字段就被无声清空"）；合并 `RELOCATE` + `TRANSFER_HOLDER` 为 `REASSIGN`；全 6 态两字文案对齐
2. **Agent-native 收口**（PR-2 A，merge commit `<待回填>`）：M3e Phase 1 三 followup 补丁；envelope error 深度结构化；`--help-json` agent 元数据导出；`--fields` 字段掩码；SKILL.md description trigger eval

本指南面向已运行 v1.0.0 的主干用户，逐步说明升级路径、breaking changes 全列表、回滚方式与已知 gap。

---

## 概览

| PR | 主题 | 合并 commit |
|---|---|---|
| PR-1 BC | 状态机焕新 + 文案重定 + CLI flag 标准化 | `b689148` (#3) |
| PR-2 A | Agent-native 收口（envelope / --help-json / --fields / description eval）| `<待回填>` (#4) |

---

## 升级路径

```bash
# 1. 备份（必须）
cp data/asset_hub.db data/asset_hub.db.v1.0.bak

# 2. 拉代码
git fetch && git checkout v2.0.0

# 3. 同步依赖
uv sync
pnpm --dir frontend install

# 4. 执行 migration（schema 单向不可回滚）
uv run alembic upgrade head

# 5. doctor 验证（v2.0 修复后的检查项 + agent-friendly fix_hint）
uv run asset-hub serve doctor --json

# 6. 重启
uv run asset-hub serve restart --mode prod
```

---

## Breaking changes 完整清单

### Schema 层（PR-1）

- `AssetStatus` 加 `BROKEN`
- `TransitionKind` 删 `RELOCATE` / `TRANSFER_HOLDER`，加 `REPORT_BROKEN` / `DECLARE_UNREPAIRABLE` / `DISMISS` / `REASSIGN`
- migration 把历史 `RELOCATE` / `TRANSFER_HOLDER` records 改写为 `REASSIGN`（作者无正式录入数据，**单向不可逆**）

### HTTP API 层（PR-1）

- `POST /api/assets/{id}/transitions` body.kind 旧值（`RELOCATE` / `TRANSFER_HOLDER`）现 422 ValidationError
- body 字段 `to_holder` / `to_location` 语义微变：部分 transition kind 从 `optional` rule（不传 = 清空）改为 `keep` rule（不传 = 保留）。"未传 vs 传 null" 现在严格区分
- API exception 响应体加 `code` / `hint?` / `fields_missing?` / `fields_invalid?` / `affected_resource_id?` **可选**顶层字段（PR-2，**向后兼容**：保留 `detail` 字段不变）

### HTTP API 层（PR-2）

- 4 个查询/写返回 endpoint 支持 `?fields=a,b,c` 字段掩码：
  - `GET /api/assets` / `GET /api/assets/{id}` / `POST /api/assets/{id}/transitions` / `GET /api/assets/{id}/transitions`
  - unknown 字段返 422 + `fields_invalid` + `hint` 列合法字段
  - **向后兼容**：不传 `?fields=` 时 response 行为 / OpenAPI schema / 前端 gen:api typed client 全不动（Option B 实现：保留 `response_model` + JSONResponse 仅在 filter 分支用）

### CLI 层（PR-1）

- 删 `asset relocate` / `asset transfer-holder` 子命令
- 加 4 个新子命令：`asset reassign` / `asset report-broken` / `asset declare-unrepairable` / `asset dismiss`
- 12 处 flag rename：统一为 `--to-holder` / `--to-location`（旧 flag 不再支持，CLI scripts 必须改）
- `asset dispose` 交互 prompt 文案 `"处置"` → `"注销"`

### CLI 层（PR-2）

- 14 asset 命令支持 `--fields a,b,c`（list / show / history + 11 transition 写命令）
  - register / update / delete / type / attachment / stats / serve 子命令**不**支持（spec 显式排除）
  - dry-run + `--fields` 组合时 dry-run 优先（preview 不被 filter）
- 所有 CLI 命令支持 `--help-json` flag 输出结构化 JSON 元数据（`{command, help, params, examples}`），agent introspect 用
- **行为级 breaking**：`asset-hub type delete <id>` 交互式取消的退出码 1 → 10（与 dry-run 同档信号化）。CLI shell wrapper 用 `case $?` 处理 cancel 的 script 需 1 行修改。影响面窄（仅 interactive TTY 模式，--json 模式不走此路径）

### Agent 调用行为差异（P2 breaking，PR-1）

v1.0 的 `optional` rule 与 v2.0 的 `keep` rule 是**行为级**breaking——agent 学过的"不传 = 清空"调用模式在 v2.0 部分反了：

| 命令调用 | v1.0 行为 | v2.0 行为 |
|---|---|---|
| `asset send-to-maintenance <id>`（不传 holder/location）| 清空 | **保留 current** |
| `asset recover <id>`（不传）| 清空 | **保留 current** |
| `asset retire <id>`（不传）| 清空 | **保留 current** |
| `asset reinstate <id>`（不传）| 清空 | **保留 current** |
| `asset checkout <id> --to-holder X`（不传 location）| location 清空 | **location 保留 current** |
| `asset return <id>` （不传 receiver/location）| 都清空 | holder 清空（`optional` 不变）；**location 保留** |

Agent 想清空 v2.0 字段必须 **explicit 传 `--to-holder ""` / `--to-location ""`**（空字符串约定 null）。SKILL.md Gotcha 段已显式列此差异。

### UI / 文案层（PR-1）

- 6 态中文文案全改（已有 5 态从三字 → 两字；新 `BROKEN` = "故障"）
- `DISPOSE` UI label / KIND_META label / GUI dispose dialog confirm phrase："处置" → "注销"
- 导出 CSV/XLSX 状态/transition kind 列值变（旧脚本按字符串匹配旧文案会断）

---

## SemVer 判定：v2.0.0

含 HTTP API 契约破坏 + CLI 子命令删除 + flag rename 12 处 + UI 文案 breaking，严格按 SemVer 标 MAJOR。`v2.0.0`。

---

## 回滚

```bash
git checkout v1.0.0
cp data/asset_hub.db.v1.0.bak data/asset_hub.db
uv sync && pnpm --dir frontend install
uv run asset-hub serve restart --mode prod
```

**不可回滚的数据**：

- v2 期间产生的 `BROKEN` 状态资产
- v2 期间产生的 `REPORT_BROKEN` / `DECLARE_UNREPAIRABLE` / `DISMISS` / `REASSIGN` transition records
- migration 改写 v1 `RELOCATE` / `TRANSFER_HOLDER` → `REASSIGN`（作者无正式录入数据，故 OK）

---

## 已知 gap / v2.x 后续

### Phase 5 description eval：1-pass 分析式

正式 5-iter A/B test 需在 host Claude Code 跑 `skill-creator/scripts/run_loop.py`（依赖 `claude -p` 子进程并行评估），本 PR-2 在 background subagent 环境受限，降级到 **1-pass 分析式优化**。已记录在 `docs/superpowers/specs/2026-05-10-v2.0-description-eval.md`。

baseline → 优化版主要改动：加"实物资产 + 硬件类型"消除 web image asset 歧义；口语化触发词（坏了 / 修不好 / 换工位）；显式 pushy 句对抗 under-trigger；"不适用于" 显式黑名单。主观 hit rate 估算从 ~11/15 → ~15/15（subjective）。

**v2.x 跟踪项**：在 host Claude Code 环境跑一次 formal 5-iter eval 验证。

### Phase 3 typer 私有 API 依赖

`--help-json` 实现走 Option D（monkeypatch `typer.main.get_command` + `typer.testing._get_command` 注入 Click flag）。`typer.testing._get_command` 是私有 API。

**缓解**：`pyproject.toml` typer pin 加 `<0.30` 上限触发主动 revisit。**v2.x 跟踪项**：在某次 typer 升级时考察更稳健的 Click 注入方案（如 Click 中间件 / Typer plugin hook）。

### PR-1 visual smoke 衍生 minor

- Dashboard / 列表 filter toggle 文案不统一（cosmetic）
- `asset-hub serve stop` 不清外部端口占用（PR-1 visual smoke 发现，PR-2 scope 外）
- asset-header.test.tsx 时间敏感 flaky（前端，main 也 fail，与 PR-1/PR-2 无关）

详见 [`followup-allocation.md` v2.0 PR-1 衍生 minor 项](./followup-allocation.md)。

### PR-1 simplify pass 衍生 minor

dialog test wrapper 重复 / `find_open_checkout_id` 2 查询合并 / migration UPDATE 全表扫描 / `useTransitionsQuery` 无分页等——M4 polish 期或独立 PR 处理。

---

## 路线图位置

| 里程碑 | 主线 | 状态 |
|---|---|---|
| ✅ v1.0.0 | M1-M3e 全部 | 已完成 2026-05-09 |
| ✅ v2.0.0 | 状态机扩展 + agent-native | 本 release（草稿，等 PR-2 merge）|
| ⏳ v2.x | CLI / SKILL.md 持续打磨、formal description eval、typer 注入方案重审 | 规划中 |
| ⏳ M4 | UI 视觉打磨 + A3 dialog 合并 + 配色重设计 | 规划中 |
| ⏳ M5 | People 实体化（spec §14.4）| 规划中 |

---

## 验证 checklist（升级后跑）

- [ ] `uv run alembic current` 显示 v2.0 head
- [ ] `uv run asset-hub serve doctor --json` 6/7 项 ok=true（仅缺 frontend/dist 在未 build 时可接受）
- [ ] `uv run asset-hub asset list --help-json` 输出结构化 JSON
- [ ] `uv run asset-hub asset list --fields id,name --json` 仅含 id/name 字段
- [ ] GUI dispose 资产路径文案显示 "注销"
- [ ] BROKEN 状态资产的 dialog 全 5 按钮（report-broken / declare-unrepairable / dismiss / repair / retire）按 transition 矩阵显示

---

## 致谢

PR-1 BC + PR-2 A 实施由 Claude Code (Opus 4.7) 在 superpowers:subagent-driven-development workflow 下完成，单元/集成/契约测套 582 passed (vs v1.0 baseline 569，+13 新)。
