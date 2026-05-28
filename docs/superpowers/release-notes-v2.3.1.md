# v2.3.1 发版升级指南

> 发布日期：2026-05-28
> 收口型 PATCH：汇集 v2.3.0 之后合入的前端视觉/结构一致性改动（[#27](https://github.com/chy5301/asset-hub/pull/27) [#28](https://github.com/chy5301/asset-hub/pull/28) [#31](https://github.com/chy5301/asset-hub/pull/31)）与一处 CLI Agent 契约增强（[#32](https://github.com/chy5301/asset-hub/pull/32)），并顺手治理版本号漂移。无新增用户功能、无 DB / API contract 破坏。

## 概览

v2.3.1 不引入新能力，是一次「收口 + 治理」：

- **前端一致性**：类型详情页对齐资产详情架构、看板修复、列表 page-header / toggle 统一、图标与 dead design token 清理
- **CLI Agent 契约增强**：`--help-json` 输出新增从命令 docstring 提取的 examples
- **版本号治理**：前端版本号从滞后的 `2.0.2` 拉齐到 `2.3.1`；后端 OpenAPI version 从写死的 `0.1.0` 改为运行时读包元数据，确立 `pyproject.toml` 为唯一版本权威源

## 升级路径

含前端改动（需重新构建）+ CLI 改动（需同步依赖），**无** DB 迁移：

```bash
git fetch --tags
git checkout v2.3.1
uv sync
uv run asset-hub serve restart --mode prod   # prod 模式自动 build 前端
```

- **无** `uv run alembic upgrade head`（无 schema 变化）
- 手动跑前端的话：`pnpm --dir frontend install && pnpm --dir frontend build`

## Breaking changes

**无**。

- DB schema 不变（无 alembic 迁移）
- API contract 不变（OpenAPI `info.version` 字段值变化不属契约破坏）
- 既有 transition / envelope error code 集合不变
- CLI `--help-json` 仅**新增** `examples` 字段，向后兼容

## 改动详情

### 前端视觉/结构一致性（#27 #28 #31）

- **#27**：类型详情页对齐资产详情架构，抽取 `DetailPageShell` 复用详情页骨架
- **#28**：看板（Dashboard）修复 + 列表页 page-header 统一 + toggle 控件统一
- **#31**：图标一致性 + dead design token 清理（闭环 #29 #30）

均为既有页面的重构/修复，无新增用户能力。

### CLI `--help-json` examples 提取（#32）

- `--help-json` 输出新增从命令 docstring 提取的 `examples`（`cli/deps.py` 提取逻辑 + 各 `*_cmd.py` 接入），便于 Agent 直接拿到用法示例
- 附带 fix：`type define` 示例字段类型 `number` → 合法的 `int`
- `SKILL.md` 命令速查区指引 Agent 用 `--help-json` 取示例
- 新增 `tests/unit/test_help_json.py` 覆盖提取逻辑

### 版本号治理

- `frontend/package.json` 版本号从 `2.0.2` 拉齐到 `2.3.1`
- `api/app.py` OpenAPI version 由写死 `"0.1.0"` 改为 `importlib.metadata.version("asset-hub")`，以后随 `pyproject.toml` 自动同步
- 确立 **`pyproject.toml` 为唯一版本权威源**：`uv.lock` 由 `uv lock` 派生、`frontend/package.json` 为 private 包不再强维护

## 测试覆盖

- 后端全测 **695 passed / 1 skipped**（含 #32 新增的 `test_help_json.py`）
- `ruff check` + `ruff format --check` 全过
- 前端本次仅 `package.json` version 字段变化，不触及代码/类型/构建；CI `frontend`（lint + tsc + vitest）与 `e2e`（Playwright chromium）job 在合并 main 时兜底

## 回滚

```bash
git fetch --tags
git checkout v2.3.0
uv sync
uv run asset-hub serve restart --mode prod
```

无数据变更，回滚安全。

## SemVer

PATCH = **v2.3.1**。本次含 #32 `feat(cli)`，但判定为对既有 `--help-json` 契约的**小幅增强**而非独立新功能，按 patch 处理；其余为前端一致性重构/修复 + 版本号治理，无新增用户功能、无 schema / API / contract 破坏。

## 来源

- PRs：[#27](https://github.com/chy5301/asset-hub/pull/27) [#28](https://github.com/chy5301/asset-hub/pull/28)（前端一致性）、[#31](https://github.com/chy5301/asset-hub/pull/31)（图标/token 清理）、[#32](https://github.com/chy5301/asset-hub/pull/32)（CLI `--help-json` examples）
- Plans：`docs/superpowers/plans/2026-05-27-ui-consistency-pr1-detail-shell.md`、`docs/superpowers/plans/2026-05-27-ui-consistency-pr2-dashboard-listheader-toggle.md`
- Specs：`docs/superpowers/specs/`（前端视觉/结构一致性 batch scope + 6 项 frontend-design 决策）
