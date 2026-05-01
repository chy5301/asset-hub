# M2c-4 · 类型管理 UI + custom_fields 结构化 builder 设计文档

- **日期**：2026-05-01
- **里程碑**：M2c-4（承接 M2d，先于 M3）
- **状态**：初稿，待实施
- **作者**：conghaoyangbobby@gmail.com（与 Claude 协同 brainstorm）
- **承接**：[`2026-04-15-asset-hub-design.md`](./2026-04-15-asset-hub-design.md) §6 路由 / §11 类型驱动字段 + [`../followup-allocation.md`](../followup-allocation.md) M2c-4 范围 + [`2026-04-24-m2c1-frontend-foundation-and-list-design.md`](./2026-04-24-m2c1-frontend-foundation-and-list-design.md) §3 审美纲领

## 0. 导读

本文档是 **M2c-4 子里程碑** 的 spec。M2c-4 主线 = "类型管理 UI（list / detail / create / edit / delete）+ custom_fields 从手撸 JSON → 结构化 builder"，同步搭车 simplify §1 的 4 项 follow-up（A1 / F3 / A2 / A4），并补齐后端 PATCH `/api/types/{id}` + CLI `type update` 命令以保证 web/CLI 能力对等（v1 spec §1 一等约束）。

| 子里程碑 | 范围 | spec |
| --- | --- | --- |
| M2c-3 · 表单 + 附件上传 + 状态切换 | RHF/Zod + acquired_at + asset_code 反向纠偏 | [✓ 已交付](./2026-04-26-m2c3-form-attachments-actions-design.md) |
| M2d · CLI 接管 web 服务生命周期 | `asset-hub serve` + 4 项 backend gaps | [✓ 已交付](./2026-04-29-m2d-cli-serve-design.md) |
| **M2c-4 · 类型管理 UI**（本文） | 类型 CRUD UI + custom_fields builder + 4 项 simplify 搭车 | 本文 |
| M3 · 看板 / 导出 / SKILL.md / §14.1/14.6/14.7 | 主 spec 残值 + smoketest B1 + simplify C1/D1/H4 | 未写 |

**Timebox**：约 1.5 周。后端 + CLI 半天；前端基础设施 + 搭车 1.5–2 天；前端 builder + 五页面 + 烟测 3 天；frontend-design 审查 + spec/plan review 0.5 天。

## 1. 目标与非目标

### 1.1 目标

1. **类型管理整套 web UI**：`/types` 列表、`/types/new` 创建、`/types/$id` 详情/编辑、删除 dialog（复用 M2d B3 的 DELETE 端点）
2. **custom_fields 结构化 builder**：用户在表单内通过卡片列表交互式增删改 FieldDef，不再手撸 JSON
3. **后端 PATCH `/api/types/{id}`**：补齐 service.update_type；router 接线；`code_prefix` 保持 immutable（DTO 已不暴露此字段）
4. **CLI `type update`**：与 web 能力对等；命令面采用 "整体替换 JSON + 顶层属性独立 flag" 形态
5. **顶部导航行**（layout B nav）：app-layout 加独立 nav 行，承载"资产 / 类型"两个一级入口；M3 加看板时只需追加 `<Link>`
6. **兼容策略 B 落地**：资产详情页对 unknown-key / 必填空 violation 显示 banner（α），不阻塞操作
7. **搭车 4 项 simplify follow-up**：A1（合并 schema builder）/ F3（zodResolver 模块化常量）/ A2（FieldShell）/ A4（field-controls 泛型 `Control<TFieldValues>`）
8. **frontend-design 4 阶段介入**：沿用 M2c-1 §3.4 承诺（spec / token reaffirm / plan review / 实施期 3 闸门）

### 1.2 非目标

- ❌ **不做迁移引擎**（兼容策略 C：dry-run 影响面 + 批量清空）—— v1 单一作者破坏性变更频率低，ROI 不匹配；登记 follow-up 留观察
- ❌ **不做 type 详情页"汇总破坏面"**（β/γ 路径）—— 仅在资产详情页加 banner（α）
- ❌ **不做 CLI 字段级 patch**（`--add-field` / `--remove-field` / `--update-field`）—— 命令面爆炸 ROI 低
- ❌ **不做 type create 后自动跳"为该类型登记首个资产"** —— UX 跳跃过大，留 M4 视情而定
- ❌ **不做 type 字段拖拽排序**（dnd-kit 等）—— v1 字段数 ≤ 10，提供 ↑↓ 按钮足够
- ❌ **不动后端 `CustomFieldDef` 单字段 schema** —— 数组级 key 唯一 / options 唯一 / min ≤ max 由前端 superRefine 兜住，后端补全留 follow-up（与 K1 envelope 同 M3 周期）
- ❌ **不动 envelope.py / 退出码语义** —— `type update` 复用 0/1/2/3/10 既有定义；K1 envelope 统一仍归 M3
- ❌ **不做看板 / 导出 / SKILL.md** —— M3 主线项

### 1.3 主 spec 钩子状态

- §6 `/types` 路由 v1 标注"只读" → 本文升级为完整 CRUD（v1 spec §1 web/CLI 对等约束驱动）
- §11 类型驱动字段模型 → 本文实现 builder UX 落地
- 主 spec 未来可考虑的"自动编号 prefix" 已在 M2c-3 落地（`code_prefix` immutable）；本文沿用该约束
- 搭车 simplify §1 follow-up：A1 / F3 / A2 / A4 → 本文同步收口，从 simplify 路线图标记完成

## 2. 系统位置与组件分解

### 2.1 文件树（新增 + 修改清单）

**后端（PR-1）**：

```
src/asset_hub/
├── api/
│   ├── routers/
│   │   └── types.py              # 改：加 PATCH /api/types/{id}
│   └── schemas/
│       └── asset_type.py         # 不动（TypeUpdate 已存在）
├── services/
│   └── asset_type.py             # 改：加 update_type(id, name?, description?, custom_fields?)
└── cli/
    └── type_cmd.py               # 改：加 type_update 子命令
```

**前端 PR-2（基础设施 + 搭车，纯重构）**：

```
frontend/src/
├── components/layout/
│   └── app-layout.tsx            # 改：加 B nav 行（资产 / 类型 + ThemeToggle）
└── features/assets/form/
    ├── build-asset-schema.ts     # 新（A1）：buildAssetSchema(fieldDefs, { mode })
    ├── build-create-schema.ts    # 删
    ├── build-edit-schema.ts      # 删
    ├── asset-create-form.tsx     # 改（F3）：CREATE_EMPTY_SCHEMA 模块级常量；切到 buildAssetSchema
    ├── asset-edit-form.tsx       # 改：切到 buildAssetSchema
    ├── asset-form-fields.tsx     # 改（A4）：control prop 改 Control<TFieldValues>
    └── field-controls/
        ├── field-shell.tsx       # 新（A2）：抽出 FormField/.../FormMessage 骨架
        ├── string-field.tsx      # 改：用 FieldShell；签名改泛型
        ├── text-field.tsx        # 改：同上
        ├── url-field.tsx         # 改：同上
        ├── number-field.tsx      # 改：同上
        ├── enum-field.tsx        # 改：同上
        ├── multi-enum-field.tsx  # 改：同上
        ├── date-field.tsx        # 改：同上
        ├── bool-field.tsx        # 改：同上 + layout="inline" 特例保留
        └── types.ts              # 不动
```

**前端 PR-3（type 管理 UI）**：

```
frontend/src/
├── styles/
│   └── globals.css               # 改：加 --color-warning token（决策 D16；light + dark 各调一组）
├── routes/
│   ├── types.tsx                 # 新：列表路由
│   ├── types.new.tsx             # 新：创建路由
│   └── types.$id.tsx             # 新：详情/编辑路由（合一）
├── api/
│   ├── hooks/
│   │   └── types.ts              # 改：加 useTypeQuery / useCreateTypeMutation
│   │                             #     / useUpdateTypeMutation / useDeleteTypeMutation
│   └── query-keys.ts             # 改：加 qk.assetTypes.detail(id)
└── features/
    ├── types/
    │   ├── list/
    │   │   ├── types-table.tsx   # 新：name / code_prefix / 字段数 / 资产数 / 操作
    │   │   └── types-page.tsx    # 新：列表页容器（toolbar + table + 空态）
    │   ├── detail/
    │   │   ├── type-detail-page.tsx    # 新：summary + builder（编辑模式）+ 操作栏
    │   │   ├── type-summary-card.tsx   # 新：name/code_prefix/description/created_at
    │   │   └── type-delete-dialog.tsx  # 新：复用 M2d B3 端点
    │   └── form/
    │       ├── type-form.tsx                       # 新：create + edit 共用
    │       ├── build-type-schema.ts                # 新：name/code_prefix/description + custom_fields
    │       └── custom-fields-builder/
    │           ├── builder.tsx                     # 新：卡片列表容器（add/remove/move）
    │           ├── field-card.tsx                  # 新：单字段卡片（折叠/展开）
    │           ├── field-attribute-form.tsx        # 新：展开后的属性表单（11 属性 conditional UI）
    │           ├── field-type-selector.tsx         # 新：9 种 type 切换器
    │           └── field-options-editor.tsx        # 新：enum/multi-enum 的 options[] 编辑（chip + add）
    └── assets/detail/
        └── custom-data-section.tsx                  # 改：加 unknown-key / required-violation banner（α）
```

### 2.2 组件职责

| 层 | 组件 | 职责 |
|---|---|---|
| 后端 service | `TypeService.update_type` | 部分更新；`exclude_unset` 区分未传/null；name 撞车 → DuplicateError；FieldDef 结构错 → ValidationError；不接收 code_prefix |
| 后端 router | `PATCH /api/types/{id}` | body=TypeUpdate；response=TypeRead；不写 try/except，依赖 app.py exception handler 集中映射 |
| CLI | `type update` | 互斥校验 / 加载 schema / dry-run diff / 真改 → service.update_type；退出码 0/1/2/3/10 |
| 前端 layout | `app-layout.tsx` | header（标题 + ThemeToggle）+ nav 行（Link → /assets / /types，active 状态） |
| 前端 form 框架 | `buildAssetSchema(fieldDefs, { mode })` | A1 合并：mode='create' 含 type_id；mode='edit' 不含 |
| 前端 form 框架 | `<FieldShell def control>{render}</FieldShell>` | A2：统一 9 个外壳；bool-field 用 `layout="inline"` 特例 |
| 前端 form 框架 | `<TFieldValues>` 泛型化 | A4：field-controls + asset-form-fields 全链路类型安全；消除 `as unknown as Control` cast |
| 前端 type list | `types-table.tsx` | 表格列：name / code_prefix / 字段数 / 资产引用数 / 操作（详情 / 删除） |
| 前端 type detail | `type-detail-page.tsx` | 顶部 summary card + builder（编辑模式）+ 提交操作栏 + 删除按钮 |
| 前端 type form | `type-form.tsx` | create + edit 共用；create 新建 RHF instance；edit reset(useTypeQuery 数据) |
| 前端 builder | `builder.tsx` | useFieldArray 管 custom_fields；add / remove / move(↑↓) |
| 前端 builder | `field-card.tsx` | 折叠态：{key} {type chip} {required *} {删除}；展开态：FieldAttributeForm |
| 前端 builder | `field-attribute-form.tsx` | 11 属性 conditional UI（int/float→unit/min/max；enum/multi-enum→options/displayAs；其他仅通用属性） |
| 前端 builder | `field-type-selector.tsx` | 9 种 type 选择；切 type 时清空 type-specific 属性（unit/min/max/options/displayAs） |
| 前端 builder | `field-options-editor.tsx` | enum/multi-enum options 编辑（chip + 输入新增 + 删除） |
| 前端 asset detail | `custom-data-section.tsx`（改） | α banner：detect orphanKeys / violatedRequired；分组渲染；不阻塞编辑 |

### 2.3 单元边界设计原则

- **type-form 与 asset-form 镜像结构**：type-form 顶层 = name/code_prefix/description + custom_fields（FieldDef[]）；asset-form 顶层 = name/serial_number/.../custom_data（Record<string,unknown>）。两者用 RHF + Zod 同套范式，但不共用文件——避免抽象过度
- **builder 是受控组件**：通过 RHF `useFieldArray('custom_fields')` 与外层 type-form 状态联动；不引入独立 state store
- **A2 FieldShell 不是逻辑层**：纯 layout 抽象（FormField/FormItem/.../FormMessage）；bool-field 因 inline 布局保留特例（`<FieldShell layout="inline">`）
- **A4 泛型化只改签名不改运行时**：`<TFieldValues extends FieldValues>` + `Control<TFieldValues>`；消除 `as unknown as Control` 双重 cast；现有 38 frontend test 不应破
- **CLI `--from` 与 `type define --from` 共用 schema 格式**：JSON 结构 = `{name, code_prefix, description?, custom_fields[]}`；update 时 `code_prefix` 字段被 service 层忽略

## 3. UI 契约

### 3.1 路由

| 路径 | 用途 | 主要状态 |
|---|---|---|
| `/types` | 类型列表 | 加载中 / 空态 / 错误 / 数据态 |
| `/types/new` | 创建类型 | 表单 / 提交中 / 提交错（字段级 + root） |
| `/types/$id` | 详情 + 编辑（合一） | 加载中 / 编辑中 / 提交中 / 删除确认 dialog / 删除中 / 错误 |

**为什么 detail/edit 合一？**v1 单一作者，类型修改即编辑——独立"详情"页只读看一遍意义不大；编辑表单本身渲染了所有信息（含 created_at / updated_at metadata）。M3 若加多人协作再拆。

### 3.2 顶部导航（B nav 行）

- **位置**：在 `app-layout.tsx` 的 header 下方加一行 nav，与 main 同 `max-w-[1400px]` 居中、`px-6` 对齐
- **内容（v1）**：`资产` (`/assets`) / `类型` (`/types`)；M3 加看板时 append `<Link to="/dashboard">看板</Link>`
- **active 状态**：通过 TanStack Router 的 `useMatchRoute` 判断；视觉用 underline + `var(--color-primary)`（Tailwind: `text-primary border-b-2 border-primary`）；dark 模式由 globals.css 的 `--color-primary` dark variant 接管，不在组件内硬编码 hex（F4 修订）
- **键盘可达**：focus-visible 可见、Tab 可遍历
- **ThemeToggle 位置**：保留在 header 右侧，不并入 nav 行（视觉关注点分离）

### 3.3 列表页 `/types`

- **toolbar**：右上 "+ 新建类型" 按钮（→ `/types/new`）；左侧标题 + 类型总数
- **table**：列 = name / code_prefix（mono font）/ 字段数（"5 个字段" chip）/ 资产引用数（数字 + 点击跳到 `/assets?type_id=…`）/ 操作（→ 详情 / 删除）
- **资产引用数获取**：每行一个 `useAssetsQuery({ type_id: row.id, limit: 0 })`——v1 类型数 < 20，可接受 N 次查询；不引入聚合端点
- **加载态**：复用 assets-list 的骨架行模式——新增 `TypesTableSkeleton`（4-6 行 muted 占位 row + 不显示列头切换图标）；**严禁 spinner**（沿用 m2c1 §3.5.5 反 spinner 红线）
- **空态**：Lucide `Inbox` 图标（与 assets-list 空态一致）+ "还没有类型" + CTA 按钮 → `/types/new`
- **错误态**：复用 M2c-1 `<ErrorState onRetry={refetch}>` 组件
- **删除入口**：行操作 `…` → 删除（dialog）

### 3.4 创建/编辑表单 `/types/new` 和 `/types/$id`

**顶层布局**：

```
┌──────────────────────────────────────────┐
│ 标题：新建类型 / 编辑类型 - {name}         │
├──────────────────────────────────────────┤
│ Section: 基本信息                          │
│   name *                                  │
│   code_prefix *  （edit 模式 readOnly）    │
│   description                             │
├──────────────────────────────────────────┤
│ Section: 自定义字段（custom_fields builder）│
│   ┌──────────────────────────────────┐  │
│   │ FieldCard 1（折叠/展开）           │  │
│   │ FieldCard 2                       │  │
│   │ ...                              │  │
│   └──────────────────────────────────┘  │
│   [+ 添加字段]                            │
├──────────────────────────────────────────┤
│ Footer: [取消] [保存]                     │
└──────────────────────────────────────────┘
```

**Footer 按钮规格**（F6 修订）：
- `[取消]` 用 `variant="outline"`（secondary，navy text + navy border，对应 m2c1 §3.5.4 navy 主色 70% 占比）
- `[保存]` 用 `variant="default"`（primary action，amber CTA，对应 §3.5.4 CTA <5% 占比中的"真正关键动作"——创建/保存类型是关键操作）
- **顺序**：取消在左、保存在右（与 M2c-3 form / M2c-2 dialog footer 同序）

**提交态**（F3 修订）：mutation pending 时按钮 `disabled` + 文案切「保存中…」（创建模式 = 「创建中…」，编辑模式 = 「保存中…」）；**严禁** `<Loader2 className="animate-spin" />` 风格 spinner（沿用 M2c-2 实施期纠偏 §1）。

**code_prefix 在 edit 模式**：input readOnly + 灰显 + 解释文案"创建后不可修改"——DTO 已不暴露此字段，前端再加一层防御。

**实现细节**：edit 模式下 `code_prefix` **不进 RHF 表单 state**（buildTypeSchema 在 mode='edit' 时本就不含此字段，见 §6.4），改为从 `useTypeQuery(id)` 数据直接渲染只读 input；提交时也不参与 PATCH body。这样既视觉可见、又不被 zod 校验、也不会被误改。

### 3.5 详情/编辑合一页 `/types/$id`

- 复用 §3.4 表单；额外 metadata 区显示 created_at / updated_at（灰文本）
- 顶部右侧：[删除类型] 按钮
- 删除流程：点击 → useAssetsQuery 拿 ref_count → ref_count > 0 显示 dialog 提示 + 禁用确认按钮；ref_count = 0 显示 dialog 让确认输入 type name 防误删

**删除 dialog 视觉规格**（F10 修订）：
- 标题：「删除类型 '{name}'」
- 描述文字：「此操作不可撤销。请输入完整类型名 '{name}' 以确认」
- 输入框：`placeholder="请输入完整类型名 '{name}'"`，受控 state；按钮 disabled until `input.trim() === name`
- 确认按钮：`variant="destructive"`，文案「永久删除」；提交中切「删除中…」（沿用 M2c-2 模式，无 spinner）
- 取消按钮：`variant="outline"`

### 3.6 资产详情 unknown-key banner（α 策略）

修改 `frontend/src/features/assets/detail/custom-data-section.tsx`：

```
declaredKeys = new Set(type.custom_fields.map(f => f.key))
orphanKeys = Object.keys(asset.custom_data).filter(k => !declaredKeys.has(k))
violatedRequired = type.custom_fields.filter(f => f.required && asset.custom_data[f.key] == null)

if (orphanKeys.length || violatedRequired.length) {
  → 渲染 banner（顶部一行 + 折叠展开列表）
    <AlertTriangle /> 该资产含 {orphanKeys.length} 个未声明字段 / {violatedRequired.length} 个必填项为空
  → 主区分两组渲染：
    - declaredKeys：正常显示
    - orphanKeys：行 text-muted-foreground + 行尾 <Badge variant="outline">未声明</Badge>（F11 修订）
}
```

**banner 视觉规格**（F1 修订）：
- 图标用 Lucide `<AlertTriangle className="h-4 w-4 shrink-0" />`（**不**用 emoji "⚠"——MASTER anti-pattern: "Emojis as icons"）
- 配色用 `var(--color-warning)` token（详见 §8.1 + 决策 D16）
- 不阻塞操作：资产的编辑、删除、状态切换（checkout / return / 状态变更）入口全部正常工作；banner 仅是信息提示，不影响任何 mutation

### 3.7 错误展示策略

| 场景 | UI |
|---|---|
| DuplicateError("code_prefix 已存在") | `setError('code_prefix', { message })` 字段级红字 |
| DuplicateError("类型名称已存在") | `setError('name', { message })` 字段级红字 |
| ValidationError("custom_fields 结构无效") | InlineErrorBanner（root error）+ 保持 builder 状态 |
| ConflictError（删 type 时并发新增引用） | toast.error + dialog 不关 |
| 网络错误 | sonner toast + InlineErrorBanner |
| Builder 数组级 key 重复 | 第二张冲突卡片 key 输入框下红字 "key 'X' 已被使用" |
| Builder min > max | max 输入框下红字 "max 不能小于 min（{min}）" |
| Builder options 重复 | 重复 chip 标红 "选项 'X' 已存在" |

## 4. 后端契约

### 4.1 PATCH `/api/types/{id}`

- **request body**：`TypeUpdate`（已存在）—— `name?` / `description?` / `custom_fields?`，无 `code_prefix`
- **response 200**：`TypeRead`（已存在）
- **404 NotFoundError**：type id 不存在
- **409 DuplicateError**：name 撞车
- **422 ValidationError**：custom_fields 结构错（CustomFieldDef.model_validate 失败）
- **router 实现**：`body.model_dump(exclude_unset=True)` 直传 service；不写 try/except；依赖 api/app.py 现有 exception handler

### 4.2 `TypeService.update_type` 实现要点

```python
def update_type(
    self,
    type_id: uuid.UUID,
    name: str | None = None,
    description: str | None = None,
    custom_fields: list | None = None,
) -> AssetType:
    t = self.get_type(type_id)  # NotFoundError 透传

    if name is not None:
        t.name = name
    if description is not None:
        t.description = description
    if custom_fields is not None:
        try:
            t.custom_fields = [CustomFieldDef.model_validate(f).model_dump() for f in custom_fields]
        except Exception as e:
            raise ValidationError(f"custom_fields 结构无效: {e}") from e

    t.updated_at = datetime.now(UTC)
    try:
        self.session.commit()
    except IntegrityError:
        self.session.rollback()
        raise DuplicateError(f"类型名称已存在: {name}") from None
    self.session.refresh(t)
    return t
```

**不接收 code_prefix**：DTO 已不暴露；service 层签名也不加；router 调用 `**body.model_dump(exclude_unset=True)` 时 TypeUpdate 没这字段，不会传到 service。

**partial 语义**：参数为 `None`（未传） → 不动；`name=""` 等显式传 → 更新（v1 不区分 `description=null` vs `description=""`，前端按需）

### 4.3 OpenAPI 契约同步

PR-1 合并后 backend 重启 → 前端 `pnpm --dir frontend gen:api` 重生 `schema.d.ts`。该步骤进 PR-1 的 verification checklist。

## 5. CLI 契约：`asset-hub type update`

### 5.1 命令面

```
asset-hub type update <id>
  [--from <path-to-schema.json>]
  [--name <new-name>]
  [--description <new-description>]
  [--dry-run]
  [--json]
  [--yes]                           # JSON 模式自动跳过确认；默认非 JSON 改 custom_fields 时弹一次确认
```

### 5.2 参数互斥与必需

| 情况 | 退出码 | 文案 |
|---|---|---|
| 啥参数都没给 | 2 | "必须提供至少一个修改源：--from / --name / --description" |
| `--from` 与 `--name` 同时给 | 2 | "--from 与 --name/--description 互斥" |
| `--from` 文件不存在 / 不是合法 JSON | 2 | "JSON 文件读取失败：{path}" |
| `<id>` 不是合法 UUID | 2 | "无效的 UUID: {raw}"（沿用 deps.parse_uuid） |
| `<id>` 不存在 | 3 | "类型不存在: {id}" |
| name 撞车 | 1 | "类型名称已存在: {name}" |
| `--from` JSON 含坏 FieldDef | 1 | "custom_fields 结构无效: ..." |

### 5.3 `--from <schema.json>` 文件格式

复用 `type define --from` 的格式：

```json
{
  "name": "笔记本",
  "code_prefix": "NB",                                       // 被忽略（update 不改）
  "description": "可选",
  "custom_fields": [
    { "key": "cpu", "type": "string", "required": true },
    ...
  ]
}
```

`code_prefix` 字段允许出现（与 define 格式对称），但**update 时被 service 层忽略**（不会因为 prefix 不一致报错）。CLI 解析时只取 `name` / `description` / `custom_fields` 三字段传给 service。

### 5.4 `--dry-run` 输出

```
$ asset-hub type update <id> --from new.json --dry-run --json
{
  "success": true,
  "data": {
    "diff": {
      "name": { "from": "笔记本", "to": "便携式电脑" },
      "description": { "unchanged": true },
      "custom_fields": {
        "added":   [{ "key": "brand", ... }],
        "removed": [{ "key": "cpu" }],
        "changed": [{ "key": "ram_gb", "from": {...}, "to": {...} }],
        "unchanged_count": 3
      }
    },
    "affected_assets_count": 12          // repo.count_assets_by_type
  },
  "metadata": {},
  "error": null
}
```

退出码 **10**（dry-run 预览），不是 1。

### 5.5 退出码总结

| 码 | 触发 | 与既有退出码语义关系 |
|---|---|---|
| 0 | 成功 | 沿用 |
| 1 | DuplicateError / ValidationError | 沿用 envelope.handle_domain_errors |
| 2 | 用法错误（互斥/缺失/格式） | 沿用 deps.parse_uuid + 本命令新增 |
| 3 | NotFoundError | 沿用 envelope.handle_domain_errors |
| 10 | dry-run 预览 | 沿用 print_dry_run |

零新增码位、零冲突；K1 envelope 统一仍归 M3 处理。

## 6. custom_fields builder 设计

### 6.1 卡片态切换

- **折叠态**（默认）：单行高，左到右：`{key 文字}` `{type chip}` `{required * 标记}` `{删除按钮 trash icon}`，点击行任意位置展开
- **展开态**：内嵌 11 属性表单（详见 §6.3 conditional UI）；右上"折叠"按钮收起
- **新增字段卡**：默认展开（用户刚加的字段需要立刻填属性）；其他卡保持原状态
- **空态**：custom_fields 为空时，显示虚线占位框 + "[+ 添加你的第一个字段]" CTA。dashed border 风格沿用 M2c-3 §6 attachment-add-slot：`border-1.5 border-dashed border-muted-foreground/40`、hover `border-primary text-primary bg-primary/5`、`transition-colors`（F12 修订）

### 6.2 卡片操作

| 操作 | UI | 实现 |
|---|---|---|
| 新增 | "+ 添加字段" 按钮 | `useFieldArray.append({ key: '', type: 'string', required: false })` |
| 删除 | 折叠态 trash icon | `useFieldArray.remove(idx)`；删除前不弹确认（轻动作可后悔） |
| 上移 | 展开态 ↑ 按钮 | `useFieldArray.move(idx, idx-1)` |
| 下移 | 展开态 ↓ 按钮 | `useFieldArray.move(idx, idx+1)` |
| 切 type | FieldTypeSelector | 改 `custom_fields.{idx}.type` + 清空 `custom_fields.{idx}.{unit,min,max,options,displayAs}` |

**为什么不上拖拽？**v1 字段数 ≤ 10；引入 dnd-kit 等于装 4 KB 包 + 增 a11y / 触屏边角；↑↓ 按钮足够。

### 6.3 11 属性 conditional UI

**所有 type 通用**：
- `key`（必填，pattern `^[a-z][a-z0-9_]*$`，placeholder "snake_case"）
- `label`（选填，placeholder "显示名"）
- `required`（toggle）
- `placeholder`（选填）
- `help`（选填）
- `default`（选填，UI 形态随 type；M2c-4 v1 仅 string/text 提供 default 输入框，其他 type default 留 v2）

**type-specific**：

| type | 额外字段 |
|---|---|
| `string` / `text` / `url` | （无） |
| `int` / `float` | `unit`（mm/GB/hours 等纯展示）/ `min` / `max` |
| `enum` / `multi-enum` | `options[]`（chip 编辑器）/ `displayAs`（'radio' or 'select'） |
| `bool` / `date` | （无） |

切 type 时**清空** type-specific 属性（避免用户在 int 状态填了 min/max，切到 enum 后旧值残留）。

### 6.4 builder 内部 zod schema 与跨字段校验

`build-type-schema.ts`：

```ts
const fieldDefSchema = z.object({
  key: z.string().regex(/^[a-z][a-z0-9_]*$/, 'key 需 snake_case'),
  label: z.string().optional(),
  type: z.enum([
    'string', 'text', 'url', 'int', 'float',
    'bool', 'date', 'enum', 'multi-enum',
  ]),
  required: z.boolean().default(false),
  placeholder: z.string().optional(),
  help: z.string().optional(),
  unit: z.string().optional(),
  min: z.number().optional(),
  max: z.number().optional(),
  options: z.array(z.string()).optional(),
  displayAs: z.enum(['radio', 'select']).optional(),
}).superRefine((def, ctx) => {
  // 单字段跨属性 1：min ≤ max（仅 int/float 时校验）
  if ((def.type === 'int' || def.type === 'float') && def.min != null && def.max != null && def.min > def.max) {
    ctx.addIssue({ path: ['max'], code: 'custom', message: `max 不能小于 min（${def.min}）` });
  }
  // 单字段跨属性 2：enum/multi-enum 必须有 options 且非空
  if ((def.type === 'enum' || def.type === 'multi-enum') && (!def.options || def.options.length === 0)) {
    ctx.addIssue({ path: ['options'], code: 'custom', message: '需要至少 1 个选项' });
  }
  // 单字段跨属性 3：options 内部唯一
  if (def.options) {
    const seen = new Set<string>();
    def.options.forEach((opt, i) => {
      if (seen.has(opt)) ctx.addIssue({ path: ['options', i], code: 'custom', message: `选项 '${opt}' 已存在` });
      seen.add(opt);
    });
  }
});

const customFieldsArraySchema = z.array(fieldDefSchema).superRefine((fields, ctx) => {
  // 数组级跨字段：custom_fields 内 key 唯一
  const seen = new Map<string, number>();
  fields.forEach((f, i) => {
    if (seen.has(f.key)) {
      ctx.addIssue({ path: [i, 'key'], code: 'custom', message: `key '${f.key}' 已被使用` });
    }
    seen.set(f.key, i);
  });
});

export function buildTypeSchema({ mode }: { mode: 'create' | 'edit' }) {
  const base = z.object({
    name: z.string().min(1, '类型名必填'),
    description: z.string().optional(),
    custom_fields: customFieldsArraySchema,
  });
  return mode === 'create'
    ? base.extend({ code_prefix: z.string().regex(/^[A-Z]{2,4}$/, '需 2-4 个大写字母') })
    : base;
}
```

**为什么校验放前端而后端不动？**

- 后端 `CustomFieldDef` 只校验单 FieldDef 内部一致性（field_validator 现状）；数组级 key 唯一 / options 唯一 / min ≤ max 后端**未实现**
- builder 在前端拦下来 = 用户体验最佳（字段级红字）+ 不依赖后端 422
- 后端补全归 follow-up（与 K1 envelope 统一同 M3 周期）

## 7. 兼容策略 B 详解

### 7.1 设计原则

- **写时不动**：service.update_type 不扫描 / 不修改任何 asset.custom_data
- **读时显示警告**：仅在资产详情页 `custom-data-section`（α）；编辑表单按当前 fieldDefs 严格渲染（不渲染 orphan key 输入框）
- **保存时按 fieldDefs 严格替换**：现状 PUT 语义已是完全替换 custom_data（C），不改

### 7.2 用户旅程示例

1. **改 label**（无破坏）：banner 不显示
2. **删字段** `cpu`：
   - 资产 detail 顶部显示 banner "1 个未声明字段（cpu）"
   - 主区 cpu 灰显 + 标"未声明"
   - 用户点编辑 → 编辑表单不渲染 cpu → 保存 → service 层 PUT 完全替换 custom_data → cpu 从数据库消失
   - 用户**主动**通过编辑流"接受清理"
3. **改 type 从 string → int**：
   - 老值 `cpu="i7-12700"` 还在数据库
   - 编辑表单按新 type 渲染 int 输入 → 老 string 值在 RHF reset 时 coerce 失败 → 显示空 → 用户填新值或保留空 → 保存 → 完全替换
4. **新加 required 字段** `brand`：
   - 老资产 custom_data 没 `brand` → banner 显 "1 个必填项为空（brand）"
   - 用户编辑 → 表单出现 brand 必填红星 → 不填则前端 zod 拦截
5. **没改任何 type 字段**：banner 不显，所有正常

### 7.3 与现有 PUT 语义的兼容

`AssetService.update_asset` 现状：`custom_data` 完全替换。本文不改这个语义；它与 α banner 是配套的——banner 提示用户"有问题"，编辑流是用户"主动接受清理"的入口。

## 8. 审美纲领（frontend-design 在 spec 阶段的承诺）

继承 [`m2c1 spec §3.5`](./2026-04-24-m2c1-frontend-foundation-and-list-design.md) 全部审美纲领（工业实用主义极简 + 键盘驱动密度感 + Fira Code/Sans + 3 Motion 时刻），不重述。**M2c-4 新增组件的承诺**：

### 8.1 新组件审美红线

| 组件 | 红线 |
|---|---|
| **B nav 行** | 高度 ≤ 40px；用 `var(--space-md)` 与 header 间距；active 状态用 underline + `var(--color-primary)`（不用 background fill）；ThemeToggle 与 nav 视觉分离 |
| **types-table** | 与 assets-table 完全同款（密度、行高、列分隔、空态图标）；不引入新组件库 |
| **type-detail-page** | summary card 用与 asset-detail-page 同款 metadata 网格；不堆 shadow / glassmorphism |
| **custom-fields-builder** | 卡片折叠态高度固定（≤ 56px）；展开态遵守 spacing token；卡片间 `var(--space-md)` 间距；折叠/展开切换 `transition-[height] duration-200 ease-out` 是 **m2c1 §3.5.5 三时刻之外的第 4 个 motion 时刻**（决策 D17，理由：交互态切换需 affordance）；其他 motion 仍受 §3.5.5 banlist 全部禁用；`prefers-reduced-motion: reduce` 时降级为瞬时切换 |
| **field-type-selector** | 用 shadcn `Select`（M2c-3 已引入），**不**用 RadioGroup 横排（9 个选项太挤）；本里程碑首次密集使用，需按 m2c1 §3.5.7 红线复审：focus ring 与 §3.5.2 "显眼方块框"对齐、`bg-popover` token、no `use client` 残留、chevron icon 用 Lucide `ChevronsUpDown`（沿用 M2c-3 Combobox） |
| **field-options-editor** | chip 用 `Badge variant="secondary"`（默认 chip 美学）；hover 时 chip 右侧显 `<X className="h-3 w-3" />` 图标点击删（沿用 M2c-1 attachment 删除按钮模式，**不**做"点 chip 即删"避免误操作）；输入框 `placeholder="输入选项后按 Enter"`；Enter 键提交、不带"添加按钮"（最小化 UI 元素） |
| **unknown-key banner** | 用 `var(--color-warning)` token 做警告色（**非** `--color-cta`，避免 CTA 与 warning 语义混淆——决策 D16）；图标用 Lucide `AlertTriangle`（**禁止 emoji**）；折叠列表默认展开（信息密度 > 折叠折腾）；可关闭（per-asset `sessionStorage` dismiss，key = `m2c4.banner.dismissed.${assetId}`；重启浏览器恢复，避免永久遗忘问题） |

### 8.2 审美决策溯源

- 卡片列表 builder = M2c-1 **§3.5.2 Differentiation（keyboard-first density）** + Analytics Dashboard category 的 "data tables, KPI cards, minimal padding" 关键词（F16 修订：原引 §3.5.4 错，§3.5.4 是配色深化）
- B nav 行 = M2c-1 §3.5 "Industrial minimalism"；不用 sidebar（Anti-pattern: "No content hidden behind fixed navbars"）
- α banner 复用 amber 色相但走**独立** `--color-warning` token（决策 D16）：CTA 与 warning 语义解耦，不让 amber 同时背"关键动作"+"警告"两层语义

### 8.3 frontend-design skill 4 阶段介入

| 阶段 | 时机 | 输出 |
|---|---|---|
| ① Spec 阶段 | 本文 §8.1 / §8.2 | 审美红线写入 spec，可追溯 |
| ② Token reaffirm | spec → plan 之间 | 由用户 invoke `/frontend-design:frontend-design` 对本文 spec 草稿做 review；review 发现的问题回写 spec |
| ③ Plan review | 写完 plan 后 | 扫 plan 是否漏了 §8.1 红线、是否有 shadcn 默认 variant 渗入 |
| ④ 实施期 3 闸门 | (a) PR-2 合并前（token reaffirm，因为 PR-2 不引入新 UI 流但要保 build-asset-schema + FieldShell 不破现有审美）/ (b) PR-3 builder 骨架可跑后 / (c) PR-3 合并前最终审查——**同时勾完 m2c1/m2c2/m2c3 通用 Pre-Delivery Checklist 7 项**（emoji / cursor-pointer / hover transition / contrast / focus-visible / reduced-motion / responsive）+ **红线扫描**（`grep -rnE 'scale-\|animate-spin\|backdrop-blur\|bg-gradient-to'` 命中数 = 0）（F17 修订） | 闸门 (b) (c) 配合 §9 Playwright 烟测一起跑 |

## 9. 测试分层

### 9.1 后端 PR-1

| 层 | 文件 | 用例最小集 |
|---|---|---|
| `tests/unit/` | `test_asset_type_service.py` | update_type_name_only / update_type_description_only / update_type_custom_fields_replace / update_type_combined_all_three / update_type_not_found_raises_404 / update_type_duplicate_name_raises / update_type_invalid_field_def_raises_validation / update_type_does_not_touch_code_prefix / update_type_partial_does_not_clear_unset_fields |
| `tests/api/` | `test_types_api.py` | patch_returns_200_with_updated_dto / patch_404_on_unknown_id / patch_409_on_duplicate_name / patch_422_on_bad_field_def / patch_with_only_name_keeps_other_fields / patch_custom_fields_full_replace_semantics |
| `tests/cli/` | `test_type_update_cli.py` | update_with_from_file / update_with_name_only / update_with_description_only / update_from_and_name_conflict_exit_2 / update_no_change_source_exit_2 / update_invalid_uuid_exit_2 / update_invalid_json_in_file_exit_2 / update_unknown_id_exit_3 / update_duplicate_name_exit_1 / update_dry_run_exit_10_outputs_diff / update_json_envelope_shape |

预估 9 + 6 + 11 = **26 后端新测**。

### 9.2 前端 PR-2（基础设施 + 搭车，纯重构）

**原则**：不增"新功能测试"。重构应能用现有 38 frontend test 网兜住。

| 层 | 文件 | 用例 |
|---|---|---|
| `tests/unit/` | `build-asset-schema.test.ts` | mode='create' 含 type_id；mode='edit' 不含；fieldDefs 注入 custom_data 子 schema 一致；与原 buildCreateSchema/buildEditSchema 行为一致（用现有用例迁移） |
| `tests/unit/` | `field-controls/field-shell.test.tsx` | required 星号渲染 / help 渲染 / layout="inline" 路径 / 错误态 message 渲染 |
| `tests/hooks/` | 现有 asset-create-form.test.tsx / asset-edit-form.test.tsx | 跑通（不改用例，只验证 PR-2 改造未破） |
| `tsc 严格模式` | (隐式) | A4 泛型化后 9 个 field-controls 类型层不退化 |

预估 ~ 4 新单测 + 现有 38 全绿。

### 9.3 前端 PR-3（type 管理 UI）

| 层 | 文件 | 用例 |
|---|---|---|
| `tests/unit/` | `build-type-schema.test.ts` | name/code_prefix/description 必填校验；code_prefix 正则；fieldDefSchema 单字段（key 正则、type 枚举、min/max number）；superRefine 三条（数组级 key 唯一、min≤max、options 唯一） |
| `tests/unit/` | `unknown-key-detector.test.ts` | orphanKeys 检测 / violatedRequired 检测 / 两者都为空时不返回 banner data |
| `tests/hooks/` | `type-form.test.tsx` | create 提交 POST / edit 提交 PATCH / DuplicateError setError(code_prefix\|name) / code_prefix readOnly in edit |
| `tests/hooks/` | `custom-fields-builder.test.tsx` | add/remove/move / 切 type 时清空 type-specific 属性 / enum options 编辑 / 卡片折叠展开 |
| `tests/hooks/` | `type-delete-dialog.test.tsx` | ref_count > 0 禁用 / ref_count = 0 删除流转 / 并发 ConflictError toast |
| `tests/hooks/` | `use-types-mutations.test.tsx` | mutation 成功后 invalidate 集合（list / detail）正确；不 invalidate qk.assets.all（兼容策略 B） |
| `tests/hooks/` | `custom-data-section.test.tsx`（改） | banner 显隐条件 / orphan key 灰显路径 |

预估 PR-3 ~ 18-24 新前端测。

### 9.4 Playwright MCP 烟测（PR-3 合并前 1 次）

**触发时机**：PR-3 实施期 frontend-design 闸门 ④(b) 与 ④(c) 之间。

**环境准备**：
- `uv run asset-hub serve start --mode dev`（独立 `ASSET_HUB_DATA_DIR=data/smoke-test` 隔离）
- Playwright 入口 `http://127.0.0.1:5173`
- 跑完 `uv run asset-hub serve stop`

**结果判定**：
- 每场景结尾 `browser_console_messages` 扫 console error（任何 error 级别 = 失败）
- 关键 API call 用 `browser_network_requests` 验证状态码
- 优先 `browser_snapshot` 看 a11y 树做断言；`browser_take_screenshot` 关键节点存盘到 `tmp/smoke-screenshots/m2c4-<scenario>.png` 给 frontend-design 闸门做视觉对照
- `browser_wait_for` 用具体文案而不是固定 sleep

**8 个场景**：

| # | 场景 | 关键动作 | 断言 |
|---|---|---|---|
| 1 | Nav 行切换 | navigate /assets → click "类型" → 等 URL /types | active 视觉切换；ThemeToggle 不被挤压 |
| 2 | Type 创建 | navigate /types/new → fill_form → 加 3 个 FieldDef（cpu string required / ram_gb int min4 max128 unit=GB / os enum [Windows,macOS,Linux]）→ 提交 | 跳到 /types/{id}；POST 201；3 张卡片渲染 |
| 3 | Builder 跨字段校验 | (a) 加重复 key (b) min=10 max=2 (c) options=[A,A,B] (d) 切 int→string 验属性清空 | 各自显错位置正确；切 type 后 RHF state 干净 |
| 4 | Type → Asset 联动 | navigate /assets/new → 选刚创建 type → 验 cpu/ram_gb/os 三动态字段 → 填值提交 | POST /api/assets 含正确 custom_data |
| 5 | Type 编辑 + B 兼容触发 banner | navigate /types/{id} → 删 ram_gb → 加 brand(string required) → 提交 → 走 step4 资产 detail | PATCH 200；asset detail 顶部 banner "1 个未声明字段(ram_gb) + 1 个必填空(brand)"；orphan 灰显 |
| 6 | Type 删除（双路径） | (a) 删 ref=0 type → 列表少一项 (b) 尝试删 step2 创建（已被引用）→ 按钮禁用 | (a) DELETE 204；(b) disabled + 文案 |
| 7 | CLI `type update` 烟测 | Bash 工具：(a) `--from new.json --dry-run --json` (b) `--name X --json` (c) 互斥 `--from + --name` | (a) exit 10 + diff envelope (b) exit 0 + TypeRead (c) exit 2 |
| 8 | frontend-design 闸门 screenshot 套 | 静态截 5 张：types-list / type-detail / type-create-form / type-edit-form / builder-card-展开 | 存盘 → 闸门 ④(c) review 时对照 MASTER tokens |

**烟测失败处理**：失败 → 不合并 PR-3 → 修问题 → 重跑该场景；新 bug → 登记 follow-up（沿用 M2d followups 文档模式）。

### 9.5 测试分层小结

- 后端：26 新测（unit + api + cli）
- 前端：~ 4 + 18-24 = **22-28 新测**；现有 38 全绿
- Playwright MCP：8 场景烟测（不进 frontend/tests/，由 Claude 执行）
- frontend-design 闸门：spec/plan/PR-2/PR-3 共 4 次

## 10. PR 拆分与依赖

```
PR-1 后端+CLI ──┐
                ├─→ PR-3 前端 UI（type 管理 + builder + banner + 闸门 + 烟测）
PR-2 前端重构 ──┘
```

| PR | 范围 | 依赖 | 验证 |
|---|---|---|---|
| **PR-1** `feature/m2c4-backend` | service.update_type / PATCH router / CLI type update / 后端 26 测 | 无 | 26 新测全绿 + ruff + `gen:api` 在 PR-1 merge 后由 PR-3 同步执行 |
| **PR-2** `feature/m2c4-form-infra` | layout B nav / A1 buildAssetSchema / F3 模块级常量 / A2 FieldShell / A4 泛型 Control / 9 field-controls 改造 | 无（与 PR-1 并行起跑） | 现有 38 frontend tests 全绿 + 4 新单测 + tsc strict 不退化 + frontend-design 闸门 ④(a) |
| **PR-3** `feature/m2c4-types-ui` | types 路由 / type-form / builder / detail-banner / 22-28 新测 / Playwright 烟测 / frontend-design 闸门 ④(b)(c) | PR-1 + PR-2 都 merge | 全测全绿 + ruff/lint clean + 烟测 8 场景全绿 + frontend-design 通过 |

每个 PR 自带独立的 `gen:api`（PR-1 merge 后 PR-3 rebase 时跑一次；PR-2 不需要，纯前端重构不动 schema）。

## 11. 已知 Gap / Follow-up（M2c-4 范围外）

| 项 | 性质 | 处理 |
|---|---|---|
| 后端 type schema 数组级校验（key 唯一 / options 唯一 / min ≤ max） | M2c-4 由前端 superRefine 兜住；后端单字段 schema 未补 | 登记 follow-up，与 K1 envelope 统一同 M3 周期处理 |
| 兼容策略 C（dry-run 影响面 + 批量清空迁移） | 工作量约等于一个独立小里程碑；v1 真实场景 ROI 不匹配 | 暂不动；触发条件 = 团队多人维护 / schema 高频迭代 |
| type 详情页"汇总破坏面"（β/γ） | 需要 SQL 聚合扫所有资产 custom_data | 暂不动；触发条件 = 资产数 ≥ 1000 或类型字段频繁删改 |
| custom_fields 字段拖拽排序 | 装 dnd-kit ~4KB；v1 字段 ≤ 10 ↑↓ 足够 | 暂不动；触发条件 = 字段数 ≥ 15 / 多用户场景 |
| CLI 字段级 patch（`--add-field` / `--remove-field` / `--update-field`） | 命令面爆炸 | 暂不动；触发条件 = Agent 频繁微调单字段（实测发现） |
| `default` 属性在 int/float/bool/date/enum/multi-enum 的 UI | M2c-4 v1 仅 string/text 提供 default 输入 | 登记 follow-up，M3 视使用反馈推进 |
| K1 envelope 统一（HIGH） | M2d 已登记 | M3 SKILL.md 完善同周期 |

## 12. 决策记录

| ID | 决策 | 理由 |
|---|---|---|
| **D1** | 范围 = web UI + CLI `type update` 同步补齐（拒绝纯前端 / 仅 builder 路径） | v1 spec §1 明确 web/CLI 对等是一等约束；纯前端会留"web 能改 CLI 不能改"不对称口子 |
| **D2** | builder 形态 = 卡片列表（拒绝行内表格 / master-detail） | v1 字段数 5-10 用不上 master-detail 横向优势；卡片折叠态信息密度足够；与 shadcn Card+Collapsible 直接对齐 |
| **D3** | 兼容策略 = B（写时不动 + 读时 banner，拒绝 A 静默 / C 迁移引擎 / D 禁止破坏） | v1 单一作者破坏频率低；C 工作量约等于独立里程碑 ROI 不匹配；D 违反 web/CLI 对等 |
| **D4** | unknown-key banner 仅在资产详情页（α，拒绝 β 编辑表单 / γ type 详情汇总） | 编辑表单不渲染 orphan key 对用户无意义；γ 需要 SQL 聚合扫 custom_data 性能与复杂度堆积 |
| **D5** | 资产保存语义保持完全替换 custom_data（C，拒绝 A 浅 merge / B 服务端截断） | M2c-3 已是完全替换；A/B 改动等于回退既有决策；与 α banner 配套：banner + 编辑入口 = 用户主动接受清理 |
| **D6** | CLI `type update` = 整体替换 + 顶层独立 flag（C，拒绝纯整体替换 / 字段级 patch） | Agent 拼 JSON 比拼一堆 flag 简单；`--name` / `--description` 是高频小改不该重传 fieldDefs；字段级 patch 命令面爆炸 |
| **D7** | 退出码完全沿用 0/1/2/3/10，零新增 | M2d 已用过；K1 envelope 统一归 M3，本文不动 |
| **D8** | 搭车范围 = 宽（A1 + F3 + A2 + A4 全做） | A4 触发场景在 type-form 引入第二个 RHF 表单时存在；与 A2 一起做最划算（都改 field-controls 签名） |
| **D9** | 顶部导航 = B 独立 nav 行（拒绝 A header tabs / C sidebar） | M3 一定加看板，A→B 迁移 30-50 行；C 与 max-w-[1400px] 居中美学冲突；B 一次到位 |
| **D10** | 跨字段校验放前端 superRefine（数组级 key 唯一 / min≤max / options 唯一） | 后端单字段 schema 未补；前端拦下来 UX 最佳；后端补全归 follow-up |
| **D11** | type detail/edit 合一页（拒绝独立详情 + 编辑两页） | v1 单一作者，类型修改即编辑；M3 多人协作再拆 |
| **D12** | 字段排序 = ↑↓ 按钮（拒绝 dnd-kit） | v1 字段 ≤ 10；引入 dnd-kit 装 4KB 包 + a11y/触屏边角不值 |
| **D13** | PR 拆三段 PR-1 + PR-2 + PR-3，PR-2 纯重构独立 | A2/A4 simplify 原文标"中风险"（RHF 泛型 + 嵌套字段路径过往踩坑）；独立 PR 单独验，避免与 builder 同 PR 互相干扰排查 |
| **D14** | Playwright 烟测由 Claude 主动执行，不进 frontend/tests/ | 沿用 M2d "Claude 执行 checklist" 模式；符合 CLAUDE.md "不写 e2e" 约束 |
| **D15** | banner 不阻塞操作（仅信息提示） | warning 语义 ≠ error；与编辑入口配套实现"用户主动接受清理"路径 |
| **D16**（frontend-design F2 修订） | banner 用独立 `--color-warning` token，**而非** `--color-cta` | m2c1 §3.5.4 明确 "状态语义色不与 Primary/CTA 撞脸" + "CTA 仅用于真正的关键动作 <5%"；让 amber 同时背"CTA"+"warning"两个语义 = 色 = 语义原则破窗。色相仍是 amber 但 token 独立、dark 模式可独立调 |
| **D17**（frontend-design F8 修订） | builder 卡片折叠动效是 m2c1 §3.5.5 三时刻之外的**第 4 个 motion 时刻** | 交互态切换需 affordance，避免点击后无视觉反馈的"瞬切感"；范围严格限于 `transition-[height] duration-200 ease-out` + `prefers-reduced-motion: reduce` 时降级；其他 motion 仍受 §3.5.5 banlist 全部禁用 |
