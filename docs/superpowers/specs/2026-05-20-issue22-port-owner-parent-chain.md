# #22 fix · check_port_owner 递归比对祖先 PID — Design

> 日期：2026-05-20
> 输入：[GitHub issue #22](https://github.com/chy5301/asset-hub/issues/22)、v2.1.0 CL-4 实现 `src/asset_hub/cli/serve/doctor.py:check_port_owner`
> 输出：fix 设计 + SemVer 定级 + SKILL/references 同步范围
> 状态：等用户复审 → writing-plans

## 背景

v2.1.0 (CL-4 #18) 加 `serve doctor` 的 `check_port_owner` 检测项：psutil `net_connections(kind="inet")` 探测 LISTEN 端口的 PID，对比 PID 文件值；若不一致返 `ok=False` + `code=external_port_owner`。

v2.2.0 后用户在 Windows 上实测发现误报：

```
uv run asset-hub serve start --mode prod
# PID 文件写入 59584
Get-NetTCPConnection -LocalPort 8000 | Select OwningProcess
# → 59740
Get-Process -Id 59584,59740 | Select Id, ProcessName
# 59584: uv (父进程)
# 59740: python (子进程，实际绑定端口)
```

`serve doctor` 输出：
```
port_owner:8000  ! 端口 8000 被外部进程 59740 占用（PID 文件记录 59584）
```

### 根因

CL-4 实现假设「PID 文件记录的进程 == 绑定端口的进程」。实际 `uv run` 进程结构是**包装进程链**：

```
uv (父，包装层) ──spawn──► python (子，实际跑 uvicorn 绑端口)
```

PID 文件由 `lifecycle.py:104-108` 写入的是 `proc_mod.start_detached(...)` 返回值——即 `uv` 父进程 PID（`uv` 不替换自身为 python，而是 spawn 子）。但 `net_connections` 看到的 LISTEN owner 是 python 子进程 PID。两者**同源不同 PID**，CL-4 直接相等比对判定为"外部进程"，误报。

### 影响

- **不影响 serve 启停**：`serve start/stop/restart` 走 PID 文件读 → kill_tree（杀整棵进程树），不依赖 port_owner 检测
- **仅 doctor 输出误导**：用户看 `!` 以为端口被外部占，可能误操作 kill 自管的 python 子
- **跨平台**：Windows 上 `uv run` 是单独 process 链路；Linux/macOS 上 `uv run` 也是 fork-exec，同样存在父子链

## 决策

| 维度 | 选定 | 备选已淘汰 |
|---|---|---|
| 修复路径 | **递归走祖先 PID 链对比 expected_pid** | A 改 `start_detached` 把 PID 文件改写为 `uv` 子的实际 python PID（侵入 lifecycle / 难处理 uv 子进程多层 spawn 场景）/ B 加 `cmdline` 比对（脆弱，不同 uv 版本 cmdline 不稳定） |
| SemVer | **PATCH = v2.2.1** | MINOR：本 fix 无新功能、无 API 变化、不改 contract，仅修 doctor 误报 |
| Test 层 | **unit 层 mock** | 集成测需要真实 uv 子进程链路，CI 难复现 |

## fix 方案

在 `doctor.py` 内：

### 新增 helper `_walks_ancestor_chain(pid: int, target: int) -> bool`

```python
def _walks_ancestor_chain(pid: int, target: int) -> bool:
    """检查 pid 的祖先链（含 pid 自身）是否含 target。

    防 uv run 父子进程链路误报：PID 文件记 uv 父，端口被 python 子绑。
    遍历 parents() 至 ROOT，遇 target == pid 即返 True。
    AccessDenied / NoSuchProcess 兜底返 False（视为"无法判定"，保持原 ok=False 行为）。
    """
    import psutil

    if pid == target:
        return True
    try:
        proc = psutil.Process(pid)
        for ancestor in proc.parents():
            if ancestor.pid == target:
                return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, PermissionError):
        return False
    return False
```

`psutil.Process.parents()` 是跨平台、返 list 含从直接父到 ROOT 的所有祖先 Process 对象。

### 改 `check_port_owner` 的 self-match 判定

原：
```python
if expected_pid is not None and actual_pid == expected_pid:
    return DoctorCheck(... ok=True, detail=f"端口 {port} 由我管理的进程 {actual_pid} 占用")
```

改为：
```python
if expected_pid is not None and _walks_ancestor_chain(actual_pid, expected_pid):
    return DoctorCheck(... ok=True, detail=f"端口 {port} 由我管理的进程 {actual_pid} 占用")
```

逻辑保持：若 `actual_pid == expected_pid` 或 `expected_pid` 是 `actual_pid` 的某层祖先（含 uv 父进程场景），均视为"自管"。

其他分支（端口空闲 / 外部 PID 占用 / 无 PID 文件）行为不变。

## 测试

新增 4 个 unit test 在 `tests/unit/test_doctor.py::TestPortOwner`（追加现有 6 case）：

1. `test_check_port_owner_self_via_parent_chain` — actual_pid 是 expected_pid 的子（mock parents() 返含 expected_pid），ok=True
2. `test_check_port_owner_self_via_grandparent_chain` — actual_pid 的祖父是 expected_pid，ok=True
3. `test_check_port_owner_external_unrelated_chain` — actual_pid parents 不含 expected_pid，ok=False（保持原行为）
4. `test_walks_ancestor_chain_handles_psutil_errors` — mock `psutil.Process` 抛 NoSuchProcess / AccessDenied，函数返 False 不抛

`run_all_checks` 现有 2 测 + `check_port_owner` 现有 4 测 (free/self/external/external_no_pidfile) 保持绿。

## 同步文档更新

### `SKILL.md`

- **命令速查 `serve doctor`**：当前不提 `port_owner` 检测项；本 PR 加一行说明其存在 + 父子链兼容声明
- **Gotcha 段**：考虑加一条「v2.1+ doctor port_owner 检测会自动识别 uv 父子进程链，无需手动忽略」—— 视粒度决定（避免 Gotcha 过载）

### `references/deploy.md`

- 加 doctor `port_owner:N` 检测项的故障排查说明：
  - 正常情况：自动识别 uv 父子链返 ok
  - 异常情况：仍 `!` 时大概率是真有外部进程占用，按 fix_hint 的 OS-specific 指令排查

### `references/workflows.md`

- `serve doctor` 工作流段如有 `port_owner` 缺失，补一行

## 明确不做（YAGNI 边界）

| 项 | 理由 |
|---|---|
| 改 `lifecycle.py` `start_detached` 让 PID 文件记 python 子 PID | 侵入 serve 主路径，且无法处理 uv 多层 spawn；解决方向不对 |
| 加 `cmdline` token 匹配（python + uvicorn）| 与 v1.0 PID state 校验机制重复；脆弱 |
| 处理 macOS / Linux 上 `uv` 是否替换自身（execv）以避免父子链 | `uv 0.5+` 在所有平台都是 spawn 子（保证 cancellation 支持）；不要为假设的"未来 execv"留 dead code |

## 风险

1. **`psutil.Process.parents()` 性能**：每个 check_port_owner 调用最多 2 次（5173 + 8000）+ 每次 mock 时 ≤ 5 层祖先，开销 < 50ms 可忽略
2. **AccessDenied 兜底返 False**：与现 `_find_port_owner_pid` AccessDenied 兜底返 None 语义一致——"无法判定时保守不报 ok=True"。Windows 通常无此限制；macOS / Linux 非 root 可能撞，结果与 v2.1 行为一致（误报）但范围只剩"非 uv run 启动 + 非 root 跑 doctor"极小情况
3. **PID 重用**：理论上 `actual_pid` 已挂、其 PID 被新进程复用、新进程的祖先**碰巧**含 `expected_pid` → 误判为 ok。概率极低（PID 重用 + 父子关系巧合），可接受

## 后续

本 spec approve 后转 writing-plans 生成 1 个 plan（task ~3 个）：

- `2026-05-20-issue22-port-owner-parent-chain.md`（含 test / impl / SKILL+references 同步 / commit）
