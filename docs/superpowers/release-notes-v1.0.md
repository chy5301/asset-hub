# v1.0 GA 发版升级指南

v1.0 GA 收口了 M3a–M3e 五个里程碑，在 M2d（基础 CRUD + 附件 + serve 框架）之上完整交付 5 态状态机、数据统计看板、CSV/XLSX 导出、时间线 UI、Agent CLI 接口及部署文档。本指南面向已运行 M2d 版本的主干用户，逐步说明升级路径、破坏性变更及回滚方式。

---

## 概览（v1.0 = M2d 之后所有里程碑）

| 里程碑 | 主线交付 | merge commit |
|---|---|---|
| M3a | 5 态状态机 + 10 transition + StateTransitionRecord 重构 + CLI 9 子命令 + 7 dialog | a360e04 + bc084e5 |
| M3b | /api/stats + 看板 4 图表 + ChartTokenProvider | c21ae55 + 98052dc |
| M3c | /api/export CSV/XLSX + ExportButton | a55beec + 5c5bab0 |
| M3d | timeline Group rail + 月份分段 + 派出类型染色 + 超长派发预警 + simplify §7 | 5320804 |
| M3e | SKILL.md + envelope 统一 + serve doctor + 5 态文案对齐 + Windows 部署文档 + playwright e2e CI + 烟测发现 3 fix（M1 baseline create_table / doctor shutil.which / e2e webServer 前台 uvicorn） | \<m3e-merge\>（实施期回填） |

---

## Breaking changes

以下变更要求完整执行升级步骤，**不可跳过任何环节**。

### 1. HTTP API transitions 端点重构（M3a）

旧端点已全部废除：

```
DELETE  POST /api/assets/{id}/checkout
DELETE  POST /api/assets/{id}/return
DELETE  PATCH /api/assets/{id}  (status 字段)
```

新统一入口：

```
POST /api/assets/{id}/transitions
Body: { "kind": "<transition_kind>", ... }
```

支持的 `kind` 值：`checkout` / `return` / `send_to_maintenance` / `recover` /
`retire` / `reinstate` / `dispose`。所有自定义脚本、Agent prompt 模板需同步更新。

### 2. 数据库 schema 单向变更（M3a migration）

- **drop** `checkout_records` 表（含全部历史记录）
- **drop** `Asset.current_checkout_id` 列
- **add** `state_transition_records` 表（承载完整状态变更历史）
- **add** `Asset.status` enum 新增 `DISPOSED` 终态

`alembic upgrade head` 执行后**数据不可回溯**，`alembic downgrade` 无法恢复已 drop 的 checkout 历史——升级前务必备份。

### 3. CLI envelope error 字段结构化（M3e）

旧格式（plain string）：

```json
{"success": false, "error": "asset not found", "data": null}
```

新格式（结构化对象）：

```json
{"success": false, "error": {"code": "not_found", "message": "asset not found"}, "data": null}
```

解析 `--json` 输出的脚本需将 `error` 从 `str` 改为 `dict`（读 `error["code"]` / `error["message"]`）。

### 4. 5 态文案对齐（M3e）

前端标签与导出列文案变更：

| 旧文案 | 新文案 |
|---|---|
| 在用 | 使用中 |
| 闲置 | 闲置中 |

**不影响** API 枚举值（`IN_USE` / `IDLE` 不变）；影响范围：Web GUI 状态标签、ExportButton 生成的 CSV/XLSX 列值。

---

## 升级前

> **重要**：M3a migration 含不可回溯的 `DROP TABLE`，升级前备份是强制要求。

1. 备份数据库：

   ```bash
   cp data/asset_hub.db data/asset_hub.db.$(date +%Y%m%d).bak
   ```

2. 备份附件目录：

   ```bash
   tar czf attachments-$(date +%Y%m%d).tgz data/attachments/
   ```

3. 如有自定义 dev 脚本或 CI 任务，确认已更新为调用新的 transitions 端点（见 Breaking change §1）。
4. 如有解析 `--json` 输出的脚本，确认已更新 error 字段读法（见 Breaking change §3）。

---

## 升级

```bash
# 1. 拉取代码（或切到 tag）
git pull
# 或：git fetch && git checkout v1.0.0

# 2. 同步后端依赖
uv sync

# 3. 同步前端依赖
pnpm --dir frontend install

# 4. 执行数据库迁移（含 drop checkout_records，单向不可回）
uv run alembic upgrade head

# 5. 验证升级后环境健康状态（7 项检查：uv / pnpm / Python / data dir / alembic head / dist / ports）
uv run asset-hub serve doctor

# 6. 重启服务
uv run asset-hub serve restart --mode prod
```

---

## 升级后验证

### 1. 自动化测试

```bash
uv run pytest                   # 后端全套，期望全绿
pnpm --dir frontend test --run  # 前端 vitest，期望全绿
uv run ruff check .             # 期望 clean
pnpm --dir frontend lint        # 期望 clean
```

### 2. CI e2e workflow

PR 与 main push 都会触发 GitHub Actions e2e workflow（ubuntu-latest，4–7 分钟）；v1.0.0 tag push 后也会跑——观察 Actions 页面是否全绿。若有失败，查看 playwright artifact 截图定位。

### 3. Windows 烟测 checklist

在本机 Windows 环境逐项手动验证：

- [ ] `register / list / show`（不是 get）
- [ ] `checkout / return` 闭环（CLI 平铺，不在 transition 子组下）
- [ ] `send-to-maintenance / recover` 维修闭环
- [ ] `retire / reinstate` 退役复活闭环
- [ ] `retire → dispose`（CLI 终态锁；CLI 用 `--yes` 跳过 prompt 确认；GUI dispose-alert-dialog 才有"输 '处置' 解锁"行为，CLI 无此层）
- [ ] CSV / XLSX 导出（GUI ExportButton 或 `GET /api/export?format=csv|xlsx&...`；CLI 无 export 顶层命令）
- [ ] dashboard `/dashboard` 加载 4 张图，状态分布显示新文案（使用中 / 闲置中）
- [ ] `serve doctor` 全 ✓（7 项均通过）
- [ ] `serve start / stop / status / restart / logs` 正常工作

---

## 烟测期发现并修复

M3e PR 推 origin 后烟测发现 3 个 v1.0 GA 阻塞/体验问题，已在本 PR 内修复：

- **fresh DB 部署 blocker**：M1 baseline migration 原本是空 stamp，新部署按 `docs/deployment.md` 跑 `alembic upgrade head` 在第 2 个 migration ALTER 不存在的 `asset_types` 表上失败。重写 baseline 加 `op.create_table` 全 5 表 + indexes + FK。
- **doctor `pnpm` Windows 假阳性**：subprocess 不读 PATHEXT，找不到 `pnpm.cmd` shim。`check_uv` / `check_pnpm` 改用 `shutil.which` 跨平台显式找 path 后再 spawn。
- **playwright e2e webServer 与 detach 模式不兼容**：`serve start --mode prod` 是 detach wrapper，spawn 后立即 exit，playwright 误判 server down。`webServer.command` 改为前台 `uvicorn`；workflow + `global-setup.ts` 加 `pnpm build` 步骤补偿（uvicorn 不自动 build）。生产 `serve start` 行为完全不变。

## 已知 gap（推 v1.1+）

以下条目已知但不阻塞 v1.0 GA，将在 v1.1 迭代中跟进：

- **Linux 真机烟测**：v1 用户场景仅限 Windows 单机；v1.1 补 Linux 验证
- **Lighthouse a11y 全站扫描 + 修复**：v1 单用户作者自用，暂无视障用户；v1.1 系统化补全
- **M2d 残留**：多代日志轮转 / `serve build` 独立子命令 / `--workers` flag（触发条件出现后跟进）
- **M3 残留**：A3 dialog 合并 / §S Toggle 视觉态 / §T `IllegalTransitionError.detail` 结构化 payload / §U KIND_META 跨文件合一 / §V `Settings.mode` 字段 / §W types/assets 风格统一 / §X dispose-dialog RHF / §Y `findOpenCheckout` 抽工具 / §Z `formatRelative` 小时级粒度
- **envelope error 深度结构化**：`{code, message}` → `{code, message, hint, fields_missing?, ...}`（v1.1 与 §T 同 PR）
- **`--help --json` 双模 / `--fields` 字段掩码**：v1.1，agent-native 检查清单候选项
- **SKILL.md description trigger eval**：v1.1 用 skill-creator 的 description optimization loop 跑 5 iteration
- **[Phase 1 followup]** CLI envelope `error.code = "cancelled"` 未在 spec inventory 正式化（`type_cmd.py:123` 引入，dry-run 后用户取消时使用，但 `envelope.py` 域异常主表未列）→ v1.1 把 `cancelled` 加入 spec §2.1 + envelope.md 主表 + 域异常映射
- **[Phase 1 followup]** `serve doctor check_alembic_head` 在 alembic 自身崩溃时 stderr 处理粗糙（直接吞 exception，不区分"alembic 命令坏"vs"迁移逻辑出错"）→ v1.1 区分两种失败走不同 fix_hint
- **[Phase 1 followup]** `serve doctor check_frontend_dist` 用相对路径假设 CWD = repo root（cwd 不是 repo root 时给假阳性 `dist_missing`）→ v1.1 用 importlib resolve repo root 或显式接受 `--repo-root` flag

---

## 回滚

若升级后发现严重问题，按以下步骤回滚：

```bash
# 1. 切回升级前的 commit（记录在升级前的 git log 里）
git checkout <pre-v1.0-commit>

# 2. 恢复数据库备份（alembic downgrade 无法恢复 drop 的 checkout_records 数据）
cp data/asset_hub.db.$(date +%Y%m%d).bak data/asset_hub.db

# 3. 同步回旧版依赖
uv sync
pnpm --dir frontend install

# 4. 重启
uv run asset-hub serve restart --mode prod
```

> **注意**：M3a migration 的 drop 操作不可通过 `alembic downgrade` 还原——必须使用备份文件覆盖。升级后在新版本产生的 `state_transition_records` 记录在回滚后将丢失，这是预期行为。
