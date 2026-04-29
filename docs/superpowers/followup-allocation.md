# Follow-up 分配（M2d / M2c-4 / M3 / 暂不动）

**日期**：2026-04-28
**输入**：[`followups-m2c3-smoketest.md`](./followups-m2c3-smoketest.md)（产品决策类 B1/B2/B3） + [`simplify-followups.md`](./simplify-followups.md)（重构清单 §1-§4）+ [`specs/2026-04-15-asset-hub-design.md`](./specs/2026-04-15-asset-hub-design.md) §11/§14 主线
**用途**：M2d 启动前确定 follow-up 落点，避免临时塞、避免漏。

判断准则：里程碑主题相关性 > 触发条件已就位 > 顺手成本最低。

---

## M2d · CLI 接管 web 服务生命周期

**主线**：spec §14.9 — `asset-hub serve start/stop/status/restart/logs`，psutil 进程树管理，PID/log 文件，dev/prod 模式。

**搭车的小项**（与 M2d 主题无关，但可在同一里程碑独立 PR 顺手吃掉，不混进 serve spec）：

| 项 | 来源 | 理由 |
|---|---|---|
| **B2** 归还时记录归还地点 + 接收人（dialog 加 return_location / return_receiver 字段） | smoketest（按 spec §14.2 真实意图实施；smoketest 原文表述失真） | 高频用户痛点；纯 service+dialog 局部小动 |
| **B3** AssetType DELETE 端点（严格拒绝引用）+ CLI | smoketest | 与 B2 同 PR 合理（service+router+CLI 三层小动）；运维盲点低成本清掉 |
| **I1** 后端 validation 补 `url` / `multi-enum` / `int.min/max` | simplify §4 | 真实功能缺口（前端能过、后端必拒），用户可触发的运行时错误，不能再拖 |
| **I2** `FieldType` Enum + 表驱动 dispatch | simplify §4 | 与 I1 同时做 ROI 最高（新增 url/multi-enum 也要进 Enum） |

> 上面 4 项打包成"M2d 期间的 backend gaps PR"独立合并，不混进 serve spec。

---

## M2c-4 · 类型管理 UI（含结构化 custom_fields builder）

**主线**：AssetType 列表 + 编辑 UI；`custom_fields` 从手撸 JSON → 结构化 builder（type 选择器、options 编辑、min/max/required 设置）。

**主题相关 follow-up**（落在 builder 同一改动面上）：

| 项 | 来源 | 理由 |
|---|---|---|
| **A1** 合并 build-create-schema / build-edit-schema | simplify §1.A | builder 输出新 fieldDefs，schema builder 必然碰；顺手合 |
| **F3** zodResolver 在 CreateForm 每次 render 重建 | simplify §1.F | 与 A1 同 PR |
| **A2** 抽 `FieldShell` 收敛 9 个 field-control | simplify §1.A | builder 让"加 field type"成为运行时操作，9 外壳的稳定性会被持续打破 |
| **A4** field-controls 泛型 `Control<TFieldValues>` | simplify §1.A | 已登记"与 A2 一起做最划算"，M2c-4 同周期 |

> A2/A4 是必须项（不是顺手）：builder 让运行时增加 field type 成常态，9 个外壳会被反复触碰。

---

## M3 · 特性完整

**主线**：看板 4 图 + `/api/stats` + CSV/XLSX 导出 + SKILL.md + §14.1 派出类型 + §14.6 audit 化 + §14.7 状态枚举 + 基础测试 + README/部署。

**已登记 / 主题强相关的 follow-up**：

| 项 | 来源 | 理由 |
|---|---|---|
| **smoketest B1** 状态切换进流转记录 | smoketest | 与 §14.6 audit 化天然合并：14.6 的 `StateTransitionRecord` 直接覆盖 B1 诉求；M2d 前不要单独建 `StatusChangeRecord` 表 |
| **C1** checkout.py 与 state_machine 双层防御统一 | simplify §1.C | 已登记"M3 §14.6/14.7 状态机升级时一并做" |
| **C3** detail page 多查 type 列表（detail DTO 补 type_name） | simplify §1.C | 已登记"M3 详情页改动时顺手做" |
| **D1** generated schema 类型业务化 alias 层 | simplify §1.D | 已登记"M3 openapi 客户端选型决策时一并做"（spec §13） |
| **H4** `error.ts` `unwrap` 签名抽 `OpenapiFetchResult<T>` | simplify §3.H | 与 D1 同周期（受 openapi 客户端选型驱动） |
| **§14.3** IDLE 资产显式 location 维护（独立"修改位置" action） | spec | M2d B2 已覆盖归还时 location；§14.3 残值缩小为"派发→归还之间的时段需独立修改位置 action" |
| **§14.8** timeline 视觉重构（时间渐隐 + 派出类型染色 + 超长派发预警） | spec | 已登记"M3 与 14.1 联动" |

---

## 暂不动（触发条件未到，不分配里程碑）

| 项 | 来源 | 触发条件 |
|---|---|---|
| A3 CheckoutDialog/ReturnDialog 合并 | simplify §1.A | 第 3 个 form dialog 出现时（M3 批量调拨等） |
| B1（前端）useStateChangeRunner hook | simplify §1.B | 与 A3 同期 |
| C2 delete_asset cascade 事务边界 | simplify §1.C | 真出现批量删除场景时 |
| E1 AssetHeader 状态矩阵抽配置数组 | simplify §1.E | M3 状态扩到 5+（§14.7）落地后；不扩则不动 |
| F1 `availableStateChanges` 预算表 | simplify §1.F | 30+ 状态时 |
| F2 attachment 批量超限 toast 聚合 | simplify §1.F | UX 复盘时 |
| G1 mutation 工厂 helper | simplify §2 | mutation ≥ 10 时 |
| G2 invalidate 失效面收窄 | simplify §2 | list 缓存条目 >10 或操作可见闪屏时 |
| G3 general-fields schema-driven | simplify §2 | reuse + quality agent 共识不做 |
| H1 `<CenteredPanel>` 整合 4 个占位组件 | simplify §3 | 第 5 个占位场景出现时 |
| H2 双套防抖 / commit 逻辑统一 | simplify §3 | 第 3 个 filter 字段时 |
| H3 / H5 / H6 / I3 / I4 / I5 / I6 | simplify | 全部"决定不做"或微优化触发器极远 |
| §14.4 People 实体化 | spec | 独立 M5 大里程碑，§14.1 之后 |

---

## 关键非显然的判断

1. **smoketest B1 不要在 M2d 单独建表** —— 与 M3 §14.6 的 `StateTransitionRecord` 设计天然合并，先做 B1 等于自己挖坑给 §14.6 填。M2d 期间只做 B2+B3。
2. **simplify I1+I2 应跟 M2d 走** —— 不是主题相关，而是 I1 是用户可触发的运行时 bug，已经拖了 M2c-3；M2c-4 的 custom_fields builder 会更早暴露 url/multi-enum 在后端不认的事实，必须在 M2c-4 之前修。
3. **simplify A2+A4 必须挂 M2c-4** —— 不是顺手，而是 builder 让"运行时增加 field type"成为常态，9 个 field-control 外壳在 M2c-4 期间会被反复触碰，不抽 FieldShell 等于反复改 9 处。
4. **B2 真实意图 = spec §14.2**（2026-04-29 brainstorm 修正）—— smoketest 原文描述"A→甲→乙 直接转交"是失真表述；真实需求是"归还时记录归还到哪个地点 + 哪个管理员接收"。M2d B2 实施完成后 §14.2 完全覆盖，从 M3 移除；§14.3 残值缩小为"派发→归还之间需独立修改位置 action"。

---

## 摘要

| 里程碑 | 主线 | 强搭车项 | 数量 |
|---|---|---|---|
| **M2d** | §14.9 serve | B2、B3、I1、I2 | 4 |
| **M2c-4** | 类型管理 UI + custom_fields builder | A1、F3、A2、A4 | 4 |
| **M3** | 看板/导出/SKILL/14.1/14.6/14.7/测试/部署 | smoketest B1、C1、C3、D1、H4、§14.3、§14.8 | 7 |
| 暂不动 | — | 13 项 | 13 |
