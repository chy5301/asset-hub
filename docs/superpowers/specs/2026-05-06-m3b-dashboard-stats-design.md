# M3b 看板 + /api/stats 设计文档

- **日期**：2026-05-06
- **状态**：初稿，待实施
- **作者**：conghaoyangbobby@gmail.com（与 Claude 协同 brainstorm）
- **范围**：M3 子里程碑 b——看板（4 张图）+ `/api/stats` 单端点 + CLI `asset-hub stats` + 3 项搭车 follow-up（C3 / D1 / H4）
- **前置**：M3a 状态机基建已合并到 main（5 态 + 10 transition kind + `StateTransitionRecord` 单表 audit）

## 0. 背景与定位

M2 已交付资产管理主线，M3a 已完成状态机基建。M3b 是 v1.0 GA 前的"全局视图 + 运营动作锚"——给单人 + AI Agent 双视角看到"我有什么 / 该处理什么"。

**核心定位**：看板不是统计页，是"运营行动召唤页"。"闲置时长 Top 10"是视觉锚，其余 3 张图是描述性背景。

**主 spec 修订项**：

- 主 [`2026-04-15-asset-hub-design.md`](./2026-04-15-asset-hub-design.md) §7 路由表写"4 张 Tremor 图表"；§8 看板章节写"shadcn/ui charts (Recharts)"——以本子 spec 为准：**采用 shadcn/ui charts (Recharts 底)**
- §13 待观察项"Tremor 若推出 Radix/shadcn 原生版本可再评估"——本子 spec 决议不再观察 Tremor，理由见 §3.4

## 1. 范围

### 1.1 包

| # | 内容 |
|---|---|
| 1 | 后端 `GET /api/stats` 单端点，4 段聚合，接 `?include_retired=&include_disposed=` 两个 toggle |
| 2 | `services/stats.py` + `api/routers/stats.py` + `api/schemas/stats.py` |
| 3 | CLI `asset-hub stats [--include-retired] [--include-disposed] [--json]`，复用 service 层（不走 HTTP） |
| 4 | 前端 `/dashboard` 路由 + 看板页（D-原版布局）+ 4 图组件 + hooks + 4 种空态 |
| 5 | 图表栈 = shadcn/ui charts（Recharts 底） |
| 6 | **C3** detail DTO 补 `type_name` + 前端 detail 页删 `useAssetTypesQuery()` |
| 7 | **D1** 全前端 `frontend/src/features/assets/types.ts` 业务 alias 层 + 全前端 generated import grep replace（一次性闭环） |
| 8 | **H4** 独立 `frontend/src/api/types.ts` 放 `OpenapiFetchResult<T>` + 简化 `unwrap` 签名 |
| 9 | **搭车**：list DTO `AssetRead` 补 `idle_days` 字段（与 stats 同源） |

### 1.2 不包

- 时间序列 / 趋势图（v2+）
- 可配置看板 / 自定义聚合（v2+）
- 看板按 type/holder/q 筛选（仅 toggle，决策 §B.3）
- §14.8 timeline 重构（→ M3d）
- M3c 导出（独立子里程碑）
- 跨子里程碑 e2e playwright 脚本（M3e 统一写）

### 1.3 PR 拆分

按"后端契约 → 前端集成"两层切（决策 §B.7）：

| PR | 内容 | 改动面 |
|---|---|---|
| **PR-1 后端契约** | service/router/schema + CLI + C3 后端补 `type_name` + AssetRead 补 `idle_days` | 后端 + CLI + 测试三层 |
| **PR-2 前端集成** | `/dashboard` 路由 + 看板页 + 4 图 + hooks + D1 alias 层 + H4 抽 types.ts + C3 前端切 | 全前端 |

PR-1 合并后跑 `pnpm gen:api` 生成新 schema → PR-2 才能开工（物理依赖）。

## 2. 后端：`/api/stats` 端点

### 2.1 响应契约

```json
GET /api/stats?include_retired=false&include_disposed=false

200 OK
{
  "type_distribution": [
    {"type_id": "uuid", "type_name": "Laptop", "count": 71}
  ],
  "status_distribution": {
    "IDLE": 78, "IN_USE": 92, "MAINTENANCE": 12
  },
  "holder_ranking": [
    {"holder": "张三", "count": 28}
  ],
  "idle_top": [
    {
      "asset_id": "uuid",
      "asset_code": "GPU-A100-03",
      "type_name": "GPU",
      "current_location": "仓库",
      "idle_days": 152,
      "idle_since": "2025-12-04T00:00:00Z"
    }
  ]
}
```

- `status_distribution.RETIRED` 仅在 `include_retired=true` 时出现；`DISPOSED` 同理
- `holder_ranking` 全量倒序，`current_holder is null` 跳过；不做 N 截断（决策 §B.2）
- `idle_top` 严格 ≤ 10；空数组允许（决策 §B.4）

### 2.2 Service 层

```python
# src/asset_hub/services/stats.py
class StatsService:
    def __init__(self, session: Session): ...

    def get_dashboard_stats(
        self,
        *,
        include_retired: bool = False,
        include_disposed: bool = False,
    ) -> StatsRead: ...
```

返回 domain DTO（`api/schemas/stats.py::StatsRead`），不返 ORM 对象（CLAUDE.md ORM/DTO 隔离约束）。

### 2.3 4 段聚合查询

| 段 | 查询要点 |
|---|---|
| 类型分布 | `select(Asset.type_id, AssetType.name, func.count(Asset.id)).join(AssetType).group_by(Asset.type_id, AssetType.name)` + `WHERE` 跟 toggle |
| 状态分布 | `select(Asset.status, func.count()).group_by(Asset.status)` + `WHERE` 跟 toggle；空状态不出现在结果时补 0 |
| 保管人排行 | `select(Asset.current_holder, func.count()).where(Asset.current_holder.is_not(None)).group_by(Asset.current_holder).order_by(count.desc())` + `WHERE` 跟 toggle |
| 闲置 Top 10 | 子查询：`select(StateTransitionRecord.asset_id, func.max(recorded_at).label("last_idle_at")).where(to_status="IDLE").group_by(asset_id)`；外层 `select(Asset).join(子查询, isouter=True).where(Asset.status="IDLE").order_by(coalesce(last_idle_at, Asset.created_at).asc()).limit(10)` |

**idle_days 起点**：用 `StateTransitionRecord` 上次 `to_status=IDLE` 的 `recorded_at`；新登记后未发生过 transition 的 IDLE 资产 fallback `Asset.created_at`（决策 §B.idle）。

**为何不用 `Asset.updated_at`**：`updated_at` 任何字段更新都刷新，改备注 / 改 location 都重置 idle 计时——语义脏。

**搭车 list DTO**：`AssetRead.idle_days` 用同一逻辑（抽 `_compute_idle_days` helper），列表"闲置时长"列与看板同源。

### 2.4 Router

```python
# src/asset_hub/api/routers/stats.py
@router.get("/stats", response_model=StatsRead)
def get_stats(
    include_retired: bool = False,
    include_disposed: bool = False,
    session: Session = Depends(get_session),
) -> StatsRead:
    return StatsService(session).get_dashboard_stats(
        include_retired=include_retired,
        include_disposed=include_disposed,
    )
```

无域异常路径；`bool` query 参数 FastAPI 自动 422，不需要在 `app.py` 加映射。

### 2.5 性能与缓存

v1 规模 < 200 资产 / < 1000 transition records。**不做缓存**。验收 P95 < 200ms（本机 SQLite）。

未来 Postgres + 资产数破 5000 时考虑给 `state_transition_records (asset_id, recorded_at, to_status)` 加复合索引。

## 3. 前端看板

### 3.1 路由与文件结构

```
frontend/src/routes/
  dashboard.tsx                       # /dashboard，file-based 路由
frontend/src/features/dashboard/      # 新建
  use-stats-query.ts                  # React Query hook
  search-schema.ts                    # zod：?include_retired=&include_disposed=
  dashboard-page.tsx                  # 主页（D-原版布局）
  charts/
    type-distribution-chart.tsx       # donut（Recharts PieChart）
    status-distribution-chart.tsx     # stacked bar（Recharts BarChart）
    holder-leaderboard.tsx            # 密集列表（自定义 div，不走 Recharts）
    idle-top-bar-chart.tsx            # horizontal bar（Recharts BarChart）
  empty-states/
    type-empty.tsx / status-empty.tsx / holder-empty.tsx / idle-empty.tsx
```

入口：列表页 / 详情页顶部导航（M3a 已落 header）增 `/dashboard` 链接 + 图标。

### 3.2 布局（D-原版）

桌面端（≥ 1024px）：左 60% 闲置榜全高 + 右 40% 三段（类型 → 状态 → 保管人 从上到下）。

```tsx
<div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-4 min-h-[600px]">
  <IdleTopBarChart />
  <div className="grid grid-rows-3 gap-4">
    <TypeDistributionChart />
    <StatusDistributionChart />
    <HolderLeaderboard />
  </div>
</div>
```

窄屏（< 1024px）退化为单列堆叠：闲置榜 → 类型 → 状态 → 保管人。

顶部 toggle 区：`<div className="flex justify-end gap-2">` 放 2 个 shadcn Toggle："显示已退役" / "显示已处置"，URL 通过 search-schema 持久化。Toggle 旁 hint icon `?`，hover 提示"默认排除已退役/已处置（与列表一致）"。

### 3.3 4 图组件

| 组件 | 形态 | 数据源 | 配色 |
|---|---|---|---|
| `IdleTopBarChart` | Recharts `BarChart layout="vertical"`，10 行水平条 | `stats.idle_top` | bar fill = `--status-idle`；> 90 天行 fg `text-destructive` 强调 |
| `TypeDistributionChart` | Recharts `PieChart` donut + 自绘 legend | `stats.type_distribution` | 6 槽 chart token（见 §3.5） |
| `StatusDistributionChart` | Recharts `BarChart layout="vertical"` 单条 stacked bar | `stats.status_distribution` | M3a 5 态 OKLCH token |
| `HolderLeaderboard` | 纯 div 列表 `avatar + name + chip` | `stats.holder_ranking` | `--muted` |

**4 种 shape 强约束**（决策 §B.1 第 3 条 + §B.2 视觉约束）：保管人禁用 horizontal bar chart；类型禁用 status/kind 色板。

`HolderLeaderboard` 用 `max-h-[18rem] overflow-y-auto` 防全量列表溢出。

### 3.4 图表栈：shadcn/ui charts (Recharts)

**为何不用 Tremor**：Tremor 自带 Tailwind 主题 / 自带色板，与项目 design-system MASTER.md 的 OKLCH 5 态 token 冲突；shadcn 风格混搭风险高。shadcn/ui charts 直接复用项目 design token + dark mode 自动 + 底层 Recharts 成熟。

**接入步骤（PR-2 第 1 步 spike）**：

1. `pnpm dlx shadcn@latest add chart`
2. 验 Tailwind v4 兼容性（项目用 v4，shadcn chart 文档多 v3 示例）
3. 不兼容 → 回 Recharts 裸用（仅样式自接 Tailwind v4 token，组件结构等价）

### 3.5 配色

- **状态**：复用 M3a 已落 `--status-idle/in-use/maintenance/retired/disposed` 5 OKLCH token
- **闲置榜 bar**：`--status-idle`（弱化）+ > 90 天行 fg `text-destructive`
- **类型分布**：新增 `--chart-1` ... `--chart-6` 6 个中性 OKLCH chart token 到 `frontend/src/styles/globals.css`；按 `type_id` 第一个字符 charCode % 6 哈希到固定槽位（同一类型每次进看板颜色稳定）
- **保管人 chip**：`--muted` token

**v1 上限 6 槽**：v1 type 数量预期 < 10；冲突可接受（同色相邻 type）；> 6 槽后续扩。

### 3.6 Hooks

```ts
// use-stats-query.ts
export function useStatsQuery(params: { includeRetired: boolean; includeDisposed: boolean }) {
  return useQuery({
    queryKey: ['stats', params],
    queryFn: () => api.GET('/api/stats', { params: { query: params } }).then(unwrap),
    staleTime: 30_000,
  })
}
```

`unwrap` 走 H4 决策抽到 `frontend/src/api/types.ts` 的简化签名。

### 3.7 空态（按图差异化，决策 §B.4）

| 图 | 触发 | 文案 | CTA |
|---|---|---|---|
| 类型分布 | `type_distribution.length === 0` | "尚未定义任何类型" | → `/types` |
| 状态分布 | `status_distribution` 全 0 | "还没有登记任何资产" | → `/assets/new` |
| 保管人 | `holder_ranking.length === 0` | "还没有派发记录" | → `/assets`（去派发） |
| 闲置榜 | `idle_top.length === 0` | "没有闲置资产" | 无 CTA（"少 = 好事"） |

**短列不视为空态**——保管人 5 行 / 闲置榜 6 行不触发空态文案，自然短列展示。

### 3.8 加载与错误

- 加载：4 图各自 `<Skeleton>`，按 D-原版布局占位
- 错误：整页 1 个 `InlineErrorBanner`（单端点失败 = 整体失败）+ 重试按钮触发 `refetch()`

## 4. CLI `asset-hub stats`

```bash
asset-hub stats                         # 默认人类可读双列表格
asset-hub stats --include-retired
asset-hub stats --include-disposed
asset-hub stats --json                  # K1 envelope
```

- `src/asset_hub/cli/stats.py` 新建，Typer command
- `from asset_hub.services.stats import StatsService`（CLAUDE.md 三层分离）
- `--json` 输出 envelope `{success, data, metadata: {took_ms}, error}`
- 人类输出用 `rich` 双列表格：左列 类型分布 + 状态分布；右列 保管人持有 + 闲置 Top 10
- 退出码：0 成功 / 1 一般错误（兜底）

## 5. Follow-up 落点

| follow-up | PR | 改动面 |
|---|---|---|
| **C3 detail DTO 补 `type_name`** | PR-1 后端 | `AssetReadDetail` 增字段 + service 跟随返 + test_asset_router 增断言 |
| **C3 前端切（删 `useAssetTypesQuery()`）** | PR-2 前端 | `asset-detail-page.tsx` 删 query，改用 `asset.type_name` |
| **D1 alias 层** | PR-2 前端 | 新建 `features/assets/types.ts` re-export 全部业务类型；grep 全前端 `from '@/api/generated/schema'` 替换 |
| **H4 OpenapiFetchResult** | PR-2 前端 | 新建 `api/types.ts`，`OpenapiFetchResult<T>` + `unwrap()` 简化签名 |
| **搭车 AssetRead.idle_days** | PR-1 后端 | `AssetRead` 增 `idle_days: int \| None` + helper 复用 stats 子查询逻辑 |

### 5.1 PR-2 内 commit 顺序

1. 基建：建 `frontend/src/api/types.ts`（H4）+ `frontend/src/features/assets/types.ts`（D1）
2. D1 grep replace：全前端 import 替换；`pnpm build`（用 `tsc -b` 而非 `tsc --noEmit`）；commit "refactor(types): D1 业务化 alias 层"
3. H4：`error.ts unwrap` 签名简化；commit "refactor(api): H4 OpenapiFetchResult<T>"
4. C3 前端切：删 `useAssetTypesQuery()`；commit "refactor(detail): C3 用 detail DTO 自带 type_name"
5. 看板新建：dashboard-page.tsx + 4 图 + hooks + search-schema + 空态；commit 按图拆 4-5 个
6. 入口接入：header 加 `/dashboard` 链接；commit "feat(nav): 看板入口"
7. playwright MCP 烟测；commit "test(dashboard): playwright MCP 烟测"

## 6. 测试

### 6.1 测试矩阵

| 层 | 文件 | 覆盖 |
|---|---|---|
| 后端 unit | `tests/unit/test_stats_service.py` | 4 段聚合各 3-5 case：0/1/N 资产 / Top N 截断 / toggle 双向 / idle_days 子查询（从未 IDLE 过 fallback `created_at` / 多次进出 IDLE 取最近 / IDLE 不足 10 件不补位） |
| 后端 unit | `tests/unit/test_asset_idle_days.py` | `AssetRead.idle_days` 与 stats 同源 |
| 后端 api | `tests/api/test_stats_router.py` | 200 + 字段完整 / toggle 透传 / bool 参数 422 |
| 后端 api（C3） | `tests/api/test_asset_router.py` | `GET /api/assets/{id}` 含 `type_name` |
| 后端 cli | `tests/cli/test_stats_cli.py` | `--json` envelope / toggle 透传 / 人类输出 / 退出码 |
| 前端 unit | `frontend/tests/unit/dashboard/` | `idle_top` > 90 天判定 / `holder_ranking` null 跳过 / `type_id` 哈希到 6 chart token 槽稳定性 / 5 态文案映射 |
| 前端 hooks | `frontend/tests/hooks/use-stats-query.test.tsx` | MSW 4 段成功 / 单段空 / 全空 4 空态触发 / toggle 触发 refetch |
| playwright MCP 烟测 | 实施期 Claude 调用 playwright MCP 自动跑 | 4 空态 / 4 图同框（D-原版）/ toggle 联动 / 窄屏退化 / 暗色模式 / 加载 skeleton |

**TDD 节奏**：每段聚合先写 service 失败 case → 实现 → API/CLI 各跟一层。前端按 hooks → 派生纯函数 → 组件。

### 6.2 故意不做

- 真 dataset 性能压测（v1 规模 < 200 资产，无意义）
- 跨子里程碑 e2e 脚本（M3e 统一写）
- shadcn/ui charts 内部渲染断言（黑盒交给 Recharts）

## 7. 风险与回滚

### 7.1 风险

| # | 风险 | 概率 | 缓解 |
|---|---|---|---|
| R1 | idle_days 子查询 SQLite 性能 | 低 | v1 < 1000 records；超阈值再加索引 `(asset_id, recorded_at, to_status)` |
| R2 | shadcn/ui charts 与 Tailwind v4 兼容 | 中 | PR-2 第 1 步 spike；不兼容回 Recharts 裸用 |
| R3 | D1 grep replace 漏改 / 误改 | 中 | 精确正则定位 + `pnpm build`（用 `tsc -b`）+ playwright MCP 主流程页面运行时验证 |
| R4 | type_id 哈希 6 槽冲突 | 低 | v1 type < 10；同色相邻可接受；spec 写明 |
| R5 | 默认排除 RETIRED/DISPOSED 与新用户认知不一致 | 低 | toggle 旁 hint icon |
| R6 | 闲置榜 fallback `created_at` 让"刚登记 IDLE"挤进 Top 10 | 中 | 这是预期行为——刚登记的库存就是闲置；spec 写明 |

### 7.2 回滚

- PR-1 单 PR revert（无数据迁移）
- PR-2 单 PR revert（前端 churn 全可逆）

## 8. 决策追踪

| # | 决策点 | 选择 | 理由 |
|---|---|---|---|
| B.1 | 看板范围 | A 严格 4 张图 + 4 设计约束 | 不加 KPI 卡（避免模板脸）/ 闲置榜为锚 / 4 种 shape / 复用 OKLCH token |
| B.2 | Top N 取数 | D + 视觉约束 | 保管人全量倒序 + 闲置 Top 10；保管人禁用 horizontal bar chart（4 种 shape 落形态分配） |
| B.3 | 看板筛选联动 | B 仅 toggle | `?include_retired=&include_disposed=`，与列表语义一致；不接 type/holder/q |
| B.4 | 空态 | B 按图差异化 | 4 种文案 + 各自 CTA；短列不视为空态 |
| B.5 | D1 范围 | C 全前端 | 一次性 grep replace 闭环 D1 |
| B.6 | H4 形态 | C 独立 `api/types.ts` | 与业务 alias 层关注点分离 |
| B.7 | PR 拆分 | B 按层 2 PR | PR-1 后端契约 / PR-2 前端集成 + 三 follow-up |
| B.8 | 图表栈 | A shadcn/ui charts | 复用 OKLCH token + 不引第二套 chart 主题 |
| B.9 | 测试基建 | A 加 CLI stats | Agent 友好度一等公民 |
| B.10 | 看板布局 | D-原版（左 60 锚 / 右 40 描述） | 闲置榜全高填 10 行无截断；左→右"召唤→导引" |
| B.idle | idle_days 起点 | B `StateTransitionRecord` | 语义精确；list DTO 同源 |

## 9. 实施时序估算

- PR-1 后端契约：~1.5 天（service TDD + router + CLI + C3 + idle_days helper + 测试三层）
- PR-2 前端集成：~3 天（基建 + D1/H4/C3 切换 + 4 图 + 空态 + playwright MCP 烟测）

## 10. 后续分配

- **不在 M3b 内的 follow-up**：见 [`followup-allocation.md`](../followup-allocation.md) M3c–M3e 段
- **本子里程碑产生的新 follow-up**：M3b 实施期 simplify review 后登记到 [`simplify-followups.md`](../simplify-followups.md) §M3b 范围段
