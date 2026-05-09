# /simplify Review · 跨里程碑未修清单（后续重构参考）

**视角**：reuse / quality / efficiency 三 agent 并行 review，按里程碑分节累积。
**用途**：判断"是否启动这些重构"的输入。每条都附 ROI 评估、改动面、风险点，便于按里程碑节奏挑选。

## 索引

- [§1 M2c-3 范围（2026-04-27 二轮）](#1-m2c-3-范围2026-04-27)
- [§2 M2c-2 范围（2026-04-27 二轮）](#2-m2c-2-范围2026-04-27二轮)
- [§3 M2c-1 范围（2026-04-27 二轮）](#3-m2c-1-范围2026-04-27二轮)
- [§4 M1 范围（2026-04-27 二轮）](#4-m1-范围2026-04-27二轮)
- [§5 M2d 范围（2026-04-29）](#5-m2d-范围2026-04-29)
- [§6 M2c-4 范围（2026-04-30）](#6-m2c-4-范围2026-04-30)
- [§7 M2 视觉收尾审计未选项（2026-05-03）](#7-m2-视觉收尾审计未选项2026-05-03)
- [§8 M3d 范围（2026-05-07）](#8-m3d-范围2026-05-07)
- [§9 M3e 范围（2026-05-09）](#9-m3e-范围2026-05-09)

---

## §1 M2c-3 范围（2026-04-27）

**分支**：feature/m2c-3（commit 8f655fb 已落地 7 处低悬果实，下面是当时记录暂不动的项）
**审查范围**：feature/m2c-3 vs main，109 文件、+13K 行

---

## 评估约定

- **ROI 高**：收益明显（去样板 / 防漂移 / 修真问题），改动面可控
- **ROI 中**：收益清晰但改动面较大，或受限于某项约束（测试断言、后端契约）
- **ROI 低**：v1 单用户场景下收益微小，仅在规模放大后才显化
- **风险**：低 = 纯重构；中 = 触发测试调整；高 = 跨层契约变更

---

## A. 表单层重复（前端）

### A1 · 合并 build-create-schema / build-edit-schema · ✅ 闭环

**M2c-4 已落地（PR-2，commit db9f946）**：Task 10 合并为 `buildAssetSchema(fieldDefs, { mode })`，Task 11 迁调用点。详细背景见 git log：`git show db9f946`。

---

### A2 · 抽 FieldShell 收敛 9 个 field-control 外壳 · ✅ 闭环

**M2c-4 已落地（PR-2，commit db9f946）**：Task 13 抽 `<FieldShell>`（含 `layout="inline"` prop 处理 bool-field 特例），Task 14 迁 8 个 field-controls。详细背景 `git show db9f946`。

---

### A3 · 合并 CheckoutDialog / ReturnDialog（抽 useFormDialog）

**位置**：`frontend/src/features/assets/detail/checkout-dialog.tsx` + `return-dialog.tsx`

**现状**：迁到 RHF+Zod 后两份 dialog 的 `useForm + zodResolver + handleOpenChange + onSubmit + try/setError('root') + InlineErrorBanner + DialogFooter` 高度同构；字段集不同（checkout: holder/location/note；return: note + currentCheckout 展示）。

**建议**：抽 `useFormDialog<T>({ schema, defaultValues, mutate, onSuccess })` hook，dialog 体只剩 fields。或更轻量的 `<FormDialog title onSubmit error pending>` 外壳。

**ROI**：中。两个 dialog 的样板减 ~30 行；但抽出后字段定义"间接化"，IDE 跳转链变长。

**风险**：低（vitest 已覆盖 checkout-dialog 2 case）。

**何时做**：M3 如新增第 3 个表单 dialog（如批量调拨），届时 3 倍化重复时再抽。当前 2 倍化值得放一放。

---

### A4 · `Control` 类型 cast 退化为 any · ✅ 闭环

**M2c-4 已落地（PR-2，commit db9f946）**：Task 15 `AssetFormFields` 与各 field-controls 改泛型 `Control<TFieldValues>`，消除 `as unknown as Control` 双重 cast。详细背景 `git show db9f946`。

---

## B. 状态切换样板（前端）

### B1 · 抽 useStateChangeRunner hook

**位置**：`frontend/src/features/assets/detail/asset-detail-page.tsx:60-72` + `state-change-alert.tsx:24-32`

**现状**：两条路径（`needsConfirm=false` 直接派发、`needsConfirm=true` alert 二次确认）各自重写 `mutateAsync → toast.success(verb 成功) → catch toast.error`。

**建议**：在 `state-change-actions.ts` 旁加 `useStateChangeRunner(asset)` hook，封装 mutation 调用 + toast + 错误处理；asset-detail-page 与 state-change-alert 都消费它。

**ROI**：中。去重 ~15 行 × 2 处；统一错误处理路径。

**风险**：低。

**何时做**：B1 + A3 可同期做（都属于"统一前端 mutation 调用 + toast 样板"主题）。

---

## C. 状态机兜底 & 后端契约

### C1 · checkout.py 与 state_machine 双层防御统一

**位置**：`src/asset_hub/services/checkout.py:31-40` 与 `:73-77`

**现状**：`checkout()` 先做精细 status 检查（IN_USE / RETIRED / MAINTENANCE）抛带文案的 StateError，紧接着又调 `assert_transition_allowed` 兜底——上面的 if-block 已覆盖所有非法 from_status，state_machine 这层永远不会触发。`return()` 同理。

**建议**：让 `assert_transition_allowed` 成为唯一 SoT；catch ValidationError 后按 from→to 映射文案，删 if-block。

**ROI**：中。消除"双 SoT 维护转换合法性"问题；未来加状态时只改 `ALLOWED_TRANSITIONS` 一处。

**风险**：中。`tests/unit/test_checkout_service.py` 的错误文案断言需同步更新。

**何时做**：M3 §14.6/14.7 状态机升级时一并做（spec 已登记升级路径）。

---

### C2 · asset.delete_asset cascade 事务边界

**位置**：`src/asset_hub/services/asset.py:188-204`

**现状**：cascade 删除附件时 `for att in att_svc.list(): att_svc.delete(att.id)` —— 每次 `delete()` 内部 commit + 查询 `any_with_sha256`，N 个附件 = N 次事务。

**建议**：把 cascade 整体放进单次事务（去掉内部 commit，最外层 `delete_asset` 一次 commit）；FS 文件删除批量做。

**ROI**：低。v1 单 asset 附件量预计 <10 张；事务边界优化对单用户场景收益微。

**风险**：中。改 `AttachmentService.delete` 事务语义会影响其它调用方（直接删单附件场景），需要拆 public 与 internal 两套接口。

**何时做**：当真出现批量删除场景时再做（目前 D17 决议显式约定 service 层 cascade，先满足正确性）。

---

### C3 · detail page 多查 type 列表

**位置**：`frontend/src/features/assets/detail/asset-detail-page.tsx:38-41` + `:94`

**现状**：详情页挂 4 个独立 query，其中 `useAssetTypesQuery()` 拉**全量 types** 仅为找出 `asset.type_id` 对应的 name。AssetRead 在 list 中已带 `type_name`（`assets-table.tsx:42`），detail DTO 没带。

**建议**：让后端 detail response 也补 `type_name`（已有 `type_name` relationship + lazy="joined"，加进 `AssetReadDetail` DTO 即可），删 `useAssetTypesQuery()` 调用。

**ROI**：中。少一个请求 + 少一个 react-query cache entry。

**风险**：低（后端契约扩字段，前端仍向后兼容）。

**何时做**：M3 详情页有改动时顺手做。

---

## D. 类型分层

### D1 · features/assets generated schema 类型直接当业务类型

**位置**：`frontend/src/features/assets/detail/state-change-actions.ts:1-6`（和其它若干处）

**现状**：`import type { components } from '@/api/generated/schema'` 后，`AssetStatus` / `AssetRead` 直接拿 generated 类型当业务类型。短期可工作，长期 `schema.d.ts` 重新生成（如后端 DTO 改名）后业务代码全 churn。

**建议**：在 `frontend/src/features/assets/types.ts`（新建）做一层 alias / re-export，业务代码只 import 这一层。

**ROI**：中。M3 接 `openapi-fetch` 或 `@hey-api/openapi-ts` 决策时（spec §13）会重新生成，届时该解耦层会显著降低 churn。

**风险**：低，但 churn 面广（需 grep 全前端替换 import）。

**何时做**：M3 做 openapi 客户端选型决策时一并做（spec §13 已登记待观察项）。

---

## E. 视图层

### E1 · AssetHeader 4×4 状态矩阵抽配置数组

**位置**：`frontend/src/features/assets/detail/asset-header.tsx:107-141`

**现状**：4 个状态分支硬编码主按钮 + IDLE 二级按钮；按钮 verb 部分走 `STATE_CHANGE_ACTIONS[k].verb`、部分走 `CHECKOUT_VERB`/`RETURN_VERB`，两套来源。`bg-emerald-600` 直接写死。

**建议**：
- 选项 A：把 primary button 配置（status → {verb, onClick, variant/className}）做成数组，render 时 `.map`
- 选项 B（reuse agent 反对）：硬抽数据驱动反而难读，控件布局逻辑不是数据

**ROI**：低。reuse agent 与 quality agent 看法分歧；当前 4 状态稳定，配置数组化收益有限。

**风险**：低。

**何时做**：暂不做。除非 M3 状态扩到 5+，届时 4 状态 → 5 状态分支硬写明显笨重时再抽。

---

## F. 其他轻微项

### F1 · `availableStateChanges` 静态预算表

**位置**：`frontend/src/features/assets/detail/state-change-actions.ts:59`

**现状**：每次 `asset-header.tsx:105` render 调用一次 `Object.entries + filter + map`。

**建议**：改 module-level `const AVAILABLE_BY_STATUS: Record<AssetStatus, StateChangeKey[]>` 静态预算表。

**ROI**：低。4 entry × 4 status 开销可忽略。

**何时做**：不做（除非未来 30+ 状态 × 几十 transition）。

---

### F2 · attachment-add-slot 批量超限 toast 聚合

**位置**：`frontend/src/features/assets/detail/attachment-add-slot.tsx:34`

**现状**：多文件超大时每个 file 都触发 `toast.error`——上传 5 个超限文件就 5 个 toast。

**建议**：批量超限时聚合一条 "X 个文件超过大小限制"。

**ROI**：低（UX 微改善）。

**何时做**：UX 复盘时顺手做。

---

### F3 · zodResolver 在 CreateForm 每次 render 重建 · ✅ 闭环

**M2c-4 已落地（PR-2，commit db9f946）**：Task 10 合并 schema builder 时一并把 `CREATE_EMPTY_SCHEMA` 提取为 module-level 常量。详细背景 `git show db9f946`。

---

## §1 总览（建议优先级）

| 优先级 | 项目 | 触发条件 |
|---|---|---|
| ✅ 已闭环 | A1 / A2 / A4 / F3 | M2c-4 PR-2（commit db9f946） |
| 🟢 顺手做 | B1 / C3 / F2 | 下次 form / detail / 上传相关改动时一并做 |
| 🟡 等里程碑 | A3 | M3 加新 form dialog（第 3 个）时启动 |
| ✅ 已闭环 | C1 | M3a PR-1 commit `42b6f46`（state_machine TRANSITION_RULES 单 SoT，service 层不再双层防御） |
| 🟡 已登记 | D1 | M3 openapi 客户端选型时一并做 |
| 🔴 暂不动 | C2 / E1 / F1 | 仅在规模放大或状态扩展时才有 ROI |

---

## §2 M2c-2 范围（2026-04-27 二轮）

**分支**：feature/m2c-3（m2c-2 已经过一轮 simplify 即 commit 08b2223；二轮在 m2c-3 完成后回头扫 m2c-2 引入但 m2c-3 未碰过的代码）
**审查范围**：m2c-2 commit 区间 6736007..08b2223 中、feature/m2c-3 上未被改写的 9 个核心文件
**已落地**：5 处修复（详见 m2c-2 simplify commit）
**视角**：reuse / quality / efficiency 三 agent 并行 review

### G. 未修条目

#### G1 · 7 处 mutation 工厂结构同质

**位置**：
- `frontend/src/api/hooks/checkouts.ts`：`useCheckoutMutation` / `useReturnMutation`
- `frontend/src/api/hooks/assets.ts`：`useCreateAsset` / `useUpdateAsset` / `useDeleteAsset` / `useChangeAssetStatusMutation`
- `frontend/src/api/hooks/attachments.ts`：`useDeleteAttachmentMutation`

**现状**：7 处全部是同一个壳：`useMutation` + `unwrap` + `onSuccess: invalidate(qk.assets.all) [+ invalidate(qk.assets.detail(id))] [+ toast]`。每处样板 5–8 行。

**建议**：抽 `useInvalidatingMutation({ mutationFn, invalidateKeys, successToast })` helper。

**ROI**：低。reuse agent 自己也归"不修"——onSuccess 失效集合各处略有差异（status mutation 多失效 history、checkout 不失效 history 因为它是 all 的子集），抽一层 helper 容易把这些注释掉的不变量丢失。

**风险**：中（需要把现存 invalidate 矩阵显式化为参数）。

**何时做**：M3 时如果再加新 mutation 让总数 ≥ 10，再考虑统一。当前 7 处稳定。

---

#### G2 · `invalidateQueries({ qk.assets.all })` 失效面过宽

**位置**：`frontend/src/api/hooks/checkouts.ts:37,59` 等多处

**现状**：checkout / return 成功后 `invalidate(qk.assets.all)` 会级联失效**所有** asset list 缓存（任意 search params）+ 所有 detail + 所有 history。`query-keys.ts:8-10` 注释里"history 嵌在 qk.assets.all 下让其级联"的设计反而是这里过宽的根源。

**建议**：只失效当前 detail + history + 列表汇总。`qc.invalidateQueries({ queryKey: qk.assets.detail(assetId) })` + `qk.assets.history(assetId)` + 一次列表 key。

**ROI**：低。v1 单用户百量级、tanstack-query 默认 staleTime 已限速；当下规模下"过宽"成本几乎不可感知。

**风险**：中（query-key shape 设计需要先动，否则 list 仍会被 all 级联）。

**何时做**：list 缓存条目 >10 或操作后真闪一下页面再动。

---

#### G3 · `general-fields.tsx` 是否该 schema-driven

**位置**：`frontend/src/features/assets/detail/general-fields.tsx`

**现状**：8 个固定字段硬编码 dl/dt/dd 渲染。

**建议**：考虑改为 schema 驱动（与 `CustomFields` 对齐架构）。

**ROI**：负。reuse agent + quality agent 都判定为不修——通用字段是 AssetRead 在 v1 的稳定面，每行格式订制点都不同（`CopyableText` only on SN/id、`whitespace-pre-wrap` only on notes、`<time>` only on dates），driver 配置反而比当前 JSX 长。

**何时做**：不做。

---

### §2 总览

| 优先级 | 项目 | 触发条件 |
|---|---|---|
| 🟡 观察 | G2 | 列表缓存 >10 或操作后真闪一下页面 |
| 🔴 暂不动 | G1 | M3 mutation 总数 ≥ 10 时再统一 |
| 🔴 决定不做 | G3 | reuse + quality agent 共识：抽象比当前 JSX 长 |

---

## §3 M2c-1 范围（2026-04-27 二轮）

**分支**：feature/m2c-3（m2c-1 已经过一轮 simplify 即 commit 08b2223；二轮在 m2c-3 完成后回头扫 m2c-1 引入但 m2c-2 / m2c-3 都未碰过的代码）
**审查范围**：m2c-1 commit 区间 2ea07ce..1e1bf0c 中、feature/m2c-3 上未被改写的 22 个核心文件（数据层 + util + 布局 + 主题 + feedback + 状态 + 列表页周边）
**已落地**：5 处修复（详见 m2c-1 simplify commit）
**视角**：reuse / quality / efficiency 三 agent 并行 review

### H. 未修条目

#### H1 · 抽 `<CenteredPanel>` 整合 4 个占位组件

**位置**：
- `frontend/src/components/feedback/error-boundary.tsx:32-46`（fallback UI）
- `frontend/src/components/feedback/error-state.tsx`
- `frontend/src/components/feedback/empty-state.tsx`
- `frontend/src/features/assets/detail/not-found-panel.tsx`

**现状**：四者都是 "icon + 标题 + 副文本 + 可选按钮 + 居中 py-XX" 同一模板，类名、间距、高度一致，仅图标 / 文案 / 按钮不同。

**建议**：抽 `<CenteredPanel icon title description action />` 或 `<StatusPanel variant="empty" | "error" | "not-found" />`，四处复用；至少把 ErrorBoundary 的 fallback UI 复用 ErrorState 组件。

**ROI**：中。去重 ~80 行；但波及 ErrorBoundary（class component）需要谨慎。

**风险**：中（ErrorBoundary 的 fallback 路径要确保抽出后仍 SSR-safe）。

**何时做**：M3 时如果再加新占位场景（5 个）触发"重复 5 倍化"再抽；当前 4 倍化勉强可忍。

---

#### H2 · `assets-filters.tsx` 双套防抖 / commit 逻辑统一

**位置**：`frontend/src/features/assets/list/assets-filters.tsx:30-50` 与 `:134-167`

**现状**：q 字段走 `useState + debounce(300) + useEffect 拉回外部` 模式；holder 字段走 `HolderInput` 的 `lastCommittedRef + onBlur/Enter` 模式。两种"本地 state + URL 单一事实"协调机制并存。

**建议**：统一为一种（建议 holder 也走 debounce 与 q 一致），或抽 `useDebouncedUrlField(key, urlValue)` 公共 hook。

**ROI**：低。两种模式语义有差异（q 高频联想搜索 vs holder 输入完才提交）；强制统一会丢掉 holder 的 commit-on-blur 语义。

**风险**：低（纯前端 + URL state）。

**何时做**：当再加第 3 个 filter 字段时（届时若也是 commit-on-blur 会让 q 显得更孤立）再考虑。

---

#### H3 · `error.ts` 的 `STATUS_MESSAGES` 中 409 / 422 dead fallback

**位置**：`frontend/src/lib/error.ts:14-18`

**现状**：`STATUS_MESSAGES` 列了 404 / 409 / 422，但 409 / 422 在 `toFriendlyMessage` 里被前置短路（有 detail 时拼自定义文案，无 detail 才落 map），FastAPI 返回的 409 / 422 一定带 detail，所以 map 里 409 / 422 是 dead fallback。

**建议**：删 409 / 422 条，留 404；或保留作防御兜底文案。

**ROI**：负。删了反而失去对"理论上后端无 detail"的覆盖。

**何时做**：不做。仅作记录。

---

#### H4 · `error.ts` `unwrap` / `unwrapVoid` 签名暴露 openapi-fetch 三元组

**位置**：`frontend/src/lib/error.ts:33,42-46,54`

**现状**：入参直接是 openapi-fetch 的 `{ data, error, response }` 三元组结构。当下不是问题，但若以后想换底层（如 Axios），三处签名都得改。

**建议**：把入参类型抽成 `OpenapiFetchResult<T>` 别名集中放 `client.ts`。

**ROI**：低。集中后面对换底层时少一处改。

**何时做**：spec §13 待观察项中 openapi 客户端选型有变更时一并做。

---

#### H5 · `column-visibility.tsx` 每次 toggle 同步写 localStorage

**位置**：`frontend/src/features/assets/list/column-visibility.tsx:71-73`

**现状**：每次 visible 变 → 写一次 localStorage（含 JSON.stringify 9 个布尔）。hot path 上每次 toggle 都同步 I/O。

**建议**：节流或合并写。

**ROI**：负。9 个布尔的 stringify + setItem 微秒级，且 toggle 是低频用户操作。

**何时做**：不做。

---

#### H6 · `assets-filters.tsx` debounce timer 无 cleanup

**位置**：`frontend/src/features/assets/list/assets-filters.tsx:37-45`

**现状**：q 输入的 `useMemo(() => debounce(...), [navigate])` 创建了 debounce，但组件 unmount 时无 timer cleanup——理论上卸载后仍可能触发一次 navigate。

**建议**：在 useEffect cleanup 里清 timer（`debounce.ts` 暂未暴露 cancel API）。

**ROI**：低。列表页 filter 组件几乎和路由同生命周期，导航切换时 router 已 unmount，泄漏窗口极小。

**何时做**：未来 `debounce.ts` 加更多调用方 / 加 cancel API 时一并做。

---

### §3 总览

| 优先级 | 项目 | 触发条件 |
|---|---|---|
| 🟡 等里程碑 | H1 | 占位场景 ≥ 5 个或新增 5th 占位组件时启动 |
| 🟡 等里程碑 | H2 | 加第 3 个 filter 字段时考虑 |
| 🟡 已登记 | H4 | spec §13 openapi 客户端选型变更时一并做 |
| 🔴 暂不动 | H6 | `debounce.ts` 加 cancel API 时一并做 |
| 🔴 决定不做 | H3 / H5 | 防御性 / 微优化，删除或修复反而失去当前优势 |

---

## §4 M1 范围（2026-04-27 二轮）

**分支**：feature/m2c-3（m1 已经过一轮 simplify 即 commit cdb2587 "审查 m1/m2a/m2b——集中 CLI 域异常映射 + 抽公共 helper"；二轮在 m2c-3 完成后回头扫 m1 引入但后续里程碑核心逻辑未改写的代码）
**审查范围**：m1 commit 区间 4b2d9e0..6651d92 中、feature/m2c-3 上未被改写核心逻辑的 11 个文件（后端核心 + CLI + API + 测试基础设施 + 脚本）
**已落地**：2 处修复（详见 m1 simplify commit）
**视角**：reuse / quality / efficiency 三 agent 并行 review

### I. 未修条目

#### I1 · `validation.py` 缺 url / multi-enum / int min/max — **真实功能缺口**

**位置**：`src/asset_hub/services/validation.py:26-53`

**现状**：后端 `_coerce` 只支持 `string / text / int / float / bool / enum / date` 7 类；前端 m2c-3 引入的 `url`、`multi-enum` 类型（`field-def-to-zod.ts:28-78`）能通过前端校验、提交到后端会落到 `raise ValidationError("未知字段类型: {t}")`。`int / float` 的 `min / max`（前端 FieldDef 已支持）在后端也未校验。

**建议**：补 `url`（正则或 `urllib.parse.urlparse` 校验 scheme/netloc）、`multi-enum`（list[str]、每个 ∈ options）、`int / float` 的 min/max 检查；同步补 unit test。

**ROI**：高。这是**双源不一致 + 真实功能缺口**——AssetType.code_prefix 已是 m2c-3 的字段，custom_fields 用户能定义 url / multi-enum 类型，但 register / update 会被后端拒。属于 bug。

**风险**：低（纯加分支 + 测试，不改既有行为）。

**何时做**：**不归 simplify，应单独开 fix PR / issue 跟踪**。优先级高于其他 followup，因为是用户可触发的运行时错误。

---

#### I2 · `validation.py` Stringly-typed dispatch + 顺序 if 链 → 表驱动

**位置**：`src/asset_hub/services/validation.py:30-53`

**现状**：6 个分支用裸字符串比较（"string"/"int"/...）。AssetType.custom_fields 是 `list[dict]` 无 schema 约束，整套体系是无约束的字符串协议；7 层平铺 `if t == "..."` 已临界。

**建议**：(a) 引入 `FieldType(str, Enum)` 集中所有类型字面量；(b) `dispatch: dict[FieldType, Callable[[Any, dict], Any]]` 表驱动替换 if 链。

**ROI**：中。一次性把"字段类型"作为一等概念建模；与 I1 一起做最划算（届时正好新增 url / multi-enum 也要进 enum）。

**风险**：中。FieldType 加入后，前端 generated schema.d.ts 会同步，AssetTypeService 和 AssetService 调用点也需要 audit；测试可能需要从字符串改 Enum 引用。

**何时做**：与 I1 合并做。一个 PR 同时引入 Enum + 补 url/multi-enum/min/max。

---

#### I3 · `db.py:get_engine` 的 `settings` 参数语义误导

**位置**：`src/asset_hub/db.py:13-24`

**现状**：模块级 `_engine` + `reset_engine()` 是为测试 monkeypatch 而生（见 `tests/cli/conftest.py:9`）。`get_engine(settings=...)` 参数仅在第一次调用生效，第二次起被静默忽略——签名误导。

**建议**：要么删 `settings` 参数（永远从环境读），要么文档化"仅首次有效"。

**ROI**：低。当下不影响功能，仅是 API 噪音。

**风险**：中（测试和 alembic 已绕开此函数，改 signature 会触发 fixture 链式调整）。

**何时做**：当真有人误用 `settings=` 参数时再修。

---

#### I4 · `api/deps.get_session` 与 `cli/deps.cli_session` 重复

**位置**：`src/asset_hub/api/deps.py:13-15` 与 `src/asset_hub/cli/deps.py:13-16`

**现状**：两份 `with Session(get_engine()) as session: yield session` 等价，前者裸 generator 给 FastAPI `Depends`，后者 `@contextmanager` 给 CLI 用。

**建议**：在 `db.py` 提供 `session_scope()` 共用，两处再各自薄包一层。

**ROI**：负。两份各 3 行，FastAPI 习惯 generator + Depends，CLI 习惯 contextmanager，强行统一会牺牲类型清晰度。

**何时做**：不做。

---

#### I5 · `tests/conftest.py` 与 `tests/api/conftest.py` engine/session 构造重复

**位置**：`tests/conftest.py:5-15` + `tests/api/conftest.py:14-23`

**现状**：两处独立写"建临时 sqlite + create_all"逻辑。api 层未复用顶层 `engine` fixture（合理，因为它要 monkeypatch env 后再 override `get_session`），但 create_all 仍重复。

**建议**：抽 `_make_test_engine(tmp_path) -> Engine` helper 放 `tests/conftest.py`。

**ROI**：负。每个 conftest <30 行，复用收益有限。

**何时做**：不做。

---

#### I6 · `cli/main.py` 模块级 import 拖慢首次响应

**位置**：`src/asset_hub/cli/main.py:1-10`

**现状**：模块级 import 三个 `*_cmd` 子 app，每个会拉链 service / SQLModel / pydantic。Typer CLI 冷启动 ~300-500ms 主要来自 SQLModel/SQLAlchemy import。

**建议**：lazy-load 子 app（Typer 不天然支持）。

**ROI**：负。Agent 调用频率不高，单次百毫秒可接受；lazy-load 复杂度远高于收益。

**何时做**：不做。

---

### §4 总览

| 优先级 | 项目 | 触发条件 / 状态 |
|---|---|---|
| ✅ **已完成（M2d Phase 0）** | I1 | M2d 落地于 `feature/m2d-validation`：补 url/multi-enum/int+float min/max 校验 + 4 + 5 + 6 unit tests |
| ✅ **已完成（M2d Phase 0）** | I2 | M2d 落地于 `feature/m2d-validation`：引入 `FieldType StrEnum` + 表驱动 dispatch（`_DISPATCH: dict[FieldType, Callable]`），与 I1 合并到同一 PR |
| 🔴 决定不做 | I3 / I4 / I5 / I6 | 协议差异 / 收益微小 / lazy-load 复杂度过高 |

---

## 决策原则记录

落地修复的共同特征：
- **改动面 ≤ 单文件局部**（少数跨 3 文件，但都是 alias / 常量提取性质）
- **零行为变更**（删未消费常量、防御性代码简化、useMemo 包裹、no-op guard、replace 等价 idiom）
- **零测试 / 极少测试调整**

未做的项普遍卡在以下一项或多项：
- 跨 5+ 文件的签名/import 改动（A1 / A2 / A4 / D1 / H1）
- 触发测试断言文案调整（C1 / I2 部分）
- 涉及后端 DTO 契约（C3 部分 / I2 触发 generated schema 同步）
- 收益与 v1 单用户规模不匹配（C2 / E1 / F1 / G1 / G2 / H5 / H6 / I3 / I4 / I5 / I6）
- agent 间共识"抽象比现状更糟"（G3 / H3）
- 等待外部决策（H4 等 openapi 客户端选型）

**例外**：I1 是真实功能缺口（前端能过、后端必拒），属于用户可触发的运行时错误，应单独开 fix PR / issue 跟踪，**不归在"暂不动"分类下**。✅ **已在 M2d Phase 0 闭环**（与 I2 合并实施）。

后续启动重构时按"触发条件"列对照即可，不必重新评估。

---

## §5 M2d 范围（2026-04-29）

**分支**：`feature/m2d-review-fixup`（commit `db60189` 已落地 4 处低悬果实，下面是当时记录暂不动的项）
**审查范围**：自 b811e07（M2d plan）到 481d3d7（feature/m2d-serve 合并），约 3150 行新增（含测试），生产代码 ~1300 行
**视角**：reuse / quality / efficiency 三 agent 并行 review

### J. 已落地（参考 commit `db60189`）

- pid.read_pid_state 抽 `_stale()` builder + 复用单一 psutil.Process 实例（合并 Quality HIGH PidState 5 ctors + Efficiency F3）
- pid.PidState 删 derivable `process_alive` 字段
- lifecycle._rollback_start → `_rollback_spawned`：直接拿已 spawn 的 (service, pid) list（Efficiency F2）
- logs.tail_lines clamp `--lines` 到 50000 上限（Efficiency F6）

### K. 未修条目

#### K1 · serve envelope 与项目 CLI envelope shape drift — **HIGH 优先级 follow-up**

**位置**：
- `src/asset_hub/cli/serve/output.py::render_json_envelope` + `serve/cmd.py::_emit_success/_emit_error`
- vs `src/asset_hub/cli/envelope.py::success_envelope/error_envelope/print_result/print_error`

**现状**：serve 命令的 JSON 信封 `error` 字段为结构化 `{"code": "serve.xxx", "message": "..."}`；其他 CLI 命令（asset/type/attachment）的 `error` 字段为 plain string。同一个 `asset-hub` 二进制的两套 envelope 形态对 Agent 消费者是 silent contract drift。

**建议**：扩 `envelope.py` 的 `error_envelope`/`print_error` 接受可选 `code=` 参数；migrate 既有 `handle_domain_errors` 把 domain 异常类名映射成 code（如 `domain.NotFoundError`）。serve cmd.py 删 `_emit_*` + `output.py::render_json_envelope`，统一走 envelope.py。

**ROI**：高（统一契约对 Agent-Native 项目意义大）。**风险**：中——需修改既有 CLI 命令的 envelope shape，触发现有 CLI tests 调整。

**何时做**：M3 SKILL.md 完善同周期（届时 SKILL.md 要文档化所有 CLI 的 JSON 输出，正好统一一次）。

---

#### K2 · cmd.py 5 子命令重复 try/except/_emit 壳

**位置**：`src/asset_hub/cli/serve/cmd.py:42-160`（start / stop / restart 三处近重复）

**现状**：每条命令都是 `try lifecycle.xxx() / except ServeLifecycleError as e / _emit_error(... code=e.code)` 6 行模板。

**建议**：抽 `_run_lifecycle(json_out, fn, *, plain_renderer, data_fn, metadata_fn)` 装饰器或 helper。3 命令各省 ~6 行 → 共省 ~18 行。

**ROI**：中。3 命令的重复未达"5 倍化"抽象阈值；加装饰器后字段定义"间接化"，IDE 跳转链变长。

**何时做**：未来 serve 子命令扩到 7+（如加 `serve doctor` / `serve build`）时考虑。

---

#### K3 · lifecycle.start_service 110 行 / 6 phase 单函数

**位置**：`src/asset_hub/cli/serve/lifecycle.py:31-141`

**现状**：phase 0-5 全集中在一个函数；已有 `# Phase 0 · ...` 注释提示分段。

**建议**：拆 5 私有 helper（`_preflight_or_raise` / `_build_if_needed` / `_rotate_logs` / `_spawn_processes` / `_health_probe_or_rollback`），主函数压缩为 5 行 orchestration。

**ROI**：中。可读性提升；但 phase 边界共享变量较多（`backend_pid` / `frontend_pid` / `started_at` / `host` 等），拆完后 helper 签名臃肿。

**何时做**：未来 start_service 再加新 phase（如 §A.1 的 `serve doctor` 集成 / `serve build` 剥离）时启动。

---

#### K4 · stringly-typed mode/service literal

**位置**：`cmd.py:52,131,175`（手写 `mode not in ("dev","prod")` / `service not in ("backend","frontend","all")` 校验 3 处）

**现状**：repeated literal validation；与项目已有 StrEnum 风格（`AssetStatus` / `PidStateStatus`）不一致。

**建议**：定义 `ServeMode(StrEnum)` 与 `ServiceTarget(StrEnum)`，让 Typer 通过 Enum 注解自动校验（Typer 原生支持），删 3 处手写检查。

**ROI**：中。typed safer；但 Typer 的 Enum 对 `--mode dev` 和 `--mode ServeMode.DEV` 输出格式不同，可能触发 help 文案变化。

**何时做**：与 K2 装饰器同期做（统一在 cmd.py 一次扫荡）；或未来 mode/service 取值再扩时启动。

---

#### K5 · `_build_status_info` 返回 untyped dict

**位置**：`src/asset_hub/cli/serve/lifecycle.py:_build_status_info` 返回 `dict[str, Any]`；`StatusReport.backend/frontend: dict[str, Any] | None`

**现状**：与同模块 `ServiceInfo` dataclass 不对称（start 用 typed dataclass，status 用 raw dict）；`render_plain_status` 读 `info["status"]` / `info["pid"]` 失去类型检查。

**建议**：定义 `StatusInfo` dataclass（`status: Literal["running","stale"]` / `pid: int` / `port: int` / `uptime_sec: int` / `healthy: bool`），与 `ServiceInfo` 平行。`StatusReport.backend/frontend: StatusInfo | None`。

**ROI**：低 - 中。类型安全；但 `_build_status_info` 是模块内部函数，外部消费者只有 `render_plain_status` + `to_dict()` —— 当前 raw dict 已被 dataclass-likeshape 约束，typo 风险低。

**何时做**：M3 时 status 命令如新增字段（如 `latency_p50`）时一并 typed 化。

---

#### K6 · 3 处 (backend, frontend) 循环重复

**位置**：
- `lifecycle._check_pids_or_clean_stale:158-169`
- `lifecycle.stop_service:202-231`
- `lifecycle._rollback_spawned`（已落地 db60189 改用 spawn list 形式，**已部分缓解**）

**现状**：每处都是 `for service in ("backend", "frontend"): f = settings.pids_dir / f"{service}.pid"; state = pid_mod.read_pid_state(...)`。

**建议**：抽 `_iter_service_states(settings: Settings) -> Iterator[tuple[str, Path, PidState]]` generator 共享。

**ROI**：低。3 处循环都很短（每处 5-10 行），抽出后 helper 签名比 inline 更绕。

**何时做**：未来 service 数量扩展（如加 prometheus-exporter 等第三个服务）时启动。

---

#### K7 · validation `_coerce_int` 与 `_coerce_float` 95% 同构

**位置**：`src/asset_hub/services/validation.py:33-50`

**现状**：两 helper 仅 `int` / `float` 构造器不同；其他 try/except + `_check_range` 完全一致。

**建议**：抽 `_coerce_numeric(value, spec, ctor)` helper；`_DISPATCH[FieldType.INT] = lambda v,s: _coerce_numeric(v,s,int)`。

**ROI**：低。15 LOC saving；但 lambda dispatch 可读性下降。

**何时做**：未来加 `decimal` / `complex` 等第 3 种数字类型时启动。

---

#### K8 · Settings 在 restart 路径多次实例化

**位置**：`lifecycle.py:307` (restart) → `:203` (stop) → `:40` (start)

**现状**：单次 restart 命令产生 3 次 `Settings()` 实例化（每次重读 .env + 跑 Pydantic 校验）。

**建议**：`stop_service`/`start_service` 加可选 `settings: Settings | None = None` kw-only 参数；`restart_service` 实例化一次传入。

**ROI**：低。微优化 v1 无影响（毫秒级）；代码清洁度边际收益。

**何时做**：v1 不做。未来如 serve 命令吞吐量成为瓶颈（极不可能）再考虑。

---

#### K9 · cmd.py logs 命令直接 reach 进 Settings

**位置**：`src/asset_hub/cli/serve/cmd.py:189` —— `path = Settings().logs_dir / f"{service}.log"`

**现状**：其他 cmd 函数都通过 lifecycle 模块；logs --follow 路径单独 reach 进 Settings 拼路径。

**建议**：在 `lifecycle.py` 加 `log_path_for(service)` helper，cmd 调它即可（logs_for_service 返回 dict，但 follow 路径需要 Path 而不是 lines list）。

**ROI**：低。一致性微改善。

**何时做**：与 K2 / K3 同期做。

### §5 总览

| 优先级 | 项目 | 触发条件 |
|---|---|---|
| 🔴 **高优先级 follow-up** | K1 | M3 SKILL.md 完善同周期 — 统一项目级 CLI envelope 契约 |
| 🟡 等里程碑 | K2 / K3 / K4 / K9 | serve 子命令再扩（doctor / build）或 cmd.py 大改时一并启动 |
| 🟡 等里程碑 | K5 | M3 status 命令加新字段时启动 |
| 🔴 暂不动 | K6 / K7 / K8 | 触发条件远未到 |

---

## §6 M2c-4 范围（2026-04-30）

**分支**：`feature/m2c4-form-infra`（PR-2 form infra 阶段，Task 11 code-quality review approve with one ask）
**审查范围**：A1 合并 `buildCreateSchema` / `buildEditSchema` → `buildAssetSchema(fieldDefs, { mode })`（Plan §Task 10）+ Task 11 迁 asset-create/edit-form
**视角**：reviewer 单视角（PR-2 quality review）

### J · `buildAssetSchema` 条件 .extend 三元导致 zod inference 丢 type_id

> **⏳ 待处理**：cast 已加注释 + 属于 spec 阶段预知的 trade-off（非工程失误）。M2c-4 PR-3 Task 27 在 `type-form.tsx` 又重现一次同款（commit d8e0b82 `as unknown as Resolver<>`），证明问题持续。建议与 §L 同周期作单独小 PR 解决。

**位置**：`frontend/src/features/assets/form/build-asset-schema.ts` + `asset-create-form.tsx` + `frontend/src/features/types/form/type-form.tsx`（PR-3 同款 cast）

**现状**：A1 把 `buildCreateSchema` / `buildEditSchema` 合并为 `buildAssetSchema(fieldDefs, { mode })`。条件三元 `mode === 'create' ? withCustom.extend({ type_id }) : withCustom` 让 zod 的 TS inference 在 `mode='create'` 时丢 `type_id`。

**症状**：`asset-create-form.tsx` 引入 2 处 cast：
- `resolver: zodResolver(CREATE_EMPTY_SCHEMA) as unknown as Resolver<CreateFormValues>`
- `parsed.data as CreateFormValues`（onSubmit 内）

EditForm 不需要 cast（`EditFormValues = Omit<CreateFormValues, 'type_id'>` 与 inferred shape 一致）。

**消除方案候选**（M2c-4 review 期评估，最终未选）：
- **路径 A · 拆 builder**：split 回 `createAssetSchema(fieldDefs)` + `editAssetSchema(fieldDefs)` 两函数，`z.infer` 直接工作。代价：A1 主张的"merged single builder"被回退；但公共 API 仍可分两个窄函数。reviewer 推荐方案。
- **路径 B · 函数重载 + 条件类型**：`buildAssetSchema<M extends Mode>(...)` + `SchemaFor<M>`。代价：类型体操重 + 函数体内仍需 cast 让 TS 接受三元返回；reviewer 不推荐。

**何时做**：post-M2c-4 单独小 PR，或 `A4 后续清理` 周期。Task 15 (A4) 范围限于 `Control<TFieldValues>`，不会顺手消除这两处 zod-inference cast。

**ROI**：低。2 cast 已加 inline 注释 + 引用 `build-asset-schema.ts` M1/M2 doc + Plan §Task 10。是被 spec 阶段 design 决议预知的 trade-off，不是工程失误。

---

### K · `acquired_at` 顶层字段 vs `custom_data` 写入路径不一致 · ✅ 闭环

**M2 收尾落地（2026-05-03，commit 8c8202f）**：FieldShell 加 `pathPrefix?: 'custom_data' | 'root'` prop（默认 `'custom_data'` 保留 8 处 custom-field 行为），DateField 透传，general-fields-form 在 acquired_at 处传 `pathPrefix='root'`。新增 field-shell pathPrefix 单测 2 case + asset-create-form integration 测试作为回归保护。Playwright 烟测验证 POST/PATCH body 中 `acquired_at` 落根路径。详细背景见 `git show 8c8202f`。

---

### L · `build-asset-schema` 双函数 vs 条件 `.extend`（扩展 §J）

> **⏳ 待处理**：与 §J 同根；建议同 PR 解决。`build-type-schema.ts` 也用了同款 union pattern，统一抽 builder 时一并处理。

**位置**：`frontend/src/features/assets/form/build-asset-schema.ts`

**现状**：§J 已登记的"条件 `.extend` 三元导致 zod inference 丢 `type_id` → 引入 2 处 cast in `asset-create-form`"。本条是 §J 的延续：明确候选解决方案。

**候选**：拆为 `buildCreateAssetSchema` + `buildEditAssetSchema` 两个窄函数（reviewer 推荐 path A）。公共 base 仍可抽 helper，但对外暴露双函数让 `z.infer` 直接工作。

**何时做**：与 §J 同周期处理；可能是同一 PR。

**ROI**：中。消除 2 cast + 让 TS inference 直接拿到 `type_id` shape。

---

### M · `useWatch` 重复订阅 + `Path<T>` cast 链路

> **⏳ 待处理**：与 §L 同 PR 处理（一并清理 form-fields 类型链路）。

**位置**：
- `frontend/src/features/assets/form/asset-form-fields.tsx:29-30`（`useWatch` type_id）
- `frontend/src/features/assets/form/asset-create-form.tsx:44`（同 field 第二处 `useWatch`）
- `frontend/src/features/assets/form/general-fields-form.tsx`（6 处 `as Path<T>` cast）

**现状**：
- Edit 模式下 `asset-form-fields` 仍订阅 `type_id` 但 `forceTypeId` 短路；
- Create 模式下 `asset-create-form` 已 `useWatch type_id`，`asset-form-fields` 又 `useWatch` 同 field — RHF 内部各自 sub，触发两次 re-render。
- `general-fields-form` 6 处 `as Path<T>` cast 因为泛型 `T extends FieldValues` 太宽，TS 推不出 path 字面量是 `T` 的合法 path。

**候选**：
- Hoist `type_id` watch 到 `asset-create-form`，通过 prop 传 `selectedType` 给 `asset-form-fields`，删 `asset-form-fields` 内部 `useWatch`
- `GeneralFieldsForm` 加 `T extends FieldValues & AssetBaseFields` 约束（其中 `AssetBaseFields` 列出 `acquired_at` / `serial_number` 等通用字段），消除 6 处 cast

**何时做**：与 §L 同 PR 处理（一并清理 form-fields 类型链路）。

**ROI**：中。性能微优化（去重一次 sub）+ 类型清晰度提升。

---

### N · `field-${def.key}` id 模板字符串重复 9 处

> **⏳ 待处理**：M3 加新 field-control 时一并做。注意 PR-3 `field-attribute-form` 也有 `field-${index}-<attr>` 模式（11 处 htmlFor）— 抽 helper 时把 types 端也覆盖。

**位置**：8 个 `field-controls/*.tsx` + `field-shell.tsx` 内的 `htmlFor` 都写 `` `field-${def.key}` ``。

**候选**：`FieldShell` 通过 `children` render-prop 多传一个 `inputId` 形参，`field-controls` 直接消费 `inputId` 而不再各自拼模板。

**何时做**：不紧迫；M3 加新 field-control 时一并做。

**ROI**：低。9 处微重复；当前稳定运行，抽出后 children render-prop 多一个 destructure 字段，可读性微降。

---

### O · `MultiEnumField` checkbox-grid `<div>` 上的 `id` 不可点击 — **a11y 微回归**

> **⏳ 待处理**：与 §N 同周期。

**位置**：`frontend/src/features/assets/form/field-controls/multi-enum-field.tsx:31`

**现状**：pre-PR 即存在；T14 重构（用 FieldShell）未引入新 bug。但 `<FormLabel htmlFor="field-${key}">` 指向的是承载 grid 的 `<div>`，div 不 focusable，点击 label 不会聚焦到任何 checkbox（label-input 关联失效）。

**候选**：用 `role="group"` + `aria-labelledby` 替代 `label htmlFor` → grid 容器；或拆出每 checkbox 独立 `<label>`。

**何时做**：与 §N 同周期。

**ROI**：低。a11y 微改善；当前键盘导航仍可工作（Tab 进入第一个 checkbox），仅 click-on-label 失效。

---

### P · NavBar 导航激活态在 `/types` 真实存在后 fuzzy match 出错 · ✅ 闭环

**M2c-4 PR-3 Task 35（commit 77caf01）已修复**：NAV_ITEMS 加 per-item `fuzzy` 字段，根 `/` 改 exact match，`/types` 保 fuzzy 前缀匹配——双 active 错乱消除。详细背景 `git show 77caf01`。

---

### Q · `TypeRead` 缺 `ref_count` 字段 → 前端 N+1 query · ✅ 闭环

**M2 收尾落地（2026-05-03，commit 03cafea + bdcc2f6）**：后端 TypeRead 加 `ref_count: int = 0` 字段；TypeService 改返回 TypeRead DTO，list_types 一次 GROUP BY 查 counts，get/create/update 单条 count_refs；TypeRepository 加 `count_assets_grouped_by_type()` 批量方法。前端 `RefCountCell` + `TypeDeleteDialog` 改读 `type.ref_count`，删除 `useTypeRefCount` workaround hook + delete-dialog refError 三态崩溃。Playwright 烟测验证 `/types` 列表只发 1 次 `GET /api/types`，N+1 消除；delete dialog 在 ref_count=3 显示禁用按钮 + "仍有 N 个资产引用"。详细背景见 `git show 03cafea bdcc2f6`。

---

### R · 表单 `form.reset(apiResponse)` 路径缺少 null-field MSW 测覆盖

> **⏳ 待处理（防御性测试）**：M2c-4 PR-3 烟测 S5 发现 (commit f2d11cc)。

**位置**：所有 RHF 编辑表单的 `useEffect(() => form.reset(initial), [initial])` 路径，目前已知：
- `frontend/src/features/types/form/type-form.tsx`（PR-3 已修，加了 `coerceFieldDefsForRHF` 归一化）
- `frontend/src/features/assets/form/asset-edit-form.tsx`（未验证是否有同款风险）

**现状**：API 返 nullable 字段为 `null`；zod schema 用 `.optional()` 接受 `undefined` 拒 `null`。`form.reset(apiResponse)` 直接喂入会让 `handleSubmit` → resolver 静默失败，submit 无任何 UI 反馈。PR-3 烟测用 Playwright MCP 才捕获，单测全绿仍漏检。

**候选**：
- 任何 `form.reset(api)` 路径在 `tests/hooks/<form>.test.tsx` 加专测：MSW handler 返带 null 字段的 payload，断言点 Save 后 mutation 成功 fire
- 长期：抽 `useFormFromApi(initialQuery, { coerce })` hook 把归一化封装一次，所有 form 共用

**何时做**：低优先；任何编辑表单加新 nullable 字段或新增 form 时同步加测。

**ROI**：高（防 silent failure 复现）/ 工作量中。

---

### S · `useArrayFieldController` helper 抽取（避 RHF nested as-never 扩散）

> **⏳ 待处理（条件触发）**：M2c-4 PR-3 final review 提示。

**位置**：`frontend/src/features/types/form/custom-fields-builder/field-attribute-form.tsx`（16 处 `as never` on `Controller name=` props）+ 同款 cast 在未来任何 array-of-objects 表单都会复现。

**现状**：RHF `Controller` `name` prop 要求字段 path 字面量在 union 内，但 `${path}.${attr}` 模板字符串经 `useFieldArray` index 后无法被 `Path<T>` 推出，只能 `as never` 强转。当前 PR-3 集中在 1 个文件、bounded scope，不是 maintainability 危机。

**触发条件**：第 4 个含 array-of-objects sub-field 的表单出现时（候选场景：批量 asset import / type schema diff editor），抽 generic helper：

```ts
// 草案
function useArrayFieldController<T extends FieldValues>(
  arrayPath: string,
  index: number,
) {
  return {
    name: <Attr extends string>(attr: Attr) => `${arrayPath}.${index}.${attr}` as Path<T>,
  };
}
```

调用：`<Controller name={f.name('key')} ... />`，cast 收敛在 helper 内一处。

**何时做**：触发条件出现时启动。当前不动避免 over-engineering（YAGNI）。

**ROI**：低（短期）/ 中长期防 cast 蔓延。

---

### T · `TypesPage` 空状态可复用 `EmptyState` 组件

> **⏳ 待处理（trivial）**：M2c-4 合并后整体 review 新发现（2026-05-03）。

**位置**：`frontend/src/features/types/list/types-page.tsx:37-45`

**现状**：内联 `flex flex-col items-center gap-3 py-16 ...` + `Inbox` icon + `Button asChild Link to="/types/new"`，与 `frontend/src/components/feedback/empty-state.tsx`（已暴露 `title`/`description`/`action` props）逻辑相同。

**候选**：`<EmptyState title="还没有类型" action={<Button asChild><Link to="/types/new">创建第一个类型</Link></Button>} />`

**何时做**：Types 列表下次改 UI 时一并；不紧迫。

**ROI**：低。10 行去重 + 跨 feature 一致性。

---

### U · `NotFoundPanel` 抽到 `components/feedback/`（第 2 次出现，trigger 已 fire）

> **⏳ 待处理（worth-fixing）**：M2c-4 合并后整体 review 新发现（2026-05-03）。

**位置**：
- `frontend/src/features/assets/detail/not-found-panel.tsx`（首次，asset 专用）
- `frontend/src/features/types/detail/type-detail-page.tsx:21-31`（M2c-4 PR-3 新增内联同款 `SearchX + h2 + p + 返回 Button`）

**候选**：lift `NotFoundPanel` 到 `frontend/src/components/feedback/not-found-panel.tsx`，参数化 `title`/`description`/`backTo`/`backLabel`，asset/type 详情页都消费。

**何时做**：M3 加第 3 个详情页之前就该做（2 倍化 + 同质度高，trigger 已 fire）。

**ROI**：中。约 15 行去重 + 防 M3 第 3 次 inline 复制。

---

### V · `TypeRead` 类型别名跨 6+ 文件重复声明

> **⏳ 待处理（trivial）**：M2c-4 合并后整体 review 新发现。

**位置**：`api/hooks/types.ts:7` + `features/types/{form/type-form,list/types-page,list/types-table,detail/type-delete-dialog,detail/type-summary-card}.tsx` 各 1 处 + `AssetTypeRead` 在 `asset-form-fields.tsx:8` `general-fields-form.tsx:9`。

**候选**：`frontend/src/features/types/types.ts` 集中 `export type TypeRead = components['schemas']['TypeRead']`。属于 §3 D1（generated-schema-shielding）但 TypeRead 已超阈值。

**何时做**：D1 启动周期顺手；当前不动。

**ROI**：低。

---

### W · Section heading 类名串复制 5 处（`text-sm font-semibold uppercase tracking-wide ... border-b pb-1.5`）

> **⏳ 待处理（trivial）**：M2c-4 合并后整体 review 新发现。

**位置**：`type-form.tsx:142,205`、`asset-form-fields.tsx:41`、`custom-fields-form.tsx:21`、`type-detail-page.tsx:47`（变体）。

**候选**：抽 `<SectionHeading>` 在 `frontend/src/components/ui/`。

**何时做**：M3 表单结构稳定后；当前不动避免过早抽象。

**ROI**：低。

---

### Q-workaround · `useTypeRefCount` hook 已废弃 · 🪦 已删除

**M2c-4 合并后整体 review（2026-05-03）短暂引入**：`api/hooks/types.ts` 加 `useTypeRefCount(typeId)` hook 统一两 callsite 的 pageSize（commit 41de4de）。**§Q 落地后整 hook 已删除**（commit bdcc2f6）：`type.ref_count` 直接来自后端，无需前端反向数。

---

## §6 M2c-4 收尾说明（2026-05-03）

M2c-4 全部三个 PR 均已合并到 main：
- **PR-1**（feature/m2c4-backend，commit d47ce91）：后端 update_type + PATCH /api/types/{id} + CLI type update
- **PR-2**（feature/m2c4-form-infra，commit db9f946）：A1 buildAssetSchema 合并 + A2 FieldShell + A4 Control 泛型化 + F3 module-level schema 常量 + B nav 行
- **PR-3**（feature/m2c4-types-ui，commit 3425ecd）：类型管理 web UI（list/detail/create/delete）+ custom_fields 结构化 builder + unknown-key banner + §P NavBar fuzzy match 修复

### 状态总览（J–W 共 14 项）

| 条目 | 状态 | 备注 |
|---|---|---|
| §J condition `.extend` cast | 🟡 部分闭环 | M3a PR-2 commit `8f91f43` build-asset-schema 合一；asset-create-form 顶层 Resolver cast 因 zod union narrowing 限制保留待 RHF/zod 升级再清 |
| §K `acquired_at` 写错位置 | ✅ 已修复 | M2 收尾 commit 8c8202f；FieldShell pathPrefix prop |
| §L 双函数拆分 | ✅ 已闭环 | M3a PR-2 commit `8f91f43`（buildAssetSchema 单 builder + 显式 mode 分支） |
| §M `useWatch` 重订阅 + Path<T> cast | ⏳ 持续 | 字符串路径泛型限制；M3 后续看板/导出表单重构时再处理 |
| §N `field-${key}` id 模板重复 | ⏳ 持续 | M3 加新 field-control 时合并；PR-3 又新增 11 处（types builder） |
| §O MultiEnumField label-input 关联 | ⏳ 持续 | 与 §N 同周期 |
| §P NavBar fuzzy match | ✅ 已修复 | M2c-4 PR-3 Task 35 commit 77caf01 |
| §Q `TypeRead.ref_count` 后端字段 | ✅ 已修复 | M2 收尾 commit 03cafea (backend) + bdcc2f6 (frontend)；批量 GROUP BY |
| §Q-workaround `useTypeRefCount` hook | 🪦 已删除 | bdcc2f6 拆除；type.ref_count 直接读后端 |
| §R null-field MSW 测覆盖 | ⏳ 防御性 | PR-3 烟测 S5 新发现；防 silent submit failure 复现 |
| §S `useArrayFieldController` helper | ⏳ 条件触发 | 第 4 个 array form 出现时启动 |
| §T `TypesPage` 空状态用 `EmptyState` | ⏳ trivial | 收尾整体 review 新发现 |
| §U `NotFoundPanel` 抽到 `components/feedback` | ⏳ worth-fixing | 收尾整体 review 新发现，2 倍化 trigger 已 fire |
| §V `TypeRead` alias 跨 6+ 文件重复 | ⏳ trivial | 收尾整体 review 新发现，合 §3 D1 |
| §W Section heading 类名串复制 5 处 | ⏳ trivial | 收尾整体 review 新发现 |

### M2c-4 收尾整体 review 已修项（2026-05-03，工作树 clean 状态新 commit）

合并后视角的额外 simplify pass：
- **架构**：`type_cmd.py` 跨层访问 `svc.repo.count_assets_by_type` → 改走 `svc.count_refs()`，符合 CLAUDE.md §1 "service 层是唯一事实"
- **DRY**：`asset_type.py::create_type` / `update_type` 重复的 `CustomFieldDef.model_validate` → 抽 `_validate_and_dump_fields` 私有 helper
- **DRY**：`useUpdateTypeMutation` invalidate `list()` + `detail(id)` 不一致 create/delete 用 `.all` → 统一 `qk.assetTypes.all`，避 M3 加新 query 漏 invalidate
- **效率**：`type-form.tsx` `useMemo` for `defaultValues` 死优化（RHF 仅初次读取）→ 删 useMemo
- **可维护**：`coerceFieldDefsForRHF` 8 处手写 `?? undefined` → 抽 `NULLABLE_FIELD_KEYS` 常量 + 循环
- **未来兼容**：sessionStorage key `m2c4.banner.dismissed` → `unknown-fields-banner.dismissed`（去 milestone 前缀）
- **质量**：`type-delete-dialog` 三态嵌套三元 → 提到独立 `describeState()` helper
- **CLAUDE.md 合规**：清理多处 WHAT / task-reference 注释（builder/field-card/field-attribute-form/types-table/type_cmd/type-form）

后续启动重构时按"触发条件"列对照即可，不必重新评估。

---

## §7 M2 视觉收尾审计未选项（2026-05-03）

**视角**：frontend-design skill 对照 ui-ux-pro-max MASTER + spec §3.5 做的 M2 阶段全栈审计；本 PR（M2 视觉收尾，[2026-05-03 spec](./specs/2026-05-03-m2-visual-polish-design.md)）闭环了 H 类全部 + M2 SectionHeading，以下是当时记录暂不动的项。

### M1 · TypesTable 未接 Motion 三时刻（stagger / tbody-fade）· ✅ 闭环（M3d C-1）

**位置**：`frontend/src/features/types/list/types-table.tsx:124`

**现状**：资产表 `tbody key={bodyKey} className="tbody-fade"` + `<tr className="stagger-row" style={animationDelay}>`（assets-table.tsx:249-254），类型表 `<tbody>` 干净无 motion。

**ROI**：低。类型 N≪资产 N（v1 类型预计 <20，资产 <500），stagger 对类型表几乎没视觉收益；不接亦不影响 spec §3.5.5 "三时刻"承诺（时刻 1 适用对象本就是"列表首屏"，types 列表首屏可独立判定）。

**风险**：低。接入 5 行 diff，纯前端。

**何时做**：M3 启动时，如类型管理也要做"首屏入场感"统一，再补；若 M3 决定"types 列表故意保持静态"，把决议写进 MASTER 实施期纠偏。

---

### M3 · 页面 H1 字号三档无 type scale token · ✅ 闭环（M3d C-2）

**位置**：
- `features/assets/detail/asset-header.tsx:57` `text-2xl font-semibold`
- `features/types/list/types-page.tsx:22` `text-xl font-semibold`
- `features/types/detail/type-detail-page.tsx:39` `text-xl font-semibold`

**现状**：每页 h1 字号各凭手感，无统一规则。

**ROI**：中。固化 "列表/详情 h1 字号约定" 防新增页面再加第 4 档；改动 trivial（约 5 行）。

**风险**：低。不动现有视觉效果（除非选定值与现有不一致）。

**何时做**：M3 看板页 + 导出页加 h1 时一并约定，避免每加一页判一次。届时定 utility class（如 `.text-page-title`）或在 `globals.css` 加 type scale 节。

---

### M4 · `attachment-grid` `transition-shadow` 配错 prop 名 · ✅ 闭环（M3d C-3）

**位置**：`frontend/src/features/assets/detail/attachment-grid.tsx:54`

**现状**：`className="... transition-shadow hover:ring-2 hover:ring-primary/40"`。`transition-shadow` 监听 `box-shadow`；hover 用的是 `ring-*`（在浏览器底层是 box-shadow 实现），所以"凑巧能用"，但语义错。

**ROI**：极低。1 行修改；视觉无变化（只是 transition 触发更精准）。

**风险**：极低（trivial）。

**何时做**：M3 任意触碰附件 grid 时顺手吃掉；不值得单独 PR。

---

## §7 M3a 范围（2026-05-04）

M3a 子里程碑（5 态状态机基建）两个 PR 已合并到 main：

- **PR-1**（feat/m3a-pr1-state-machine-backend，merge `a360e04`）：后端 5 态 + 10 transition kind + TransitionService SoT + alembic migration + CLI 9 命令
- **PR-2**（feat/m3a-pr2-frontend-state-machine，merge `bc084e5`）：前端切换 transitions 端点 + 7 dialog + Toggle chip + 10 kind timeline + simplify §J/§L 清理

### 闭环条目

| 条目 | 状态 | commit ref |
|---|---|---|
| §C1 checkout.py vs state_machine 双层防御 | ✅ 已闭环 | M3a PR-1 commit `42b6f46`（TRANSITION_RULES 单 SoT；service 层 record_transition 不再 if-block 双层防御） |
| §J condition `.extend` cast | 🟡 部分闭环 | M3a PR-2 commit `8f91f43`（schema 合一）；顶层 Resolver cast 因 zod union narrowing 暂保留 |
| §L 双函数拆分 | ✅ 已闭环 | M3a PR-2 commit `8f91f43` |
| smoketest B1 状态切换进流转记录 | ✅ 已闭环 | M3a PR-1 commit `e741efb` `StateTransitionRecord` 表 + commit `fcdfb47` TransitionService 写入 |

### A3 推迟说明

A3（CheckoutDialog/ReturnDialog 合并）时机已到——M3a 引入 7 个 dialog 后第 3 个 form dialog 早已出现。**决议推迟到 M4 UI 打磨期**：M3a 优先保 5 态 + 10 transition kind 的功能落地，dialog 抽象层若现在做会延后里程碑且容易落入 frontend-design skill 警告的"AI 模板脸"。

### 烟测发现新登记 follow-up

- **§S 列表 Toggle pressed 视觉态较弱**：on/off chip 视觉差异不明显。M2c-3 §3 ToggleGroup pattern 复用了，但 Toggle 单独使用时缺少 elevation/shadow 区分。下次 list filter UX 改动时一并处理。

### Code review / simplify review 新登记 follow-up

- **§T `IllegalTransitionError` detail 结构化 payload**（M3a code review I3）：当前 `detail` 是中文自然语言字符串（如 "CHECKOUT_INTERNAL 必须提供 to_holder"），前端 `test_post_transition_required_field_missing_returns_409` 类测试按字面 match "to_holder"。后续若 translate 文案会破。改造方案：`detail` 改为 `{ "detail": "...", "code": "missing_holder" | "missing_location" | "illegal_from", "kind": "...", "from_status": "..." }` 结构化 payload，前端 dialog 按 code 渲染本地化文案。**触发时机**：i18n 启动 / 前端 dialog 形态稳定后（M4 后期）。
- **§U `KIND_META` 跨 3 文件合一**（M3a simplify Agent 1 F2）：`transition-timeline.tsx` `KIND_META`（10 kind label/Icon/bgClass/fgClass）、`simple-transition-dialog.tsx` `META`（3 kind label/description/Icon/bgClass/fgClass）、`checkout-dialog.tsx` `META`（2 kind verb/Icon/audience）三表都按 `TransitionKind` keyed，重复登记 label + Icon。统一抽 `TRANSITION_META: Record<TransitionKind, { label, Icon, bgClass, fgClass }>` 到 `available-transitions.ts`（或新 `transition-meta.ts`），dialog 用 satellite extra 表覆盖 dialog 专属字段（description/audience/holderLabel）。**触发时机**：M3d 高级视觉重构 timeline 时一并做，避免独立 PR 影响面跨 3 文件。
- **§V `Settings.mode` 字段替代 `os.environ.get`**（M3a simplify Agent 1 F6）：`api/app.py` 用裸 `os.environ.get("ASSET_HUB_MODE")`，`lifecycle.py` 用裸 `os.environ["ASSET_HUB_MODE"] = mode`，是局部破例——项目其他配置统一走 `Settings()`（`config.py` `env_prefix="ASSET_HUB_"`）。改造：`Settings` 加 `mode: Literal["dev","prod"] | None = None` 字段，`api/app.py` 改 `Settings().mode == "dev"`；`lifecycle.py` 仍需 `os.environ` mutation 让子进程继承（or 走 `subprocess.Popen(env={...})` 更干净）。**触发时机**：下次 Settings 加新字段或 serve 命令重构时。
- **§W types 详情/列表 vs assets 详情/列表面板风格不统一**（用户提）：types-summary-card 居中布局 vs assets-header 左对齐；types 列表 vs assets 列表的 column-visibility / pagination / filter 区视觉风格差异。**触发时机**：M4 UI 打磨期统一规范（与 §S Toggle 视觉、A3 dialog 合并、编辑/删除按钮位置等一并处理）。
- **§X `dispose-alert-dialog.tsx` 用 useState 而非 RHF**（M3a code review 隐含）：当前 dialog 用 `useState<string>(confirmText)` + `useState<string>(note)` 直接管理表单，与其他 6 个 dialog 用 RHF + zodResolver 风格不一致；但 dispose 字段简单（只有 confirm phrase + note）+ 校验逻辑特殊（unlocked = phrase === "处置"），抽 RHF 价值不大。**触发时机**：仅在 dialog 字段扩多 / 加 zod 校验需求时切换，否则保持现状。

---

## §8 M3d 范围（2026-05-07）

M3d 子里程碑（timeline 视觉重构 + simplify §7 三搭车）单 PR 完成（feat/m3d-timeline-visual，5 phase commit）：

- Phase 1 `2dbb574`: design token (--status-borrowed / --warning) + MASTER.md type scale 节
- Phase 2 `dcdcaed`: utility 纯函数 (calcOverdue / formatRelative / timeline-grouping)
- Phase 3 `9587c38`: transition-timeline 重构 (KIND_META 5 替换 / Group rail / 月份分段)
- Phase 4 `3dcdf56`: CheckoutDialog Calendar+Popover + AssetHeader overdue 角标
- Phase 5 `9d5284b`: simplify §7 三搭车 (TypesTable motion / H1 二档 / attachment-grid prop)

### 闭环条目

| 条目 | 状态 | commit ref |
|---|---|---|
| §7 M1 TypesTable Motion 三时刻 | ✅ 已闭环 | M3d Phase 5 commit `9d5284b`（C-1） |
| §7 M3 H1 字号三档 type scale | ✅ 已闭环 | M3d Phase 5 commit `9d5284b`（C-2，含 globals.css 注释 + MASTER.md "排版" 节 SoT） |
| §7 M4 attachment-grid transition-shadow prop | ✅ 已闭环 | M3d Phase 5 commit `9d5284b`（C-3，transition-shadow → transition-all） |
| §14.8 派出类型染色（spec 主线） | ✅ 已闭环 | M3d Phase 3 commit `9587c38`（E2 形态：Group rail + 月份分段） |
| §14.8 时间渐隐 | ❌ M3d 决议作废 | spec §1.1 详述（与 Group rail + 月份分段双层时间分层冗余） |
| §14.8 超长派发预警 | ✅ 已闭环 | M3d Phase 4 commit `3dcdf56`（基于 due_at 两阶段） |

### 烟测发现 / final review 新登记 follow-up

- **§Y `closedCheckoutIds` Set 构建跨 2 文件重复**（M3d final review I1）：`timeline-grouping.ts::groupByCheckout` L40-44 与 `asset-header.tsx::useOverdueForOpenCheckout` L45-48 逻辑同构（filter RETURN.closes_transition_id → Set）。可抽 `findOpenCheckout(transitions): TransitionRead | null` 工具函数到 `lib/transition-state.ts`，两处复用。**触发时机**：第三处复制出现时，或 transition 状态查询逻辑再扩展。
- **§Z `formatRelative` v1 仅天级**（spec §0 不包）：无小时/分钟粒度，timeline 卡若同日多次 transition 全显示"今天"，调试时区分困难。**触发时机**：用户反馈或同日多 transition 真实场景出现。
- **`useOverdueForOpenCheckout` loading 闪现**（U5 quality reviewer I2）：transitions 加载期间 hook 返 null → 角标"先不显示再突然出现"轻微视觉跳动。当前接受（有 detail 页 skeleton 兜底）；后续若用户反馈再处理。
- **`bg-status-borrowed/15` className 直选脆弱**（U5 quality reviewer I4）：checkout-dialog.test 用 `document.body.querySelector(".bg-status-borrowed\/15")` 耦合 Tailwind utility 字符串，换 token 名时测试挂。改 `screen.getByText("出借").closest("span").toHaveClass(...)` 更稳。**触发时机**：simplify pass。

---

## §9 M3e 范围（2026-05-09）

M3e 子里程碑（v1.0 GA 收口）单 PR 完成（feat/m3e-ga，4 phase commit）：

- Phase 1 envelope 升级 + serve doctor
- Phase 2 5 态文案对齐 + 薄弱点补测
- Phase 3 文档全集（SKILL.md + references/ + deployment.md + README + release-notes-v1.0）
- Phase 4 playwright e2e 7 spec + GitHub Actions

### 闭环条目

| 条目 | 状态 | commit ref |
|---|---|---|
| K1 envelope 统一（HIGH 优先级 follow-up） | ✅ 已闭环 | M3e Phase 1 |
| M2d serve doctor known gap | ✅ 已闭环 | M3e Phase 1 |
| 5 态文案 3 字对齐（IDLE/IN_USE 改） | ✅ 已闭环 | M3e Phase 2 |
| 5 态 filter include_retired/disposed 测试薄弱点 | ✅ 已闭环 | M3e Phase 2 |
| SKILL.md 起草 + references/ 4 文件 | ✅ 已闭环 | M3e Phase 3 |
| Windows 部署文档 + README 全量重写 + release-notes-v1.0 | ✅ 已闭环 | M3e Phase 3 |
| playwright e2e CI 7 spec + GitHub Actions | ✅ 已闭环 | M3e Phase 4 |

### 推 v1.1 的 follow-up

- envelope error 结构化升级 `{code, message, hint, fields_missing?}`（与 simplify §T 同 PR）
- `--help --json` 双模 / `--fields` 字段掩码（agent-native checklist 候选）
- SKILL.md description trigger eval（用 skill-creator description optimization loop 跑 5 iteration）
- references/ staleness 检查 helper（与 spec / 代码同步）
- Phase 1 followup: CLI envelope error code = "cancelled" 入 spec §2.1 + envelope.md 主表
- Phase 1 followup: serve doctor check_alembic_head stderr 处理细化（区分"alembic 命令本身坏" vs "迁移逻辑出错"）
- Phase 1 followup: serve doctor check_frontend_dist 用 importlib resolve repo root 或 --repo-root flag（替代相对路径假设）
