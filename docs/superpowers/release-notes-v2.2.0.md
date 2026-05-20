# v2.2.0 发版升级指南

> 发布日期：2026-05-20
> 单 PR 视觉打磨主 PR (#21)，含 6 子项 A/B/C/D/E/F；不动 db 与 CLI。

## 概览

v2.2.0 是 v2.1.0（清场期 4 PR）之后的 M4 视觉打磨里程碑，**单 PR 合并**：

| 子项 | 主题 |
|---|---|
| M4-A | 抽 `useFormDialog` hook 收敛 CheckoutDialog/ReturnDialog 表单样板 |
| M4-B | 配色精打磨 5 修复点（背景割裂 / toggle 文案 / chip 边框 / status 色 / 空错loading 收口）|
| M4-C | 看板可用性（#13）—— Y 轴用 name + 排版收口 |
| M4-D | lightbox 大屏宽度（#14）|
| M4-E | 列表 type/status 列排序（#15）|
| M4-F | asset-header.test.tsx 时间敏感 flaky 修 |

## 升级路径

```bash
cp data/asset_hub.db data/asset_hub.db.v2.1.bak
git fetch && git checkout v2.2.0
uv sync && pnpm --dir frontend install
# 无 db migration（v4 head 与 v2.1.0 一致）
uv run asset-hub serve restart --mode prod
```

## Breaking changes

**无**。本里程碑仅前端视觉打磨 + dialog hook 抽离 + 1 处后端 schema 加字段（IdleTopItem 加 `name`，前端 typed client 已同步），无 DB schema / CLI / API 路由破坏。

## 改动详情

### M4-A useFormDialog hook 抽离

- 新增 `frontend/src/features/assets/detail/use-form-dialog.ts`：泛型 hook 封装 `useForm + zodResolver + onSubmit (含 setError('root') 错误处理) + handleOpenChange (含 mutation 进行中防关闭)`
- `CheckoutDialog` 239 → 220 行（-19 行），`ReturnDialog` 169 → 154 行（-15 行）
- 外部行为零变化，现有 dialog test 全绿

### M4-B 配色精打磨 5 修复点

1. **看板背景割裂修**：dashboard route 容器消费 MASTER `--dashboard-bg-radial-from/to` token 实现 radial gradient，消除卡片 `bg-card` 与全局 `bg-background` 的色块割裂
2. **filter toggle 文案统一**：dashboard / 列表统一为「显示退役 / 显示注销」
3. **Toggle chip pressed 边框加深**：`border-status-X/30` → `border-status-X/60`，第一眼可见 on/off 差异
4. **status 色 token 校准**：BROKEN token 与 MASTER spec 锁定值一致（verified 未被改动）
5. **空 / 错 / loading 态视觉收口**：dashboard / 列表 / 详情 3 页全用公共组件（`EmptyState` / `GridSkeleton` / `DetailSkeleton` / `TimelineSkeleton` / `NotFoundPanel` / `ErrorState`）。Dashboard 4 chart 卡片各用 thin wrapper 保留 chart-specific 语义

### M4-C 看板可用性（闭环 #13）

- 后端 `IdleTopItem` 加 `name: str` 字段
- `_idle_top` SQL select 加 `Asset.name`，`AssetType.name.label("type_name")` 显式区分解包冲突
- `pnpm gen:api` 同步前端 typed client
- `idle-top-bar-chart` Y 轴 `dataKey: asset_code → name`，`width: 90 → 140`
- Tooltip 主标 name，副标 `asset_code · type_name`
- dashboard 排版用 `grid-cols-12` + chart 卡片 `col-span-6` (2x2 布局)

### M4-D lightbox 大屏宽度（闭环 #14）

- `DialogContent` className `max-w-[90vw]` → `!max-w-[90vw]`（important 覆盖 `dialog.tsx` 默认 `sm:max-w-sm`；tailwind-merge 不会自动覆盖不同响应式前缀）
- `DialogContent showCloseButton={false}` 关默认 X，保留自定义工具栏 X

### M4-E 列表 type/status 列排序（闭环 #15）

- 抽 `statusSortingFn` 到 `assets-table-sorting.ts`，按 `ASSET_STATUS_VALUES` 数组下标排序（生命周期序：IDLE → IN_USE → MAINTENANCE → BROKEN → RETIRED → DISPOSED）
- `assets-table.tsx` 删 type / status 两列的 `enableSorting: false`
- status 列加 `sortingFn={statusSortingFn}`，未知状态返 0 防 schema 漂移
- 加 e2e spec `12-list-sort-by-type-status.spec.ts` 防回归（CI 验）

### M4-F asset-header 时间敏感 flaky 修

- 根因 M3d commit `3dcdf56` 引入 `due_at = Date.now() - N * 86400000`，解析时无时区按 local 时间偏移
- 改用 `vi.useFakeTimers + vi.setSystemTime` 固定到 `2026-01-15 UTC`，`due_at` 用固定 ISO 时间戳——时区无关
- 顺手修同文件 5 个时间敏感 case；连跑 10 次无 flaky

## 实施期纠偏（M4，2026-05-20）

详见 `design-system/asset-hub/MASTER.md` §「实施期纠偏（M4，2026-05-20）」段。含 5 项新增 override 记录 + Pre-Delivery Checklist 7 项 verify + 反 AI-slop 红线 grep 0 命中。

## 回滚

```bash
git checkout v2.1.0
cp data/asset_hub.db.v2.1.bak data/asset_hub.db
uv sync && pnpm --dir frontend install
uv run asset-hub serve restart --mode prod
```

无不可回滚的数据变更（M4 不动 DB schema / migration）。

## SemVer

含 user-visible 视觉改动 + 后端 1 处 schema 新增字段（向后兼容），无 breaking。新增功能 → MINOR → `v2.2.0`。

## 来源

- Spec: `docs/superpowers/specs/2026-05-17-m4-batch-plan-design.md` § M4 主 PR 段
- Plan: `docs/superpowers/plans/2026-05-17-m4-visual-polish.md`（8 phase / 19 commit squash 进 main）
- PR: #21
