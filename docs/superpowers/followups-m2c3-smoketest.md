# M2c-3 烟测后未决项（需求/产品决策类）

**日期**：2026-04-27
**来源**：M2c-3 合并入 main 后的人工烟测
**性质**：与 `simplify-followups.md` 的重构清单不同，本文记录的是**需要产品决策**的功能扩展项——属于"是否做、什么时候做、怎么做"的输入。

烟测中发现的纯 bug / UX 缺陷已在烟测当次修掉（A 组：归还提示一闪、附件缩放、编辑菜单跳转、登记 submit 哑火），不在本文范围内。

---

## B1 · 状态切换是否进流转记录

### 现状

`src/asset_hub/services/asset.py::AssetService.change_status`（§14.5 的 4 个轻量动作：送修 / 修好回库 / 退役 / 重新启用）**只**修改 `asset.status`，**不**写 `CheckoutRecord`。

详情页`流转记录`区块由 `frontend/src/features/assets/detail/checkout-timeline.tsx` 渲染，数据源是 `useCheckoutHistoryQuery`（→ `GET /api/assets/{id}/history`）→ 仅返回 `CheckoutRecord`。

→ 用户视角下，"送修 / 修好回库 / 退役 / 重新启用"四类动作发生后**没有任何历史可追溯**，只能从 `asset.status + asset.updated_at` 推断"曾发生过状态变化"，但看不到时间序列、看不到细节（是谁在什么时候送的修？退役理由？）。

烟测反馈：M2c-3 spec 把这 4 类动作定为"轻量"，但**用户期望它们和派发/归还一样可追溯**——这是设计与期望的分歧。

### 三条候选方案

#### 方案 A · 复用 `CheckoutRecord` 表，加 `kind` 字段

把 `CheckoutRecord` 改成更通用的"流转事件"，加 `kind: "checkout" | "return" | "send_to_maintenance" | "return_from_maintenance" | "retire" | "reactivate"`，原 `holder/location/checkout_note/return_note` 字段对状态变化事件留空（或复用 `note`）。

- **优点**：单一历史表、单一 API、单一 UI——timeline 直接展示所有事件，对前端无侵入
- **缺点**：模型语义模糊（一个表 6 种事件，DTO 也得变 union）；需要 migration（可能要 backfill 现有 RETIRED/MAINTENANCE 资产的"创建时即 retire"事件，否则历史断层）
- **改动面**：后端 model + service + DTO + migration；前端 timeline 卡片要按 kind 渲染不同样式
- **ROI**：中——长期最干净，但短期成本不低
- **风险**：中（migration backfill 是判断题，没有"标准答案"）

#### 方案 B · 新增独立 `StatusChangeRecord` 表，详情页加"状态历史"区块

保留 `CheckoutRecord` 不动，新建独立的 `StatusChangeRecord(asset_id, from_status, to_status, changed_at, note)`。`change_status` service 写入这张新表。

详情页加第二个区块"状态历史"，与"流转记录"并列。

- **优点**：模型语义清晰，两类事件互不干扰；前端"流转记录"区块零改动
- **缺点**：详情页两个时间轴区块，用户视觉上需要切换；如果未来还想统一展示，又要回到方案 A 的事
- **改动面**：后端 model + service + 新 router + 新 DTO + migration；前端加新 query hook + 新区块组件
- **ROI**：中——隔离性最好但 UX 上有割裂感
- **风险**：低（纯新增，不破坏既有）

#### 方案 C · 暂不做，保留 status 单点真相

接受 v1 的"轻量状态切换不留痕"。在详情页 `状态` 字段旁加一行小字提示"状态由 ... 切换，时间 {asset.updated_at}"——但只能展示**最近一次**变化，更早的丢失。

- **优点**：零模型改动；继续保持 spec §14.5 的"轻量"定位
- **缺点**：用户的核心诉求（可追溯）没有解决
- **改动面**：仅前端文案
- **ROI**：低——只是缓兵之计
- **风险**：极低

### 决策建议

→ **方案 B 是最稳妥的中期选择**。如果未来"状态历史"和"派发/归还"展示要合并再走方案 A 的迁移，单向不可逆但代价可控（拆完表就回不来）。

→ **不建议方案 A**，因为 v1 期就把模型搞复杂会拖累后续开发节奏。等真有"统一事件流"的运营诉求再迁。

→ **不建议方案 C**，因为它没解决问题，只是把问题塞进 `updated_at`。

**建议落地阶段**：M2d 之前——M2d 是 CLI serve 接管 web 服务生命周期，跟数据模型无关，可以并行做 B；或者 M2d 之后单独开 M2e 做。

---

## B2 · 归还时是否支持"直接转交"

### 现状

`src/asset_hub/services/checkout.py::CheckoutService.return_(asset_id, note)`：归还只接受备注，归还后 `asset.holder/location` 清空。详情页 `ReturnDialog` 也只有"备注"一个字段。

用户视角：A 派发给同事甲，甲想交给乙，必须**两步**：先归还（asset 变 IDLE），再派发给乙（asset 变 IN_USE）。流转记录里看到一个"甲归还"事件 + 一个"乙派发"事件。

烟测反馈：用户期望归还 dialog 里能直接选下一个持有人和位置——一键完成"换人持有"。

### 候选方案

#### 方案 A · 复合操作：归还 dialog 加可选「转交给」字段

`ReturnDialog` 里加 `holder?` + `location?` 字段，留空则普通归还，填写则触发"归还 + 立即派发"复合事务。后端 `CheckoutService.return_` 接受可选 `next_holder + next_location`，在同一事务内：

1. 关闭当前 `CheckoutRecord`
2. 若有 `next_holder`：开启新 `CheckoutRecord(holder=next_holder, ...)`，asset 直接保持 IN_USE 不经过 IDLE

- **优点**：用户体验最丝滑；流转记录两条事件仍然清晰
- **缺点**：service 方法语义膨胀（`return_` 不再是纯归还）；状态机要允许 `IN_USE → IN_USE`（语义上没动，但流转记录两条）
- **改动面**：后端 service + DTO（`CheckoutReturn` 加 next_holder/next_location）+ 状态机；前端 ReturnDialog 加字段
- **ROI**：高（用户高频场景）
- **风险**：低（事务边界清楚；状态机改动只是放宽自循环）

#### 方案 B · 不做复合，改 UX 文案引导两步操作

`ReturnDialog` 顶部加一行提示"如需直接换人持有，请归还后从详情页或列表行『派发』菜单继续派发给新持有人"。

- **优点**：零业务改动
- **缺点**：用户的真实诉求没解决，只是降低预期
- **ROI**：低
- **风险**：极低

### 决策建议

→ **方案 A 优先**。这是真正的高频场景，分两步操作的代价对用户每次都是显性的。

→ **落地阶段建议**：M2d 之前或之后均可——独立的小特性，不挡 M2d 的 CLI serve 工作。

→ **scope 注意**：方案 A 的 service 方法名要不要改（`return_` → `return_or_transfer`）？保留 `return_` 避免破坏 CLI/test 兼容更稳；新增可选参数即可，不改方法名。

---

## B3 · AssetType 不可删

### 现状

烟测期间作者临时通过 CLI 创建了一个 `投影仪Smoke` (PJ) 类型用于测试，事毕想清理掉，发现：

- 后端 router `src/asset_hub/api/routers/types.py` **未实现 DELETE** 端点（实测 `DELETE /api/types/{id}` 返回 HTTP 405 Method Not Allowed）
- CLI（`asset-hub type ...`）也无 `delete` / `remove` 子命令
- 唯一清理方式：直连 SQLite 删 `asset_types` 行（烟测里就是这么做的：`Session.delete(t) + commit()`）

→ v1 单用户场景下，**被错版 prefix 或重复命名误建的 type 没有任何 GUI/CLI 路径能清理**，只能开 Python REPL 操作 DB。这是个低频但难受的运维盲点。

### 候选方案

#### 方案 A · 直接补 DELETE 端点 + CLI

`DELETE /api/types/{type_id}` + `asset-hub type delete <id>`。

需要决定：

1. **删除时若仍有 asset 引用该 type 怎么办？** 选项：
   - (a) 严格拒绝（`409 Conflict` / "请先删除/迁移所有引用此类型的资产"）—— 安全但麻烦
   - (b) cascade 删除所有引用资产（沿用 §14.5 删 asset 的策略）—— 危险，单条 type 可能挂着几十条资产
   - (c) 软删除（加 `is_archived` 列；type 仍在但不出现在选择器）—— 最稳但要 model + migration
2. **是否需要二次确认？** 走列表页 type 编辑页的 ⋯ 菜单 + AlertDialog（与 asset 删除模式一致）

→ **推荐 (a)**：单用户场景下"先删完所有此类型的 asset 再删 type"的工作量可接受；服务端硬约束最简单。

- **改动面**：后端 router + service + CLI command + 前端（如要做 GUI 删 type 入口）
- **ROI**：低 - 中。低频，但 0→1 没成本特别高
- **风险**：低（孤立特性）

#### 方案 B · 暂不做，文档化"误建只能 SQL 清"

接受 v1 单用户场景下的临时痛感。下次 type 误建时打开 Python REPL：

```py
from asset_hub.db import get_engine
from sqlmodel import Session, select
from asset_hub.models.asset_type import AssetType
s = Session(get_engine())
t = s.exec(select(AssetType).where(AssetType.name == '...')).first()
s.delete(t); s.commit()
```

- **优点**：零开发
- **缺点**：用户体验差；让 Agent CLI 用户陷入"我误建了一个 type 怎么删"的盲区
- **ROI**：极低 - 仅省下一次开发时间

### 决策建议

→ **方案 A 推荐 (a) 严格拒绝模式**。这是 spec §14 没明示的运维 gap，不影响主路径但偶发会卡人。

→ **落地阶段建议**：与 B2（直接转交）并列，可一起在 M2d 前的短迭代里清掉，或者干脆挪到下个里程碑。

---

## 索引（按优先级）

| 项 | 性质 | 推荐方案 | 落地优先级 | 阻塞 M2d？ |
|---|---|---|---|---|
| B2 直接转交 | 高频用户痛点 | A · 归还 dialog 加可选转交字段 | 高（建议 M2d 前/并行） | 否 |
| B1 状态历史 | 可追溯性 gap | B · 新增 `StatusChangeRecord` 表 | 中（建议 M2d 后单独里程碑） | 否 |
| B3 AssetType 不可删 | 运维盲点 | A · 补 DELETE 端点 + CLI（严格拒绝引用） | 低 - 中（M2d 前后均可） | 否 |

三条都不阻塞 M2d。**建议在 M2d 启动前先把 B2 做掉**（小改动、高 ROI）；B1 的方案 B 等 M2d 完成后再启动单独里程碑；B3 顺手放进 B2 的同一 PR 也合理（都是 service+router+CLI 三层小动）。
