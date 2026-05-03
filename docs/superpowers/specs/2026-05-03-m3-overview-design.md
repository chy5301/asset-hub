# M3 总览设计文档

- **日期**：2026-05-03
- **状态**：初稿，待实施
- **作者**：conghaoyangbobby@gmail.com（与 Claude 协同 brainstorm）
- **范围**：M3 跨子里程碑总览（子里程碑划分 + 状态机模型 + 跨子里程碑约束）。各子里程碑细节留给独立 spec。

## 0. 背景

M2 已完成全部 7 个子里程碑（M2a → M2b → M2c-1 → M2c-2 → M2c-3 → M2d → M2c-4 → M2 视觉收尾），v1 资产管理主线流程基本就位。M3 是 v1.0 GA 前的最后一组工作，包含状态机基建、看板、导出、timeline 视觉重构、SKILL.md 与部署。

主 spec [`2026-04-15-asset-hub-design.md`](./2026-04-15-asset-hub-design.md) §11 把 M3 列为单行（`看板 4 图 + /api/stats；CSV/XLSX 导出；SKILL.md 完善；§14.1 派出类型扩展；§14.6 audit 化；§14.7 状态枚举完善；基础测试覆盖；README + 部署文档`），但实际跨多个相互依赖的子系统，单 spec → 单 plan → 单实施周期不可行——M2 的拆分经验（7 子里程碑各自独立 PR）适用于 M3。本文是 M3 总览，覆盖：

- 子里程碑划分与顺序（§1）
- 状态机模型（M3a 核心，影响所有子里程碑）（§2）
- 子里程碑边界承诺（每个包什么 / 不包什么）（§3）
- 跨子里程碑约束（数据迁移 / API 演进 / 测试基建时序 / K1 envelope 时机）（§4）
- 风险与回滚（§5）

## 1. 子里程碑划分与顺序

**M3a → M3b → M3c → M3d → M3e**（串行）：

| 子里程碑 | 主线 | 强搭车 follow-up |
|---|---|---|
| **M3a** · 状态机基建 | §14.6 audit 化 + §14.7 状态枚举（5 态）+ §14.1 派出类型 + §14.3 IDLE location 独立 action | smoketest B1（被 §14.6 覆盖）/ simplify C1（双层防御统一）/ §J / §L 实施期顺手 |
| **M3b** · 看板 + /api/stats | 4 张图（类型 / 状态 / 保管人 Top N / 闲置时长 Top N）+ 状态分布按 5 态 | C3（detail DTO 补 type_name）/ D1（generated schema alias）/ H4（unwrap 签名抽 OpenapiFetchResult） |
| **M3c** · 导出 | CSV / XLSX `/api/export` + `asset-hub export` CLI + 按当前筛选透传 | — |
| **M3d** · timeline 视觉重构 + M2 视觉收尾扫尾 | §14.8（时间渐隐 + 派出类型染色 + 超长派发预警）+ timeline 接管 10 个 transition kind 视觉 | simplify §7（types motion / h1 type scale / attachment transition） |
| **M3e** · SKILL.md + 部署 + 测试基建 | SKILL.md 完善 / Linux 真机烟测（M2d 附录 B 残留）/ Windows 部署文档 / playwright e2e 烟测脚本 / 补齐已知薄弱点 | **K1 envelope 统一（HIGH 优先级，与 SKILL.md 同 PR）** |

**顺序理由**：
- M3a 是状态机大重构，是 M3d timeline 染色（依赖派出类型）+ M3b 看板状态分布（依赖 5 态）的前置条件；先做最干净
- M3b 看板与 M3c 导出工程上无依赖，但单人项目不并行（评审/合并冲突反而麻烦），按规模递减串行
- M3d 必须在 M3a 之后（派出类型染色依赖 §14.1）
- M3e 必须最后——CLI 在 M3a/M3b/M3c 都会扩，提前写 SKILL.md 会反复改

**brainstorm 决策追踪**：
- 决策 1（People 实体化是否提前到 M3a）：**B 坚持 M5**——M3a 已经够大，加 People migration + dialog typeahead 改造会让 M3a 翻倍
- 决策 2（M3e 测试基建口径）：**D = playwright e2e 烟测脚本 + 补齐薄弱点**——v1.0 GA 需要 CI 跑的回归脚本兜底，不只是手动 playwright MCP

## 2. 状态机模型（M3a 核心）

### 2.1 状态枚举（5 态）

| status | 中文文案 | 含义 | 可派发 | 可 REINSTATE | 列表默认显示 |
|---|---|---|---|---|---|
| `IDLE` | 闲置 | 在库可派发 | ✓ | — | ✓ |
| `IN_USE` | 在用 | 已派出（kind 区分组内/对外） | ✗ | — | ✓ |
| `MAINTENANCE` | 维修中 | 维修中，不可派发 | ✗ | — | ✓ |
| `RETIRED` | 已退役 | 暂时退役（备件 / 转借 / 暂停服役，可复活） | ✗ | ✓ | ✗（toggle 显示） |
| `DISPOSED` | 已处置 | 彻底处置（卖 / 捐 / 销毁，终态） | ✗ | ✗ | ✗（toggle 显示） |

**M3a 子 spec 修订（2026-05-03）**：5 态文案最终为 IDLE→闲置 / IN_USE→在用 / MAINTENANCE→维修中 / RETIRED→已退役 / DISPOSED→已处置。修订理由：
- IDLE "在库" → "闲置"——v1 资产位置有家/办公室/仓库多种，"在库"暗示物理仓库；"闲置"中性表达"未投入使用"
- IN_USE "派发中" → "在用"——"派发中"过于偏向派发动作，忽略 CHECKOUT_EXTERNAL（出借）；"在用" 中性，覆盖派发+出借+任何使用场景
- MAINTENANCE "维修中"（未变）
- RETIRED "已退役"（未变）
- DISPOSED "已处置"（未变）

**主 spec §14 顶部 ⚠️ 文案约定修订**：
- `RETIRED` 中文文案 → **"已退役"**
- `DISPOSED` 中文文案 → **"已处置"**
- 旧约定"不用'报废'"延续：`SCRAPPED` 不引入；"已处置"中性覆盖卖 / 捐 / 销毁全场景

**列表筛选**：
- 默认 `WHERE status NOT IN ('RETIRED', 'DISPOSED')`
- toggle "显示已退役" + toggle "显示已处置"（独立或合并 UI 由 M3a 实施期定）

**与 §14.7 候选 A/B/C 的关系**：
- 候选 A（拆 RETIRED + ARCHIVED）/ 候选 B（RETIRED 兼任归档）/ 候选 C（保留单 RETIRED）—— 本文采用**候选 A 的拆分思路 + DISPOSED 命名**（避免 ARCHIVED 的"数据归档"语义混淆"物理处置"）；同时 RETIRED 保留"暂时退役（可复活）"语义

### 2.2 Transition kind 值域（10 个）

| # | kind | from → to | 备注 |
|---|---|---|---|
| 1 | `CHECKOUT_INTERNAL` | IDLE → IN_USE | 组内派发；设 holder + location |
| 2 | `CHECKOUT_EXTERNAL` | IDLE → IN_USE | 向外出借；设 holder + location |
| 3 | `RETURN` | IN_USE → IDLE | 归还（kind 跟随对应 OPEN checkout 的 kind）；可改 holder + location（M2d 已落 `return_location` / `return_receiver` 字段映射到 `to_location` / `to_holder`） |
| 4 | `SEND_TO_MAINTENANCE` | IDLE → MAINTENANCE | 送修；可改 holder + location |
| 5 | `RECOVER_FROM_MAINTENANCE` | MAINTENANCE → IDLE | 修好回库；可改 holder + location |
| 6 | `RETIRE` | IDLE / MAINTENANCE → RETIRED | 暂时退役（可复活）；可改 holder + location |
| 7 | `REINSTATE` | RETIRED → IDLE | 仅 RETIRED 可 → IDLE；可改 holder + location |
| 8 | `DISPOSE` | RETIRED / MAINTENANCE → DISPOSED | 终态；清 holder + location；IDLE 不能直接 DISPOSE |
| 9 | `RELOCATE` | IDLE / IN_USE / MAINTENANCE / RETIRED → 同 status | 仅 location 变；DISPOSED 排除 |
| 10 | `TRANSFER_HOLDER` | IDLE / IN_USE / MAINTENANCE / RETIRED → 同 status | holder（± location）变；DISPOSED 排除 |

**关键边界拍板**（brainstorm Q1-Q5 + Q1=C + Q2=是）：
- **归还不按 kind 拆**（单一 RETURN，kind 跟随对应 OPEN checkout）—— Q1=A
- **IN_USE → MAINTENANCE 直跳走两步显式**（dialog 提示"将先记 RETURN 再 SEND_TO_MAINTENANCE"，service 写两条 record）—— Q2=C
- **MAINTENANCE → RETIRED 允许**（复用 RETIRE kind，不爆炸）—— Q3=A
- **IN_USE 期间 holder/location 变更算独立 transition**（TRANSFER_HOLDER）—— Q4=A
- **RELOCATE 走 StateTransitionRecord 单表**（不另开 LocationChangeRecord 表）—— Q5=A
- **holder 字段在所有非终态都可有值**（Q1=C）：IDLE 仓管 / IN_USE 派发对象 / MAINTENANCE 维修联系人 / RETIRED 备件库管理员 / DISPOSED 无
- **M3a 子 spec 修订（2026-05-03）**：RETURN 后 `asset.holder = to_holder`（不再清空）—— `to_holder` NULL 表示无人值守仓库；非 NULL 表示归还接收人 / 仓管，他成为新 holder。修订 M2d `CheckoutService.return_()` 强制清 holder 行为，对齐 Q1=C 决议。
- **MAINTENANCE 在 RELOCATE / TRANSFER_HOLDER 合法 from 内**（Q2=是）：维修台搬迁 / 维修联系人变更是真实场景；禁止会逼用户走假动作污染 timeline

### 2.3 数据模型：StateTransitionRecord（激进合并方案）

**brainstorm 决策 §2.3 = A 激进合并**：删 CheckoutRecord，所有 transition 都进单一 StateTransitionRecord 宽表。

```python
class TransitionKind(StrEnum):
    CHECKOUT_INTERNAL = "CHECKOUT_INTERNAL"
    CHECKOUT_EXTERNAL = "CHECKOUT_EXTERNAL"
    RETURN = "RETURN"
    SEND_TO_MAINTENANCE = "SEND_TO_MAINTENANCE"
    RECOVER_FROM_MAINTENANCE = "RECOVER_FROM_MAINTENANCE"
    RETIRE = "RETIRE"
    REINSTATE = "REINSTATE"
    DISPOSE = "DISPOSE"
    RELOCATE = "RELOCATE"
    TRANSFER_HOLDER = "TRANSFER_HOLDER"


class StateTransitionRecord(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    asset_id: UUID = Field(foreign_key="asset.id")
    kind: TransitionKind
    from_status: AssetStatus       # M3a 修订：NOT NULL（按状态机定义反推）
    to_status: AssetStatus         # 同上
    from_holder: str | None
    to_holder: str | None
    from_location: str | None
    to_location: str | None
    note: str | None
    created_at: datetime
    # 派发/归还专用扩展字段
    due_at: datetime | None              # 仅 CHECKOUT_* 用：期望归还时间
    closes_transition_id: UUID | None    # 仅 RETURN 用：本次归还关闭的 CHECKOUT_* 行 id
```

**M3a 子 spec 修订（2026-05-03）**：

- **删除 `actor: str | None` 字段**——YAGNI。v1 单用户场景无来源区分需求；M5 People 实体化时再加（届时为 FK to Person，字符串字段反正要被替换）
- `from_status` / `to_status` 改 NOT NULL（M3a 后所有新行都有值；旧 CheckoutRecord 不迁移）

**理由**：
1. asset-hub 不是高并发 OLTP，宽表 NULL 字段开销可忽略
2. timeline 是核心 UX（详情页主区），单表 query 实现/优化最简单
3. service 层只暴露 `record_transition(kind, ...)` 一个接口，避免双层防御争议（直接闭环 simplify C1）
4. **M3a 子 spec 修订（2026-05-03）**：旧"M2a/M2d 已落 `return_location` / `return_receiver` 字段映射到 `to_location` / `to_holder`，零语义损失"段作废——M3a 不迁移历史测试数据，PR-1 合并前用户手动清空 db；migration 仅 schema 变更，旧字段映射承诺不再适用。
5. **M3a 子 spec 修订（2026-05-03）**：旧"alembic migration 一次性把 checkout_record → state_transition_record 数据搬过来"段作废——M3a 不做数据迁移，migration 仅 schema 变更（add `DISPOSED` enum / create `state_transition_records` / drop `checkout_records` / drop `Asset.current_checkout_id`），PR-1 合并前手动清空测试数据库重建。

**Service 层签名**（M3a 子 spec 已细化，签名见 [`2026-05-03-m3a-state-machine-design.md`](./2026-05-03-m3a-state-machine-design.md) §3.1）：

```python
def record_transition(
    asset_id: UUID,
    kind: TransitionKind,
    *,
    to_holder: str | None = None,
    to_location: str | None = None,
    note: str | None = None,
    due_at: datetime | None = None,  # 仅 CHECKOUT_* 用
) -> StateTransitionRecord: ...
```

**M3a 子 spec 修订（2026-05-03）**：删除 `actor` 参数（model 字段已删）。

**状态机校验层**（合法 from/to 矩阵）：service 层内的纯函数 `validate_transition(current_status, kind, to_holder, to_location)`，按 §2.2 表强制校验，违法抛 `IllegalTransitionError` → **router 409 Conflict**（M3a 子 spec 修订：从原 422 改 409，与 ConflictError 同语义类；详见 M3a spec §2.7）。

## 3. 子里程碑边界承诺

### M3a · 状态机基建

**包**（M3a 子 spec 修订（2026-05-03）：详见 [`2026-05-03-m3a-state-machine-design.md`](./2026-05-03-m3a-state-machine-design.md) §1.1；此处仅保留摘要）：
- alembic schema migration（**仅 schema 变更，不迁移测试数据**；PR-1 合并前用户手动清空 db）：
  1. `Asset.status` enum 加 `DISPOSED`（5 态）
  2. 建 `state_transition_records` 表
  3. drop 旧 `checkout_records` 表（PR-1 同 migration 直接删除，不留 1 release 兜底）
  4. drop `Asset.current_checkout_id` 字段（不再反规范化）
- StateTransitionRecord 模型 + service `record_transition()` + 状态机校验层（simplify C1 双层防御统一在此层）
- 后端 API 改造：废 `POST /api/assets/{id}/checkout` / `/return` / 散点 PATCH status，统一为 `POST /api/assets/{id}/transitions { kind, ... }`（**不向后兼容**——见 §4.2）
- CLI 改造：9 个新子命令覆盖 10 个 transition kind（`asset checkout --kind internal|external` 合并 CHECKOUT_INTERNAL/EXTERNAL；其余 `asset return / send-to-maintenance / recover / retire / reinstate / dispose / relocate / transfer-holder` 各对一个 kind）
- 前端改造：7 个 dialog 组件（6 独立 + 1 SimpleTransitionDialog 共用，按 status token 染色 + AlertDialog/Dialog 按可逆性区分）+ 列表 2 个 status-token Toggle chip（替代普通 checkbox） + 新增 `--status-disposed` OKLCH token pair
- 5 态文案修订（在用 / 闲置 / 维修中 / 已退役 / 已处置）；frontend `status-labels.ts` 同步
- **M3a PR-1 修订 RETURN 后 asset.holder/location 行为**：跟随 to_holder/to_location，不强制清空（修订 M2d `CheckoutService.return_()` 行为）
- timeline 视觉**沿用 M2c-2 当前形态**（仅 transition 类型扩展，不做 §14.8 重构）

**不包**：§14.8 timeline 视觉重构（→ M3d）；§14.4 People 实体化（→ M5）；看板 / 导出 / SKILL.md；ARCHIVED 状态（已被 RETIRED+DISPOSED 二分覆盖）

### M3b · 看板 + /api/stats

**包**：
- 后端 `GET /api/stats` 单端点 4 段聚合（类型分布 / 状态分布 5 态 / 保管人 Top N / 闲置时长 Top N）
- 前端 `/dashboard` 路由 + 4 张图表
- 前端图表栈选型（Tremor / Recharts / shadcn-ui chart / nivo）—— 子 spec brainstorm
- 强搭车：C3（detail DTO 补 type_name）/ D1（generated schema alias 层）/ H4（unwrap 签名抽 OpenapiFetchResult）

**不包**：时间序列 / 趋势图（v2+）；可配置看板 / 自定义聚合（v2+）

### M3c · 导出

**包**：
- 后端 `GET /api/export?status=&type=&holder=&q=&format=csv|xlsx` 复用列表 filter
- XLSX：openpyxl，列宽自适应、冻结首行、状态色条件格式（5 态色）
- CLI `asset-hub export` 复用 service
- 前端列表"导出"按钮把当前 filter 序列化进 query string

**不包**：派出历史 / transition 历史导出（暂不做）；自定义列选择（v2+）

### M3d · timeline 视觉重构 + M2 视觉收尾扫尾

**包**：
- §14.8 完整：时间渐隐（≤90d 100% / ≤180d 80% / 更早 60%）+ 派出类型染色（CHECKOUT_INTERNAL 蓝 / CHECKOUT_EXTERNAL 琥珀，pill + ring 双层信号）+ 超长派发预警（> 90 天 Clock icon + text-destructive + "派发 N 天"）
- timeline 接管 10 个 transition kind 的视觉表达（每个 kind 配 icon + 文案模板）
- simplify §7：types motion 决议 / 页面 h1 type scale token / attachment transition prop fix

**不包**：看板视觉（M3b 已交付）

### M3e · SKILL.md + 部署 + 测试基建

**包**：
- SKILL.md 完善：含 5 态 + 10 transition + JSON 信封统一描述 + 常见任务流（登记 → 派发 → 归还 / 送修 / 退役 / 处置 + 导出）
- **K1 envelope 统一（HIGH）**：serve 命令的 envelope 与项目 CLI envelope 在 SKILL.md 同 PR 统一为单一契约
- Linux 真机烟测（M2d 附录 B 残留）
- Windows 部署文档 + README 更新（含 v1.0 release notes）
- **playwright e2e 烟测脚本**：场景集（登记 → 派发 → 归还 → 送修 → 修好 → 退役 → 重启用 → 处置 + 导出 + 看板加载），CI 跑
- **测试薄弱点补齐**：覆盖率扫，重点补 §14.6 audit / 派出类型 / 各 transition / 5 态 filter

**不包**：性能 / 压力测试（v1+）；多租户 / 多用户场景（v2+）

## 4. 跨子里程碑约束

### 4.1 数据迁移与回滚

**M3a 子 spec 修订（2026-05-03）**：原"一次性完成 schema 变更 + 数据搬迁 + 1 release 兜底回滚"段作废，整段重写为：

- PR-1 合并前手动清空测试数据（`rm data/asset_hub.db` + 清空 attachments）
- alembic migration 仅 schema 变更（add `DISPOSED` enum / create `state_transition_records` / drop `checkout_records` / drop `Asset.current_checkout_id`）
- alembic downgrade 自动反向，但 db 已清空，无现实回滚意义
- M3a PR-1 即终局，**不留 1 release 兜底**
- 单子里程碑（M3b/c/d/e）合并后发现问题 → 单 PR revert 即可

### 4.2 API 演进策略

- **M3a 不向后兼容**：直接废旧 endpoint，统一新端点 `POST /api/assets/{id}/transitions`。CLI/Web 都是单仓库内可控，前后端同 PR 切换；外部消费者（Agent SKILL.md）尚未 GA，无破坏面
- **OpenAPI schema 同步**：M3a 后端改完必跑 `pnpm --dir frontend gen:api`（CLAUDE.md 已硬约束）
- **CLI envelope 统一（K1）**：M3e 在 SKILL.md 同 PR 落地；M3a/b/c/d 期间 CLI 子命令**遵循当前 envelope**，M3e 统一时**不破坏 contract** 只 polish 字段命名/error 形态

### 4.3 测试基建时序

- **每个子里程碑自带 TDD**（service / CLI / API / 前端按 CLAUDE.md 测试分层），不变
- **playwright e2e 烟测脚本**：场景集要求 M3a 状态机就位 + M3b 看板就位 + M3c 导出就位才能完整跑——所以 e2e **只能 M3e 写**，不能在 M3a 写部分场景再 M3e 补全
- **playwright MCP 烟测**（不进 CI）保留：M3a/b/c/d 实施期作为子里程碑内的视觉验证；M3e 的 e2e 脚本是另一层（CI 跑、不依赖手动）

### 4.4 K1 envelope 统一时机

- **M3a/b/c/d 期间不动 envelope**（仅消费当前 contract）
- **M3e SKILL.md 同 PR 一次扫所有 CLI**（含 serve 子命令 + 9 个 transitions 子命令 + export + stats），统一字段命名 / error 形态 / exit code 语义
- **理由**：K1 是文档驱动的 polish（SKILL.md 要把 envelope 文档化，正好统一），分散到各子里程碑会反复触碰 envelope 反复 review

### 4.5 强搭车 follow-up 时机锁定

| follow-up | 子里程碑 | 实施时机 |
|---|---|---|
| simplify C1（双层防御统一） | M3a | 状态机校验层就位时（§2.3 A 方案直接闭环） |
| simplify C3（detail DTO 补 type_name） | M3b | detail DTO 改造时（顺手） |
| simplify D1（generated schema alias） | M3b | openapi 客户端选型决策时 |
| simplify H4（unwrap 签名抽 OpenapiFetchResult） | M3b | 与 D1 同 PR |
| simplify K1（envelope 统一） | M3e | SKILL.md 同 PR |
| simplify §J / §L | M3a | 实施期 simplify-review 顺手 |
| simplify §7（M2 视觉收尾未选项） | M3d | timeline 重构同 PR |
| smoketest B1（状态切换进流转） | M3a | 被 §14.6 audit 化覆盖 |
| §14.3 IDLE location 独立 action | M3a | RELOCATE transition |
| §14.8 timeline 视觉 | M3d | 主线 |

## 5. 风险与回滚

### 5.1 风险清单

| # | 风险 | 等级 | 缓解 |
|---|---|---|---|
| ~~R1~~ | ~~M3a 数据迁移破坏现有 checkout 历史~~ | ~~高~~ | **M3a 子 spec 决议不迁移测试数据；风险消失。整行作废。** |
| R2 | M3a 范围过大（5 态 + 10 transition + service 改造 + API 改造 + CLI 9 子命令 + 前端 dialog 改造） | 高 | **M3a 子 spec 决议**：拆 PR-1（后端契约 + schema migration）+ PR-2（前端切换 + UX）；PR-1 内顺序 phase 1（migration + model）→ phase 2（service + state machine）→ phase 3（API + CLI），单 PR 内分阶段 commit 但不分 PR |
| R3 | API 不向后兼容破坏外部消费者 | 低 | v1 GA 前 CLI/Web 是单仓库内全控；SKILL.md 尚未发布；外部 Agent 消费的就是仓库内 CLI |
| R4 | M3b 看板技术栈选型失误（Tremor 维护节奏 / shadcn-ui chart 不成熟） | 中 | M3b 子 spec brainstorm 时对比；主 spec §13 已登记"Tremor 若推出 Radix/shadcn 原生版本可再评估" |
| R5 | M3e playwright e2e 跨子里程碑场景脚本维护成本 | 中 | 场景控制在 5-8 个核心流（覆盖 happy path 即可），不追求完整覆盖（覆盖率靠 unit/api/cli 测试） |
| R6 | K1 envelope 统一改动面隐性扩散（CLI consumer 比预期多） | 低 | M3e SKILL.md 同 PR 时全仓库 grep envelope 字段名（serve.\*\.json / asset \*.json）确认 consumer 边界 |
| R7 | M3 总周期过长（5 子里程碑串行） | 中 | 子里程碑独立 PR 独立合 main，每个收尾后即可发版；不强求"全部完成才算 v1.0"——v1.0 GA 在 M3e 完成时打 tag |
| R8 | 状态机模型 RELOCATE/TRANSFER_HOLDER 高频暴露语义边界 case | 低 | M3a 实施期通过单测覆盖各 from-status 组合；UX 边界（菜单显隐）M3d 视觉重构时再调 |
| R9 | **M3a 子 spec 新增**：5 态文案修订（在用/闲置/维修中/已退役/已处置）破坏现有 UI 视觉一致性 | 低 | M2 视觉收尾后 status-labels.ts 是单一 SoT，修订时 grep 全前端确保无硬编码"派发中"等字面量 |
| R10 | **M3a 子 spec 新增**：shadcn Toggle 组件未装 / 装时引入 next-themes 残留 | 低 | PR-2 实施期检查（grep `frontend/src/components/ui/toggle.tsx`；如新引入按 M2c-3 §3 4 项审查清单走） |
| R11 | **M3a 子 spec 新增**：DISPOSED 终态无回滚导致用户误处置 | 低 | DisposeAlertDialog 输入"处置"字符串解锁按钮 + state machine 强制 from RETIRED/MAINTENANCE（IDLE 不可直 DISPOSE） |

### 5.2 不缓解的已知风险

- **§14.4 People 实体化推到 M5**：M3a 期间 holder 仍是 `str`，重名/改名仍无法处理——已接受的取舍
- **DISPOSED 终态无回滚**：用户误点 DISPOSE 后无法 REINSTATE——通过 "DISPOSE 必须 from RETIRED/MAINTENANCE"（不能 IDLE 直 DISPOSE）+ 二次确认 dialog 缓解，但不消除
- **M3 周期内 M4（UI 打磨）不启动**：v1.0 GA 时 UI 仍按 M2/M3d 形态，"达到 frontend-design 审美标准"留给 M4

## 6. 后续工作

- 本文是 M3 总览；各子里程碑独立 brainstorm + spec：
  - [`2026-05-03-m3a-state-machine-design.md`](./2026-05-03-m3a-state-machine-design.md) ✅ **已写入（2026-05-03）**
  - `2026-XX-XX-m3b-dashboard-design.md`
  - `2026-XX-XX-m3c-export-design.md`
  - `2026-XX-XX-m3d-timeline-visual-design.md`
  - `2026-XX-XX-m3e-skill-and-deploy-design.md`
- 主 spec 同步：M3 总览定稿后，需修订 [`2026-04-15-asset-hub-design.md`](./2026-04-15-asset-hub-design.md) §14 顶部 ⚠️ 文案约定（加 DISPOSED）+ §14.7 候选选定 + §11 路线图行（M3 拆 5 个子里程碑）
- followup-allocation.md 同步：M3 拆分确认后更新 §M3 表格

## 7. brainstorm 决策追踪

| 决策点 | 选择 | 备注 |
|---|---|---|
| M3 是否拆子里程碑？ | B | 拆 + 今天先 brainstorm 总览 spec |
| 顺序 | A | M3a → M3b → M3c → M3d → M3e |
| M3a 范围 | A 全包 | 核心（§14.6+§14.7）+ §14.1 派出类型 + §14.3 IDLE location 独立 action |
| 状态枚举 | 5 态 | IDLE / IN_USE / MAINTENANCE / RETIRED / DISPOSED |
| RETIRED vs DISPOSED 拆分 | 拆 | RETIRED 可复活 / DISPOSED 终态 |
| Q1 归还按 kind 拆？ | A | 单一 RETURN，kind 跟随对应 OPEN checkout |
| Q2 IN_USE → MAINTENANCE 直跳？ | C | 显式两步（dialog 提示，写两条 record） |
| Q3 MAINTENANCE → RETIRED 允许？ | A | 复用 RETIRE kind |
| Q4 IN_USE 期间 holder/location 变更算独立 transition？ | A | TRANSFER_HOLDER 独立 kind |
| Q5 RELOCATE 走 StateTransitionRecord？ | A | 单表，不开 LocationChangeRecord |
| holder 字段语义 | C | 所有非终态都可有值（含 MAINTENANCE） |
| MAINTENANCE 在 RELOCATE/TRANSFER_HOLDER 合法 from？ | 是 | 维修台搬迁 / 维修联系人变更是真实场景 |
| §2.3 StateTransitionRecord vs CheckoutRecord 关系 | A | 激进合并，删 CheckoutRecord |
| People 实体化提前到 M3a？ | B | 坚持 M5 |
| M3e 测试基建口径 | D | playwright e2e 烟测脚本 + 补齐薄弱点 |
| DISPOSE 合法 from | C | RETIRED / MAINTENANCE → DISPOSED（IDLE 必先 RETIRE） |

**M3a 子 spec 追加（2026-05-03）**：

| 决策点 | 选择 | 备注 |
|---|---|---|
| M3a 数据迁移策略 | 不迁移 | 测试数据可清空重建；migration 仅 schema 变更 |
| StateTransitionRecord 是否含 actor 字段 | 否 | YAGNI；v1 单用户无来源区分需求；M5 People 实体化时再加 |
| RETURN 后 asset.holder 行为 | 跟随 to_holder | 修订 M2d 行为；NULL 表示无人值守仓库 |
| IllegalTransitionError HTTP 映射 | 409 Conflict | 与 ConflictError 同语义类；闭环 simplify C1 |
| 5 态中文文案 | 闲置/在用/维修中/已退役/已处置 | 修订 frontend 现有"在用/闲置/维护/退役"漂移 |
| M3a PR 拆分 | 2 PR | PR-1 后端契约 + schema migration；PR-2 前端切换 + UX |
| transition kind 中文 label | 派发/出借/归还/送修/维修完成/退役/重新启用/处置/变更位置/变更保管人 | 简洁 + 风格统一 |
| API 请求 body 形态 | 单一 body shape | service 层 SoT 校验；不用 discriminated union |
| API 响应 body 形态 | 仅 transition row | 与项目现有 mutation pattern 一致；TanStack Query 原生范式 |
| dialog 数量与拆分 | 7 个组件（6 独立 + 1 共用） | 各自视觉差异化；A3 useFormDialog 推迟 M4 |
| 列表 toggle UX | Toggle chip with status token | 非普通 checkbox |
| timeline 新 kind 视觉 | 最简文案 + 显式 icon×token 表 | §14.8 高级视觉留 M3d |
