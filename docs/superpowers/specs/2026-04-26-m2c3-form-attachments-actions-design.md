# M2c-3 · 表单 + 附件上传 + 删除 + 状态切换 + 后端字段补齐 设计文档

- **日期**：2026-04-26
- **里程碑**：M2c 第 3 子项（表单 + 附件上传 + §14.5 状态切换 + §14.10 acquired_at + §K 后端字段补齐 + 简化 asset_code 反向纠偏）
- **状态**：初稿，待实施
- **作者**：conghaoyangbobby@gmail.com（与 Claude 协同 brainstorm）
- **承接**：[`2026-04-15-asset-hub-design.md`](./2026-04-15-asset-hub-design.md) §7.1 / §14.5 / §14.10 / [`2026-04-24-m2c1-frontend-foundation-and-list-design.md`](./2026-04-24-m2c1-frontend-foundation-and-list-design.md) / [`2026-04-25-m2c2-detail-flow-attachments-design.md`](./2026-04-25-m2c2-detail-flow-attachments-design.md)

## 0. 导读

本文档是 **M2c 子里程碑拆分后的第 3 份 spec**。

| 子里程碑 | 范围 | spec |
| --- | --- | --- |
| M2c-1 · 地基 + 列表 | 前端工具链、数据层、主题、布局壳、资产列表页 | [✓ 已交付](./2026-04-24-m2c1-frontend-foundation-and-list-design.md) |
| M2c-2 · 详情 + 流转 + 附件查看 | 详情页 + 派发/归还对话框 + 流转 timeline + 附件查看 + 删除 | [✓ 已交付](./2026-04-25-m2c2-detail-flow-attachments-design.md) |
| **M2c-3 · 表单 + 附件上传 + 状态切换 + 后端字段补齐**（本文） | 登记/编辑/删除资产 + 附件上传 + §14.5 状态切换 web 入口 + acquired_at + asset_code（简化版反向纠偏）+ Vitest + RHF + Zod | 本文 |
| M2c-4 · 类型管理 UI | AssetType CRUD + 结构化 custom_fields builder | 未写 |
| M2d · CLI 接管 web 服务生命周期 | `asset-hub serve start/stop/status/restart/logs` | 未写（spec §14.9 有详案） |

M3（看板 + 导出 + SKILL.md + §14.1 派出类型扩展 + §14.6 audit 化 + §14.7 状态枚举完善）、M4（审美打磨）均在 M2c 完结 + M2d 完结之后再动。

**里程碑顺序**：M2c-3 → M2d → M2c-4 → M3 → M4。M2d 与 M2c-4 顺序在 brainstorm 阶段已拍：先 M2d（daily dev 体验改善每天兑现）。

## 1. 目标与非目标

### 1.1 目标

把 M2c-1 列表页 + M2c-2 详情页的"只读 + 流转"两层拼图补完最后一块——让用户能在 web 完整完成「登记 → 编辑 → 上传附件 → 状态流转 → 删除」全生命周期。同时把 M1 brainstorm 砍掉但后续 spec 漂移误记成"M3 待补"的 `asset_code` 以**简化版**形态加回（简化 = 砍掉年度计数与并发锁，仅保留 `{type_prefix}-{per-type 序号}`）。

### 1.1.1 资产侧（前端 + 后端协同）

- **登记表单** 路由 `/assets/new`：
  - 单页线性布局；H2 分区（"基础信息" + "<type_name>"）；type 切换 → 直接替换（无过渡动效）
  - 通用字段：name（必填）/ type（必填）/ SN / acquired_at / holder / location / notes
  - 动态 custom_fields 渲染：按 `AssetType.custom_fields`（FieldDef 数组）schema-driven 生成 RHF + Zod
  - type select 空状态 → inline 提示"用 CLI `asset-hub type define …` 创建，或让 Agent 帮你建"（type 管理 UI 在 M2c-4）
  - 提交成功 → 跳 `/assets/<新 id>` 详情页 + Toast "登记成功"
- **编辑表单** 路由 `/assets/:id/edit`：
  - 与登记表单字段集合完全相同，复用 `<AssetFormFields>` 子组件
  - **`type` 字段 disabled + 文字提示"创建后不可改"**（避免 custom_data 字段集合漂移）
  - 拉取现有 asset 数据预填；提交走 PATCH；成功 → 跳回 `/assets/:id` + Toast "更新成功"
- **删除资产**：详情页 ⋯ 菜单 + 列表页 ⋯ 菜单，触发 AlertDialog 简单二次确认
  - **派发中（IN_USE）资产删除按钮 disabled**，文案"需先归还"；避免孤儿 CheckoutRecord
  - 删除成功 → 跳列表 + Toast "删除成功"（详情页触发时）/ 留列表 + Toast（列表页触发时）
- **附件上传**：详情页"附件"section grid 末尾**内嵌 add slot**（虚线 + tile）
  - 点击触发 `<input type="file" multiple>`；拖拽到 add slot 也触发上传
  - 多文件并发上传，每个文件独立 progress（上传中临时变 progress tile）
  - 失败的文件保留 error tile 可点重试
  - 单文件 ≤10MB（前端 + 后端双重校验）；mime 类型用 `<input accept>` 引导，后端兜底
- **§14.5 状态切换 web 入口**：列表页 ⋯ 菜单 + 详情页 CTA 区域 + ⋯ 菜单。新增 4 个动作：
  - **送修**（IDLE → MAINTENANCE）：可在 IDLE 状态作为次按钮直显
  - **修好回库**（MAINTENANCE → IDLE）：MAINTENANCE 状态主按钮
  - **退役**（IDLE / MAINTENANCE → RETIRED）：⋯ 菜单 + AlertDialog 二次确认
  - **重新启用**（RETIRED → IDLE）：RETIRED 状态主按钮
  - 状态切换实现：`PATCH /api/assets/:id` body `{ status: "MAINTENANCE" }`，service 层 enforce 转换合法性（详见 §5.5 状态机）

### 1.1.2 类型侧（仅后端字段补齐 + 前端消费）

- `AssetType.code_prefix` 必填字段：`^[A-Z]{2,4}$`、unique、**immutable**（创建后不允许 PATCH）
- type 管理 web UI **仍不做**——推 M2c-4。本里程碑在登记表单空状态文案给"先去创建 type"引导
- CLI `type define` 加 `--prefix XX` 必填参数（M1 已有的命令扩参数）

### 1.1.3 列表页变更

- **第一列改回 `asset_code`**（mono Fira Code）：M2c-1 的 `serial_number ?? id.slice(0,8)` 兜底显式拆解为两列
- **SN 独立列**（mono Fira Code），缺失显 `—` muted
- **acquired_at 列默认隐藏**，column-visibility 可开启
- **列顺序最终形态**：`编号 | 名称 | SN | 类型 | 状态 | 持有人 | 位置 | 更新时间 | ⋯`
- 排序键 `code` 直接对应 `asset_code` 字段（不再走客户端 `accessorFn`）

### 1.1.4 后端字段补齐（§K 部分）

| 字段 | 表 | 类型 | 备注 |
| --- | --- | --- | --- |
| `asset_code` | `assets` | `str` unique not null | `{prefix}-{seq:03d}` 自动生成；service 层 register 时 `MAX(per_type_seq)+1` |
| `code_prefix` | `asset_types` | `str` unique not null | `^[A-Z]{2,4}$`，immutable |
| `acquired_at` | `assets` | `date` nullable | 业务入账日期；不预填 |
| `type_name` 反规范化 | `assets`（或不实质化） | — | plan 阶段定（候选：SQLAlchemy `relationship + association_proxy`，不真加列） |
| `current_checkout_id` | `assets` | `UUID` nullable FK | service 层在 checkout/return 时维护；详情页"当前派发"不再前端 history 推导 |

DB migration 一次性补齐：旧资产按 type + created_at 顺序回填 asset_code；旧 AssetType 必须一次性补 code_prefix（用 CLI 交互或 SQL 直填）。**首版 spec 估计旧数据条数 < 50，可手动审查**。

### 1.1.5 框架引入

- **Vitest + Testing Library**：β 档覆盖（纯函数 + 关键 hook 失效逻辑 + msw mock）；组件交互测推 M2c-4
- **react-hook-form + zod**：所有新表单（登记 / 编辑）+ 把 M2c-2 的 `CheckoutDialog` / `ReturnDialog` 从纯 React state **迁移**到 RHF（M2c-2 spec §10.4 留的债，本里程碑兑现，独立 Task）

### 1.2 非目标（明确推走）

| 非目标 | 去处 |
| --- | --- |
| 类型管理 web UI（list / create / edit / delete + 结构化 custom_fields builder） | **M2c-4（独立子里程碑）** |
| CLI 接管 web 服务生命周期（`asset-hub serve …`） | **M2d（独立子里程碑，spec §14.9 已有详案）** |
| 派出类型扩展（"向外出借"、split-button、`CheckoutRecord.kind`） | M3（§14.1） |
| 状态转换 audit 化（`StateTransitionRecord` 模型） | M3+（§14.6） |
| 状态枚举完善（"故障未送修" / `RETIRED` 分化为 `RETIRED + ARCHIVED` 等） | M3 业务驱动（§14.7） |
| 流转 timeline 视觉重构（时间渐隐 / 类型染色 / 超长预警） | M3（§14.8） |
| `AssetType` 编辑、删除（含资产时迁移） | M2c-4 |
| 软删除 / 回收站机制 | M3+ |
| 看板 / 导出 / SKILL.md | M3 |
| 命令面板 / 响应式 polish / 微动效 polish | M4 |
| i18n 脚手架 | 直接硬编码中文 |
| 完整年度 asset_code（`{prefix}-{year}-{seq}` + 年度重置 + 并发锁） | 简化版 + acquired_at 已 cover；完整版**永不**做（设计判断） |

## 2. 关键决策（已定）

每条决策在 brainstorm 阶段逐个对齐，此处定型。

| ID | 决策 | 选项 | 理由 |
| --- | --- | --- | --- |
| D1 | M2c-3 范围 | **范围 4**：A 核心 + §14.5 状态切换 + §14.10 acquired_at + §K 后端字段补齐（含简化 asset_code 反向纠偏） | 后端 deploy 一次到位；§14.5 几乎免费；M3 卸下"补字段"包袱聚焦看板/导出 |
| D2 | `AssetType.custom_fields` 格式 | **数组形态（FieldDef 列表）**，显式顺序，每元素 `{name, label?, type, required?, default?, placeholder?, help?, unit?, min?, max?, options?, displayAs?}` 12 字段 | 顺序敏感（schema-driven UI 字段顺序就是用户看到的顺序）；FieldDef 加新属性零成本；Zod schema 从 list 生成代码更直 |
| D3 | 登记/编辑表单总骨架 | **单页线性 + H2 分区**（"基础信息" + "<type_name>"）+ type 切换直接替换（无过渡动效） | v1 字段总量小（通用 ~6 + type-specific ~3-8），wizard 是过度设计；H2 分区与 M2c-2 详情页 `space-y-10 + <h2>` 同款语义分区；type 切换瞬间替换符合"决策已变更"的强信号 |
| D4 | 简化 asset_code 加回（M1 反向纠偏） | **{prefix}-{per-type seq:03d}**（如 NB-007）；prefix 从 AssetType 来；seq 全局 per-type 递增，**不带年份、无年度重置、无并发锁** | M1 brainstorm 砍掉的是复杂版（带年份 + 重置 + 锁）；简化版砍掉这些复杂度，仅保留"一眼知类型"的扫读价值；年份语义由 `acquired_at` 字段独立承担（DRY） |
| D5 | `code_prefix` UX | **AssetType 必填字段**，格式 `^[A-Z]{2,4}$`，**immutable**（创建后不允许 PATCH）；输入小写自动转大写；DB unique 兜底 | 中文场景下自动推导 prefix（拼音/首字母）效果差，让用户起 2-4 字母不构成负担；immutable 避免历史 asset_code 语义漂移 |
| D6 | 列表第一列形态 | **`asset_code` 主列（mono Fira Code）+ SN 独立次列（mono Fira Code，缺失 `—` muted）** | frontend-design skill 审核首选；前缀字母 + 序号双层视觉节奏；SN 退到名称之后符合"标识符 → 含义 → 辅助标识"的信息层级（GitHub Issues / Linear / Jira 同款 prior art） |
| D7 | 字段类型 → 控件映射 | string→Input；text→Textarea；int/float→`type="text" + inputMode` + Zod（不用 type=number）；bool→Checkbox（**不**用 Switch）；date→shadcn Calendar in Popover；enum 阈值 ≤4→RadioGroup ≥5→Select；multi-enum 阈值同 enum（≤4 多 Checkbox ≥5 Combobox）；url→type="url"；displayAs override 兜底 | type=number 有滚轮误改/科学记数等老坑，业界现代做法都是 text+inputMode+Zod；表单语义是"配合提交"而非"立即生效"，Checkbox 比 Switch 对；阈值经验值 |
| D8 | `unit` 语义 | **仅显示**：input 内右侧 muted 后缀（如 "32 GB"）；不参与 Zod 校验；`custom_data` 存纯数字 | 量纲信息存于 `AssetType.custom_fields`，data 字段不重复 |
| D9 | 编辑表单的 type 处理 | **disabled + 文字提示"创建后不可改"** | type 改 → custom_data 字段集合全变 → 数据丢失或 schema 漂移；统一禁止，要改类型 = 删除资产重建 |
| D10 | 登记/编辑组件结构 | **两个独立组件** `<AssetCreateForm>` + `<AssetEditForm>`，共享 `<AssetFormFields>` 底层组件 | 业务流程不同（登记是从无到有 / 编辑是在已有基础上改）；模式分支 `mode="create" \| "edit"` 收益不高 |
| D11 | 提交后跳转 | 登记成功 → `/assets/<新 id>` + Toast "登记成功"；编辑成功 → `/assets/:id` + Toast "更新成功"；失败 → 留页 + inline error banner（顶部）+ field-level 红边/红字 | 登记后用户自然想看详情；编辑入口本来就在详情页 ⋯ 菜单，回去合理 |
| D12 | 附件上传形态 | **grid 末尾内嵌 add slot**（虚线 tile + "+ 添加附件" 文字），点击触发 `<input multiple>` + 拖拽支持；多文件并发；上传中变 progress tile；失败保留 error tile 可点重试 | 与 M2c-2 附件 grid 同框排列，零新视觉概念，fewer-but-better；移动端自适应（grid 列数响应宽度自动调） |
| D13 | 详情页动作入口布局 | **主按钮 + ⋯ 菜单**（沿用 M2c-2 形态）；按状态显隐：IDLE 主按钮"派发" + 次按钮"送修"；IN_USE 主按钮"归还"；MAINTENANCE 主按钮"修好回库" + ⋯ 菜单含"退役…"；RETIRED 主按钮"重新启用" + ⋯ 菜单不含状态切换；编辑永远在 ⋯ 菜单；删除在 ⋯ 菜单底部 danger color | 8 动作 × 4 状态全显 → 列表/详情都过载；按状态显隐 + 主按钮放当前状态最常用 + ⋯ 菜单纳次频/破坏性 |
| D14 | 状态机转换合法性 | **简化路径**：MAINTENANCE 仅从 IDLE 进入；RETIRED 仅从 IDLE / MAINTENANCE 进入；IN_USE 状态下要任何状态切换必须先归还；RETIRED 唯一出口"重新启用"回 IDLE；不允许的转换 service 层抛 `ValidationError` | 数据模型最简（不需要"派发中送修自动归还"的特殊路径）；业务语义诚实——送修/退役都是"暂时不可派发"，要先把派发清完；v1 单用户场景"先归还再送修"两步走不算累赘 |
| D15 | 删除资产二次确认 | **简单 AlertDialog**（候选 A）：标题"确认删除？"；body 含 `<asset_name> · <asset_code>` + 影响说明；按钮"取消" + "确认删除"（destructive 红） | v1 单用户场景误删恢复成本不高；MASTER 反 AI-slop 倾向"克制"——多一步输入名称的确认在小规模工具上是过度防御；M3+ 可加软删除回收站 |
| D16 | 派发中能否删除 | **不能**——状态 IN_USE 时删除按钮 disable + tooltip "需先归还" | 避免孤儿 CheckoutRecord（引用已删除 asset） |
| D17 | 删除 cascade 行为 | service 层显式：删 asset → 同事务删该 asset 所有 CheckoutRecord + 所有 Attachment（含 FS 文件 + DB 元数据） | CheckoutRecord 业务上仅对 asset 有意义；Attachment 已和 asset 绑定 |
| D18 | acquired_at 类型 + 默认 + migration | `date` nullable；登记表单不预填 today；旧数据 migration 全部回填 null；列表默认隐藏，column-visibility 可开启 | 业务意义入账日期，不预填避免与 created_at 混淆；旧数据真不知就别假装知道 |
| D19 | Vitest 覆盖范围 | **β 档**：纯函数 + 关键 hook 失效逻辑（msw mock）；组件交互测推 M2c-4 | 引入 Vitest 是建立基础设施；首批测有抓手的部分；组件交互测在 M2c-4 加 type builder 时再扩 |
| D20 | RETIRED 列表过滤 | **本里程碑不加默认过滤**——RETIRED 资产在列表与其他状态平等显示 | 默认过滤是 §14.7 状态枚举完善范围（M3 业务驱动）；现阶段加 toggle 是预设 ARCHIVED 拆分的方向，反而锁死 M3 设计空间 |
| D21 | type 管理 UI 分配 | 完全推 **M2c-4**（独立子里程碑） | γ 级 type CRUD + 结构化 custom_fields builder 复杂度等于 M2c-1 量级；塞进 M2c-3 必爆；登记表单空状态有 inline 引导文案 |

## 3. 设计系统 baseline

### 3.1 baseline 继承（不重跑 ui-ux-pro-max）

完整继承 M2c-1 + M2c-2 已建立的全套：

- `design-system/asset-hub/MASTER.md` —— 全局权威 tokens；M2c-1 + M2c-2 实施期纠偏区块已沉淀
- `design-system/asset-hub/pages/assets-list.md` —— 列表页 override，本里程碑按 D6 列布局调整需要补一条"列顺序与 mono 字段聚类"的 override
- `frontend/src/styles/globals.css` —— CSS variable + 4 态状态色 token；M2c-3 **不新增任何变量**

### 3.2 是否需要 page override

- **登记/编辑表单**：不生成 `pages/assets-form.md`——表单页与 MASTER baseline 一致，按 §3.4 审美纲领落即可
- **assets-list.md**：补一条"列顺序：`asset_code | name | SN | type | status | holder | location | updated_at`"（D6）
- 其余偏离 MASTER 的细节按实施期纠偏（§3.3 闸门 ④）回写到 MASTER 末尾

### 3.3 frontend-design skill 在本里程碑的位置（与 M2c-2 同款 4 闸门）

| 闸门 | 时机 | 内容 |
| --- | --- | --- |
| ① | spec 阶段（**当前文档**） | §3.5 审美纲领明确写出 M2c-3 各 Task 必须满足的红线；plan 阶段每个 UI Task 末尾"§3.5 约束引用"栏对齐 |
| ② | 实施期 Task 粒度 | 每完成一个 UI 组件 Task，跑一次 §3.5 红线扫描（grep `scale-` / `animate-spin` / `backdrop-blur` / `gradient`）；不通过当 Task 立即修复 |
| ③ | 合并前最终审查 | 跑一遍附录 A 烟测（约 18 项）+ MASTER `Pre-Delivery Checklist` 7 项 + frontend-design skill 走一轮 |
| ④ | 纠偏回写 | M2c-3 实施期发现的上游缺口、临时权宜、偏离 MASTER 的细节，回写到 MASTER 末尾"实施期纠偏（M2c-3）"区块 |

### 3.4 §3.5 审美纲领（M2c-3 落地清单）

| § | 条目 | M2c-3 落地点 |
| --- | --- | --- |
| §3.5.1 | fewer-but-better（密度克制） | 表单单列布局（H2 分区，无 sidebar 装饰）；附件 add slot 与已有 tile 同等 grid 单元（不引入独立 dropzone 区）；删除 AlertDialog 不含输入名称等高摩擦元素 |
| §3.5.2 | 字体（Fira Sans body / Fira Code 编号） | 列表 `asset_code` / SN 列继续 `font-code`；登记/编辑表单内的 asset_code 预览显示用 `font-code`；CTA 按钮文字 Fira Sans |
| §3.5.3 | 状态色（4 态语义） | 详情页 CTA 主按钮色按状态：IDLE→primary 蓝、IN_USE→primary、MAINTENANCE→success 绿、RETIRED→muted 灰；状态切换的 mutation pending 按钮文字切（"送修中…" / "归还中…" / 等） |
| §3.5.4 | radius=0.375rem | 表单 input / select / Calendar Popover / AlertDialog 全部跟 token |
| §3.5.5 | Motion 三时刻 | 时刻 1（页面入场）：登记/编辑表单页**不做 stagger**（与 M2c-2 详情页同源）；时刻 2（交互反馈）：button hover 色变 150-300ms / type 切换瞬间替换无 transition / 附件上传 progress 用宽度 transition；时刻 3（状态切换）：`prefers-reduced-motion` 全降级 |
| §3.5.6 | 红线（禁 transform scale / animate-spin / backdrop-blur / 多层 shadow / 渐变背景） | mutation pending 不显式 spinner（按钮文字切）；AlertDialog overlay `bg-black/50` 不 blur；附件 add slot hover 用 `border-color` + `bg` 轻变化（不用 shadow / scale） |
| §3.5.7 | shadcn variant 审查 | 本里程碑首次引入 `Form / Input / Textarea / Checkbox / RadioGroup / Select / Combobox / Calendar / Popover` 等 shadcn 组件；引入即审：移除 Next 残留 `"use client"`；`Calendar` 中文 locale；`Select` content 默认 `bg-popover` 在主题切换下自然适配 |

### 3.4.1 MASTER override（本里程碑显式补充）

承接 M2c-2 已写入 MASTER 的覆盖清单，本里程碑新增：

| MASTER 条目 | M2c-3 覆盖 | 理由 |
| --- | --- | --- |
| `Inputs: padding 12px 16px` | 表单 input padding 改 `8px 10px`（shadcn 默认 size="default"） | MASTER 给的是 hero/landing 风格 padding；表单密度场景下 shadcn 默认更合适 |
| `Modal: backdrop-filter: blur(4px)` | AlertDialog overlay `bg-black/50` 不 blur（沿用 M2c-2 已设） | 同 M2c-2 |
| 无明确条目 | 附件 add slot 风格：`border: 1.5px dashed muted-foreground` + hover `border-primary text-primary bg-primary/5` | MASTER 未涉及 dropzone 元素，本里程碑显式定义；与 button hover 用色温变化同源 |

### 3.5 反 AI-slop 红线（M2c-3 显式禁项）

落实到具体场景：

- **表单提交按钮 pending 态**：禁 spinner，仅文字切换（"登记中…" / "保存中…"）
- **type 切换动效**：禁 height transition / scale fade-in；瞬间替换
- **附件上传中态**：tile 内进度条用宽度 transition（150-300ms ease），**禁** spinner / pulsing 动画
- **删除 AlertDialog**：禁 backdrop blur；禁 destructive 按钮的 `hover:scale-105` 等 layout-shift
- **状态切换 mutation 反馈**：用 Toast（已有 sonner）+ 按钮文字切；禁全屏 overlay
- **Calendar Popover**：禁 `animate-in slide-in-from-top` 等 popover 入场动效（沿用 Radix 默认 fade-in 即可）

## 4. 架构与文件结构

### 4.1 架构（在 M2c-1/M2c-2 基础上的增量）

```
                  /assets/new                    /assets/:id/edit
                       │                                │
                       ▼                                ▼
              <AssetCreateForm>              <AssetEditForm>
                       │                                │
                       └──────────┬─────────────────────┘
                                  │
                                  ▼
                         <AssetFormFields>
                       ┌──────────┼──────────┐
                       │          │          │
                <GeneralFieldsForm>  <CustomFieldsForm>
                                          │
                                          ▼
                              <DynamicFieldRenderer>
                                          │
                          ┌──────────┬────┴────┬───────────┬──────────┐
                          ▼          ▼         ▼           ▼          ▼
                   <StringField> <IntField> <DateField> <EnumField> <BoolField>
                                                    ...

                  /assets/:id (M2c-2 详情页)
                       │
                       ▼
              <AssetDetailPage>
                       │
                       ├── <AssetHeader>  ─── CTA + ⋯ 菜单（D13 矩阵）
                       │                         │
                       │              ┌──────────┼──────────┬──────────┐
                       │              ▼          ▼          ▼          ▼
                       │       <CheckoutDialog> <ReturnDialog> <StateChangeAlert> <DeleteAssetAlert>
                       │       (RHF 迁版)       (RHF 迁版)      (4 个动作复用一个组件)
                       │
                       ├── ... GeneralFields / CustomFields / CheckoutTimeline (M2c-2 已有)
                       │
                       └── <AttachmentSection>
                                  │
                                  ├── <AttachmentGrid> (M2c-2 已有)
                                  └── <AttachmentAddSlot>  ←── 新增
                                            │
                                            ▼
                                     <UploadAttachmentMutation>
```

### 4.2 文件结构（新增 + 修改清单）

```
frontend/src/
├── routes/
│   ├── assets.new.tsx                       (新)
│   └── assets.$id.edit.tsx                  (新)
│
├── features/assets/
│   ├── form/                                 (新目录)
│   │   ├── asset-create-form.tsx            (新)
│   │   ├── asset-edit-form.tsx              (新)
│   │   ├── asset-form-fields.tsx            (新；登记/编辑共享)
│   │   ├── general-fields-form.tsx          (新)
│   │   ├── custom-fields-form.tsx           (新)
│   │   ├── dynamic-field-renderer.tsx       (新)
│   │   ├── field-controls/                   (新目录，每种 type 一个)
│   │   │   ├── string-field.tsx
│   │   │   ├── text-field.tsx
│   │   │   ├── int-field.tsx
│   │   │   ├── float-field.tsx
│   │   │   ├── bool-field.tsx
│   │   │   ├── date-field.tsx
│   │   │   ├── enum-field.tsx
│   │   │   ├── multi-enum-field.tsx
│   │   │   └── url-field.tsx
│   │   ├── field-def-to-zod.ts              (新；FieldDef[] → ZodObject schema 生成器；纯函数，Vitest 头号目标)
│   │   └── form-toast.ts                    (新；统一登记/编辑/删除/状态切换的 Toast 文案)
│   │
│   ├── detail/
│   │   ├── checkout-actions.ts              (M2c-2 已有，本里程碑扩 STATE_CHANGE_VERBS 等)
│   │   ├── state-change-actions.ts          (新；4 个状态切换的 verb / target / 二次确认文案)
│   │   ├── checkout-dialog.tsx              (M2c-2 已有，**迁 RHF**)
│   │   ├── return-dialog.tsx                (M2c-2 已有，**迁 RHF**)
│   │   ├── state-change-alert.tsx           (新；4 个状态切换共用的 AlertDialog)
│   │   ├── delete-asset-alert.tsx           (新；详情页 + 列表页共用)
│   │   ├── asset-header.tsx                 (M2c-2 已有，扩 §14.5 的 4 动作 + ⋯ 菜单按状态显隐)
│   │   ├── attachment-section.tsx           (M2c-2 已有 grid，扩 add slot)
│   │   ├── attachment-add-slot.tsx          (新)
│   │   └── current-checkout.ts              (M2c-2 已有，本里程碑保持纯净；§K 后端 current_checkout_id 落地后可弃用，本里程碑暂留)
│   │
│   └── list/
│       ├── assets-table.tsx                  (改：列顺序 + asset_code 主列 + SN 独立列)
│       ├── column-visibility.tsx             (改：加 acquired_at 默认隐藏 + 调列标签)
│       └── search-schema.ts                  (改：sort 默认 asset_code 升序)
│
├── api/
│   ├── hooks/
│   │   ├── use-asset-mutation.ts            (M2c-1 已有的 hook 文件骨架，本里程碑接通 useCreateAssetMutation / useUpdateAssetMutation / useDeleteAssetMutation / useChangeAssetStatusMutation)
│   │   └── use-attachment-mutation.ts       (M2c-2 已有 useDeleteAttachmentMutation，本里程碑加 useUploadAttachmentMutation)
│   └── unwrap.ts                             (M2c-2 已有；不动)
│
├── lib/
│   ├── zod-helpers.ts                       (新；input parser 类工具，如把 "32" 转成 int）
│   └── upload-progress.ts                   (新；XHR 上传 progress event helper，因为 fetch 不支持 upload progress)
│
├── components/
│   └── ui/                                   (shadcn 组件)
│       ├── form.tsx                          (新，shadcn add)
│       ├── input.tsx                         (新)
│       ├── textarea.tsx                      (新)
│       ├── checkbox.tsx                      (新)
│       ├── radio-group.tsx                   (新)
│       ├── select.tsx                        (新)
│       ├── popover.tsx                       (新)
│       ├── calendar.tsx                      (新)
│       └── command.tsx                       (新；Combobox 依赖)
│
└── tests/                                    (新目录，本里程碑首次)
    ├── setup.ts                              (vitest config + Testing Library 全局 setup)
    ├── unit/
    │   ├── field-def-to-zod.test.ts          (核心；FieldDef → Zod schema 行为测)
    │   ├── current-checkout.test.ts          (M2c-2 函数单测，本里程碑首测)
    │   ├── custom-field-formatter.test.ts    (同上)
    │   └── upload-progress.test.ts           (XHR upload progress 工具)
    └── hooks/
        ├── use-create-asset-mutation.test.tsx (msw mock 测 mutation 失效)
        ├── use-delete-asset-mutation.test.tsx (同)
        └── use-change-asset-status-mutation.test.tsx (同)

frontend/                                     (配置)
├── vitest.config.ts                          (新)
└── package.json                              (改：加 vitest / @testing-library/react / @testing-library/jest-dom / msw / jsdom)

src/asset_hub/                                (后端改动)
├── models/
│   ├── asset.py                              (改：加 asset_code / acquired_at 列)
│   └── asset_type.py                         (改：加 code_prefix 列)
│
├── api/schemas/
│   ├── asset.py                              (改：AssetRead / AssetCreate / AssetUpdate 加新字段；AssetUpdate 不允许改 type_id；ChangeStatusBody 新 DTO)
│   └── asset_type.py                         (改：TypeCreate 加 code_prefix 必填；TypeUpdate 不暴露 code_prefix)
│
├── services/
│   ├── asset.py                              (改：register 时生成 asset_code；change_status 新方法 + 状态机 enforce；delete_asset cascade 处理 CheckoutRecord 与 Attachment)
│   ├── asset_type.py                         (改：TypeService.create 加 code_prefix unique 检测；不暴露 update_prefix)
│   └── state_machine.py                      (新；4 状态 × 转换合法性矩阵的纯逻辑模块，service 层调用)
│
├── api/routers/
│   ├── assets.py                             (改：DELETE /api/assets/{id} 新；PATCH /api/assets/{id} body 加 status 字段；POST /api/assets/{id}/attachments 上传)
│   └── attachments.py                        (改或新；上传端点；可能与 assets.py 合并)
│
├── cli/
│   ├── asset_cmd.py                          (改：register 加 --acquired-at；新 delete / change-status / upload 子命令)
│   └── type_cmd.py                           (改：define 加 --prefix 必填)
│
├── storage/
│   └── adapter.py                            (改：上传文件流接口；保留 v1 本地 FS 实现)
│
└── alembic/                                  (新目录，migration)
    └── versions/
        └── 001_m2c3_field_backfill.py       (新；asset_code / code_prefix / acquired_at / current_checkout_id 字段补齐 + 旧数据回填)

tests/                                        (后端测试)
├── unit/
│   ├── test_state_machine.py                (新；4×4 转换矩阵全 case)
│   └── test_asset_service_register.py       (改；asset_code 自动生成)
├── api/
│   └── test_state_change_endpoint.py        (新)
└── cli/
    └── test_change_status_cli.py            (新)
```

### 4.3 依赖（runtime + dev 新增）

#### Frontend

| 包 | 类型 | 用途 |
| --- | --- | --- |
| `react-hook-form` | runtime | 表单状态 + 验证 |
| `@hookform/resolvers` | runtime | RHF + Zod 桥接 |
| `vitest` | dev | 单测 |
| `@vitest/ui` | dev | （可选）UI 模式 |
| `@testing-library/react` | dev | 组件交互测（M2c-4 用得多，本里程碑仅基础设施） |
| `@testing-library/jest-dom` | dev | DOM 断言 |
| `@testing-library/user-event` | dev | 用户交互模拟 |
| `jsdom` | dev | Vitest browser env |
| `msw` | dev | mutation hook 测试 mock 服务 |

#### Backend

| 包 | 用途 |
| --- | --- |
| `alembic` | DB migration（M1 跳过 Alembic 直接 `create_all`，本里程碑补齐——必须有 migration 才能在已有 DB 上加 not null + unique 字段并回填） |

`zod` / `date-fns` / shadcn 已在项目中（M2c-1 / M2c-2 装），不再列。

## 5. 数据层

### 5.1 后端数据模型变更（§K 部分落地）

#### 5.1.1 Asset 表新增列

```python
# src/asset_hub/models/asset.py
class Asset(SQLModel, table=True):
    # ... 既有列
    asset_code: str = Field(unique=True, index=True, nullable=False)           # 新
    acquired_at: date | None = Field(default=None)                              # 新
    current_checkout_id: uuid.UUID | None = Field(                              # 新；§K 反规范化
        foreign_key="checkout_records.id", default=None
    )
```

#### 5.1.2 AssetType 表新增列

```python
# src/asset_hub/models/asset_type.py
class AssetType(SQLModel, table=True):
    # ... 既有列
    code_prefix: str = Field(unique=True, index=True, nullable=False,           # 新
                             regex=r"^[A-Z]{2,4}$")
```

#### 5.1.3 type_name 反规范化方式

候选 A：在 `Asset` 表加 `type_name: str` 列，service 层在 `register` / `update` 时同步维护
候选 B：用 SQLAlchemy `relationship` + `column_property` 让 `Asset.type_name` 在 select 时 JOIN 拿出
候选 C：FastAPI `AssetRead` DTO 用 Pydantic `computed_field` + 异步加载

**plan 阶段决定**。倾向候选 B：性能可接受（v1 数据量小）+ 数据一致性最强（不用应用层维护反规范化）+ 改 type 名字时 asset 显示自动跟新。

### 5.2 DB Migration（首次引入 Alembic）

M1 时为了简化跳过了 Alembic（直接 `SQLModel.metadata.create_all` 幂等建表）。本里程碑必须补齐——给已有 DB 加 not null + unique 字段并回填旧数据。

`alembic/versions/001_m2c3_field_backfill.py` 单一 migration 完成所有改动：

1. **AssetType 加 `code_prefix`**：先 nullable 加列；停服 + 手动审查（数据量小，估 < 10 个 type）+ SQL 直填 prefix；最后改 not null + unique
2. **Asset 加 `asset_code`**：先 nullable 加列；按 type_id + created_at 顺序生成 `{prefix}-{seq:03d}` 回填；改 not null + unique
3. **Asset 加 `acquired_at`**：默认 null，无需回填
4. **Asset 加 `current_checkout_id`**：默认 null；扫描所有 status=IN_USE 的 asset，找 history 中 returned_at IS NULL 的最新一条 CheckoutRecord 回填

migration 步骤在 `release-notes-m2c3.md`（plan 阶段产出）写明手工干预点；新部署直接跑 `alembic upgrade head` + `python scripts/seed_examples.py` 即可。

### 5.3 API 端点新增 + 调整

| 端点 | 方法 | 状态 |
| --- | --- | --- |
| `/api/assets/{id}` | PATCH | 改：body 接受 `status` 字段；service 层用 state_machine enforce 转换合法性 |
| `/api/assets/{id}` | DELETE | **新**：cascade 删 CheckoutRecord + Attachment（FS + DB） |
| `/api/assets/{id}/attachments` | POST | **新**：multipart/form-data 上传单文件；多文件由前端 N 次并发请求 |
| `/api/assets` | POST | 改：body 加 `acquired_at` 可选；不接受 asset_code（系统生成） |
| `/api/types` | POST | 改：body 加 `code_prefix` 必填 |
| `/api/types/{id}` | PATCH | 改：body 不接受 code_prefix（immutable） |

**为什么不为状态切换搞 4 个独立端点**（如 `POST /api/assets/{id}/maintenance/send`）：

- 状态切换本质是单字段更新；用一个 PATCH + state_machine 校验比 4 个端点更内聚
- `state_machine.py` 是后端纯逻辑模块，独立单测 4×4 转换矩阵
- M3 §14.6 audit 化时，state_machine 升级为 `StateTransitionRecord` 写入逻辑，端点形态不变

### 5.4 前端 hook 新增 + 调整（继承 M2c-1/M2c-2 query key 规范）

```ts
// src/api/hooks/use-asset-mutation.ts
useCreateAssetMutation()    // POST /api/assets → 失效 qk.assets.all
useUpdateAssetMutation()    // PATCH /api/assets/:id → 失效 qk.assets.detail(id) + qk.assets.all
useDeleteAssetMutation()    // DELETE /api/assets/:id → 失效 qk.assets.all（detail 由 navigate 走 unmount 自然清）
useChangeAssetStatusMutation() // PATCH /api/assets/:id { status } → 失效 qk.assets.detail(id) + qk.assets.all + qk.assets.history(id)

// src/api/hooks/use-attachment-mutation.ts
useUploadAttachmentMutation() // POST /api/assets/:id/attachments → 失效 qk.assets.attachments(id)
useDeleteAttachmentMutation() // M2c-2 已有
```

mutation 失效策略与 M2c-1 §5.4 一致；列表 + 详情 + history 哪些受影响，在 plan Task 内填表对齐。

### 5.5 状态机模块（service 层纯逻辑）

```python
# src/asset_hub/services/state_machine.py
ALLOWED_TRANSITIONS = {
    AssetStatus.IDLE: {
        AssetStatus.IN_USE,        # 派发（既有）
        AssetStatus.MAINTENANCE,   # 送修
        AssetStatus.RETIRED,       # 退役
    },
    AssetStatus.IN_USE: {
        AssetStatus.IDLE,          # 归还（既有）
    },
    AssetStatus.MAINTENANCE: {
        AssetStatus.IDLE,          # 修好回库
        AssetStatus.RETIRED,       # 退役
    },
    AssetStatus.RETIRED: {
        AssetStatus.IDLE,          # 重新启用
    },
}

def assert_transition_allowed(from_status: AssetStatus, to_status: AssetStatus) -> None:
    if to_status not in ALLOWED_TRANSITIONS[from_status]:
        raise ValidationError(f"不允许从 {from_status} 转到 {to_status}")
```

CheckoutService 既有的 `register_checkout` / `return_checkout` 在事务内调 `assert_transition_allowed` + service 层显式更新 `Asset.status`；新增的 `change_asset_status` 也走同一函数。

### 5.6 FieldDef → Zod schema 生成（前端纯函数，Vitest 头号目标）

```ts
// src/features/assets/form/field-def-to-zod.ts
export function fieldDefsToZodSchema(defs: FieldDef[]): z.ZodObject<...> {
  const shape: Record<string, z.ZodTypeAny> = {};
  for (const def of defs) {
    let s = baseZodFor(def.type);              // string -> z.string(), int -> z.coerce.number().int()...
    if (def.min != null) s = s.min(def.min);
    if (def.max != null) s = s.max(def.max);
    if (def.options) s = z.enum(def.options as [string, ...string[]]);
    if (!def.required) s = s.optional();
    shape[def.name] = s;
  }
  return z.object(shape);
}
```

10+ 测试用例（每种 type × required/optional × min/max × options 边界）覆盖。

## 6. 路由 + UUID 校验

### 6.1 新路由

```ts
// /assets/new
createFileRoute('/assets/new')({ component: AssetCreateForm })

// /assets/:id/edit
createFileRoute('/assets/$id/edit')({
  parseParams: ({ id }) => ({ id: parseUuid(id) }),  // 同 M2c-2 详情页，复用 lib/uuid.ts
  component: AssetEditForm,
})
```

UUID 校验失败 → 走 TanStack Router 的 `errorComponent`（404 形态，沿用 M2c-2 的 `<NotFoundPanel>`）。

### 6.2 列表/详情页跳转点

- 列表页右上角加"+ 登记资产"按钮 → `/assets/new`
- 详情页 ⋯ 菜单"编辑" → `/assets/:id/edit`
- 列表页 ⋯ 菜单"编辑" → `/assets/:id/edit`

## 7. UI 设计（按组件拆解，每段含 §3.5 约束引用）

### 7.1 AssetCreateForm

**职责**：登记新资产。

**布局**（参考 brainstorm 阶段 mock 候选 1·H2 分区式）：

```
┌─────────────────────────────────────┐
│ 登记新资产                           │
│ /assets/new                         │
│                                     │
│ ━━ 基础信息 ━━━━━━━━━━━━━━━━━━━━━━━ │
│ 资产名 *      [____________]        │
│ 资产类型 *    [笔记本电脑 ▾]        │
│ SN            [____________]        │
│ 入账日期      [选择日期 📅]         │
│ 持有人        [____________]        │
│ 位置          [____________]        │
│ 备注          [____________]        │
│               [____________]        │
│                                     │
│ ━━ 笔记本电脑 [5 个字段] ━━━━━━━━━━ │
│ CPU *         [____________]        │
│ RAM *         [_____ ] GB           │
│ 存储          [_____ ] GB           │
│ 保修截止      [选择日期 📅]         │
│ 颜色          ○ 银色 ● 深空灰 ○ 黑色 │
│                                     │
│              [取消]  [登记]         │
└─────────────────────────────────────┘
```

**关键行为**：
- type select 切换 → 直接替换下方 type-specific 字段，无 transition；form 状态 `useEffect` 重置 custom_data 为该 type 的 default 值（FieldDef.default）
- type select 空（未创建任何 type）→ inline 提示"尚未创建任何类型。请用 CLI 创建：`asset-hub type define --name <名称> --prefix <NB>` 或让 Agent 帮你建" + 禁用所有其他字段
- asset_code 字段**不在表单中显示**——系统自动生成，提交后用户在详情页看到
- 提交流程：RHF + Zod schema（通用字段固定 + custom_fields 动态）→ submit handler → useCreateAssetMutation → success 跳详情 + Toast / failure 留页 + inline error banner

**§3.5 约束引用**：§3.5.1（H2 分区，不用 Card）；§3.5.2（label 用 Fira Sans，asset_code 预览不显示因此本组件无 mono 字段）；§3.5.3（提交按钮 primary 蓝，pending 时文字"登记中…"）；§3.5.5（type 切换无 transition，submit 按钮色变 200ms）；§3.5.6（红线：禁 spinner / blur）；§3.5.7（首次引入 Form / Input / Textarea / Checkbox / RadioGroup / Select 全部审 variant）

### 7.2 AssetEditForm

**职责**：编辑现有资产。

**与 AssetCreateForm 的差异**：

- 进入时 `useAssetDetailQuery(id)` 拉取数据 + `defaultValues` 预填到 RHF
- **type 字段 disabled** + label 旁加 muted 文字"创建后不可改"——与"取消"按钮等高放置以保持视觉对齐
- asset_code 字段**只读显示**（mono Fira Code，灰色背景）：用户能看到自己的编号
- 提交按钮文案 "保存"（不是"登记"）；pending 文字"保存中…"
- 提交成功 → 跳 `/assets/:id` + Toast "更新成功"；失败 → 留页 + inline

### 7.3 AssetFormFields（共享底层）

**职责**：抽出登记/编辑表单共享的字段渲染逻辑。

接受 props：
- `mode: 'create' | 'edit'`
- `formContext: ReturnType<typeof useForm>`
- `selectedTypeId: string | null`（用于决定 custom_fields 区块）

不直接管 submit handler / 提交后跳转 / 数据预填——这些由父组件（Create/Edit）负责。

### 7.4 DynamicFieldRenderer + field-controls/

**职责**：根据 FieldDef.type 渲染对应控件。

```ts
function DynamicFieldRenderer({ def, control }: { def: FieldDef; control: Control }) {
  switch (def.type) {
    case 'string': return <StringField def={def} control={control} />;
    case 'text':   return <TextField def={def} control={control} />;
    case 'int': case 'float': return <NumberField def={def} control={control} />;
    case 'bool':   return <BoolField def={def} control={control} />;
    case 'date':   return <DateField def={def} control={control} />;
    case 'enum':   return <EnumField def={def} control={control} />;
    case 'multi-enum': return <MultiEnumField def={def} control={control} />;
    case 'url':    return <UrlField def={def} control={control} />;
  }
}
```

每个子组件用 RHF `<Controller>` 接 form state；controls 表见 D7。

**控件细节**：

| Type | 控件细节 |
| --- | --- |
| `string` | shadcn `<Input type="text">` |
| `text` | shadcn `<Textarea rows={3}>` |
| `int` | `<Input type="text" inputMode="numeric">`；Zod `coerce.number().int()` |
| `float` | `<Input type="text" inputMode="decimal">`；Zod `coerce.number()` |
| `bool` | shadcn `<Checkbox>`；label 旁 |
| `date` | shadcn `<Popover>` + `<Calendar locale={zhCN}>`；display 用 `format(date, 'yyyy-MM-dd', { locale: zhCN })` |
| `enum` | options ≤4 → `<RadioGroup>`；options ≥5 → `<Select>`；FieldDef.displayAs override |
| `multi-enum` | options ≤4 → 多个 `<Checkbox>` 平铺；options ≥5 → `<Combobox>`（shadcn `<Command>` + `<Popover>` + 多选 + 已选项 chip 显示在 input） |
| `url` | `<Input type="url">`；Zod `string().url()` |

**unit 显示**：`int` / `float` 字段如有 `def.unit`，input 内右侧 muted 显示（用 `<div className="relative"><Input className="pr-12" /><span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">GB</span></div>` 套法）；不参与校验，提交值仅是数字。

### 7.5 AttachmentAddSlot（附件 add slot）

**职责**：附件 grid 末尾的"+ 添加附件"虚线 tile。点击 + 拖拽都能上传。

**视觉**：

```
┌─────────────────┐
│       +         │
│   添加附件      │  ← 虚线 1.5px / muted-foreground / 圆角同 tile
│                 │  ← hover: border-primary / text-primary / bg-primary/5（150ms transition-colors）
└─────────────────┘
```

**上传中态**：tile 内显示文件名（截断）+ 进度条（宽度 transition）：

```
┌─────────────────┐
│ design_v3.pdf   │
│ ▓▓▓▓▓▓░░░░ 65% │
└─────────────────┘
```

**失败态**：tile 内显示 error icon + "重试" 按钮：

```
┌─────────────────┐
│  ⚠ 上传失败     │
│   [重试]        │
└─────────────────┘
```

**多文件并发**：用户一次选 5 个文件 → grid 末尾插入 5 个临时 progress tiles + 1 个 add slot；每个文件独立 mutation；成功后 tile 替换为新文件 thumbnail；add slot 仍永久存在。

**实现细节**：
- 用 XHR 而非 fetch（fetch 不支持 upload progress）—— `lib/upload-progress.ts` 封装
- 拖拽：`onDragOver` / `onDrop` event handler；e.preventDefault；从 `e.dataTransfer.files` 取 FileList
- 文件大小前端预校验（>10MB inline 拒绝 + Toast）；mime 类型不前端硬限制，accept attribute 引导

**§3.5 约束引用**：§3.5.1 fewer-but-better（与已有附件 tile 同框）；§3.5.5 hover/transition 用 color 变化（不用 shadow）；§3.5.6 红线（禁 spinner，进度条用宽度 transition）；移动端响应式（grid 列数自然降级）

### 7.6 §14.5 状态切换：state-change-actions.ts + state-change-alert.tsx

**职责**：把 4 个状态切换动作的元数据、AlertDialog 文案、PATCH 调用统一成一份。

```ts
// src/features/assets/detail/state-change-actions.ts
export const STATE_CHANGE_ACTIONS = {
  send_to_maintenance: {
    fromStatuses: ['IDLE'],
    toStatus: 'MAINTENANCE',
    verb: '送修',
    inProgressVerb: '送修中…',
    confirmTitle: '送修这台设备？',
    confirmBody: (asset) => `${asset.name} · ${asset.asset_code} 将转为维修中状态。`,
    confirmAction: '确认送修',
    needsConfirm: false,  // 直接调，不弹 AlertDialog（轻量动作）
  },
  return_from_maintenance: {
    fromStatuses: ['MAINTENANCE'],
    toStatus: 'IDLE',
    verb: '修好回库',
    inProgressVerb: '回库中…',
    needsConfirm: false,
  },
  retire: {
    fromStatuses: ['IDLE', 'MAINTENANCE'],
    toStatus: 'RETIRED',
    verb: '退役',
    inProgressVerb: '退役中…',
    confirmTitle: '退役这台资产？',
    confirmBody: (asset) => `${asset.name} · ${asset.asset_code} 将标记为退役。退役后默认仍在列表中显示，可通过"重新启用"复活。`,
    confirmAction: '确认退役',
    needsConfirm: true,
  },
  reactivate: {
    fromStatuses: ['RETIRED'],
    toStatus: 'IDLE',
    verb: '重新启用',
    inProgressVerb: '启用中…',
    confirmTitle: '重新启用这台资产？',
    confirmBody: (asset) => `${asset.name} · ${asset.asset_code} 将从退役状态恢复为闲置。`,
    confirmAction: '确认启用',
    needsConfirm: true,
  },
} as const;
```

**为什么 send_to_maintenance / return_from_maintenance 不需要 AlertDialog**：操作轻量、可逆、低破坏性——和"派发/归还"一档；多一步确认是过度防御。**retire / reactivate 需要确认**——退役偏向不可逆（虽然技术上可重新启用，但行为意义已经"封存"）；重新启用是把封存资产重新拉回流通，需要确认是有意为之。

**state-change-alert.tsx**：通用 AlertDialog，按 STATE_CHANGE_ACTIONS[key] 渲染文案；按"确认"调 useChangeAssetStatusMutation。

**§3.5 约束引用**：§3.5.6 红线（destructive 按钮不用 hover scale）；§3.5.5 mutation pending 按钮文字切；AlertDialog overlay `bg-black/50` 不 blur

### 7.7 详情页 AssetHeader 扩展（§14.5 落地）

按 D13 的 4 状态 × 动作矩阵实现。

| 状态 | 主按钮 | 次按钮 | ⋯ 菜单（按顺序） |
| --- | --- | --- | --- |
| IDLE | 派发 | 送修 | 编辑 / 退役… / [分隔线] / 删除… |
| IN_USE | 归还 | — | 编辑 / [分隔线] / 删除（disabled，tooltip "需先归还"） |
| MAINTENANCE | 修好回库 | — | 编辑 / 退役… / [分隔线] / 删除… |
| RETIRED | 重新启用 | — | 编辑 / [分隔线] / 删除… |

按钮文字带 "…" 后缀 = 触发 AlertDialog；不带 = 直接调用或 navigate 走。

**列表页 ⋯ 菜单**：与详情页 ⋯ 菜单内容**不完全相同**——为避免列表上密集出现状态切换动作（破坏扫读节奏），列表 ⋯ 菜单仅显示「编辑 / 派发 / 归还 / 删除」四项；状态切换（送修/修好回库/退役/重新启用）只在详情页可触发。这是显式的简化决策，spec 写明。

### 7.8 DeleteAssetAlert

**触发点**：详情页 ⋯ 菜单"删除…" + 列表页 ⋯ 菜单"删除…"

**形态**（D15）：

```
┌─────────────────────────────────────┐
│ 确认删除？                           │
│                                     │
│ ThinkPad X1 Carbon · NB-007 将被    │
│ 永久删除，所有关联的派发记录、附件   │
│ 元数据也会清空。                    │
│                                     │
│ 此操作不可撤销。                    │
│                                     │
│              [取消]  [确认删除]     │
└─────────────────────────────────────┘
```

- 触发自详情页 → 删除成功后 navigate 列表 + Toast
- 触发自列表页 → 删除成功后留列表 + Toast
- IN_USE 资产删除菜单项 disabled + tooltip "需先归还"

### 7.9 列表页变更（assets-table.tsx）

**列定义改动**：

```ts
{
  id: 'asset_code',                            // ← 改自 'code'
  accessorKey: 'asset_code',                   // ← 不再 accessorFn
  header: '编号',
  cell: ({ row }) => <span className="font-code text-xs">{row.original.asset_code}</span>,
},
{
  id: 'name',
  // ... 既有
},
{
  id: 'serial_number',                          // ← 新独立列
  accessorKey: 'serial_number',
  header: 'SN',
  cell: ({ row }) => row.original.serial_number
    ? <span className="font-code text-xs">{row.original.serial_number}</span>
    : <span className="text-muted-foreground">—</span>,
},
{
  id: 'type',
  // ... 既有（type_name 由后端 §K relationship 补齐后可去掉客户端 join）
},
// ... status / holder / location / updated_at 既有
{
  id: 'acquired_at',                            // ← 新，默认隐藏
  accessorKey: 'acquired_at',
  header: '入账日期',
  cell: ({ row }) => row.original.acquired_at
    ? formatDate(row.original.acquired_at)
    : <span className="text-muted-foreground">—</span>,
},
{
  id: 'actions',
  // ... 既有
},
```

`column-visibility.tsx`：

```ts
// 默认可见
const DEFAULT_VISIBLE = ['asset_code', 'name', 'serial_number', 'type', 'status', 'holder', 'location', 'updated_at'];
// 默认隐藏
const DEFAULT_HIDDEN = ['acquired_at'];
```

**列标签**（COLUMN_LABELS）：
```
asset_code: "编号",
name: "名称",
serial_number: "SN",
type: "类型",
status: "状态",
holder: "持有人",
location: "位置",
updated_at: "更新时间",
acquired_at: "入账日期",
```

**默认排序**：`search-schema.ts` 的 `sort` 默认 `asset_code` 升序（M2c-1 是 `-updated_at`）——asset_code 升序更符合"按登记顺序看资产"的直觉。

**列表页右上角加"+ 登记资产"按钮**：跳 `/assets/new`。

### 7.10 M2c-2 Dialog 迁 RHF（独立 Task）

`CheckoutDialog` / `ReturnDialog` 从纯 `useState` + 手工校验迁到 `react-hook-form` + Zod。

**迁移范围**：
- 表单 state：`useState<{holder, location, note}>` → `useForm<{holder, location, note}>` + zodResolver
- 校验：手工 if 检查 → Zod schema：`{ holder: z.string().min(1), location: z.string().optional(), note: z.string().optional() }`
- error 显示：`<inline error banner>` 改为每字段 `<FormMessage>`（shadcn Form 体系）
- 提交按钮 disabled 逻辑 → RHF `formState.isValid` + `formState.isSubmitting`
- 不动 JSX 骨架 / Toast / mutation hook / Dialog overlay 配色

**Pre / Post 行为对齐**：迁移前后用户看到的 UX 完全一致；迁移仅是状态层切换。

**Vitest 验收**：写一个 `checkout-dialog.test.tsx`（仅本组件）验证表单基本流程——M2c-3 是引入 Vitest 的窗口，Dialog 是首批用 RHF 的组件，正好做组件交互测的"feasibility 试点"。这条 Vitest 用例**计入 D19 β 档**（视作"关键 hook 失效逻辑"的边界扩展）。

### 7.11 type select 空状态

登记表单的 type select 空时（`useAssetTypesQuery` 返回 `data.length === 0`）：

```
资产类型 *  [▾]  ← 禁用状态
↓
┌─ inline 警告（form 上方）─────────────────────┐
│ 尚未创建任何类型。请用 CLI 创建一个：        │
│   asset-hub type define \                    │
│     --name "笔记本电脑" --prefix NB \        │
│     --custom-fields "..."                    │
│ 或让 Agent 帮你建（"创建一个笔记本电脑类型"  │
│ 这种自然语言指令即可）。                     │
└──────────────────────────────────────────────┘
```

文案直接显示 CLI 命令以便复制（`code` 块格式）。提交按钮在此场景下 disabled。

## 8. 错误处理（继承 M2c-2 四层 + 新增表单层）

| 层 | 触发点 | 处理 |
| --- | --- | --- |
| L0 | 路由参数（UUID 非法） | TanStack Router parseParams 抛错 → `errorComponent` 显示 NotFoundPanel |
| L1 | 顶层 query（拉详情/列表/types） | `<ErrorState onRetry={refetch}>` 全屏 |
| L2 | 区块级 query（attachments / history） | 区块内 ErrorState（小） |
| L3 | mutation（登记/编辑/删除/状态切换/上传） | inline error banner（form 顶部）+ field-level 高亮（Zod 校验失败时）；网络/服务器错误 → Toast + 留页 |
| L4 | 表单 schema 校验（Zod） | RHF 自动 inline 显示 FormMessage |

详情：

- **登记/编辑提交失败**：
  - HTTP 4xx 业务错误（如"asset_code 重复"——理论上不会发生，但理论上 prefix 撞车时会）→ 表单顶部 inline banner 显示 server message
  - HTTP 5xx → Toast "保存失败，请重试"，表单不变
  - Zod 校验失败 → 不发请求，inline field-level 提示

- **附件上传失败**：
  - 单文件失败 → tile 显示 error 状态 + 重试按钮；其他文件不受影响
  - mime 类型不允许（后端 422）→ Toast "不支持的文件类型"
  - >10MB → Toast "文件超过 10MB 限制"

- **状态切换失败**：
  - 不允许转换（service 层 ValidationError）→ Toast 显示具体错误（如"不允许从 IN_USE 转到 MAINTENANCE"）
  - 这种情况理论上不该发生（前端按状态显隐已 cover），但后端兜底必须；Toast 文案直接来自后端

## 9. 测试策略（M2c-3 引入 Vitest β 档）

### 9.1 测试基础设施

```ts
// frontend/vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    css: false,
  },
});
```

```ts
// frontend/tests/setup.ts
import '@testing-library/jest-dom';
import { setupServer } from 'msw/node';
import { handlers } from './msw-handlers';

const server = setupServer(...handlers);
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### 9.2 β 档覆盖清单（约 12-15 个测试文件）

#### 纯函数（高 ROI，必测）

- `field-def-to-zod.test.ts` —— 每种 type × required × min/max × options 边界 ≈ 20+ case
- `current-checkout.test.ts` —— M2c-2 函数；空 history / 全已归还 / 单一 active / 多 active（异常） 4 case
- `custom-field-formatter.test.ts` —— 每种 type × empty/null/undefined ≈ 15 case
- `upload-progress.test.ts` —— XHR mock 验证 progress event 处理
- `state-change-actions.test.ts` —— STATE_CHANGE_ACTIONS 元数据 → 文案渲染（snapshot test）

#### Hook（中 ROI，挑关键的测）

- `use-create-asset-mutation.test.tsx` —— msw mock POST，验证 onSuccess 失效 `qk.assets.all`（用 `queryClient.invalidateQueries` spy）
- `use-delete-asset-mutation.test.tsx` —— msw mock DELETE，验证失效 + navigate
- `use-change-asset-status-mutation.test.tsx` —— msw mock PATCH，验证失效 detail + history + all

#### 后端 Python（pytest，已有基础设施）

- `test_state_machine.py` —— 4×4 转换矩阵全 case（合法 7 + 非法 9）
- `test_asset_service_register.py` 扩 —— asset_code 自动生成（同 type 多次 register seq 递增）
- `test_state_change_endpoint.py` —— PATCH 状态合法/非法 → 200/422
- `test_change_status_cli.py` —— CLI `--json` 输出信封形态

### 9.3 不在本里程碑测的（M2c-4 加）

- 登记表单完整 RHF 流程（type 切换、submit、错误显示）—— 需要 React Testing Library + 复杂 user-event 模拟，留 M2c-4 一并完整覆盖
- 详情页 4 状态 × ⋯ 菜单显隐 —— 视觉断言密集，M2c-4 加
- 附件上传 progress + 失败重试 —— XHR mock 复杂度高，M2c-4 加

## 10. 扩展兼容性 + 锚点

### 10.1 M2c-4（type 管理 UI）锚点

本里程碑落地的几个点为 M2c-4 准备：

- **`field-def-to-zod.ts`** 已写完——M2c-4 的 CustomFieldsBuilder 提交时也调用此函数生成 schema 试运行验证
- **field-controls/ 9 个组件** 已写完——M2c-4 的 type 编辑器要把它们以"预览"方式渲染，让用户编辑 FieldDef 后能立刻看到表单长什么样
- **AssetType.code_prefix 字段 immutable**——M2c-4 的 TypeEditPage 不允许改 prefix，本里程碑后端 schema 已锁
- **登记表单 type select 空状态**——M2c-4 落地后这段引导文案改为"+ 创建新类型"按钮跳 `/types/new`

### 10.2 M2d（CLI 接管 web 服务生命周期）锚点

本里程碑只新增 CLI 子命令（`asset register --acquired-at` / `asset delete` / `asset change-status` / `asset upload` / `type define --prefix`），不动服务生命周期。M2d 单独 spec/plan 处理 `serve start/stop/...`，与本里程碑不耦合。

### 10.3 M3 §14.1 派出类型扩展锚点

本里程碑保持 M2c-2 留下的 `CHECKOUT_VERB` / `RETURN_VERB` 常量 + `checkout-actions.ts` 模块结构不动。M3 升级路径（已记录于 M2c-2 spec §10.1）：

- `checkout-actions.ts` 升级为 `CHECKOUT_TYPES` 数组（含 `kind: 'internal' | 'external'`）
- AssetHeader CTA 升级为 split-button
- CheckoutDialog 顶部加派出类型 RadioGroup
- timeline `formatCheckoutStatus` 接管 internal/external 文字分化

本里程碑做完后，这条升级路径仍是单一文件 + 几个组件改动。

### 10.4 M3 §14.6 状态转换 audit 化锚点

本里程碑的 `state_machine.py` 是 service 层纯逻辑模块。M3 升级到 audit 化时：

- 抽 `StateTransitionRecord` 模型（`asset_id / from_status / to_status / kind / actor / note / at`）
- service 层在每次 `assert_transition_allowed` 后，事务内 insert 一条 `StateTransitionRecord`
- API 端点形态不变（PATCH /api/assets/:id { status }）
- 详情页 timeline 升级为接管所有状态切换展示（不只是派发/归还）

`state_machine.py` 模块化已经为这条升级铺好路。

### 10.5 M3 §14.7 状态枚举完善锚点

本里程碑的状态机用 `AssetStatus` 4 态枚举 + `ALLOWED_TRANSITIONS` 字典。M3 §14.7 拆 `RETIRED → RETIRED + ARCHIVED` 时：

- `AssetStatus` 加 `ARCHIVED` 枚举值
- `ALLOWED_TRANSITIONS` 加 RETIRED → ARCHIVED 转换（"彻底归档"）
- 列表默认 filter `status != ARCHIVED`，加"显示已归档"toggle
- ARCHIVED 资产隐藏所有动作（包括"重新启用"——已归档不可逆）

枚举扩展是局部改动，不动 state_machine 形态。

### 10.6 数据库 migration 后续

本里程碑首次引入 Alembic（M1 跳过）。后续所有 schema 改动都走 alembic：

- M2c-4 暂不预期 schema 改动（type 管理 UI 仅消费现有 schema）
- M3 §14.1 加 `CheckoutRecord.kind` —— 新 migration
- M3 §14.6 加 `StateTransitionRecord` 表 —— 新 migration
- M3 §14.7 加 `ARCHIVED` 枚举值 —— SQLite 不支持 ENUM ALTER，需要 string column 处理（spec 阶段已假设 status 用 string，不是 ENUM TYPE）

## 11. DoD

### 11.1 功能 DoD

- [ ] `/assets/new` 路由 + AssetCreateForm：用户可登记一台带 custom_fields 的资产；type select 空状态有 inline 引导
- [ ] `/assets/:id/edit` 路由 + AssetEditForm：用户可编辑资产所有字段（除 type）；asset_code 只读显示
- [ ] 详情页 + 列表页 ⋯ 菜单"删除"：AlertDialog 二次确认；IN_USE 资产 disable
- [ ] 附件 add slot：grid 末尾虚线 tile，点击 + 拖拽上传；多文件 + progress + 失败重试
- [ ] §14.5 状态切换：4 个动作（送修 / 修好回库 / 退役 / 重新启用）按状态显隐；retire / reactivate 走 AlertDialog
- [ ] 列表页：第一列 asset_code（mono）+ SN 独立列 + acquired_at 默认隐藏；默认排序 `asset_code` 升序
- [ ] CheckoutDialog / ReturnDialog 迁 RHF：UX 行为前后一致；Vitest 试点测试通过
- [ ] 后端字段补齐：asset_code / code_prefix / acquired_at / current_checkout_id 全部到位；alembic migration 可复现执行
- [ ] state_machine：4×4 转换矩阵 service 层 enforce + pytest 全测过
- [ ] CLI：`asset register --acquired-at` / `asset delete` / `asset change-status` / `asset upload` / `type define --prefix` 全部 `--json` 信封测过

### 11.2 工程 DoD

- [ ] frontend `pnpm build` / `pnpm lint` 全绿
- [ ] frontend `pnpm test`（vitest）所有 case 通过
- [ ] backend `uv run pytest` 全绿
- [ ] backend `uv run ruff check .` 全绿
- [ ] alembic upgrade head 在已有 v0.5 数据库上能跑通（dry-run 用 v0.5 dump 数据库验证）
- [ ] design-system MASTER `Pre-Delivery Checklist` 7 项全过
- [ ] frontend-design 闸门 ②③ 全过
- [ ] 反 AI-slop 红线 grep 0 命中（`scale-` / `animate-spin` / `backdrop-blur` / `bg-gradient`）

### 11.3 文档 DoD

- [ ] 主 spec `2026-04-15-asset-hub-design.md` 同步更新：
  - §11 路线图加 M2c-4 + M2d
  - §14.5 状态从"M2c-3 候选"改"M2c-3 已收"
  - §14.10 同上
  - §K（M2c-2 spec §10.3）打标"M2c-3 已部分落地"——`asset_code` / `code_prefix` / `acquired_at` / `current_checkout_id` 已完成；`type_name` 反规范化方式 plan 阶段拍
  - 新增 §14.11 反向纠偏说明：M1 砍 asset_code 决策与 M2c-3 加回简化版的关系（详见 §12）
- [ ] design-system MASTER 末尾加"实施期纠偏（M2c-3）"区块（实施期纠偏闸门④）
- [ ] CLI SKILL.md 更新（plan 阶段产出，M3 才正式承担——但本里程碑新 CLI 子命令的 `--help` 文本要友好）

## 12. 反向纠偏：M1 砍 asset_code 决策与 M2c-3 加回简化版

### 12.1 M1 决策的回溯

M1 brainstorm（`2026-04-16-m1-skeleton.md:12`）明写：

> **砍掉 `asset_code` 和 `code_prefix`，资产唯一标识仅用 UUID + 可选 `serial_number`**

理由（推断）：v1 单用户 + UUID 已唯一 + SN 是真业务标识 + "自动生成内部编号"是企业资产管理系统的复杂度，单用户 + Agent 工具不需要。

### 12.2 实际后果与 spec 漂移

M1 砍掉之后：

- 主 spec §5.1（`2026-04-15-asset-hub-design.md:115`）**未同步更新**——仍写 `asset_code | string, unique | 默认自动生成`
- M2c-1 spec/plan 假定 asset_code 存在；列表第一列设计成 `asset_code(mono)` 列
- 实施期发现字段不存在，M2c-1 实施期纠偏（MASTER §1）写明"权宜：列表用 SN ?? id.slice(0, 8) 顶替"
- M2c-2 spec §10.3 把 asset_code 列入"M2c-1 + M2c-2 共同遗留 → M3 一次性补"

漂移路径：M1 砍掉 → 主 spec 没改 → M2c-1/M2c-2 按"asset_code 存在"假设写 spec → 实施期发现没有 → 误读为"M3 待补缺口"。

### 12.3 M2c-3 brainstorm 的重新评估

经过 frontend-design skill 正式审核（6 候选 vs MASTER）：

- **候选 E（简化 asset_code，形如 NB-007）** 在视觉肌理 / 信息密度 / Agent 友好度 / 与 mono 调性契合度等维度综合最优
- **候选 D（自增 #）** 是次选；A/C 是保底；B/F 不及格

简化 asset_code 与 M1 砍掉的版本**形态不同**：

| 维度 | M1 砍掉的 | M2c-3 加回的 |
| --- | --- | --- |
| 形态 | `{prefix}-{year}-{seq}`（如 NB-2026-001） | `{prefix}-{seq}`（如 NB-007） |
| 计数器 | per-type per-year | per-type 全局 |
| 年度重置 | 需要 | 不需要 |
| 并发锁 | 需要 | 不需要 |
| AssetType.last_seq_year/no | 需要 | 不需要 |
| 年份语义 | 在 asset_code 里 | 由 `acquired_at` 字段独立承担（DRY） |

也就是说：**M2c-3 加回的不是 M1 砍掉的那个东西**。M1 砍的是工程复杂度过重的"完整版"；M2c-3 引入的是仅保留视觉/扫读价值、剥离了所有 v1 不需要的复杂度的"简化版"。

### 12.4 主 spec §14.11 新增条目

主 spec §14 末尾新增：

```markdown
### 14.11 简化 asset_code 反向纠偏（M2c-3 落地）

**M2c-3 落地**。M1 brainstorm（`plans/2026-04-16-m1-skeleton.md:12`）当时砍掉了 asset_code，理由是"v1 UUID 已唯一 + SN 即足"。但 M2c-1 实施期发现：

- 列表页第一列没有合适的标识符（用 `SN ?? id.slice(0,8)` 顶替形成视觉混淆）
- 用户口头/Agent CLI 引用没有简短手柄（UUID 短码无意义）

M2c-3 经 frontend-design skill 正式审核 6 候选后，重新引入 **简化 asset_code**：

- 形态：`{prefix}-{seq:03d}`（如 NB-007），prefix 来自 AssetType.code_prefix 必填字段
- 与 M1 砍掉的版本差别：**砍掉年度计数器、并发锁、AssetType.last_seq_year/no 等所有 v1 不需要的复杂度**；年份语义由 §14.10 acquired_at 字段独立承担
- 业务价值：列表扫读节奏 + 用户口头引用 + Agent CLI 友好度（`--code NB-007` / `--prefix NB` 批量过滤）

**和 M1 决策的关系**：M2c-3 加回的不是 M1 砍掉的那个东西。M1 砍的是工程复杂度过重的"完整版 asset_code"，简化版是另一个折衷点——形态优势保留，复杂度削平。

详见 [`m2c3-...-design.md`](#) §12。
```

### 12.5 工程影响

- 后端 model + schema + service + CLI 字段补齐（详见 §5.1 / §5.3）
- 前端列表页第一列从 `serial_number ?? id.slice(0,8)` 切回 `asset_code`（详见 §7.9）
- M2c-1 实施期纠偏（MASTER §1 "后端 AssetRead DTO 缺 asset_code 字段"）状态从"待办（M3）"改"M2c-3 已落地"
- M2c-2 spec §10.3 后端字段补齐清单中 asset_code / code_prefix 标"M2c-3 已落地"

## 附录 A · 手工烟测清单（M2c-3）

合并前作者在浏览器中逐项执行：

### A.1 登记表单
1. 进入 `/assets/new`，type select 空 → 显示 inline CLI 引导文案 + 提交按钮 disabled
2. CLI 创建一个 type（NB），刷新 → type select 可选；选择 NB → "笔记本电脑"区块出现
3. 通用字段 + custom 字段填完，提交 → 跳详情页 + Toast "登记成功"
4. 详情页查看：asset_code 自动生成形如 NB-001 / NB-002（顺序按 type 内）；acquired_at 显示空（未填）
5. 改 type → custom 区块**直接替换**（无 transition）；旧 custom 数据清空（按 default）
6. 必填项留空提交 → field-level inline error；submit 按钮 disabled

### A.2 编辑表单
7. 详情页 ⋯ 菜单"编辑" → 跳 `/assets/:id/edit`；type 字段 disabled + 提示"创建后不可改"；asset_code 只读 mono 灰色显示
8. 改 holder + custom 字段，提交 → 跳回详情 + Toast "更新成功"

### A.3 删除资产
9. 详情页 ⋯ 菜单"删除…" → AlertDialog 显示 asset_name + asset_code + 影响说明；点"取消"关闭
10. 重新点"删除…" → 点"确认删除"→ 跳列表 + Toast "删除成功"；列表中该资产消失
11. 派发中（IN_USE）资产 → ⋯ 菜单"删除" disabled + tooltip "需先归还"

### A.4 附件上传
12. 详情页"附件"section grid 末尾出现"+ 添加附件"虚线 tile
13. 点击 → 文件选择器；选 3 个文件 → grid 末尾插 3 个 progress tile + 1 个 add slot；progress 跑条；成功后变 thumbnail
14. 拖拽 1 个文件到 add slot → 同上
15. 拖拽一个 >10MB 文件 → Toast "文件超过 10MB 限制"，无 tile 创建
16. 模拟网络断开（DevTools throttling），上传 → tile 显示 error + 重试按钮；点重试恢复

### A.5 §14.5 状态切换
17. IDLE 资产详情页：主按钮"派发"+ 次按钮"送修"；⋯ 菜单含"退役…" + 删除…
18. 点"送修"（不弹 AlertDialog）→ Toast "送修中…"→"已送修"；状态变 MAINTENANCE；主按钮变"修好回库"
19. 点"修好回库"→ 状态回 IDLE
20. 点"退役…"→ AlertDialog 二次确认；点确认 → 状态变 RETIRED；主按钮变"重新启用"
21. 点"重新启用"→ AlertDialog 二次确认；状态回 IDLE

### A.6 列表页
22. 列表第一列 asset_code（mono Fira Code）+ SN 独立列（缺失 — muted）
23. 默认排序 asset_code 升序
24. column-visibility toggle 中可开启"入账日期"列；开启后列表显示
25. 列表右上角"+ 登记资产"按钮跳 `/assets/new`

### A.7 RHF 迁移（CheckoutDialog / ReturnDialog）
26. 派发资产 → CheckoutDialog 出现；holder 必填留空 → field-level error；填 holder + 提交 → 成功
27. 归还资产 → ReturnDialog 出现；note 可选；提交 → 成功
28. 与 M2c-2 行为对比：UX 完全一致

### A.8 反 AI-slop 红线
29. DevTools Performance 录制：登记/编辑/状态切换/上传过程 → 无 spinner 旋转、无 backdrop blur、无 transform scale
30. DevTools Computed → 字体审计：表单内 input 用 Fira Sans；asset_code / SN 显示用 Fira Code

---

**spec 完。**
