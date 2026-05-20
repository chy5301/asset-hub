# M4 启动批次规划 — Design

> 日期：2026-05-17
> 输入：v2.0.2 之后的 5 个 open issues（#12 / #13 / #14 / #15 / #16）+ [`followup-allocation.md`](../followup-allocation.md) 中的 v2.0 PR-1/PR-2 衍生 minor 项 + [`release-notes-v2.0.md`](../release-notes-v2.0.md) §路线图中的 M4 主线
> 输出：清场期 4 PR + M4 主 PR 的 batch 切分、依赖、发版节奏
> 状态：等用户复审 → writing-plans

## 背景

v2.0.2 已发布（2026-05-14），其后 main 累计 6 commit 全部为 doc/chore 类（SKILL.md Gotcha #8–#11 累加 + GitHub Issue Forms / contact_links / PR 模板 / label 同步脚本），未发版。当前 main 干净。

### 待办池清点

1. **5 个 open issue（GitHub）**：#12 / #13 / #14 / #15 / #16（详情见 `gh issue view`）
2. **`release-notes-v2.0.md` §已知 gap**：
   - formal 5-iter description eval —— **作者无 run_loop 兴趣，本 batch 不做**
   - typer 私有 API 依赖 —— 已 pin `typer<0.30` 作哨兵，等触发再处理，**M4 范围外**
3. **`followup-allocation.md` v2.0 PR-1/PR-2 衍生 minor 项**：
   - Dashboard vs 列表 filter toggle 文案不统一（"已退役" vs "显示退役"）
   - `serve stop` 不清外部端口（PR-C 部分修了探测，但 stop 本身仍只清自管 PID）
   - `asset-header.test.tsx:225` "逾期 3 天" 测时间敏感 flaky（M3d 引入）
   - /simplify pass 衍生后端 minor：dialog test wrapper 重复 / `find_open_checkout_id` 2 查询可合并 / migration UPDATE 全表扫描 / `useTransitionsQuery` 无分页
   - e2e workflow playwright browser install 无 cache（PR-A 后实测，第 2/3 次都因冷下载 chromium 撞 15min timeout cancel）
4. **`release-notes-v2.0.md` §路线图 M4 原定**：UI 视觉打磨 + A3 dialog 合并（CheckoutDialog/ReturnDialog 抽 useFormDialog）+ 配色重设计
5. **`release-notes-v2.0.md` §路线图 M5**：People 实体化（spec §14.4）—— **本 batch 范围外**

---

## 决策

| 维度 | 选定 | 备选已淘汰 |
|---|---|---|
| Batch 切分 | **B：清场期 + M4 主线 + 独立小项** | A 保守分阶段（5+ 次 release 太碎）/ C M4 一锅炖（schema 改动与视觉混在同 PR review 撕裂） |
| 配色重设计幅度 | **P：精细化打磨** | R 色板重制（高下雨到所有页面，需 design 决策 + e2e 视觉回归，本里程碑容量不够）/ T 推倒重来（需独立 frontend-design skill brainstorming 头脑风暴会议） |
| 发版节奏 | **2 次 release**：清场期 4 PR → v2.1.0；M4 主 PR → v2.2.0 | S 3 次（v2.0.3 + v2.1.0 + v2.2.0，#16 不必单独占一次 release）/ U 1 次（与 batch B 原意"清场 vs 主线"分阶段相悖）|

---

## 清场期 · v2.1.0

CL-1/2/3/4 可并行打开 PR，合并不互相阻塞，最后一个合完发 v2.1.0。

### CL-1 · #16 brand 升 Asset 顶层公共字段（MINOR，**阻塞 M4**）

**动机**（参见 issue #16 完整描述）：

- 4 个 AssetType 中 3 个 custom_fields 重复定义同语义 `brand`，违反 DRY
- "其他" 类型无 custom_fields，brand 只能塞 `notes`，存储位置不一致影响导出/导入
- 跨类型聚合（按品牌统计 / 筛选）需扫 JSON 且依赖每类型 key 命名一致 —— 脆弱
- 沿用 v2.0 PR-3 `model` 拆列的判断准则：字段在每个 AssetType 重复出现、语义一致、描述资产本身而非类型规格 → 应升顶层

**改动面**（全栈，模仿 v2.0 PR-3 模式；**全栈 brand 列序统一为"name → brand → model"**，与日常语序「Lenovo ThinkPad T14」一致）：

- **数据模型**：`Asset.brand: str | None = Field(default=None, index=True)`，**字段定义位置紧贴 `name` 之后、`model` 之前**；alembic v4 migration（`add_column` + `ix_assets_brand` + 反向 drop，batch_alter_table）
- **数据迁移**：alembic 同次 migration 内扫所有 row，将 `custom_data.brand`（若存在且顶层 brand 为 null）回填到顶层 `brand` 列；**不动** custom_data.brand 键（JSON 弹性，零破坏）。release-notes-v2.1.0 写明用户应在升级后手动从对应 AssetType 删 brand custom field
- **AssetType reserved key 校验**（全集锁）：

  ```python
  # services/asset_type.py
  RESERVED_CUSTOM_FIELD_KEYS: frozenset[str] = frozenset({
      # Asset 顶层 user-writable 字段
      "asset_code", "serial_number", "name", "model", "brand",
      "holder", "location", "notes", "acquired_at",
      # CLI / 直觉别名
      "sn",
      # 系统/关系字段（防恶意撞）
      "type", "type_name", "type_id", "status", "id", "custom_data",
  })
  ```

  `create_type` / `update_type` 校验 `custom_fields[].key not in RESERVED_CUSTOM_FIELD_KEYS`，违规 → ValidationError + hint "key 'X' 是 Asset 顶层公共字段或保留名，请用其他 key"。**对现有 AssetType 零破坏**（仅 future create/update 时拒绝 read 不动）。release-notes-v2.1.0 升级路径需明确：用户应手动从对应 AssetType 删 brand / model / 其他 reserved key 重名的 custom field。**理由**：v1 / v2.0 PR-3 都没加这层校验，遗留 GPU AssetType 等含 `key=model` 的 custom field（v2.0 release-notes 只软提醒未强制），CL-1 抓机会一锁全锁、不再留同类坑。

- **Service 层**：`register` / `update_asset` 加 brand 参数（update 用 `_Unset` 哨兵区分"未传 vs null 清空"）；`SortByField` Literal + `SORT_FIELD_WHITELIST` frozenset + repository `_SORT_COLUMN_MAP` 三处加 brand；`list_filtered` q OR-chain 加 `Asset.brand.contains(q)`
- **DTO 层**：`AssetCreate` / `AssetUpdate` / `AssetRead` 加 brand 字段（**位置紧邻 name 之后、model 之前**）；router `create_asset` 加 `brand=body.brand` 透传
- **CLI 层**：`asset register --brand <txt>`（**位置紧邻 `--name` 之后、`--model` 之前**，help="品牌"）；`asset update --set '{"brand":...}'` 复用 JSON 模式；`asset list --sort brand` + help text 更新
- **前端层**：types AssetRow 加 brand（位置 name 后 / model 前）；表单 `general-fields-form` 在 name FormField **之后**、model FormField **之前**插入 brand FormField；详情 `asset-header` 副行排列为「brand · model」（用户期望阅读顺序）；详情 `general-fields` "名称" 行之后、"型号" 行之前插 "品牌" 行；`assets-table` 在 name 列之后、model 列之前插入 brand 列（可 sort、空 "—"）；`column-visibility` ColumnKey + COLUMN_LABELS + ALL_KEYS 加 brand；`asset-create-form` / `asset-edit-form` 加 defaultValues + reset + submit payload；`build-asset-schema` zod baseShape 加 brand nullable optional
- **导出**：`services/export.py` `_FIXED_COLUMN_NAMES` 加 "品牌"（11 列 → 12 列，**位置在 "名称" 之后、"型号" 之前**）：

  ```python
  _FIXED_COLUMN_NAMES = [
      "资产编号", "名称", "品牌", "型号", "类型", "状态",
      "保管人", "位置", "闲置天数", "入账日期", "铭牌编号", "备注",
  ]
  ```

  示例 CSV 行：

  ```csv
  资产编号,名称,品牌,型号,类型,状态,保管人,位置,闲置天数,入账日期,铭牌编号,备注
  LP-2024-001,工位本-01,Lenovo,ThinkPad T14 Gen 4,笔记本电脑,使用中,张三,上海办公室,0,2024-03-15,PF-XXXX,
  ```

  `_build_rows` 注入 `a.brand or ""`；既有测试 column 索引（旧 model 在 index 2，新 brand 在 index 2、model 在 index 3）/ autofilter 范围 `A1:K{n}` → `A1:L{n}` / header startswith 更新
- **examples/types/\*.json**：删 3 个含 brand custom_field 的 example type 中的 brand 项（laptop / bus-interface / dc-power）
- **SKILL.md**：Asset 顶层公共字段速查表加 brand 行（位置 name 后 / model 前）；Gotcha #8（顶层 vs custom 边界）更新含 brand + 提示 reserved key 校验已强制生效
- **CLI / API 测试基线**：service / cli / api / migration 四层 TDD；reserved key 校验测 5+ case（每类 reserved 一个 + 别名 sn 一个 + 通过 case）

**M4 阻塞原因**：CL-1 与 M4 主 PR 都改 frontend `general-fields-form` / `asset-header` / `general-fields` / `assets-table` / 导出 4-5 个同一改动面文件。先 CL-1 后 M4 = M4 视觉一次画完最终字段集；并行或反向 = 互相覆盖。

### CL-2 · #12 CLI FieldType 枚举暴露（MINOR，不阻塞）

**动机**：Agent 设计 AssetType 时无源码访问无法知道 `custom_fields[].type` 合法值。已实测 v2.0.2 后 skill 验证中 Agent 写过 `type: "boolean"`（合法值是 `bool`）。

**改动面**（issue #12 方案 A）：

- 扩 `--help-json` 输出：在 `type define` 命令的 `--fields` 参数描述下嵌套 `valid_field_types: ["string", "text", "url", "int", "float", "bool", "enum", "multi-enum", "date"]`
- 实现：`FieldType` enum 已在 `services/field_type.py` 集中，从那里 source of truth 反射
- 测试：`tests/cli/test_type_cmd.py` 加 `--help-json` 含 valid_field_types 断言
- 不改动：Pydantic `CustomFieldDef.type` 仍是 `str`（业务约束保留在 service 层的现有架构，不为 introspect 改 DTO）

**不在 scope**：方案 B（独立 `type fields list` 子命令）—— 多一个命令增加 surface area，`--help-json` 嵌套足够

### CL-3 · e2e workflow playwright cache（PATCH，不阻塞）

**动机**：v2.x PR-A merge 后实测 `.github/workflows/e2e.yml` step 9 `pnpm exec playwright install --with-deps chromium` 每次冷下 ~250MB chromium binary，第 2/3 次（rerun）连卡 14m48s 撞 15min timeout cancel。本身 0 改动也复现，与本仓库代码无关。

**改动面**：

- `.github/workflows/e2e.yml` 在 `pnpm install` 之后、playwright install 之前插入 `actions/cache@v4` step
- 缓存路径 `~/.cache/ms-playwright`
- cache key：`${{ runner.os }}-playwright-${{ hashFiles('frontend/pnpm-lock.yaml') }}`（playwright 版本变就失效）
- 不改 `timeout-minutes: 15`（cache hit 时充裕；cold start 多数情况仍能在 15min 内完成；若后续仍反复 timeout 再单独抬到 20）

**不在 scope**：换用 `microsoft/playwright-github-action`（外部 action 多一层依赖，cache 已够）

### CL-4 · `serve stop` 不清外部端口（PATCH，不阻塞）

**动机**：v2.0 PR-1 / PR-3 visual smoke 两次撞，根因 v2.x PR-C 已部分修（IPv6 双栈探测 + Vite `strictPort: true`），但 `serve stop` 本身仍只 kill PID 文件里记的进程。当端口被非 serve 拉起的旧 Vite 实例占住时，`serve start` 后 strictPort 会让新 Vite fail-fast（PR-C 修复），但 doctor 没有给出明确诊断指引。

**改动面**（doctor 增强）：

- `serve doctor` 加 `check_port_owner` 项：探测 `frontend_port` / `backend_port` 占用者 PID，若 PID 不等于 PID 文件值（或 PID 文件不存在但端口被占）→ 返 `ok=false` + fix_hint 含 OS-specific 指令（Windows `Get-NetTCPConnection -LocalPort 5173 \| ... \| Stop-Process` / Linux `lsof -i :5173`）
- 测试：`tests/unit/test_doctor.py::test_check_port_owner_external` 新增

**不在 scope**：

- `serve stop` 主动 kill 外部进程 —— CLI 不该清不归我管的进程
- `serve start` 增加额外探测 —— PR-C 的 strictPort + IPv6 双栈已足够 fail-fast

---

## M4 主 PR · v2.2.0

启动条件：v2.1.0 tagged + pushed。

单 PR 包，分支 `feat/m4-visual-polish`（或 `feat/m4` 简称）。

### M4-A · A3 dialog 合并

**位置**：`frontend/src/features/assets/detail/checkout-dialog.tsx` + `return-dialog.tsx`

**改动**：抽 `useFormDialog<T>({ schema, defaultValues, mutate, onSuccess })` hook（或 `<FormDialog>` 外壳），dialog 体只剩字段定义 + 描述文字。预计样板 -30 行。

**测试**：`tests/components/checkout-dialog.test.tsx` 现有 2 case 保持绿；新增 `useFormDialog.test.ts` unit case。

### M4-B · 配色精打磨（幅度 P）

只修具体问题点，**不动 MASTER.md 整体色板架构**。修复清单：

1. **#13 看板背景割裂**：dashboard `bg-card` 与页面 body 背景色对不上 → 改 dashboard 卡片背景与全局 bg 协调（具体方案：参 `design-system/asset-hub/MASTER.md` 与可能存在的 `pages/dashboard.md`）
2. **Dashboard vs 列表 filter toggle 文案不统一**：统一为"显示退役 / 显示注销"句式（句式与 STATUS_META label 配套更清晰）
3. **toggle / filter chip 样式校准**：dashboard 与列表 toggle 视觉收敛
4. **status 色 token 校准**：6 态色对比度审计（特别是 BROKEN 故障态 token）
5. **空 / 错 / loading 态视觉差距收口**：常见问题面 audit 列表（限定在 dashboard + 列表 + 详情 3 页）

**不在 scope**：

- 字体重选 / 间距系统重制 / 整体 hierarchy 重设（属 R 或 T 幅度）
- 跨页面 audit（限定在以上 5 修复点）

### M4-C · 看板可用性（#13 剩余项）

- **Y 轴 label 改 `name`**：`frontend/src/features/dashboard/charts/idle-top-bar-chart.tsx` `<YAxis dataKey="asset_code" />` → `name`；扩 API schema `IdleTopItem` 加 `name: str`；`services/stats_service.py` 闲置 Top 查询 select `Asset.name`；`pnpm --dir frontend gen:api` 同步类型
- **看板排版**：栅格对齐、卡片间距、信息密度调整（限定改 `frontend/src/features/dashboard/dashboard-page.tsx` + `dashboard-header.tsx`，不深入 chart 内部）

### M4-D · 附件 lightbox（#14）

**位置**：`frontend/src/features/assets/detail/attachment-lightbox.tsx`

**改动**（issue #14 方案 A）：

- `DialogContent` 加 `!max-w-[90vw]` important 覆盖默认 `sm:max-w-sm` （tailwind-merge 不会自动覆盖不同响应式前缀）
- `DialogContent` 传 `showCloseButton={false}`，保留自定义工具栏里的 X（下载/删除/关闭聚一处）
- 测试：`frontend/tests/unit/attachment-lightbox.test.tsx`（如不存在则新增）覆盖 sm 断点宽度 + 单 X 渲染

### M4-E · 列表排序（#15）

**位置**：`frontend/src/features/assets/list/assets-table.tsx`

**改动**：

- 第 125 行 `type` 列：删 `enableSorting: false`（保留现有 `accessorFn: (r) => r.type_name ?? ""`，默认字典序）
- 第 136 行 `status` 列：删 `enableSorting: false` + 加自定义 `sortingFn`，按 `ASSET_STATUS_VALUES`（定义在 `search-schema.ts`，顺序已是 IDLE→IN_USE→MAINTENANCE→BROKEN→RETIRED→DISPOSED 生命周期序）下标排序
- URL `sort` 参数与现有列保持一致（客户端 `manualSorting: false`，零后端改动）

### M4-F · asset-header flaky test fix（顺修）

**位置**：`frontend/tests/components/asset-header.test.tsx:225`

**根因**：M3d commit `3dcdf56` 引入，测试构造 `due_at = Date.now() - 3 * 86400000` 解析时无时区导致按 local 时间偏移得到 3+ 天而非 3 天。

**改动**：用 `vi.useFakeTimers()` 冻结时间到固定 ISO 时间戳，或断言 `/逾期 \d 天/` 正则（不强 3）。**选 fake timers**（更准确）。

### M4 总改动面

- frontend：dialog wrapper / dashboard 3 文件 / lightbox / assets-table / asset-header test / 可能 design-system tokens 微调
- backend：仅 `IdleTopItem` schema + stats_service select Asset.name（M4-C 唯一后端改动）
- gen:api：跑一次

### M4 测试基线

- frontend unit + e2e 保持现有规模
- 新增：`useFormDialog.test.ts` / `attachment-lightbox.test.tsx`（sm 宽度 + 单 X）/ assets-table sortingFn 单测
- 视觉验证：用 Playwright MCP 烟测（非固化 e2e）—— `browser_snapshot` dashboard 3 页 + lightbox 大屏 + 列表排序状态
- 固化 e2e：列表排序加 1 个 spec（防止 enableSorting 误设回 false 回归）

---

## 调度

```
时间线：

[现在]            [v2.1.0]              [v2.2.0]
  │                   │                     │
  ├─ CL-1 #16 ──┐     │                     │
  ├─ CL-2 #12 ──┤     │                     │
  ├─ CL-3 e2e ──┼─► tag v2.1.0 ──► M4-PR ──┴─► tag v2.2.0
  └─ CL-4 stop ─┘                            
```

- **CL-1/2/3/4**：可并行打开 4 个 PR；合并不互相阻塞；最后一个合完触发 v2.1.0 tag + release-notes
- **M4-PR**：单 PR 包 A/B/C/D/E/F 六个子项；启动条件 v2.1.0 tagged
- **CL-2/3/4 与 CL-1 不互依**，但发版等齐（statement 简洁、release notes 一次性消化）

---

## 明确不做（YAGNI 边界）

| 项 | 来源 | 不做理由 |
|---|---|---|
| formal 5-iter description eval | release-notes-v2.0 §gap | 作者无 run_loop 兴趣 |
| typer 私有 API 依赖处理 | release-notes-v2.0 §gap | 已 pin `<0.30` 哨兵，等触发再说 |
| simplify §7 后端 minor（`find_open_checkout_id` 2 查询合并 / migration UPDATE 全表扫描 / `useTransitionsQuery` 无分页 / dialog test wrapper 重复）| followup-allocation | 跟 M4 改动面 0 重叠，ROI 低，触发条件未到 |
| A3 之外的 dialog 改造（state-change-alert 等）| simplify §1.B | M4 只动 checkout/return；其他 dialog 不蹭 |
| 配色重设计 R/T 幅度 | M4 决策 | 选定 P 精细化打磨 |
| 整体 audit（跨页面字体 / 间距 / hierarchy）| M4 决策 | P 幅度限定在已列出 5 修复点 |
| M5 People 实体化 | spec §14.4 | 下个里程碑 |
| `serve stop` 主动 kill 外部进程 | followup-allocation | CLI 不该清不归我管的进程 |

---

## 风险

1. **CL-1 数据迁移**：用户存量 `custom_data.brand` 与新 `Asset.brand` 同步策略需在 alembic 内部做 read-write 迁移（仅当顶层 null 时回填）。alembic 必须用 `batch_alter_table`（SQLite 改表必需，CLAUDE.md 已明文）。回滚不可逆（同 v2.0.0 PR-1 migration 风险定级）。
2. **AssetType reserved key 全集校验**：reserved set 含 16 项（asset_code / serial_number / sn / name / model / brand / holder / location / notes / acquired_at / type / type_name / type_id / status / id / custom_data）。error message 必须指明撞到的具体 reserved 名 + 提示用顶层字段或换 key。**对现有 AssetType 含 model / brand / sn 等 reserved key 重名 custom_field 零破坏**（仅 future create/update 拒绝）。release-notes-v2.1.0 升级路径含"手动从 AssetType 删 brand / model / 其他 reserved key 重名 custom field"步骤；同步更新 SKILL.md Gotcha #8
3. **gen:api 同步**：CL-1（schema 改 +1 字段）+ M4-C（IdleTopItem 加 name）都必须 `pnpm --dir frontend gen:api`，CLAUDE.md 已明文，但容易漏 → plan 里显式列为 phase 收尾 task
4. **M4-B 配色精打磨 scope creep**：P 幅度容易越做越宽，本 spec 已锁定 5 修复点 checklist 防扩散；plan 阶段须把每个修复点的"何时停"显式写出
5. **CL-3 cache key 不当**：playwright 升级时 cache 失效靠 `hashFiles('frontend/pnpm-lock.yaml')` 触发；若改用 monorepo 工具单独锁 playwright 版本 cache 不失效会拿到旧 binary
6. **CL-4 doctor check 平台差异**：Windows / Linux / macOS 的 "PID by port" 探测命令不同；psutil 已是项目依赖，优先用 psutil 而非 OS 命令
7. **release-notes 撰写**：v2.1.0（清场期合包，含 #16 user-visible feature + 3 polish）+ v2.2.0（M4 视觉打磨）各自需要独立 release notes，特别是 v2.1.0 brand 升级路径含 AssetType 手动清理步骤

---

## 后续

本 spec approve 后转 writing-plans 生成 5 个 plan：

- `2026-05-17-cl1-brand-promotion.md`（最大，6 phase 起步）
- `2026-05-17-cl2-fieldtype-introspection.md`（小）
- `2026-05-17-cl3-e2e-playwright-cache.md`（小）
- `2026-05-17-cl4-serve-doctor-port-owner.md`（小）
- `2026-05-17-m4-visual-polish.md`（中，6 子项 A-F）

CL-2/3/4 plan 可以精简到 2-3 phase；CL-1 / M4 需要详细 phase 切分。
