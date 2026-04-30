# /simplify Review · 跨里程碑未修清单（后续重构参考）

**视角**：reuse / quality / efficiency 三 agent 并行 review，按里程碑分节累积。
**用途**：判断"是否启动这些重构"的输入。每条都附 ROI 评估、改动面、风险点，便于按里程碑节奏挑选。

## 索引

- [§1 M2c-3 范围（2026-04-27 二轮）](#1-m2c-3-范围2026-04-27)
- [§2 M2c-2 范围（2026-04-27 二轮）](#2-m2c-2-范围2026-04-27二轮)
- [§3 M2c-1 范围（2026-04-27 二轮）](#3-m2c-1-范围2026-04-27二轮)
- [§4 M1 范围（2026-04-27 二轮）](#4-m1-范围2026-04-27二轮)
- [§5 M2d 范围（2026-04-29）](#5-m2d-范围2026-04-29)

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

### A1 · 合并 build-create-schema / build-edit-schema

**位置**：`frontend/src/features/assets/form/build-create-schema.ts` + `build-edit-schema.ts`

**现状**：两份 baseSchema 仅差一个 `type_id` 字段，`acquired_at / serial_number / holder / location / notes` 完全相同。

**建议**：合并为 `buildAssetSchema(fieldDefs, { mode: 'create' | 'edit' })`，内部 `mode === 'create' ? base.extend({ type_id }) : base`；`CreateFormValues / EditFormValues` 用 `z.infer<ReturnType<typeof buildAssetSchema>>` 各自导出。

**ROI**：中。代码减约 30 行，单一定义点；但 `buildEditSchema(fieldDefs)` 调用点（`asset-edit-form.tsx`、test）需同步签名改造。

**风险**：低（纯前端、有 vitest 覆盖）。

**何时做**：下一次 form 层有改动时顺手合，不值得单独开 PR。

---

### A2 · 抽 FieldShell 收敛 9 个 field-control 外壳

**位置**：`frontend/src/features/assets/form/field-controls/*.tsx`（string / text / url / number / enum / multi-enum / bool / date 共 9 个）

**现状**：每个组件都重复 `FormField → FormItem → FormLabel(+ 必填星) → FormControl → FormDescription → FormMessage` 骨架，约 8-12 行/文件。

**建议**：抽 `<FieldShell def={def} control={control}>{(field) => <Input ... />}</FieldShell>`，bool-field 因布局不同保留特例或加 `layout="inline"` prop。

**ROI**：中。9 文件 × 8-12 行 = ~80 行去重；但抽出后调试自定义渲染时需多看一层。

**风险**：低。

**何时做**：未来再加新 field type 时（届时 9 → 10 重复 + 1 倍化）才有动手价值；现在 9 个已稳定，不优先。

---

### A3 · 合并 CheckoutDialog / ReturnDialog（抽 useFormDialog）

**位置**：`frontend/src/features/assets/detail/checkout-dialog.tsx` + `return-dialog.tsx`

**现状**：迁到 RHF+Zod 后两份 dialog 的 `useForm + zodResolver + handleOpenChange + onSubmit + try/setError('root') + InlineErrorBanner + DialogFooter` 高度同构；字段集不同（checkout: holder/location/note；return: note + currentCheckout 展示）。

**建议**：抽 `useFormDialog<T>({ schema, defaultValues, mutate, onSuccess })` hook，dialog 体只剩 fields。或更轻量的 `<FormDialog title onSubmit error pending>` 外壳。

**ROI**：中。两个 dialog 的样板减 ~30 行；但抽出后字段定义"间接化"，IDE 跳转链变长。

**风险**：低（vitest 已覆盖 checkout-dialog 2 case）。

**何时做**：M3 如新增第 3 个表单 dialog（如批量调拨），届时 3 倍化重复时再抽。当前 2 倍化值得放一放。

---

### A4 · `Control` 类型 cast 退化为 any

**位置**：`asset-create-form.tsx:121` + `asset-edit-form.tsx:102`

**现状**：`control={form.control as unknown as Control}` 双重 cast，9 个 field-control 签名也都用 `Control` 而非 `Control<CreateFormValues>`，丢失字段名补全。

**建议**：把 `AssetFormFields` 与各 field-controls 改泛型 `<TFieldValues extends FieldValues>`，传入 `Control<TFieldValues>`。

**ROI**：中。类型安全显著提升；但需改 9+ 文件签名。

**风险**：中。RHF 泛型与 `custom_data: Record<string, unknown>` 嵌套字段路径有过过去版本踩坑记录，需额外验证。

**何时做**：与 A2 一起做最划算（都要改 field-controls 签名）。

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

### F3 · zodResolver 在 CreateForm 每次 render 重建

**位置**：`frontend/src/features/assets/form/asset-create-form.tsx:23-24`

**现状**：`useForm({ resolver: zodResolver(buildCreateSchema([])) })` ——`buildCreateSchema([])` 每次 render 重建（参数恒为 `[]`）。EditForm 已修，CreateForm 因 RHF useForm 仅在 first render 用 resolver，后续靠内部 ref 跟踪，影响仅是 GC 压力轻微。

**建议**：把 `buildCreateSchema([])` 提到 module-level 常量。

**ROI**：低。微优化。

**何时做**：与 A1（合并 schema）一起做。

---

## §1 总览（建议优先级）

| 优先级 | 项目 | 触发条件 |
|---|---|---|
| 🟢 顺手做 | A1 / B1 / C3 / F2 / F3 | 下次 form / detail / 上传相关改动时一并做 |
| 🟡 等里程碑 | A2 + A4 / A3 | M3 加新 field type 或新 form dialog 时启动 |
| 🟡 已登记 | C1 | M3 §14.6/14.7 状态机升级时一并做 |
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

| 优先级 | 项目 | 触发条件 |
|---|---|---|
| 🔴 **高优先级 fix（非 simplify）** | I1 | 立即开单独 PR / issue——这是用户可触发的运行时错误 |
| 🟡 与 I1 合并做 | I2 | I1 启动时一并引入 FieldType Enum |
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

**例外**：I1 是真实功能缺口（前端能过、后端必拒），属于用户可触发的运行时错误，应单独开 fix PR / issue 跟踪，**不归在"暂不动"分类下**。

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

后续启动重构时按"触发条件"列对照即可，不必重新评估。
