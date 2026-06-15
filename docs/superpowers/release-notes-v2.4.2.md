# v2.4.2 发版升级指南

> 发布日期：2026-06-15
> Bugfix PATCH：修复桌面便携版（pywebview/WebView2 内嵌）点击「导出 → Excel/CSV」后静默失败、文件下载不下来的问题（[#42](https://github.com/chy5301/asset-hub/issues/42)，PR [#43](https://github.com/chy5301/asset-hub/pull/43)）。无新增用户功能、无 DB / API contract 破坏。

## 概览

v2.4.2 是一次纯 bugfix，仅影响**桌面便携版**：

- **桌面导出下载修复**：桌面版点「导出」选 Excel/CSV 后无任何反应、文件下不来。本版修复后弹出原生保存对话框，正常导出 XLSX/CSV。
- Web 浏览器访问与 `serve` 模式**一直正常**，不受此 bug 影响（用真实浏览器，下载由浏览器接管）。

## 升级路径

仅桌面 launcher 一行改动，**无** DB 迁移、**无** API contract 变化：

```bash
git fetch --tags
git checkout v2.4.2
uv sync
```

- **无** `uv run alembic upgrade head`（无 schema 变化）
- 桌面便携版：下载新版本 zip，解压覆盖整个文件夹（`data/` 保留）

## Breaking changes

**无**。

- DB schema 不变（无 alembic 迁移）
- API contract 不变（OpenAPI `info.version` 字段值变化不属契约破坏）
- 既有 transition / envelope error code 集合不变
- 改动仅落在 `desktop/window.py`，不涉及 service / CLI / API / 存储

## 改动详情

### 桌面版 WebView2 下载修复（#42 / PR #43）

**症状**：桌面便携版资产列表页点「导出 ▾ → Excel / CSV」后静默失败——无文件、无报错、无任何反应。

**根因**：

1. 前端导出走浏览器原生下载：`export-button.tsx` 用 `<a href="/api/export?..." download>`，后端 `routers/export.py` 返回 `Content-Disposition: attachment`。真实浏览器无问题。
2. 桌面版为 pywebview 6.2.1（WebView2）内嵌，**默认 `webview.settings['ALLOW_DOWNLOADS'] = False`**。
3. 该开关为 False 时，WebView2 的 `DownloadStarting` 事件被处理器直接 `args.Cancel = True` 静默取消——不抛异常，故无任何提示。
4. `desktop/window.py::open_window()` 创建窗口前从未覆盖该默认值。

**修复**：在 `open_window` 调 `webview.start` 前设 `webview.settings["ALLOW_DOWNLOADS"] = True`，让原生保存对话框接管下载。

## 测试覆盖

- 新增 `tests/unit/test_desktop_window.py::test_open_window_enables_downloads`：注入 fake `webview` 模块，断言 `open_window` 必将 `ALLOW_DOWNLOADS` 置 True。
- **注意**：WebView2 真实下载行为只在桌面运行时发生，单测只能守住「设置被开启」这个契约，端到端下载需在打包版手动烟测。
- PR #43 CI 全绿：`backend`、`frontend`、`e2e` 三 job 均 pass。

## 回滚

```bash
git fetch --tags
git checkout v2.4.1
uv sync
```

无数据变更，回滚安全（回滚后桌面版导出会重新失效）。

## SemVer

PATCH = **v2.4.2**。单一 bugfix（桌面版导出下载），无新增用户功能、无 schema / API / contract 破坏。

## 来源

- Issue：[#42](https://github.com/chy5301/asset-hub/issues/42)（桌面便携版导出功能无法下载文件）
- PR：[#43](https://github.com/chy5301/asset-hub/pull/43)（fix(desktop) + 单测守卫）
