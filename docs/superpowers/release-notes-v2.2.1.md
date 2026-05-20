# v2.2.1 发版升级指南

> 发布日期：2026-05-20
> 单 PR patch (#23)，仅修 v2.1.0 CL-4 引入的 doctor 误报 bug，无新功能。

## 概览

v2.2.1 是 v2.2.0 之后的 patch，闭环 [issue #22](https://github.com/chy5301/asset-hub/issues/22)。

## 升级路径

```bash
git fetch && git checkout v2.2.1
uv sync
# 无 db migration / 前端 / CLI contract 变化
uv run asset-hub serve restart --mode prod
```

## Breaking changes

**无**。本 patch 仅修 `serve doctor` 的 `check_port_owner` 误报行为，无新功能、无 API 变化、不改 contract。

## 改动详情

### #22 修复：`check_port_owner` 识别 uv 父子进程链路

**根因**：v2.1.0 CL-4 加 `check_port_owner` 时假设 PID 文件值 == 绑定端口者。实际 `uv run asset-hub serve start` 是 uv 父进程 + python 子进程链路：

```
uv (父，包装层) ──spawn──► python (子，实际跑 uvicorn 绑端口)
```

PID 文件由 `lifecycle.py` 写入 `start_detached` 返回值（即 uv 父 PID），但 `net_connections` 看到的 LISTEN owner 是 python 子 PID。`check_port_owner` 直接相等比对 → 误报"外部进程占用"：

```
port_owner:8000  ! 端口 8000 被外部进程 59740 占用（PID 文件记录 59584）
```

**修复**：

- `doctor.py` 新增 `_walks_ancestor_chain(pid: int, target: int) -> bool`：psutil.Process.parents() 跨平台返从直接父到 ROOT 的所有祖先；遍历比对 target；AccessDenied / NoSuchProcess 兜底返 False
- `check_port_owner` self-match 判定从 `actual_pid == expected_pid` 改为 `_walks_ancestor_chain(actual_pid, expected_pid)`
- 其他分支（空闲 / 外部 PID 有 / 无 PID 文件）行为不变

**影响范围**：

- 修复前：`serve doctor` 在 Windows 上对 `uv run` 启动的 serve 误报 port_owner `!`；不影响 serve 启停（serve start/stop/restart 走 PID 文件 + kill_tree，不依赖 port_owner 检测）
- 修复后：自动识别 uv 父子链，返 ok=True

### 配套文档

- `SKILL.md` `serve doctor` 段补 port_owner 检测项介绍 + v2.2.1+ uv 父子链识别说明
- `references/deploy.md` 故障排查表加 port_owner 误报行

## 测试覆盖

新增 4 个 unit test 在 `tests/unit/test_doctor.py::TestPortOwnerParentChain`：

1. 直接父链路（uv → python）→ ok=True
2. 多层祖父链路 → ok=True
3. 不相关祖先链 → ok=False（保持原行为）
4. psutil 异常兜底（NoSuchProcess / AccessDenied）→ 返 False 不抛

后端全测 671 passed / 1 skipped。

## 回滚

```bash
git checkout v2.2.0
uv sync
uv run asset-hub serve restart --mode prod
```

无数据变更，回滚安全。

## SemVer

PATCH = **v2.2.1**。仅修 doctor 误报 bug，无新功能、无 API 变化、不改 contract。

## 来源

- GitHub issue #22（CLOSED via PR #23）
- Spec: `docs/superpowers/specs/2026-05-20-issue22-port-owner-parent-chain.md`
- Plan: `docs/superpowers/plans/2026-05-20-issue22-port-owner-parent-chain.md`
- PR: #23
