# #22 fix · check_port_owner 递归比对祖先 PID Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 `check_port_owner` 加 `_walks_ancestor_chain(pid, target)` helper，让 `uv run` 父子进程链路下 port_owner 检测不误报。

**Architecture:** psutil.Process.parents() 跨平台返祖先链 list，遍历比对 expected_pid；AccessDenied / NoSuchProcess 兜底返 False。

**Tech Stack:** psutil（已在 deps）、`tests/unit/test_doctor.py::TestPortOwner`（v2.1.0 CL-4 加）。

**Spec 来源**：`docs/superpowers/specs/2026-05-20-issue22-port-owner-parent-chain.md`。
**先决条件**：v2.2.0 (`ee53222`) 已发布；fix 分支 `fix/issue-22-port-owner-parent-chain` 已从 main 切出。
**预期开销**：单 PR / 1 phase / 3 task / commit 2-3 条。SemVer **PATCH = v2.2.1**。

---

## Phase 1：fix + 文档同步

### Task 1：写 4 个 failing test

**Files:**

- Modify: `tests/unit/test_doctor.py`（在现有 `TestPortOwner` class 或末尾追加）

- [ ] **Step 1：写测**

新增 4 测（mock `psutil.Process` 模拟祖先链）：

```python
def test_check_port_owner_self_via_parent_chain(monkeypatch):
    """actual_pid 的直接父是 expected_pid → ok=True（uv 父子场景）。"""
    from asset_hub.cli.serve import doctor

    # mock _find_port_owner_pid 返 59740（python 子）
    monkeypatch.setattr(doctor, "_find_port_owner_pid", lambda port: 59740)

    # mock psutil.Process(59740).parents() 返 [Mock(pid=59584)]（uv 父）
    class FakeProc:
        pid = 59584
    class FakePython:
        def parents(self): return [FakeProc()]
    import psutil
    monkeypatch.setattr(psutil, "Process", lambda pid: FakePython() if pid == 59740 else None)

    result = doctor.check_port_owner(8000, expected_pid=59584)
    assert result.ok is True
    assert "59740" in result.detail
    assert "我管理" in result.detail


def test_check_port_owner_self_via_grandparent_chain(monkeypatch):
    """actual_pid 的祖父是 expected_pid（多层 spawn 场景）→ ok=True。"""
    from asset_hub.cli.serve import doctor
    import psutil

    monkeypatch.setattr(doctor, "_find_port_owner_pid", lambda port: 100)

    class P:
        def __init__(self, pid): self.pid = pid
    class FakeChild:
        def parents(self): return [P(99), P(98)]   # parent=99, grandparent=98
    monkeypatch.setattr(psutil, "Process", lambda pid: FakeChild() if pid == 100 else None)

    result = doctor.check_port_owner(8000, expected_pid=98)   # 期 grandparent
    assert result.ok is True


def test_check_port_owner_external_unrelated_chain(monkeypatch):
    """actual_pid 的祖先链不含 expected_pid → ok=False（保持原行为）。"""
    from asset_hub.cli.serve import doctor
    import psutil

    monkeypatch.setattr(doctor, "_find_port_owner_pid", lambda port: 9999)

    class P:
        def __init__(self, pid): self.pid = pid
    class FakeUnrelated:
        def parents(self): return [P(8888), P(7777)]   # 不含 expected
    monkeypatch.setattr(psutil, "Process", lambda pid: FakeUnrelated() if pid == 9999 else None)

    result = doctor.check_port_owner(8000, expected_pid=12345)
    assert result.ok is False
    assert result.code == "external_port_owner"
    assert "9999" in result.detail


def test_walks_ancestor_chain_handles_psutil_errors(monkeypatch):
    """psutil.Process raises NoSuchProcess → _walks_ancestor_chain 返 False 不抛。"""
    from asset_hub.cli.serve import doctor
    import psutil

    def raise_no_such(pid):
        raise psutil.NoSuchProcess(pid)
    monkeypatch.setattr(psutil, "Process", raise_no_such)

    # 直接测 helper
    assert doctor._walks_ancestor_chain(9999, 12345) is False
```

- [ ] **Step 2：跑测看 fail**

```bash
uv run pytest tests/unit/test_doctor.py -v -k "parent_chain or grandparent_chain or external_unrelated_chain or walks_ancestor"
```

期望 4 测全 FAIL（_walks_ancestor_chain 未实现 + check_port_owner 仍用直接相等）。

- [ ] **Step 3：commit**

```bash
git add tests/unit/test_doctor.py
git commit -m "test(serve/doctor): 加 #22 port_owner 父子链 failing tests

4 case 覆盖：直接父 / 祖父 / 不相关祖先链 / psutil 异常兜底。
实现在下个 commit 跟进。"
```

### Task 2：实现 _walks_ancestor_chain + 改 check_port_owner

**Files:**

- Modify: `src/asset_hub/cli/serve/doctor.py`

- [ ] **Step 1：在 `_find_port_owner_pid` 之后、`check_port_owner` 之前追加 helper**

```python
def _walks_ancestor_chain(pid: int, target: int) -> bool:
    """检查 pid 的祖先链（含 pid 自身）是否含 target。

    防 uv run 父子进程链路误报：PID 文件记 uv 父，端口被 python 子绑（#22）。
    AccessDenied / NoSuchProcess 兜底返 False（视为"无法判定"）。
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

- [ ] **Step 2：改 `check_port_owner` self-match 判定**

把：

```python
    if expected_pid is not None and actual_pid == expected_pid:
        return DoctorCheck(...)
```

改为：

```python
    if expected_pid is not None and _walks_ancestor_chain(actual_pid, expected_pid):
        return DoctorCheck(...)
```

其他分支不动。

- [ ] **Step 3：跑测看 pass**

```bash
uv run pytest tests/unit/test_doctor.py -v
```

期望全 PASS（原 25 + 新 4 = 29 测）。

- [ ] **Step 4：跑后端全测**

```bash
uv run pytest -q 2>&1 | tail -5
```

期望全绿（667 + 4 = 671 passed）。

- [ ] **Step 5：lint**

```bash
uv run ruff check . && uv run ruff format --check .
```

- [ ] **Step 6：commit**

```bash
git add src/asset_hub/cli/serve/doctor.py
git commit -m "fix(serve/doctor): port_owner 检测识别 uv 父子进程链路（闭环 #22）

v2.1.0 CL-4 加 check_port_owner 时假设 PID 文件值 == 绑定端口者。
uv run 实际是 uv 父 + python 子两进程，PID 文件记 uv 父，
端口由 python 子绑 → 直接相等比对误报「外部进程占用」。
新增 _walks_ancestor_chain(pid, target) helper：psutil.Process.parents() 跨平台返祖先链，
遍历比对；AccessDenied / NoSuchProcess 兜底返 False。
check_port_owner self-match 判定改用此 helper。
其他分支（空闲 / 外部 / 无 PID 文件）行为不变。"
```

### Task 3：SKILL.md + references 同步

**Files:**

- Modify: `SKILL.md`（命令速查 `serve doctor` 段）
- Modify: `references/deploy.md`（doctor 故障排查段；如已有就加 port_owner 行）
- Modify: `references/workflows.md`（如 serve doctor 工作流段缺 port_owner 提示）

- [ ] **Step 1：SKILL.md serve doctor 速查补 port_owner 检测项**

grep 定位现有 serve doctor 速查位置：

```bash
grep -n "serve doctor\|doctor.*--json" SKILL.md
```

在 doctor 项目清单段加（位置看实际格式）：

```
- `port_owner:5173` / `port_owner:8000`：端口实际占用者 PID 与 PID 文件比对（v2.1+；v2.2.1 起识别 uv 父子链）
```

- [ ] **Step 2：references/deploy.md 加 port_owner 故障排查**

在「故障排查」段（grep 定位）加：

```
| port_owner 误报 | 大概率是真有外部进程占；v2.2.1+ 已自动识别 uv 父子链 | 按 fix_hint 的 OS-specific 指令排查（lsof / Get-NetTCPConnection）|
```

- [ ] **Step 3：commit**

```bash
git add SKILL.md references/
git commit -m "docs(skill,deploy): 补 doctor port_owner 检测项 + uv 父子链识别说明

#22 闭环配套文档：SKILL.md serve doctor 速查加 port_owner 介绍；
references/deploy.md 故障排查表补 port_owner 行。"
```

---

## Phase 2：smoke + PR + tag v2.2.1

### Task 4：本地 smoke + PR + tag

- [ ] **Step 1：本地手测**（如本地 serve 跑着）

```bash
uv run asset-hub serve start --mode prod
uv run asset-hub serve doctor
# 期望 port_owner:8000 报 ok （绿✓），无 ! 误报
uv run asset-hub serve stop
```

如本地不便跑，跳过——CI 不验 uv 父子链场景（unit test 已 mock 覆盖）。

- [ ] **Step 2：lint + 全测最终**

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest -q 2>&1 | tail -5
```

期望全绿。

- [ ] **Step 3：push + PR**

```bash
git push -u origin fix/issue-22-port-owner-parent-chain
gh pr create --base main --title "fix(serve/doctor): port_owner 检测识别 uv 父子进程链路（闭环 #22）" --body "..."
```

- [ ] **Step 4：等 CI 三绿**

```bash
gh pr checks <pr>
```

- [ ] **Step 5：squash merge**

```bash
gh pr merge <pr> --squash --delete-branch
```

- [ ] **Step 6：tag v2.2.1 + push tag + 写 release-notes-v2.2.1**

---

## Self-Review Checklist

- [x] Spec coverage：spec §fix 方案 + §同步文档更新 全在 Task 1-3
- [x] 不在 scope：未改 `lifecycle.py` 写 PID 逻辑；未加 cmdline 比对
- [x] TDD：先写 4 fail test，再实现
- [x] 无 placeholder：每 task 含完整代码 + 测试 + commit msg

## 风险

- `psutil.Process(pid)` 当 PID 已挂时抛 NoSuchProcess —— 已在 _walks_ancestor_chain 内 try/except 兜底
- macOS / Linux 非 root 跑 doctor 可能 AccessDenied — 兜底返 False，行为与 v2.1.0 一致（保守不 ok）
