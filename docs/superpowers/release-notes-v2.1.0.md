# v2.1.0 发版升级指南

> 发布日期：2026-05-20
> 含 4 个独立合并的清场期 PR（CL-1 #20 / CL-2 #19 / CL-3 #17 / CL-4 #18）。

## 概览

v2.1.0 含 4 个独立合并的 polish PR：

| PR | 主题 |
|---|---|
| CL-1 | brand 升 Asset 顶层公共字段 + AssetType reserved key 全集校验 |
| CL-2 | CLI --help-json 暴露 type define 的 valid_field_types |
| CL-3 | e2e workflow playwright browser cache |
| CL-4 | serve doctor 加 check_port_owner 探测外部端口占用 |

## 升级路径

```bash
cp data/asset_hub.db data/asset_hub.db.v2.0.bak
git fetch && git checkout v2.1.0
uv sync && pnpm --dir frontend install
uv run alembic upgrade head
uv run asset-hub serve restart --mode prod
```

## Breaking changes

### Schema（CL-1）

- `Asset` 加 `brand: str | None` 顶层字段（位置紧贴 name 之后、model 之前），加 `ix_assets_brand` 索引
- alembic v4 migration 含数据回填：custom_data.brand（非空字符串，顶层为 null 时）→ 顶层 brand
- custom_data.brand 键保留不动（JSON 弹性零破坏）

### 升级注意（CL-1）

历史 AssetType 含 `key="brand"` 的 custom_field 不会被破坏（read 仍生效），但**强烈建议手动从 AssetType 删除**——否则会出现以下 UI 异常：

**双输入框现象**（清理前）：

```
编辑资产表单：
  名称：[ 工位本-01           ]
  品牌：[ Lenovo              ]   ← 顶层 brand 输入框（CL-1 新增）
  型号：[ ThinkPad T14 Gen 4  ]
  品牌：[ Lenovo              ]   ← custom_data.brand 输入框（历史 custom_field 残留）
```

清理后**收敛为单输入框**：

```
编辑资产表单：
  名称：[ 工位本-01           ]
  品牌：[ Lenovo              ]   ← 仅顶层 brand
  型号：[ ThinkPad T14 Gen 4  ]
```

**清理流程**：

1. 在前端 type 管理页编辑对应 AssetType
2. 删除 `custom_fields` 中 `key=brand` 的项
3. 保存
4. 已录入资产的 `custom_data.brand` 键自动失效（顶层 brand 已是真实数据源，导出 / 搜索 / 聚合 / 详情页显示都从顶层走）；JSON 弹性，键残留不影响

**视觉变化清单**（清理生效）：

- 编辑表单：双"品牌"输入框 → 单顶层"品牌"输入框
- 详情页 general-fields：原"品牌"行（来自 custom_data）+ 新"品牌"行（来自顶层）→ 单"品牌"行
- 详情页 header 副行：原可能含 custom_data.brand 渲染 → 仅顶层 brand 渲染（自然语序 brand · model）
- 列表表格：原可能 brand custom column → 仅顶层 brand 固定列

同理建议清理已有 AssetType 中 `key in {model, serial_number, sn, name, holder, location, notes, acquired_at}` 等 reserved key 重名 custom_field —— CL-1 起 future create/update 这些 key 会被拒绝。

### CLI（CL-1）

- `asset register` 加 `--brand <txt>` flag（位置紧邻 `--sn` 之后、`--model` 之前）
- `asset update --set '{"brand": ...}'` 复用 JSON 模式自然支持
- `asset list --sort brand` 可用

### API（CL-1）

- `POST /api/assets` body 接受可选 `brand`
- `PATCH /api/assets/{id}` body 接受 `brand`（exclude_unset 模式：未传 → keep，传 null → 清空）
- `GET /api/assets` response 含 `brand` 字段
- `GET /api/assets?q=foo` 搜索范围扩到 brand
- `GET /api/assets?sort_by=brand` 可用

### UI（CL-1）

- 列表表格新增 "品牌" 列（位于 "名称" 列右侧、"型号" 列左侧，默认显示）
- 详情页 header 副行：「品牌 · 型号」（任一非空时渲染）
- 详情页 general-fields 加 "品牌" 行
- 编辑表单加 "品牌" 输入（紧邻 name 之后、model 之前）
- CSV/XLSX 导出新增 "品牌" 列（11 列 → 12 列，autofilter A1:L{n}）

### CLI（CL-2）

- `asset-hub type define --help-json` 输出 `--fields` 参数下嵌套 `valid_field_types` 数组（9 值）

### 服务端（CL-4）

- `asset-hub serve doctor` 输出新增 `port_owner:5173` / `port_owner:8000` 检测项
- 外部进程占用端口时 `ok=false` + `fix_hint` 含 OS-specific 指令

### CI（CL-3）

- `.github/workflows/e2e.yml` 加 playwright browser cache，e2e job 冷启动时间从 14m+ 降到 ~2 min

## 回滚

```bash
git checkout v2.0.2
cp data/asset_hub.db.v2.0.bak data/asset_hub.db
uv sync && pnpm --dir frontend install
uv run asset-hub serve restart --mode prod
```

不可回滚的数据：

- v2.1 期间通过顶层 brand 字段写入的数据（custom_data.brand 仍有原值，但回退后只能用 v2.0 的 custom_field 路径）

## SemVer

含 user-visible 新字段（brand） + CLI 新 flag（--brand）+ AssetType 校验新增（拒新建包含 reserved key），但**对存量行为零破坏**。新增功能 + 严格校验 → MINOR → `v2.1.0`。
