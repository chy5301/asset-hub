# M2c-4 类型管理 UI 部署手工干预清单

## 概览

M2c-4 完整交付内容（PR-1 + PR-2 + PR-3 三个分支合并）：

- **PR-1（feature/m2c4-backend，已合并 d47ce91）**：后端 update_type service + PATCH /api/types/{id} router + CLI `asset-hub type update` 命令（`--name` / `--from` / `--dry-run` / `--json`）
- **PR-2（feature/m2c4-form-infra，已合并 db9f946）**：A1 合并 `buildAssetSchema(fieldDefs, { mode })` + F3 module-level schema 常量 + A2 `<FieldShell>` 抽象收敛 9 个 field-control + A4 `Control<TFieldValues>` 泛型化消除双重 cast + B 顶部 nav 行（资产 / 类型导航）
- **PR-3（feature/m2c4-types-ui，2026-05-02 合并）**：类型管理 web UI（/types 列表 + /types/new 创建 + /types/{id} 编辑/删除）+ custom_fields 结构化 builder（9 种字段类型 + superRefine 三条校验）+ 资产详情 unknown-key banner（B 策略）+ 3 条 file-based routes + §P fuzzy match 修复

## 升级前

1. 备份数据库 `data/asset_hub.db`
2. **无后端 schema 变更**：PR-1 仅加 update_type service + PATCH router，未修改表结构；alembic 不需要 upgrade

## 升级

```bash
git pull
uv sync
pnpm --dir frontend install
pnpm --dir frontend gen:api
pnpm --dir frontend build  # 如有生产部署
```

## 升级后验证

```bash
uv run pytest                           # 311 passed + 1 skipped
pnpm --dir frontend test --run         # 73 passed (16 files)
uv run ruff check .                    # All checks passed
pnpm --dir frontend lint               # 0 errors
cd frontend && pnpm exec tsc -b        # 0 errors
```

> **已知 lint warnings（非错误）**：2 处 `react-table incompatible-library` — 分别在 `assets-table.tsx` + `types-table.tsx`，属于 TanStack Table v8 与 eslint-plugin-react-hooks 的已知 pattern，不影响运行。

## CLI 表面验证

```bash
# 查看帮助（exit 0）
uv run asset-hub type update --help

# 成功更新（exit 0 + JSON 信封）
uv run asset-hub type update <type-uuid> --name "笔记本电脑（更新）" --json

# 从文件读取属性（dry-run exit 10 + diff 预览）
uv run asset-hub type update <type-uuid> --from type_patch.json --dry-run --json

# 互斥校验（--from 与字段直写同时出现 exit 2）
uv run asset-hub type update <type-uuid> --from type_patch.json --name "冲突" --json
```

> 替换 `<type-uuid>` 为 `uv run asset-hub type list --json | python -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])"` 获取的真实 UUID。

## Web UI 烟测（已通过 Playwright MCP 8 场景）

- [x] `/types` 列表页：skeleton 加载态 + 空态 dashed border + 错误态三态切换
- [x] `/types/new` 创建类型：builder 9 种字段类型 select + superRefine 三条跨字段校验（options 非空 / min≤max / prefix 唯一性）
- [x] `/types/{id}` 编辑：TypeForm create/edit 共用 + 保存成功 toast + 404 not-found 态
- [x] `/types/{id}` 删除：二次输入 name 确认 + ref_count 守卫（有资产引用时禁删）
- [x] 资产详情 unknown-key banner：AlertTriangle 图标 + 未声明字段灰显 + sessionStorage dismiss
- [x] B nav 行 active 状态：切换 / → /types 互斥，精确匹配（§P fix commit 77caf01）
- [x] TypeForm reset 归一化：编辑页点保存不再静默失败（null→undefined 归一化 commit f2d11cc）
- [x] Type → Asset 联动：资产创建/编辑选 type 后 custom_fields builder 定义的字段动态渲染并提交

烟测截图：`tmp/smoke-screenshots/m2c4-*.png`（5 张，不入库）

## 关键 commits（PR-3，共 33 commits）

- `8b5096a` — fix routes: types.tsx 拆 layout + types.index.tsx，匹配 assets.$id 模式（critical：不拆则 /types/new 和 /types/{id} 不渲染）
- `f2d11cc` — fix types: TypeForm reset 前归一化 null→undefined 避免 zod 拒绝导致 silent submit failure（critical：烟测 S5 发现）
- `b2f14d8` — fix types-delete: canDelete 加 isLoading 竞态守卫 + isError 默认 hasRefs=true
- `0b43193` — fix builder: field-attribute-form Array.isArray 守卫修运行时崩溃 + 9 处 a11y htmlFor/id 配对
- `cc2cfc9` — fix builder: field-card chevron focus 改用 outline（避 Card overflow-hidden 切割）
- `fad540e` — fix builder: field-options-editor X 按钮 outline focus + errorSet useMemo
- `d8e0b82` — fix types: TypeForm resolver/control 加 §J/§L cast 解决 tsc -b 推导（Task 27 retroactive）
- `77caf01` — feat routes: /types /types/new /types/{id} 三条 file-based route + §P NavBar 精确匹配修双 active 错乱 + 删 5 处 as never cast

## 已知 Gap / 后续

| 项 | 性质 | 处理 |
|---|---|---|
| 后端 type schema 数组级校验（custom_fields key 唯一性、min≤max 等） | M2c-4 由前端 superRefine 兜住；后端目前只校验单字段 schema | 与 K1 envelope 统一同 M3 周期 |
| `acquired_at` 写入路径 bug（§K）| pre-existing：`DateField` 经 FieldShell 写到 `custom_data.acquired_at` 而非顶层 | M3 排期前**必须**独立 small PR 修复 |
| 兼容策略 C 迁移引擎（旧 asset 数据 schema-aware 转换）| v1 单作者 ROI 不匹配 | 暂不动 |
| dnd-kit 拖拽排序（custom_fields 顺序）| v1 字段 ≤ 10，↑↓ 按钮足够 | 暂不动 |
| `default` 值 UI 在 int/float/bool/date/enum/multi-enum 类型 | v1 仅 string/text 支持 default | 登记 follow-up，下一里程碑 |
| MultiEnumField label htmlFor 指向 div（a11y §O）| click-on-label 失效，键盘导航正常 | M3 加新 field-control 时一并做 |

## 部署后第一周关注

- 监控 unknown-key banner 出现频率：高频 = 类型 schema 频繁变动信号，可能需要 C 迁移引擎
- 监控 CLI `type update` 互斥错误率（exit 2）：评估是否需要优化 help 文案或 CLI UX
