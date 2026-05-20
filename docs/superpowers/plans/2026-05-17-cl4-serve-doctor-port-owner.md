# CL-4 · serve doctor 加 port owner 检测项 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 `asset-hub serve doctor` 加 `check_port_owner` 项，探测 `frontend_port` / `backend_port` 占用者 PID；若 PID 不等于 PID 文件值（或 PID 文件不存在但端口被占）→ 返 `ok=false` + fix_hint 含 OS-specific 指令。

**Architecture:** 沿用现有 `doctor.py` 的 `DoctorCheck` dataclass + `check_*` 函数模式。用 psutil（已是项目依赖）的 `net_connections` API 跨平台探测端口占用者 PID，与 PID 文件值比对。

**Tech Stack:** psutil（跨平台 PID by port）、`asset_hub.cli.serve.pid`（读 PID 文件值）。

**Spec 来源**：`docs/superpowers/specs/2026-05-17-m4-batch-plan-design.md` CL-4 段。

**预期开销**：单 PR / 3 task（含测试）/ commit `feat(serve): doctor 加 check_port_owner 探测外部端口占用`。SemVer PATCH。

---

## Phase 1：核心实现 + 测试

### Task 1：写 failing test（外部进程占用端口）

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\tests\unit\test_doctor.py`（在文件末尾追加新 case；现有 19 个 test_check_*, 行号见 spec scan §23）

**前置约定**（保持与现有 check 一致）：

- 函数签名 `check_port_owner(port: int, expected_pid: int | None) -> DoctorCheck`
- `expected_pid=None` 含义：PID 文件不存在或读不出
- 返 `DoctorCheck(name, ok, detail, code?, fix_hint?)`，shape 见 `doctor.py:27-32`
- 端口空闲：`ok=True`, `detail="端口 5173 空闲"`
- 端口由 expected_pid 占用：`ok=True`, `detail="端口 5173 由我管理的进程 12345 占用"`
- 端口由其他 PID 占用：`ok=False`, `code="external_port_owner"`, `detail="端口 5173 被外部进程 9999 占用"`, `fix_hint=...`
- PID 文件不存在但端口被占：`ok=False`, `code="external_port_owner"`, `detail="端口 5173 被进程 9999 占用，但本机无对应 PID 文件"`, `fix_hint=...`

- [ ] **Step 1：写 4 个 failing test**

在 `tests/unit/test_doctor.py` 末尾追加：

```python
def test_check_port_owner_free(monkeypatch):
    """端口空闲 → ok=True。"""
    from asset_hub.cli.serve import doctor

    monkeypatch.setattr(
        doctor, "_find_port_owner_pid", lambda port: None
    )
    result = doctor.check_port_owner(5173, expected_pid=12345)
    assert result.ok is True
    assert "空闲" in result.detail


def test_check_port_owner_self(monkeypatch):
    """端口由 expected_pid 占用 → ok=True。"""
    from asset_hub.cli.serve import doctor

    monkeypatch.setattr(
        doctor, "_find_port_owner_pid", lambda port: 12345
    )
    result = doctor.check_port_owner(5173, expected_pid=12345)
    assert result.ok is True
    assert "12345" in result.detail
    assert "我管理" in result.detail


def test_check_port_owner_external(monkeypatch):
    """端口被外部进程占用，expected_pid 给定 → ok=False + fix_hint。"""
    from asset_hub.cli.serve import doctor

    monkeypatch.setattr(
        doctor, "_find_port_owner_pid", lambda port: 9999
    )
    result = doctor.check_port_owner(5173, expected_pid=12345)
    assert result.ok is False
    assert result.code == "external_port_owner"
    assert "9999" in result.detail
    assert result.fix_hint is not None
    assert "5173" in result.fix_hint


def test_check_port_owner_external_no_pidfile(monkeypatch):
    """端口被占但 PID 文件不存在 → ok=False + 不同 detail。"""
    from asset_hub.cli.serve import doctor

    monkeypatch.setattr(
        doctor, "_find_port_owner_pid", lambda port: 9999
    )
    result = doctor.check_port_owner(5173, expected_pid=None)
    assert result.ok is False
    assert result.code == "external_port_owner"
    assert "9999" in result.detail
    assert "无对应 PID 文件" in result.detail
```

- [ ] **Step 2：跑 test 看 fail**

```bash
uv run pytest tests/unit/test_doctor.py::test_check_port_owner_free -v
uv run pytest tests/unit/test_doctor.py::test_check_port_owner_self -v
uv run pytest tests/unit/test_doctor.py::test_check_port_owner_external -v
uv run pytest tests/unit/test_doctor.py::test_check_port_owner_external_no_pidfile -v
```

期望 4 个全 FAIL，错误内容：`AttributeError: module 'asset_hub.cli.serve.doctor' has no attribute '_find_port_owner_pid'`（或 `check_port_owner`）。

### Task 2：实现 `_find_port_owner_pid` + `check_port_owner`

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\src\asset_hub\cli\serve\doctor.py`（在末尾追加；现有 check_* 见 spec scan §20，到 `check_port_free` 行 233-244 之后追加）

- [ ] **Step 1：实现两个函数**

在 `doctor.py` 现有 `check_port_free` 函数（行 233-244）之后追加：

```python
def _find_port_owner_pid(port: int) -> int | None:
    """跨平台探测 LISTEN 状态下指定端口的占用进程 PID。返 None 表示无占用。

    psutil.net_connections 在 macOS / Linux 上需 root；在 Windows 上不需要。
    本工具为单机开发场景，假设进程有权限读自己的连接表。
    """
    import psutil

    try:
        conns = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, PermissionError):
        return None
    for c in conns:
        if c.laddr and c.laddr.port == port and c.status == "LISTEN":
            return c.pid
    return None


def check_port_owner(port: int, expected_pid: int | None) -> DoctorCheck:
    """探测端口占用者 PID 与 expected_pid 是否一致。

    expected_pid=None：PID 文件不存在或读不出（serve 未启动 / 文件损坏）。
    """
    actual_pid = _find_port_owner_pid(port)
    if actual_pid is None:
        return DoctorCheck(
            name=f"port_owner:{port}",
            ok=True,
            detail=f"端口 {port} 空闲",
        )
    if expected_pid is not None and actual_pid == expected_pid:
        return DoctorCheck(
            name=f"port_owner:{port}",
            ok=True,
            detail=f"端口 {port} 由我管理的进程 {actual_pid} 占用",
        )
    # 外部进程占用
    if expected_pid is None:
        detail = (
            f"端口 {port} 被进程 {actual_pid} 占用，但本机无对应 PID 文件"
        )
    else:
        detail = (
            f"端口 {port} 被外部进程 {actual_pid} 占用（PID 文件记录 {expected_pid}）"
        )
    fix_hint = (
        f"端口 {port} 被本工具管理范围外的进程占用，无法启动 serve。\n"
        f"  Windows：Get-NetTCPConnection -LocalPort {port} | Stop-Process -Id $_ -Force\n"
        f"  Linux/macOS：lsof -i :{port} 然后 kill <pid>"
    )
    return DoctorCheck(
        name=f"port_owner:{port}",
        ok=False,
        detail=detail,
        code="external_port_owner",
        fix_hint=fix_hint,
    )
```

**说明**：

- 用 psutil.net_connections 跨平台一致（spec §6 风险点：CL-4 doctor check 平台差异 → psutil 是首选）
- AccessDenied 兜底（macOS / Linux 非 root）：返 None 视为"无法判定"——保持 ok=True 让 doctor 继续，避免误报
- `name` 用 `port_owner:{port}` 与端口绑定，可在同次 doctor 运行覆盖 frontend / backend 两端口（5173 + 8000）

- [ ] **Step 2：跑 test 看 pass**

```bash
uv run pytest tests/unit/test_doctor.py::test_check_port_owner_free tests/unit/test_doctor.py::test_check_port_owner_self tests/unit/test_doctor.py::test_check_port_owner_external tests/unit/test_doctor.py::test_check_port_owner_external_no_pidfile -v
```

期望 4 个 PASS。

### Task 3：把 `check_port_owner` 接到 `run_all_checks` 聚合

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\src\asset_hub\cli\serve\doctor.py` — `run_all_checks` 函数（spec scan §23 提到 `test_run_all_checks_aggregates` 行 243 / `test_run_all_checks_dev_mode_includes_5173` 行 253 已有覆盖 → 看 `run_all_checks` 实现位置）

- [ ] **Step 1：定位 `run_all_checks` 实现**

```bash
grep -n "def run_all_checks" src/asset_hub/cli/serve/doctor.py
```

期望返一行：`def run_all_checks(mode: str = ...) -> list[DoctorCheck]:` 之类。

- [ ] **Step 2：写 failing test —— `run_all_checks` 应在 dev mode 含 port_owner:5173 和 port_owner:8000**

在 `tests/unit/test_doctor.py` 末尾追加：

```python
def test_run_all_checks_includes_port_owner(monkeypatch):
    """run_all_checks 在 dev mode 应包含两个 port_owner 检测（5173 + 8000）。"""
    from asset_hub.cli.serve import doctor

    # 不动其他 check 行为，仅期望 port_owner 出现
    monkeypatch.setattr(doctor, "_find_port_owner_pid", lambda port: None)
    results = doctor.run_all_checks(mode="dev")
    names = [r.name for r in results]
    assert "port_owner:5173" in names
    assert "port_owner:8000" in names


def test_run_all_checks_prod_mode_no_5173_owner(monkeypatch):
    """prod 模式无前端端口 → port_owner:5173 不应出现，但 port_owner:8000 必须有。"""
    from asset_hub.cli.serve import doctor

    monkeypatch.setattr(doctor, "_find_port_owner_pid", lambda port: None)
    results = doctor.run_all_checks(mode="prod")
    names = [r.name for r in results]
    assert "port_owner:5173" not in names
    assert "port_owner:8000" in names
```

跑：

```bash
uv run pytest tests/unit/test_doctor.py::test_run_all_checks_includes_port_owner tests/unit/test_doctor.py::test_run_all_checks_prod_mode_no_5173_owner -v
```

期望 2 个 FAIL（缺 port_owner:5173 / port_owner:8000）。

- [ ] **Step 3：实现接入**

在 `doctor.py::run_all_checks` 中（spec scan §20 已有 `check_port_free` 在 5173/8000 端口的接入逻辑，照搬模式）：

读 PID 文件值用 `asset_hub.cli.serve.pid` 模块。具体 `pid` 模块的 API：

```bash
grep -n "def.*pid\|def read_pid" src/asset_hub/cli/serve/pid.py
```

期望返函数如 `read_pid(name: str) -> int | None` 或类似。

在 `run_all_checks` 加 port_owner 检测：

```python
# 在已有的 check_port_free 调用之后追加
from asset_hub.cli.serve.pid import read_pid  # 顶部 import

# 在 run_all_checks 函数内部，已有的 check_port_free(8000) 之后：
backend_pid = read_pid("backend")
results.append(check_port_owner(8000, expected_pid=backend_pid))
if mode == "dev":
    frontend_pid = read_pid("frontend")
    results.append(check_port_owner(5173, expected_pid=frontend_pid))
```

**注意**：实际 `read_pid` 的函数名 / 参数 / 返回 shape 可能不同，**先 grep 确认再写**。如 `pid.py` 模块没有现成 `read_pid` helper，则在 `doctor.py` 内联读 PID 文件（用 `Path("data/.asset-hub-serve-backend.pid")` 或项目实际 PID 文件路径，参考 `pid.py` 源码）。

- [ ] **Step 4：跑全测**

```bash
uv run pytest tests/unit/test_doctor.py -v
```

期望全部 23 个测试（19 原有 + 4 port_owner + 2 run_all_checks_port_owner）PASS。

- [ ] **Step 5：commit**

```bash
git add src/asset_hub/cli/serve/doctor.py tests/unit/test_doctor.py
git commit -m "feat(serve): doctor 加 check_port_owner 探测外部端口占用

v2.0 PR-1 / PR-3 visual smoke 两次撞「外部进程占用 frontend port 让 Vite fail-fast 但 doctor 无诊断」的 gap。
psutil.net_connections 跨平台探测 LISTEN 状态下指定端口的 PID，对比 PID 文件值：
- 端口空闲 / 自管进程占用 → ok=True
- 外部 PID 占用 → ok=False + fix_hint 含 OS-specific kill 指令（Windows Get-NetTCPConnection / Linux lsof）
- AccessDenied（macOS/Linux 非 root）→ 兜底返 ok=True 避免误报
run_all_checks dev 模式覆盖 5173 + 8000 两端口，prod 模式仅 8000。"
```

---

## Phase 2：smoke + PR

### Task 4：本地 smoke + PR

**Files:** （无代码改动）

- [ ] **Step 1：本地手测**

```bash
# 1. 先启 serve
uv run asset-hub serve start --mode dev

# 2. 在另一终端起一个临时 Python http server 占 5174 端口（不要占 5173 让 serve 正常）
python -m http.server 5174 &

# 3. 用 doctor 跑（应看 5174 不在 doctor 检测范围内，无影响）
uv run asset-hub serve doctor --json | python -m json.tool

# 4. 停 serve，把 http server 改占 5173
uv run asset-hub serve stop
python -m http.server 5173 &

# 5. 跑 doctor —— port_owner:5173 应 ok=false + fix_hint 出现
uv run asset-hub serve doctor --json | python -m json.tool
# 期望看到 port_owner:5173 ok=false code=external_port_owner

# 6. 清理
kill %1  # 或对应的 http.server PID
```

如步骤 5 输出符合预期，本 plan 成功。

- [ ] **Step 2：lint + 全测**

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

期望全绿。

- [ ] **Step 3：开 PR**

```bash
git push -u origin <branch-name>
gh pr create --title "feat(serve): doctor 加 check_port_owner 探测外部端口占用" --body "$(cat <<'EOF'
## Summary
- doctor 新增 check_port_owner(port, expected_pid)，psutil 跨平台探测 LISTEN 状态 PID
- run_all_checks dev mode 覆盖 5173 + 8000；prod mode 仅 8000
- 外部 PID 占用 → ok=false + fix_hint 含 OS-specific 指令

## Test plan
- [x] 4 个 _find_port_owner_pid mock 单测 PASS
- [x] 2 个 run_all_checks 聚合单测 PASS
- [x] 本地 smoke：用 python -m http.server 5173 模拟外部占用，doctor --json 输出 port_owner:5173 ok=false 带 fix_hint
- [x] AccessDenied 兜底（macOS/Linux 非 root 场景）：返 None 视为"无法判定"保持 ok=True

闭环 followup-allocation v2.0 PR-1/PR-3 衍生 minor「serve stop 不清外部端口」的诊断侧。
spec：docs/superpowers/specs/2026-05-17-m4-batch-plan-design.md CL-4 段。
EOF
)"
```

- [ ] **Step 4：等 CI + merge**

```bash
gh pr checks <pr-number>
# 期望 backend + frontend + e2e 全绿
gh pr merge --squash --delete-branch
```

---

## Self-Review Checklist

- [x] Spec coverage：spec §CL-4 提到的 `check_port_owner` / fix_hint 含 OS-specific 指令 / `tests/unit/test_doctor.py::test_check_port_owner_external` —— 全在 Task 1-3
- [x] 不在 scope：未动 `serve stop` 主动 kill 外部进程（spec 明示不做）；未给 `serve start` 加额外探测（PR-C 的 strictPort + IPv6 双栈已足够）
- [x] 用 psutil 而非 OS-specific 命令（spec §6 风险点明示）
- [x] AccessDenied 兜底（spec scan §22 psutil 已在项目）
- [x] 无 placeholder：全部函数体、test 体、commit msg 完整

## 风险

- **macOS / Linux 非 root 用户**：`psutil.net_connections(kind="inet")` 可能抛 `AccessDenied`。本实现兜底返 None 视为"无法判定"。如开发者反馈"看不到外部占用诊断"，再考虑用 OS-specific fallback（lsof / netstat），但优先靠用户用 fix_hint 给出的 OS 命令手动查。
- **psutil 的 `net_connections` 在 Windows 上偶发 timeout**：本机进程数极多时可能 >1s。仅 doctor 命令路径触发，不影响 serve 正常运行。
- **`run_all_checks` 的 mode 参数语义**：spec scan §23 显示 `test_run_all_checks_dev_mode_includes_5173` 已存在 → 说明 mode="dev" / mode="prod" 是现成接口。本 plan 复用此接口，不动 mode 语义。
