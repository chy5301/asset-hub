# M3e SKILL.md + 部署 + 测试基建（v1.0 GA 收口）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** M3e 子里程碑落地——CLI envelope 统一 + serve doctor + 5 态文案对齐 + SKILL.md / 部署文档 / README / v1.0 release notes + playwright e2e CI workflow，让 v1.0 可发版。

**Architecture:** 单 PR 单分支 `feat/m3e-ga`，按 4 phase commit 切分。Phase 顺序刚性：envelope 升级 → 5 态文案/薄弱点补测 → 文档（依赖前 2 phase 稳态）→ e2e+CI（依赖前 3 phase）。零数据库 schema 改动；零 HTTP API 契约破坏；零前端 generated schema 改动。

**Tech Stack:** Python 3.12 / FastAPI / SQLModel / Typer / pytest / openpyxl · React 19 / TanStack Router / TanStack Query / Tailwind v4 / shadcn/ui · @playwright/test（新增） / GitHub Actions / ubuntu-latest runner.

**Spec:** [`docs/superpowers/specs/2026-05-09-m3e-skill-and-deploy-design.md`](../specs/2026-05-09-m3e-skill-and-deploy-design.md)

**前置约束（基于 verify 后的事实）：**

- 当前 `src/asset_hub/cli/envelope.py::print_error(message, json_output, exit_code)` 不带 `code` 参数；error 字段是 plain string
- `src/asset_hub/cli/serve/cmd.py` 5 子命令各自走 `_emit_success` / `_emit_error` + `serve/output.py::render_json_envelope`，error 字段是 `{code, message}` 结构化
- `src/asset_hub/cli/serve/lifecycle.py` 抛 `ServeLifecycleError(code, message)` 双字段；现有 10 个 serve.* code（`serve.port_occupied` / `dist_missing` / `health_probe_timeout` / `frontend_failed_to_start` / `data_unwritable` / `already_running` / `build_failed` / `kill_failed` / `mode_required` / `usage`）
- `src/asset_hub/errors.py` 6 个域异常类：`NotFoundError` / `DuplicateError` / `ValidationError` / `StateError` / `ConflictError` / `IllegalTransitionError`
- `frontend/src/features/assets/status-labels.ts` `STATUS_META` 是 5 态前端 SoT；当前 IN_USE label = "在用"、IDLE label = "闲置"
- `src/asset_hub/services/export.py:28-32` `STATUS_LABELS` dict 是后端 5 态 SoT
- `tests/cli/test_serve_*.py` 5 文件已断言 `error.code` / `error.message` dict shape；其余 CLI 测试断言 plain string
- 仓库根**不存在** `SKILL.md`；`docs/deployment.md` 不存在
- README.md 存在但 stale（M2/M3 标"规划中"、`./scripts/dev.sh` 已删、CLI 示例缺 transition/export/stats/serve）
- 项目无 playwright npm 依赖（仅 playwright MCP 用于 visual smoke）
- 项目无 `.github/workflows/`
- main branch 当前 commit `2d055a9`（含本 spec）

**任务总览**（38 task / 5 phase）：

- Phase 0 · 起分支 + workspace 准备（T01）
- Phase 1 · envelope 升级 + serve doctor（T02-T11）
- Phase 2 · 5 态文案 + 薄弱点补测（T12-T18）
- Phase 3 · 文档（T19-T26）
- Phase 4 · playwright e2e + GitHub Actions（T27-T36）
- Phase 5 · 收尾（PR + followup 回填）（T37-T38）

---

## Phase 0 · 起分支

### Task 1: 起分支 `feat/m3e-ga`

**Files:** 无

- [ ] **Step 1.1: 同步 main**

```bash
git checkout main
git pull --ff-only origin main 2>&1 || true
```

- [ ] **Step 1.2: 起分支**

```bash
git checkout -b feat/m3e-ga
```

预期输出：`Switched to a new branch 'feat/m3e-ga'`

- [ ] **Step 1.3: 验证起点**

```bash
git log --oneline -1
```

预期：见到 `2d055a9 docs(spec): M3e SKILL.md + 部署...`

---

## Phase 1 · envelope 升级 + serve doctor

### Task 2: 写 envelope 单元测试（TDD 红）

**Files:**
- Create: `tests/unit/test_envelope.py`

- [ ] **Step 2.1: 创建 test_envelope.py**

写完整文件：

```python
"""envelope.py 升级后的 contract 测试。

验证 6 个域异常 → handle_domain_errors → envelope error shape {code, message} + exit_code。
M3e §2.6 Phase 1 验收点之一。
"""
from __future__ import annotations

import json

import pytest

from asset_hub.cli.envelope import (
    error_envelope,
    handle_domain_errors,
    print_error,
    success_envelope,
)
from asset_hub.errors import (
    ConflictError,
    DuplicateError,
    IllegalTransitionError,
    NotFoundError,
    StateError,
    ValidationError,
)


def test_success_envelope_shape():
    out = json.loads(success_envelope({"id": "abc"}, count=3, took_ms=12.5))
    assert out["success"] is True
    assert out["data"] == {"id": "abc"}
    assert out["metadata"] == {"count": 3, "took_ms": 12.5}
    assert out["error"] is None


def test_error_envelope_shape():
    out = json.loads(error_envelope("Asset 不存在", code="not_found"))
    assert out["success"] is False
    assert out["data"] is None
    assert out["metadata"] == {}
    assert out["error"] == {"code": "not_found", "message": "Asset 不存在"}


@pytest.mark.parametrize(
    "exc,expected_code,expected_exit",
    [
        (NotFoundError("x 不存在"), "not_found", 3),
        (DuplicateError("sn 重复"), "duplicate", 1),
        (ValidationError("字段非法"), "validation", 1),
        (StateError("状态不允许"), "state_conflict", 1),
        (ConflictError("被引用"), "conflict", 1),
        (IllegalTransitionError("非法转换"), "illegal_transition", 1),
    ],
)
def test_handle_domain_errors_maps_code_and_exit(capsys, exc, expected_code, expected_exit):
    with pytest.raises(SystemExit) as ei:
        with handle_domain_errors(json_output=True):
            raise exc

    assert ei.value.code == expected_exit
    out = json.loads(capsys.readouterr().out)
    assert out["error"]["code"] == expected_code
    assert out["error"]["message"] == str(exc)


def test_validation_exit_2_when_usage_flag_set(capsys):
    with pytest.raises(SystemExit) as ei:
        with handle_domain_errors(json_output=True, exit_2_on_validation=True):
            raise ValidationError("无效 UUID")

    assert ei.value.code == 2
    out = json.loads(capsys.readouterr().out)
    assert out["error"] == {"code": "validation", "message": "无效 UUID"}


def test_print_error_requires_keyword_code(capsys):
    """code 是 keyword-only，禁止裸 print_error('失败') 漏 code。"""
    with pytest.raises(TypeError):
        print_error("oops", True)  # 未传 code，应报 TypeError
```

- [ ] **Step 2.2: 运行测试验证 fail**

```bash
uv run pytest tests/unit/test_envelope.py -v
```

预期：所有测试 FAIL（`error_envelope` 未接受 `code=`、`handle_domain_errors` 未 map code、`print_error` 未要求 keyword-only code 等）

### Task 3: 改写 envelope.py 让测试通过

**Files:**
- Modify: `src/asset_hub/cli/envelope.py`

- [ ] **Step 3.1: 重写 envelope.py 全文**

```python
import json
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, NoReturn

from pydantic import BaseModel

from asset_hub.errors import (
    AssetHubError,
    ConflictError,
    DuplicateError,
    IllegalTransitionError,
    NotFoundError,
    StateError,
    ValidationError,
)


_DOMAIN_ERROR_CODES: dict[type[AssetHubError], str] = {
    NotFoundError: "not_found",
    DuplicateError: "duplicate",
    ValidationError: "validation",
    StateError: "state_conflict",
    ConflictError: "conflict",
    IllegalTransitionError: "illegal_transition",
}


def success_envelope(data: Any, count: int | None = None, took_ms: float | None = None) -> str:
    meta: dict[str, Any] = {}
    if count is not None:
        meta["count"] = count
    if took_ms is not None:
        meta["took_ms"] = round(took_ms, 1)
    return json.dumps(
        {"success": True, "data": data, "metadata": meta, "error": None},
        ensure_ascii=False,
        default=str,
    )


def error_envelope(message: str, *, code: str) -> str:
    return json.dumps(
        {
            "success": False,
            "data": None,
            "metadata": {},
            "error": {"code": code, "message": message},
        },
        ensure_ascii=False,
    )


def print_result(data: Any, json_output: bool, *, count: int | None = None) -> None:
    if json_output:
        print(success_envelope(data, count=count))
    else:
        from rich import print as rprint
        rprint(data)


def print_error(
    message: str, json_output: bool, *, code: str, exit_code: int = 1
) -> NoReturn:
    if json_output:
        print(error_envelope(message, code=code))
    else:
        from rich.console import Console
        Console(stderr=True).print(f"[red]错误:[/red] {message}")
    raise SystemExit(exit_code)


def print_dry_run(payload: Any, json_output: bool, *, message: str) -> NoReturn:
    if json_output:
        print(success_envelope(payload))
    else:
        from rich import print as rprint
        rprint(f"[yellow]dry-run:[/yellow] {message}")
    raise SystemExit(10)


def to_json_dict(schema_cls: type[BaseModel], obj: Any) -> dict:
    return schema_cls.model_validate(obj).model_dump(mode="json")


@contextmanager
def handle_domain_errors(
    json_output: bool,
    *,
    exit_2_on_validation: bool = False,
) -> Generator[None, None, None]:
    """把域异常按 CLI 退出码契约翻译成 print_error。

    退出码：NotFoundError → 3；ValidationError → 1（默认）/ 2（exit_2_on_validation=True）；
    其余 ConflictError/DuplicateError/IllegalTransitionError/StateError → 1。
    error.code 由 _DOMAIN_ERROR_CODES 显式映射，避与状态机歧义（StateError → state_conflict）。
    与 api/app.py 的 HTTP 映射对称。
    """
    try:
        yield
    except AssetHubError as e:
        code = _DOMAIN_ERROR_CODES[type(e)]
        if isinstance(e, NotFoundError):
            exit_code = 3
        elif isinstance(e, ValidationError) and exit_2_on_validation:
            exit_code = 2
        else:
            exit_code = 1
        print_error(str(e), json_output, code=code, exit_code=exit_code)
```

- [ ] **Step 3.2: 运行 envelope 测试验证 pass**

```bash
uv run pytest tests/unit/test_envelope.py -v
```

预期：全 PASS。

- [ ] **Step 3.3: 运行 ruff 与全套测试看冲击面**

```bash
uv run ruff check src/asset_hub/cli/envelope.py tests/unit/test_envelope.py
uv run pytest tests/cli/ -x 2>&1 | tail -50
```

**预期 ruff clean，但 `pytest tests/cli/` 会有大量 fail**——这正常：现有 CLI 测试断言 `error == "..."` plain string，新 envelope 给 `error == {"code": ..., "message": ...}` dict。下个 task 修复。

### Task 4: 修复主 CLI 测试 error 字段断言（asset / type / attachment / transition / stats）

**Files:**
- Modify: `tests/cli/test_asset_cli.py`
- Modify: `tests/cli/test_type_cli.py`
- Modify: `tests/cli/test_attachment_cli.py`
- Modify: `tests/cli/test_transition_cmds.py`
- Modify: `tests/cli/test_stats_cli.py`
- Modify: `tests/cli/test_type_cli_delete.py`
- Modify: `tests/cli/test_type_cli_update.py`

- [ ] **Step 4.1: grep 出全部断言定位**

```bash
git grep -nE 'parsed\["error"\]\s*==|payload\["error"\]\s*==|"error":\s*"' tests/cli/ 2>&1
```

预期：列出 12-18 处需修订的位置。

- [ ] **Step 4.2: 逐处修订**

每处修订形式：

```python
# Before
assert parsed["error"] == "Asset 不存在"

# After
assert parsed["error"] == {"code": "not_found", "message": "Asset 不存在"}
```

或对 message-only 断言宽松匹配：

```python
# Before
assert "已存在" in parsed["error"]

# After
assert parsed["error"]["code"] == "duplicate"
assert "已存在" in parsed["error"]["message"]
```

规则：
- `NotFoundError` 抛的位置 → `code == "not_found"`
- `DuplicateError` → `"duplicate"`
- `ValidationError` → `"validation"`
- `ConflictError` → `"conflict"`（如 type delete 引用冲突）
- `IllegalTransitionError` → `"illegal_transition"`
- `StateError` → `"state_conflict"`

- [ ] **Step 4.3: 跑 CLI 测试套件**

```bash
uv run pytest tests/cli/ -x 2>&1 | tail -30
```

预期：全 PASS。如有遗漏断言，按提示继续修。

### Task 5: 验 serve 测试不退化（保险跑一遍）

**Files:** 无（serve 测试已经 dict shape 断言，不需改）

- [ ] **Step 5.1: 跑 serve 测试**

```bash
uv run pytest tests/cli/test_serve_*.py -v 2>&1 | tail -40
```

预期：全 PASS（serve cmd.py 还没改，envelope 形态没变，serve 测试不受影响）。

如有 fail，说明 grep 没找全；回 Task 4 补。

### Task 6: commit Phase 1.1 envelope 改造

- [ ] **Step 6.1: 提交**

```bash
git add src/asset_hub/cli/envelope.py tests/unit/test_envelope.py tests/cli/
git commit -m "$(cat <<'EOF'
refactor(cli): 统一 envelope error 为 {code, message}

主 envelope 升级：error_envelope 加 code 关键字必填参数；handle_domain_errors 通过 _DOMAIN_ERROR_CODES 显式 dict 映射 6 个域异常到 lowercase code（NotFoundError→not_found / StateError→state_conflict 避歧义）。print_error code keyword-only 防漏。

新增 tests/unit/test_envelope.py 6 case 覆盖 success/error 形态、6 域异常 code+exit_code map、validation exit 2 usage 模式、print_error 拒绝裸 message。

修复 tests/cli/test_{asset,type,attachment,transition,stats}_cli*.py 的 error 字段断言（plain string → dict shape）。
EOF
)"
```

预期：commit 创建成功，HEAD 移动。

### Task 7: 重写 serve/cmd.py 走新 envelope（删 _emit_*）

**Files:**
- Modify: `src/asset_hub/cli/serve/cmd.py`

- [ ] **Step 7.1: 重写 cmd.py 全文**

```python
from __future__ import annotations

import sys
from typing import Annotated

import typer

from asset_hub.cli.envelope import print_error, success_envelope
from asset_hub.cli.serve import lifecycle
from asset_hub.cli.serve import logs as logs_mod
from asset_hub.cli.serve.lifecycle import ServeLifecycleError
from asset_hub.cli.serve.output import (
    render_plain_start,
    render_plain_status,
    render_plain_stop,
)
from asset_hub.config import Settings

serve_app = typer.Typer(name="serve", help="管理后端 + 前端服务生命周期", no_args_is_help=True)


def _emit_success_plain(plain_text: str) -> None:
    if plain_text:
        print(plain_text)


@serve_app.command("start")
def start(
    mode: Annotated[str, typer.Option("--mode", help="启动模式 (dev|prod)")] = "prod",
    skip_build: Annotated[bool, typer.Option("--skip-build", help="跳过自动 build")] = False,
    port: Annotated[int | None, typer.Option("--port", help="覆盖后端端口")] = None,
    frontend_port: Annotated[int | None, typer.Option("--frontend-port", help="覆盖前端端口")] = None,
    host: Annotated[str | None, typer.Option("--host", help="覆盖后端 host")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="JSON 信封输出")] = False,
):
    """启动服务（默认 prod 模式）。"""
    if mode not in ("dev", "prod"):
        print_error(
            f"invalid --mode '{mode}' (expected dev|prod)",
            json_out, code="serve.usage", exit_code=2,
        )
    try:
        result = lifecycle.start_service(
            mode=mode,  # type: ignore[arg-type]
            skip_build=skip_build,
            port_override=port,
            frontend_port_override=frontend_port,
            host_override=host,
        )
    except ServeLifecycleError as e:
        print_error(e.message, json_out, code=e.code, exit_code=1)

    if json_out:
        print(success_envelope(result.to_dict()))
    else:
        _emit_success_plain(render_plain_start(result))
    raise typer.Exit(code=0)


@serve_app.command("stop")
def stop(
    json_out: Annotated[bool, typer.Option("--json", help="JSON 信封输出")] = False,
):
    """停止当前在跑的服务（幂等）。"""
    try:
        result = lifecycle.stop_service()
    except ServeLifecycleError as e:
        print_error(e.message, json_out, code=e.code, exit_code=1)

    if json_out:
        print(success_envelope(result.to_dict()))
    else:
        _emit_success_plain(render_plain_stop(result))
    raise typer.Exit(code=0)


@serve_app.command("status")
def status(
    json_out: Annotated[bool, typer.Option("--json", help="JSON 信封输出")] = False,
    no_probe: Annotated[bool, typer.Option("--no-probe", help="跳过 HTTP 健康探测")] = False,
):
    """查询服务状态（含 HTTP 健康探测）。"""
    report = lifecycle.status_service(no_probe=no_probe)
    if json_out:
        # status 的 took_ms / probed 在 report.metadata()，这里走 success_envelope 的 take_ms 路径
        meta = report.metadata()
        print(success_envelope(report.to_dict(), took_ms=meta.get("took_ms")))
    else:
        _emit_success_plain(render_plain_status(report))
    raise typer.Exit(code=0)


@serve_app.command("restart")
def restart(
    mode: Annotated[str | None, typer.Option("--mode", help="显式指定模式 (dev|prod)")] = None,
    skip_build: Annotated[bool, typer.Option("--skip-build")] = False,
    port: Annotated[int | None, typer.Option("--port")] = None,
    frontend_port: Annotated[int | None, typer.Option("--frontend-port")] = None,
    host: Annotated[str | None, typer.Option("--host")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="JSON 信封输出")] = False,
):
    """重启服务（自动推断 mode；如无法推断需 --mode）。"""
    if mode is not None and mode not in ("dev", "prod"):
        print_error(
            f"invalid --mode '{mode}' (expected dev|prod)",
            json_out, code="serve.usage", exit_code=2,
        )
    try:
        stop_res, start_res = lifecycle.restart_service(
            mode_override=mode,  # type: ignore[arg-type]
            skip_build=skip_build,
            port_override=port,
            frontend_port_override=frontend_port,
            host_override=host,
        )
    except ServeLifecycleError as e:
        print_error(e.message, json_out, code=e.code, exit_code=1)

    if json_out:
        print(success_envelope({"stop": stop_res.to_dict(), "start": start_res.to_dict()}))
    else:
        if not stop_res.stopped and not stop_res.stale_cleaned:
            plain = "- Not running, starting fresh\n" + render_plain_start(start_res)
        else:
            plain = render_plain_stop(stop_res) + "\n" + render_plain_start(start_res)
        _emit_success_plain(plain)
    raise typer.Exit(code=0)


@serve_app.command("logs")
def logs(
    service: Annotated[str, typer.Option("--service", help="日志源 (backend|frontend|all)")] = "backend",
    lines: Annotated[int, typer.Option("--lines", help="一次性 tail 行数")] = 200,
    follow: Annotated[bool, typer.Option("--follow", help="持续 tail（Ctrl+C 终止）")] = False,
    json_out: Annotated[bool, typer.Option("--json", help="JSON 信封输出（仅一次性模式）")] = False,
):
    """查看服务日志（默认 backend，最近 200 行）。"""
    if service not in ("backend", "frontend", "all"):
        print_error(
            f"invalid --service '{service}' (expected backend|frontend|all)",
            json_out, code="serve.usage", exit_code=2,
        )

    if follow:
        if json_out:
            print("warning: --json ignored in --follow mode", file=sys.stderr)
        if service == "all":
            print("warning: --follow only supports single service; using backend", file=sys.stderr)
            service = "backend"
        path = Settings().logs_dir / f"{service}.log"
        if not path.exists():
            print(f"- No logs available for {service}")
            raise typer.Exit(code=0)
        try:
            for line in logs_mod.follow_log(path):
                sys.stdout.write(line)
                sys.stdout.flush()
        except KeyboardInterrupt:
            pass
        raise typer.Exit(code=0)

    out = lifecycle.logs_for_service(
        service=service,  # type: ignore[arg-type]
        lines=lines,
    )
    if all(len(v) == 0 for v in out.values()):
        if json_out:
            print(success_envelope({"service": service, "lines": [], "truncated": False}))
        else:
            print(f"- No logs available for {service}")
        raise typer.Exit(code=0)

    if json_out:
        if service == "all":
            payload = {"services": out}
        else:
            payload = {"service": service, "lines": out[service], "truncated": False}
        print(success_envelope(payload))
        raise typer.Exit(code=0)

    text_parts = []
    if service == "all":
        for s_name, s_lines in out.items():
            for ln in s_lines:
                text_parts.append(f"[{s_name}] {ln}")
    else:
        text_parts = out[service]
    print("\n".join(text_parts))
    raise typer.Exit(code=0)
```

- [ ] **Step 7.2: 跑 serve 测试**

```bash
uv run pytest tests/cli/test_serve_*.py -v 2>&1 | tail -30
```

预期：全 PASS（envelope 形态等价：serve 测试断言 `error.code` / `error.message` 已是 dict shape，并未改）。

### Task 8: 删 serve/output.py 死代码

**Files:**
- Modify: `src/asset_hub/cli/serve/output.py`

- [ ] **Step 8.1: 删 render_json_envelope + ServeError**

打开 `src/asset_hub/cli/serve/output.py`，删除：
- `class ServeError` dataclass（约 L68-74）
- `def render_json_envelope(...)` 函数（约 L77-90）

保留：
- `ServiceInfo` / `StartResult` / `StopResult` / `StatusReport` dataclass
- `render_plain_start` / `render_plain_stop` / `render_plain_status` / `_fmt_uptime`

删完后 import `json` 不再需要——也删 `import json` 一行。

- [ ] **Step 8.2: 验证无 dangling import**

```bash
git grep -n 'render_json_envelope\|ServeError' src/ tests/ 2>&1
```

预期：**无任何匹配**。如有 import 残留，删干净。

- [ ] **Step 8.3: 跑全套测试**

```bash
uv run pytest tests/ 2>&1 | tail -20
uv run ruff check .
```

预期：全 PASS + ruff clean。

### Task 9: commit Phase 1.2 serve cmd 重写

- [ ] **Step 9.1: 提交**

```bash
git add src/asset_hub/cli/serve/cmd.py src/asset_hub/cli/serve/output.py
git commit -m "$(cat <<'EOF'
refactor(serve): 5 子命令走主 envelope (删 render_json_envelope/_emit_*)

serve/cmd.py 5 子命令 (start/stop/status/restart/logs) 走 envelope.py 的 print_error / success_envelope；ServeLifecycleError(code, message) pass through 到 print_error，serve.* dot prefix 自然继承。
serve/output.py 删 render_json_envelope (~15 LOC) + ServeError dataclass (~10 LOC) 死代码。
serve usage 错误 code = serve.usage（与现有形态一致）。
EOF
)"
```

### Task 10: 写 doctor 测试（TDD 红）+ 实现 doctor

**Files:**
- Create: `tests/unit/test_doctor.py`
- Create: `src/asset_hub/cli/serve/doctor.py`

- [ ] **Step 10.1: 写 tests/unit/test_doctor.py**

```python
"""serve doctor 7 检查项的单元测试。

每检查项 mock subprocess / Path 状态，验证 ok/detail/code/fix_hint。
M3e §2.6 Phase 1 验收。
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from asset_hub.cli.serve.doctor import (
    DoctorCheck,
    DoctorResult,
    check_alembic_head,
    check_data_writable,
    check_frontend_dist,
    check_pnpm,
    check_port_free,
    check_python_version,
    check_uv,
    run_all_checks,
)


class _FakeRun:
    def __init__(self, stdout: str = "", returncode: int = 0):
        self.stdout = stdout
        self.returncode = returncode


def test_check_uv_ok(monkeypatch):
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.subprocess.run",
        lambda *a, **kw: _FakeRun(stdout="uv 0.5.4\n", returncode=0),
    )
    c = check_uv()
    assert c.ok is True
    assert "0.5.4" in c.detail


def test_check_uv_missing(monkeypatch):
    def _raise(*a, **kw):
        raise FileNotFoundError("uv not found")
    monkeypatch.setattr("asset_hub.cli.serve.doctor.subprocess.run", _raise)
    c = check_uv()
    assert c.ok is False
    assert c.code == "serve.uv_missing"
    assert c.fix_hint  # 有引导


def test_check_pnpm_ok(monkeypatch):
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.subprocess.run",
        lambda *a, **kw: _FakeRun(stdout="9.12.3\n", returncode=0),
    )
    c = check_pnpm()
    assert c.ok is True


def test_check_pnpm_missing(monkeypatch):
    def _raise(*a, **kw):
        raise FileNotFoundError("pnpm not found")
    monkeypatch.setattr("asset_hub.cli.serve.doctor.subprocess.run", _raise)
    c = check_pnpm()
    assert c.ok is False
    assert c.code == "serve.pnpm_missing"


def test_check_python_version_ok():
    c = check_python_version()
    # 当前测试环境就是 >= 3.12（pyproject 已锁），应该 ok
    assert c.ok is True


def test_check_data_writable_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    c = check_data_writable()
    assert c.ok is True


def test_check_data_writable_missing(tmp_path, monkeypatch):
    fake = tmp_path / "no_such_dir"
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(fake))
    c = check_data_writable()
    # data dir 不存在或不可写应失败
    assert c.ok is False
    assert c.code == "serve.data_unwritable"


def test_check_alembic_head_ok(monkeypatch):
    # alembic current 与 alembic heads 输出一致
    outputs = iter(["abc123 (head)\n", "abc123\n"])
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.subprocess.run",
        lambda *a, **kw: _FakeRun(stdout=next(outputs), returncode=0),
    )
    c = check_alembic_head()
    assert c.ok is True


def test_check_alembic_head_outdated(monkeypatch):
    outputs = iter(["abc123\n", "def456\n"])
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.subprocess.run",
        lambda *a, **kw: _FakeRun(stdout=next(outputs), returncode=0),
    )
    c = check_alembic_head()
    assert c.ok is False
    assert c.code == "serve.alembic_outdated"


def test_check_frontend_dist_ok(tmp_path, monkeypatch):
    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html/>")
    monkeypatch.chdir(tmp_path)
    c = check_frontend_dist()
    assert c.ok is True


def test_check_frontend_dist_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    c = check_frontend_dist()
    assert c.ok is False
    assert c.code == "serve.dist_missing"
    assert "build" in c.fix_hint.lower()


def test_check_port_free_ok(monkeypatch):
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.proc_mod.is_port_in_use",
        lambda port: False,
    )
    c = check_port_free(8000)
    assert c.ok is True


def test_check_port_free_occupied(monkeypatch):
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.proc_mod.is_port_in_use",
        lambda port: True,
    )
    c = check_port_free(8000)
    assert c.ok is False
    assert c.code == "serve.port_occupied"


def test_run_all_checks_aggregates(monkeypatch, tmp_path):
    """全部 ok 时 result.ok=True；至少一个 fail 时 ok=False。"""
    # mock 全 ok
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_uv",
        lambda: DoctorCheck(name="uv", ok=True, detail="0.5.4"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_pnpm",
        lambda: DoctorCheck(name="pnpm", ok=True, detail="9.12.3"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_python_version",
        lambda: DoctorCheck(name="python", ok=True, detail="3.12.7"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_data_writable",
        lambda: DoctorCheck(name="data_dir", ok=True, detail="/tmp"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_alembic_head",
        lambda: DoctorCheck(name="alembic", ok=True, detail="head"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_frontend_dist",
        lambda: DoctorCheck(name="frontend_dist", ok=True, detail="ok"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_port_free",
        lambda port: DoctorCheck(name=f"port_{port}", ok=True, detail="free"),
    )

    result = run_all_checks(mode="prod")
    assert result.ok is True
    assert result.issue_count == 0
    assert len(result.checks) == 7  # uv/pnpm/python/data/alembic/dist + 1 port (prod 不查 5173)


def test_run_all_checks_dev_mode_includes_5173(monkeypatch):
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_uv",
        lambda: DoctorCheck(name="uv", ok=True, detail="0.5.4"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_pnpm",
        lambda: DoctorCheck(name="pnpm", ok=True, detail="9.12.3"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_python_version",
        lambda: DoctorCheck(name="python", ok=True, detail="3.12.7"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_data_writable",
        lambda: DoctorCheck(name="data_dir", ok=True, detail="/tmp"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_alembic_head",
        lambda: DoctorCheck(name="alembic", ok=True, detail="head"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_frontend_dist",
        lambda: DoctorCheck(name="frontend_dist", ok=True, detail="ok"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_port_free",
        lambda port: DoctorCheck(name=f"port_{port}", ok=True, detail="free"),
    )

    result = run_all_checks(mode="dev")
    assert len(result.checks) == 8  # +5173
```

- [ ] **Step 10.2: 运行测试验证 fail**

```bash
uv run pytest tests/unit/test_doctor.py -v
```

预期：FAIL（doctor 模块尚不存在）。

- [ ] **Step 10.3: 实现 src/asset_hub/cli/serve/doctor.py**

```python
"""serve doctor 子命令的核心检查逻辑。

read-only 诊断；不抛域异常；所有 check 收集后聚合渲染。
M3e §2.4。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from asset_hub.cli.serve import proc as proc_mod
from asset_hub.config import Settings


@dataclass
class DoctorCheck:
    name: str
    ok: bool
    detail: str = ""
    code: str | None = None
    fix_hint: str = ""

    def to_dict(self) -> dict:
        d = {"name": self.name, "ok": self.ok, "detail": self.detail}
        if not self.ok:
            d["code"] = self.code or ""
            d["fix_hint"] = self.fix_hint
        return d


@dataclass
class DoctorResult:
    checks: list[DoctorCheck] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    @property
    def issue_count(self) -> int:
        return sum(1 for c in self.checks if not c.ok)

    def to_dict(self) -> dict:
        return {
            "checks": [c.to_dict() for c in self.checks],
            "ok": self.ok,
            "issue_count": self.issue_count,
        }


def _run_version(cmd: str) -> str:
    """运行 `<cmd> --version`，返回 stdout（已 strip）。FileNotFoundError 让 caller 捕。"""
    result = subprocess.run(
        [cmd, "--version"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip()


def check_uv() -> DoctorCheck:
    try:
        out = _run_version("uv")
        return DoctorCheck(name="uv (>= 0.4)", ok=True, detail=out)
    except FileNotFoundError:
        return DoctorCheck(
            name="uv (>= 0.4)", ok=False, detail="not found",
            code="serve.uv_missing",
            fix_hint="install uv: https://docs.astral.sh/uv/getting-started/installation/",
        )


def check_pnpm() -> DoctorCheck:
    try:
        out = _run_version("pnpm")
        return DoctorCheck(name="pnpm (>= 9)", ok=True, detail=out)
    except FileNotFoundError:
        return DoctorCheck(
            name="pnpm (>= 9)", ok=False, detail="not found",
            code="serve.pnpm_missing",
            fix_hint="install pnpm: npm install -g pnpm@9",
        )


def check_python_version() -> DoctorCheck:
    v = sys.version_info
    s = f"{v.major}.{v.minor}.{v.micro}"
    if v >= (3, 12):
        return DoctorCheck(name="Python (>= 3.12)", ok=True, detail=s)
    return DoctorCheck(
        name="Python (>= 3.12)", ok=False, detail=s,
        code="serve.python_version_low",
        fix_hint="upgrade to Python 3.12+",
    )


def check_data_writable() -> DoctorCheck:
    settings = Settings()
    p = Path(settings.data_dir)
    if not p.exists():
        return DoctorCheck(
            name="data dir writable", ok=False, detail=f"{p} not exists",
            code="serve.data_unwritable",
            fix_hint=f"mkdir -p {p}",
        )
    test_file = p / ".doctor_writable_probe"
    try:
        test_file.write_text("")
        test_file.unlink()
        return DoctorCheck(name="data dir writable", ok=True, detail=str(p))
    except OSError as e:
        return DoctorCheck(
            name="data dir writable", ok=False, detail=f"{p} ({e})",
            code="serve.data_unwritable",
            fix_hint=f"check filesystem permissions on {p}",
        )


def check_alembic_head() -> DoctorCheck:
    try:
        cur = subprocess.run(
            ["uv", "run", "alembic", "current"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        head = subprocess.run(
            ["uv", "run", "alembic", "heads"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
    except FileNotFoundError:
        return DoctorCheck(
            name="alembic head", ok=False, detail="uv/alembic not available",
            code="serve.alembic_outdated",
            fix_hint="run `uv sync` then `uv run alembic upgrade head`",
        )

    cur_rev = cur.split()[0] if cur else ""
    head_rev = head.split()[0] if head else ""
    if cur_rev and cur_rev == head_rev:
        return DoctorCheck(
            name="alembic head", ok=True,
            detail=f"{cur_rev[:8]} (current = head)",
        )
    return DoctorCheck(
        name="alembic head", ok=False,
        detail=f"current={cur_rev[:8] or '<none>'} head={head_rev[:8] or '<none>'}",
        code="serve.alembic_outdated",
        fix_hint="run `uv run alembic upgrade head`",
    )


def check_frontend_dist() -> DoctorCheck:
    p = Path("frontend/dist/index.html")
    if p.exists():
        return DoctorCheck(name="frontend/dist", ok=True, detail="present")
    return DoctorCheck(
        name="frontend/dist", ok=False, detail="missing",
        code="serve.dist_missing",
        fix_hint="run `pnpm --dir frontend build`",
    )


def check_port_free(port: int) -> DoctorCheck:
    in_use = proc_mod.is_port_in_use(port)
    name = f"port :{port} free"
    if not in_use:
        return DoctorCheck(name=name, ok=True, detail="free")
    return DoctorCheck(
        name=name, ok=False, detail="in use",
        code="serve.port_occupied",
        fix_hint=f"stop existing service on :{port} or override with --port",
    )


def run_all_checks(*, mode: str = "prod") -> DoctorResult:
    """聚合 7-8 项检查；mode='dev' 时额外查 :5173。"""
    checks = [
        check_uv(),
        check_pnpm(),
        check_python_version(),
        check_data_writable(),
        check_alembic_head(),
        check_frontend_dist(),
        check_port_free(8000),
    ]
    if mode == "dev":
        checks.append(check_port_free(5173))
    return DoctorResult(checks=checks)
```

- [ ] **Step 10.4: 跑测试验证 pass**

```bash
uv run pytest tests/unit/test_doctor.py -v
```

预期：全 PASS。

### Task 11: 注册 doctor 子命令 + plain 渲染 + CLI 测试

**Files:**
- Modify: `src/asset_hub/cli/serve/cmd.py`
- Create: `tests/cli/test_serve_doctor.py`

- [ ] **Step 11.1: 在 cmd.py 加 doctor 子命令**

在文件末尾追加：

```python
@serve_app.command("doctor")
def doctor(
    mode: Annotated[str, typer.Option("--mode", help="检查 mode (dev|prod)")] = "prod",
    json_out: Annotated[bool, typer.Option("--json", help="JSON 信封输出")] = False,
):
    """诊断环境/版本/依赖/端口/dist 7-8 项；read-only。"""
    from asset_hub.cli.serve.doctor import run_all_checks
    if mode not in ("dev", "prod"):
        print_error(
            f"invalid --mode '{mode}' (expected dev|prod)",
            json_out, code="serve.usage", exit_code=2,
        )

    import time
    t0 = time.perf_counter()
    result = run_all_checks(mode=mode)
    took_ms = int((time.perf_counter() - t0) * 1000)

    if json_out:
        print(success_envelope(result.to_dict(), took_ms=took_ms))
    else:
        # plain 渲染
        print("SERVICE                  STATUS")
        for c in result.checks:
            mark = "✓" if c.ok else "!"
            line = f"{c.name:<24} {mark} {c.detail}"
            if not c.ok and c.fix_hint:
                line += f"\n  → {c.fix_hint}"
            print(line)
        print()
        if result.ok:
            print("All checks passed.")
        else:
            print(f"{result.issue_count} issue(s). Run with --json for machine-readable output.")
    raise typer.Exit(code=0 if result.ok else 1)
```

- [ ] **Step 11.2: 写 tests/cli/test_serve_doctor.py**

```python
"""serve doctor CLI 测试 (plain / json / fail exit 1)。"""
from __future__ import annotations

import json

from typer.testing import CliRunner

from asset_hub.cli.main import app
from asset_hub.cli.serve.doctor import DoctorCheck

runner = CliRunner()


def _mock_all_ok(monkeypatch):
    """所有 check 都返回 ok=True。"""
    for fn in ("check_uv", "check_pnpm", "check_python_version",
               "check_data_writable", "check_alembic_head", "check_frontend_dist"):
        monkeypatch.setattr(
            f"asset_hub.cli.serve.doctor.{fn}",
            lambda _fn=fn: DoctorCheck(name=_fn, ok=True, detail="ok"),
        )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_port_free",
        lambda port: DoctorCheck(name=f"port_{port}", ok=True, detail="free"),
    )


def _mock_dist_missing(monkeypatch):
    """only frontend_dist fails。"""
    for fn in ("check_uv", "check_pnpm", "check_python_version",
               "check_data_writable", "check_alembic_head"):
        monkeypatch.setattr(
            f"asset_hub.cli.serve.doctor.{fn}",
            lambda _fn=fn: DoctorCheck(name=_fn, ok=True, detail="ok"),
        )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_frontend_dist",
        lambda: DoctorCheck(
            name="frontend/dist", ok=False, detail="missing",
            code="serve.dist_missing",
            fix_hint="run `pnpm --dir frontend build`",
        ),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_port_free",
        lambda port: DoctorCheck(name=f"port_{port}", ok=True, detail="free"),
    )


def test_doctor_plain_all_ok(monkeypatch):
    _mock_all_ok(monkeypatch)
    result = runner.invoke(app, ["serve", "doctor"])
    assert result.exit_code == 0
    assert "All checks passed" in result.stdout
    assert "✓" in result.stdout


def test_doctor_json_all_ok(monkeypatch):
    _mock_all_ok(monkeypatch)
    result = runner.invoke(app, ["serve", "doctor", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["data"]["ok"] is True
    assert payload["data"]["issue_count"] == 0
    assert len(payload["data"]["checks"]) == 7  # prod mode


def test_doctor_json_one_fail_exits_1(monkeypatch):
    _mock_dist_missing(monkeypatch)
    result = runner.invoke(app, ["serve", "doctor", "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["success"] is True  # success=true 因为 doctor 不抛域异常；但 data.ok=false
    assert payload["data"]["ok"] is False
    assert payload["data"]["issue_count"] == 1
    bad = [c for c in payload["data"]["checks"] if not c["ok"]][0]
    assert bad["code"] == "serve.dist_missing"
    assert "build" in bad["fix_hint"]


def test_doctor_invalid_mode_exits_2(monkeypatch):
    result = runner.invoke(app, ["serve", "doctor", "--mode", "invalid", "--json"])
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "serve.usage"


def test_doctor_dev_mode_includes_5173(monkeypatch):
    _mock_all_ok(monkeypatch)
    result = runner.invoke(app, ["serve", "doctor", "--mode", "dev", "--json"])
    payload = json.loads(result.stdout)
    assert len(payload["data"]["checks"]) == 8
```

- [ ] **Step 11.3: 跑 doctor CLI 测试**

```bash
uv run pytest tests/cli/test_serve_doctor.py -v
```

预期：全 PASS。

- [ ] **Step 11.4: 跑全套测试 + ruff**

```bash
uv run pytest tests/ 2>&1 | tail -20
uv run ruff check .
```

预期：全 PASS + clean。

- [ ] **Step 11.5: commit Phase 1.3 doctor 落地**

```bash
git add src/asset_hub/cli/serve/doctor.py src/asset_hub/cli/serve/cmd.py tests/unit/test_doctor.py tests/cli/test_serve_doctor.py
git commit -m "$(cat <<'EOF'
feat(serve): doctor 子命令 (uv/pnpm/Python/data dir/alembic/dist/ports 7 检查)

诊断 read-only：聚合渲染所有 check（不是第一个错就 fail），失败 issue 含 code + fix_hint。
mode=dev 时额外检查 :5173；mode=prod 仅 :8000。
JSON 形态：data.checks[] 含 name/ok/detail/(code+fix_hint when fail)；data.ok 为聚合；exit 0 全过 / 1 至少一失败。
EOF
)"
```

---

## Phase 2 · 5 态文案 + 薄弱点补测

### Task 12: 改前端 5 态 SoT (status-labels.ts)

**Files:**
- Modify: `frontend/src/features/assets/status-labels.ts`

- [ ] **Step 12.1: 改 IN_USE / IDLE 的 label**

```ts
// Before
IN_USE: { label: "在用", ... }
IDLE: { label: "闲置", ... }

// After
IN_USE: { label: "使用中", ... }
IDLE: { label: "闲置中", ... }
```

其他 3 态（MAINTENANCE/RETIRED/DISPOSED）label 不变。

- [ ] **Step 12.2: 跑前端 tsc 验证**

```bash
pnpm --dir frontend tsc -b
```

预期：0 错。

### Task 13: grep + 修前端硬编码字面量

**Files:** 视 grep 结果定

- [ ] **Step 13.1: grep 全前端 src 硬编码**

```bash
git grep -nE '"在用"|"闲置"' frontend/src 2>&1
```

注意：要排除 status-labels.ts（SoT 已改）。如果其他文件出现"在用"/"闲置"裸字面量，逐处替换：

- "在用" → "使用中"
- "闲置" → "闲置中"

**注意保留**："闲置时长" / "闲置天数" / "闲置 Top 10" 这类指标性概念**不替换**（它们是名词性指标，不指 IDLE 状态）。

- [ ] **Step 13.2: 验 tsc + lint**

```bash
pnpm --dir frontend tsc -b
pnpm --dir frontend lint
```

预期：0 错。

### Task 14: 同步前端测试 4 文件

**Files:**
- Modify: `frontend/tests/components/status-distribution-chart.test.tsx`
- Modify: `frontend/tests/components/idle-top-bar-chart.test.tsx`
- Modify: `frontend/tests/components/dashboard-motion.test.tsx`
- Modify: `frontend/tests/components/dashboard-header.test.tsx`

- [ ] **Step 14.1: grep 测试文件硬编码字面量**

```bash
git grep -nE '"在用"|"闲置"' frontend/tests 2>&1
```

- [ ] **Step 14.2: 替换字面量**

每处：
- `"在用"` → `"使用中"`
- `"闲置"` → `"闲置中"`

同样**不替换**"闲置时长" / "闲置天数" 类。

- [ ] **Step 14.3: 跑前端测试**

```bash
pnpm --dir frontend test --run
```

预期：全 PASS。

### Task 15: 改后端 5 态 SoT (export.STATUS_LABELS)

**Files:**
- Modify: `src/asset_hub/services/export.py`

- [ ] **Step 15.1: 改 STATUS_LABELS dict**

L28-32 区域：

```python
# Before
STATUS_LABELS: dict[AssetStatus, str] = {
    AssetStatus.IN_USE: "在用",
    AssetStatus.IDLE: "闲置",
    AssetStatus.MAINTENANCE: "维修中",
    AssetStatus.RETIRED: "已退役",
    AssetStatus.DISPOSED: "已处置",
}

# After
STATUS_LABELS: dict[AssetStatus, str] = {
    AssetStatus.IN_USE: "使用中",
    AssetStatus.IDLE: "闲置中",
    AssetStatus.MAINTENANCE: "维修中",
    AssetStatus.RETIRED: "已退役",
    AssetStatus.DISPOSED: "已处置",
}
```

- [ ] **Step 15.2: grep 后端测试是否断言旧文案**

```bash
git grep -nE '"在用"|"闲置"' tests/ 2>&1
```

如有断言 `"在用"` / `"闲置"` 字面（如导出列断言），改成新值；不替换"闲置天数"等指标。

- [ ] **Step 15.3: 跑后端测试**

```bash
uv run pytest tests/api/test_export_routes.py tests/unit/test_export_service.py -v
```

预期：全 PASS。

### Task 16: 写 5 态 filter 后端 unit 测试 6 case

**Files:**
- Modify: `tests/unit/test_asset_service.py`

- [ ] **Step 16.1: 在文件末尾追加 6 个 test 函数**

```python
class TestListAssetsRetiredDisposedFilter:
    """5 态 filter 列表拼接 — M3e §3.2 薄弱点补测。"""

    def _seed_5_states(self, session, type_id):
        """seed 5 个资产，每态各 1 个，返回 (idle_id, in_use_id, maint_id, retired_id, disposed_id)。"""
        # 这里假设 conftest 提供 session + 1 个 type_id；具体 helper 复用既有 pattern
        ...

    def test_default_excludes_retired_and_disposed(self, session, type_id):
        from asset_hub.services.asset import AssetService
        ids = self._seed_5_states(session, type_id)
        svc = AssetService(session)
        result = svc.list_assets()
        statuses = {a.status for a in result.items}
        assert statuses == {"IDLE", "IN_USE", "MAINTENANCE"}  # RETIRED/DISPOSED 排除

    def test_include_retired_only(self, session, type_id):
        from asset_hub.services.asset import AssetService
        ids = self._seed_5_states(session, type_id)
        svc = AssetService(session)
        result = svc.list_assets(include_retired=True)
        statuses = {a.status for a in result.items}
        assert "RETIRED" in statuses
        assert "DISPOSED" not in statuses

    def test_include_disposed_only(self, session, type_id):
        from asset_hub.services.asset import AssetService
        ids = self._seed_5_states(session, type_id)
        svc = AssetService(session)
        result = svc.list_assets(include_disposed=True)
        statuses = {a.status for a in result.items}
        assert "DISPOSED" in statuses
        assert "RETIRED" not in statuses

    def test_include_both(self, session, type_id):
        from asset_hub.services.asset import AssetService
        ids = self._seed_5_states(session, type_id)
        svc = AssetService(session)
        result = svc.list_assets(include_retired=True, include_disposed=True)
        statuses = {a.status for a in result.items}
        assert statuses == {"IDLE", "IN_USE", "MAINTENANCE", "RETIRED", "DISPOSED"}

    def test_explicit_status_retired_overrides_default_exclusion(self, session, type_id):
        from asset_hub.services.asset import AssetService
        from asset_hub.models import AssetStatus
        ids = self._seed_5_states(session, type_id)
        svc = AssetService(session)
        result = svc.list_assets(status=AssetStatus.RETIRED)  # 显式 status，应强制包含
        statuses = {a.status for a in result.items}
        assert statuses == {"RETIRED"}  # 不依赖 include_retired flag

    def test_explicit_status_disposed_overrides(self, session, type_id):
        from asset_hub.services.asset import AssetService
        from asset_hub.models import AssetStatus
        ids = self._seed_5_states(session, type_id)
        svc = AssetService(session)
        result = svc.list_assets(status=AssetStatus.DISPOSED)
        statuses = {a.status for a in result.items}
        assert statuses == {"DISPOSED"}
```

实施时先**读 `tests/unit/test_asset_service.py` 现有 fixture 形态**——`session` / `type_id` fixture 可能是 `conftest.py` autouse；`_seed_5_states` 实现要参考已有 `_seed_assets` 等 helper。

- [ ] **Step 16.2: 跑测试**

```bash
uv run pytest tests/unit/test_asset_service.py::TestListAssetsRetiredDisposedFilter -v
```

如果 `list_assets(status=RETIRED, include_retired=False)` 行为不是"显式 status override"——代码逻辑就是 bug，**先改服务层**让显式 status 强制包含；这正是薄弱点补测发现的回归风险。

预期最终：6 case 全 PASS。

### Task 17: 写 5 态 filter API 测试 2 case + frontend Toggle 测试 1 case

**Files:**
- Modify: `tests/api/test_asset_routes.py`
- Create: `frontend/tests/hooks/assets-filters-toggle.test.tsx`

- [ ] **Step 17.1: 后端 API 加 2 case**

在 `tests/api/test_asset_routes.py` 末尾追加：

```python
class TestListAssetsFilterRetiredDisposed:
    """API 层覆盖 5 态 filter 4 组合 spot check + 显式 status 子句。"""

    def test_query_combinations(self, client, session, type_id, _seed_5_states):
        """无 flag → 不含 retired/disposed；都开 → 全 5 态。"""
        _seed_5_states(session, type_id)
        r1 = client.get("/api/assets")
        assert r1.status_code == 200
        statuses_default = {a["status"] for a in r1.json()["items"]}
        assert "RETIRED" not in statuses_default and "DISPOSED" not in statuses_default

        r2 = client.get("/api/assets?include_retired=true&include_disposed=true")
        assert r2.status_code == 200
        statuses_full = {a["status"] for a in r2.json()["items"]}
        assert statuses_full == {"IDLE", "IN_USE", "MAINTENANCE", "RETIRED", "DISPOSED"}

    def test_explicit_status_overrides_include_flags(self, client, session, type_id, _seed_5_states):
        """status=RETIRED 不需要 include_retired 即返回。"""
        _seed_5_states(session, type_id)
        r = client.get("/api/assets?status=RETIRED")
        assert r.status_code == 200
        statuses = {a["status"] for a in r.json()["items"]}
        assert statuses == {"RETIRED"}
```

`_seed_5_states` 复用 conftest 的 fixture（如不存在，写个 conftest 级 fixture）。

- [ ] **Step 17.2: 跑后端 API 测试**

```bash
uv run pytest tests/api/test_asset_routes.py::TestListAssetsFilterRetiredDisposed -v
```

预期：PASS。

- [ ] **Step 17.3: 写前端 Toggle URL sync 测试**

`frontend/tests/hooks/assets-filters-toggle.test.tsx`：

```tsx
/**
 * assets-filters Toggle on/off → URL search params 同步 → list query refetch。
 * M3e §3.2 薄弱点补测前端层。
 */
import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AssetsFilters } from "@/features/assets/list/assets-filters";

// 复用 frontend/tests/msw-handlers.ts 的 MSW mock + RouterProvider 形态
import { renderWithRouter } from "@/test-utils/render-with-router"; // 或既有 helper

describe("AssetsFilters Toggle URL sync", () => {
  it("toggle 显示已退役 → URL 加 include_retired=true", async () => {
    const user = userEvent.setup();
    const { router } = renderWithRouter(<AssetsFilters />);

    const toggle = screen.getByRole("button", { name: /已退役/i });
    await user.click(toggle);

    await waitFor(() => {
      expect(router.state.location.search).toContain("include_retired=true");
    });
  });

  it("toggle 显示已处置 → URL 加 include_disposed=true", async () => {
    const user = userEvent.setup();
    const { router } = renderWithRouter(<AssetsFilters />);

    const toggle = screen.getByRole("button", { name: /已处置/i });
    await user.click(toggle);

    await waitFor(() => {
      expect(router.state.location.search).toContain("include_disposed=true");
    });
  });
});
```

实施时**先 verify**：
- `renderWithRouter` 是否已存在（否则用既有 hook test 的 setup pattern）
- AssetsFilters 的 toggle role/aria-label 是不是 "已退役" / "已处置"——grep 文件确认实际 label

- [ ] **Step 17.4: 跑前端测试**

```bash
pnpm --dir frontend test --run frontend/tests/hooks/assets-filters-toggle.test.tsx
```

预期：PASS。

### Task 18: commit Phase 2

- [ ] **Step 18.1: 提交**

```bash
git add frontend/src/features/assets/status-labels.ts \
        frontend/src/ \
        frontend/tests/ \
        src/asset_hub/services/export.py \
        tests/unit/test_asset_service.py \
        tests/api/test_asset_routes.py \
        tests/api/conftest.py
git commit -m "$(cat <<'EOF'
refactor(frontend): 5 态文案对齐 3 字（闲置中/使用中）+ 薄弱点补测

5 态 SoT 修订：
- frontend/src/features/assets/status-labels.ts STATUS_META: IN_USE → 使用中、IDLE → 闲置中（其余 3 态不变）
- src/asset_hub/services/export.py STATUS_LABELS dict 同步

薄弱点补测（M3e §3.2 5 态 filter 列表拼接）：
- tests/unit/test_asset_service.py + 6 case (默认排除 retired/disposed / include_retired/disposed 4 组合 / 显式 status 强制包含)
- tests/api/test_asset_routes.py + 2 case (4 组合 spot check + 显式 status 子句)
- frontend/tests/hooks/assets-filters-toggle.test.tsx + 2 case (Toggle on/off URL search params sync)

前端测试 4 文件 + 后端测试同步替换字面量；保留"闲置时长/闲置天数/闲置 Top 10"等指标性概念。
EOF
)"
```

---

## Phase 3 · 文档

### Task 19: 起 SKILL.md（仓库根 + frontmatter + 主体骨架）

**Files:**
- Create: `SKILL.md`

- [ ] **Step 19.1: 写 SKILL.md 主体**

按 spec §4.1 + 复核校准后的 description 写：

```markdown
---
name: asset-hub
description: |-
  小组资产管理工具（命令 asset-hub）的 Agent 入口。
  使用此 skill 当用户在 asset-hub 项目里提到资产登记 / 状态流转（派发、归还、送修、退役、处置）/ 列表筛选 / CSV/XLSX 导出 / 看板统计 / AssetType 自定义字段 / serve 子命令（start/stop/status/restart/logs/doctor）/ 在 Windows 部署 asset-hub / asset-hub 升级，或在项目目录里直接调用 asset-hub 命令。
  包含 5 态状态机（闲置中/使用中/维修中/已退役/已处置）、10 种 transition、JSON envelope 契约、CLI 命令速查、常见任务流。
---

# asset-hub

小组资产管理工具。Web GUI 面向作者本人，CLI 面向 AI Agent（即此文件的主消费者）。

## 何时用我

- 资产 CRUD（登记 / 查询 / 编辑 / 删除）
- 状态流转（10 种 transition）
- 类型管理（AssetType 自定义字段定义）
- 看板查询（4 段聚合统计：类型 / 状态 / 保管人 Top 10 / 闲置时长 Top 10）
- 数据导出（CSV / XLSX，按当前筛选透传）
- 服务生命周期（serve start/stop/status/restart/logs/doctor）

## 资产状态机（5 态）

| status | 中文文案 | 含义 | 可派发 | 列表默认显示 |
|---|---|---|---|---|
| `IDLE` | 闲置中 | 在库可派发 | ✓ | ✓ |
| `IN_USE` | 使用中 | 已派出（kind 区分组内/对外） | ✗ | ✓ |
| `MAINTENANCE` | 维修中 | 维修中，不可派发 | ✗ | ✓ |
| `RETIRED` | 已退役 | 暂时退役（备件/转借/暂停服役，可复活） | ✗ | ✗（toggle 显示） |
| `DISPOSED` | 已处置 | 彻底处置（卖/捐/销毁，终态） | ✗ | ✗（toggle 显示） |

## 10 种 transition

| kind | from → to | 必填字段 |
|---|---|---|
| `CHECKOUT_INTERNAL` | IDLE → IN_USE | to_holder, to_location |
| `CHECKOUT_EXTERNAL` | IDLE → IN_USE | to_holder, to_location |
| `RETURN` | IN_USE → IDLE | （可改 to_holder, to_location） |
| `SEND_TO_MAINTENANCE` | IDLE → MAINTENANCE | （可改 to_holder, to_location） |
| `RECOVER_FROM_MAINTENANCE` | MAINTENANCE → IDLE | （可改 to_holder, to_location） |
| `RETIRE` | IDLE / MAINTENANCE → RETIRED | （可改 to_holder, to_location） |
| `REINSTATE` | RETIRED → IDLE | （可改 to_holder, to_location） |
| `DISPOSE` | RETIRED / MAINTENANCE → DISPOSED | confirm phrase = "处置" |
| `RELOCATE` | IDLE / IN_USE / MAINTENANCE / RETIRED → 同 status | to_location |
| `TRANSFER_HOLDER` | IDLE / IN_USE / MAINTENANCE / RETIRED → 同 status | to_holder |

## CLI envelope 速查

成功响应：

```json
{ "success": true, "data": <任意>, "metadata": { "took_ms": 12, "count": 5 }, "error": null }
```

错误响应：

```json
{ "success": false, "data": null, "metadata": {}, "error": { "code": "<error_code>", "message": "<中文 detail>" } }
```

退出码：`0` 成功 / `1` 一般错误 / `2` 用法/参数错误 / `3` 资源不存在 / `10` dry-run 预览。

## 命令速查

资产 CRUD：

- `asset-hub asset register --name <name> --type-id <uuid> --sn <sn> [--custom <json>] [--photo <path>] [--json]`
- `asset-hub asset list [--status <status>] [--type-id <uuid>] [--include-retired] [--include-disposed] [--json]`
- `asset-hub asset get <id> [--json]`
- `asset-hub asset update <id> [--name <name>] [--sn <sn>] [--custom <json>] [--json]`
- `asset-hub asset delete <id> [--dry-run] [--yes] [--json]`

状态流转（每 transition kind 1 子命令）：

- `asset-hub asset transition checkout <id> --kind internal|external --to-holder <name> --to-location <loc> [--due-at <iso>] [--note <txt>]`
- `asset-hub asset transition return <id> [--to-holder <name>] [--to-location <loc>] [--note <txt>]`
- `asset-hub asset transition send-to-maintenance <id> [--to-holder <name>] [--to-location <loc>] [--note <txt>]`
- `asset-hub asset transition recover <id> [--to-holder <name>] [--to-location <loc>] [--note <txt>]`
- `asset-hub asset transition retire <id> [--to-holder <name>] [--to-location <loc>] [--note <txt>]`
- `asset-hub asset transition reinstate <id> [--to-holder <name>] [--to-location <loc>] [--note <txt>]`
- `asset-hub asset transition dispose <id> --confirm 处置 [--note <txt>]`
- `asset-hub asset transition relocate <id> --to-location <loc> [--note <txt>]`
- `asset-hub asset transition transfer-holder <id> --to-holder <name> [--to-location <loc>] [--note <txt>]`

类型管理：

- `asset-hub type define --from <json-file> [--json]`
- `asset-hub type list [--json]`
- `asset-hub type get <id> [--json]`
- `asset-hub type update <id> [...] [--json]`
- `asset-hub type delete <id> [--dry-run] [--yes] [--json]`

附件：

- `asset-hub attachment upload <asset-id> --path <file> [--json]`
- `asset-hub attachment list <asset-id> [--json]`
- `asset-hub attachment delete <attachment-id> [--json]`

看板与导出：

- `asset-hub stats [--json]`
- `asset-hub export --format csv|xlsx [--status <s>] [--type-id <uuid>] [--holder <name>] [--q <query>] --output <path>`

服务生命周期：

- `asset-hub serve start [--mode dev|prod] [--skip-build] [--port N] [--frontend-port N] [--json]`
- `asset-hub serve stop [--json]`
- `asset-hub serve status [--no-probe] [--json]`
- `asset-hub serve restart [--mode dev|prod] [--json]`
- `asset-hub serve logs [--service backend|frontend|all] [--lines N] [--follow] [--json]`
- `asset-hub serve doctor [--mode dev|prod] [--json]`

## Gotchas

- **DISPOSED 是终态**：一旦设置不可回退到 IDLE。这是因为 DISPOSED 对应物理处置（卖 / 捐 / 销毁），与 RETIRED（暂时退役、可复活）严格区分。如果用户说"先放着以后可能用"，应该 `transition retire`，不是 `transition dispose`。
- **DISPOSE 必须 from RETIRED / MAINTENANCE**：IDLE 不能直接 DISPOSE，必须先 RETIRE。这是为了让"用户误点处置"成本最小化（多一步 dialog 二次确认）。
- **归还后 holder/location 跟随 to_holder/to_location，不强制清空**：M3a 行为修订。`to_holder=null` 表示无人值守仓库；非 null 表示归还接收人 / 仓管成为新 holder。
- **IN_USE → MAINTENANCE 直跳走两步**：dialog 会提示"将先记 RETURN 再 SEND_TO_MAINTENANCE"，service 写两条 record。这是为了让 timeline 真实反映"派发期间送修"的两步语义，不丢历史。
- **5 态文案 vs 枚举值严格区分**：UI 显示 "闲置中/使用中/维修中/已退役/已处置"，API 与 CLI `--json` 输出 "IDLE/IN_USE/MAINTENANCE/RETIRED/DISPOSED"。在 `--json` 输出里看见 "IN_USE" 不是 bug。

## 详细参考

- 10 transition 完整规则（**何时读**：用户问 RELOCATE 与 TRANSFER_HOLDER 区别 / dialog 行为 / from-status 边界）：[references/transitions.md](./references/transitions.md)
- envelope error code 完整 inventory（**何时读**：解析 CLI error 遇到未知 code、调试 exit_code、需引用错误处理对照表）：[references/envelope.md](./references/envelope.md)
- 端到端任务流（**何时读**：用户给出"帮我登记 + 派发 + 归还"完整流程，或需要 --json 输出对照样本）：[references/workflows.md](./references/workflows.md)
- 部署 / serve doctor / 故障排查（**何时读**：`serve start` 失败、`serve doctor` 输出有 issue、用户问"在 Windows 怎么部署 / 怎么备份"）：[references/deploy.md](./references/deploy.md)
```

- [ ] **Step 19.2: 验证渲染 + 行数**

```bash
wc -l SKILL.md
```

预期：≤ 200 行。

### Task 20: 写 references/transitions.md

**Files:**
- Create: `references/transitions.md`

- [ ] **Step 20.1: 写完整 references/transitions.md**

```markdown
# transitions reference

> ⚠️ 与 `src/asset_hub/services/transition.py` + `src/asset_hub/api/routers/transitions.py` + `frontend/src/features/assets/detail/*-dialog.tsx` 同源约定 — 改一处必查另一处。

10 种 transition 完整规则。补充 SKILL.md 主体的 transition 速查表。

## from-status 矩阵（合法性）

| kind | from 合法 | to | 备注 |
|---|---|---|---|
| `CHECKOUT_INTERNAL` | IDLE | IN_USE | 组内派发 |
| `CHECKOUT_EXTERNAL` | IDLE | IN_USE | 向外出借 |
| `RETURN` | IN_USE | IDLE | kind 跟随对应 OPEN checkout |
| `SEND_TO_MAINTENANCE` | IDLE | MAINTENANCE | 送修；IN_USE 期间送修走两步（先 RETURN 再 SEND） |
| `RECOVER_FROM_MAINTENANCE` | MAINTENANCE | IDLE | 修好回库 |
| `RETIRE` | IDLE / MAINTENANCE | RETIRED | 暂时退役（可复活） |
| `REINSTATE` | RETIRED | IDLE | 仅 RETIRED → IDLE |
| `DISPOSE` | RETIRED / MAINTENANCE | DISPOSED | **IDLE 不可直 DISPOSE**（必先 RETIRE）；终态不可逆 |
| `RELOCATE` | IDLE / IN_USE / MAINTENANCE / RETIRED → 同 status | 同 status | 仅 location 变；DISPOSED 排除 |
| `TRANSFER_HOLDER` | IDLE / IN_USE / MAINTENANCE / RETIRED → 同 status | 同 status | holder（± location）变；DISPOSED 排除 |

## 必填字段（按 kind）

| kind | 必填 | 可选 |
|---|---|---|
| `CHECKOUT_INTERNAL` / `CHECKOUT_EXTERNAL` | `to_holder`, `to_location` | `due_at`, `note` |
| `RETURN` | （无必填） | `to_holder`, `to_location`, `note`（不传则 holder 跟随 NULL = 无人值守） |
| `SEND_TO_MAINTENANCE` / `RECOVER_FROM_MAINTENANCE` / `RETIRE` / `REINSTATE` | （无必填） | `to_holder`, `to_location`, `note` |
| `DISPOSE` | confirm phrase（前端 dialog 输 "处置" 解锁；CLI 用 `--confirm 处置`）| `note` |
| `RELOCATE` | `to_location` | `note` |
| `TRANSFER_HOLDER` | `to_holder` | `to_location`, `note` |

## Dialog 行为（前端 7 dialog 设计）

| dialog 文件 | 覆盖 kind |
|---|---|
| `checkout-dialog.tsx` | CHECKOUT_INTERNAL / CHECKOUT_EXTERNAL（kind 单选 + 派发对象 / 位置 / 期望归还） |
| `return-dialog.tsx` | RETURN（归还接收人 / 归还位置 可选） |
| `simple-transition-dialog.tsx` | SEND_TO_MAINTENANCE / RECOVER_FROM_MAINTENANCE / REINSTATE（共用） |
| `retire-alert-dialog.tsx` | RETIRE（AlertDialog 二次确认） |
| `dispose-alert-dialog.tsx` | DISPOSE（AlertDialog + 输 "处置" 解锁） |
| `relocate-dialog.tsx` | RELOCATE |
| `transfer-holder-dialog.tsx` | TRANSFER_HOLDER |

## Service 行为

- `record_transition(asset_id, kind, *, to_holder=None, to_location=None, note=None, due_at=None)` 是唯一入口
- service 内 `validate_transition(current_status, kind, to_holder, to_location)` 校验 from-status + 必填字段
- 违法 → `IllegalTransitionError(detail)` → router 409 Conflict / CLI exit 1 + `error.code = "illegal_transition"`
- 写入 `state_transition_records` 表 + 反规范化更新 `Asset.status` / `Asset.holder` / `Asset.location`
- RETURN 自动找最近 OPEN CHECKOUT_* 行，写 `closes_transition_id` 关闭闭环
- IN_USE → MAINTENANCE 直跳：service 不接受；前端 dialog 拆两步显式调用

## REST 端点

`POST /api/assets/{asset_id}/transitions`：

```json
{
  "kind": "CHECKOUT_INTERNAL",
  "to_holder": "张三",
  "to_location": "北京办公室",
  "due_at": "2026-06-01T00:00:00Z",
  "note": "项目 X"
}
```

响应：刚创建的 `StateTransitionRecord` 行（含 `id` / `from_status` / `to_status` / `closes_transition_id` 等）。
```

### Task 21: 写 references/envelope.md

**Files:**
- Create: `references/envelope.md`

- [ ] **Step 21.1: 写完整 references/envelope.md**

```markdown
# envelope reference

> ⚠️ 与 `src/asset_hub/cli/envelope.py` + `src/asset_hub/cli/serve/lifecycle.py` 同源约定 — 改一处必查另一处。

CLI envelope error code 完整 inventory + JSON 示例 + edge case。

## envelope 形态

成功：

```json
{ "success": true, "data": <任意>, "metadata": { "took_ms": 12, "count": 5 }, "error": null }
```

错误：

```json
{ "success": false, "data": null, "metadata": {}, "error": { "code": "<error_code>", "message": "<中文 detail>" } }
```

dry-run（破坏性命令的预览）：

```json
{ "success": true, "data": { "would_delete": true, ... }, "metadata": {}, "error": null }
```

dry-run 退出码 = 10（语义化区分"成功执行" 与"成功预览不执行"）。

## error code 完整清单

### 域异常（主 CLI）

| code | 来源异常 | HTTP map | exit_code |
|---|---|---|---|
| `not_found` | NotFoundError | 404 | 3 |
| `duplicate` | DuplicateError | 409 | 1 |
| `validation` | ValidationError | 422 | 1（默认）/ 2（usage 错误） |
| `state_conflict` | StateError（业务规则冲突） | 409 | 1 |
| `conflict` | ConflictError（跨对象引用冲突，如 type 被资产引用） | 409 | 1 |
| `illegal_transition` | IllegalTransitionError | 409 | 1 |

### serve 子命令（保留 dot prefix namespace）

| code | 触发 |
|---|---|
| `serve.usage` | --mode 取值非 dev/prod、--service 取值非 backend/frontend/all 等用法错误 |
| `serve.port_occupied` | :8000 / :5173 被占 |
| `serve.dist_missing` | prod 模式启动但 frontend/dist 缺失 |
| `serve.health_probe_timeout` | start 后 /api/healthz 多次重试仍未 200 |
| `serve.frontend_failed_to_start` | dev 模式启动 vite 进程失败 |
| `serve.data_unwritable` | data dir 不存在或无写权 |
| `serve.already_running` | start 时检测到 stale 或 active pid |
| `serve.build_failed` | pnpm build 失败 |
| `serve.kill_failed` | stop 时 SIGTERM/SIGKILL 都失败 |
| `serve.mode_required` | restart 无法推断 mode + 未提供 --mode |
| `serve.uv_missing` | doctor 检测 uv 不在 PATH |
| `serve.pnpm_missing` | doctor 检测 pnpm 不在 PATH |
| `serve.python_version_low` | doctor 检测 Python < 3.12 |
| `serve.alembic_outdated` | doctor 检测 alembic current ≠ heads |

## edge case

### dry-run 退出码

`asset delete --dry-run` / `type delete --dry-run` 返回 `success=true` + 退出码 10。在 shell 脚本里：

```bash
asset-hub asset delete xxx --dry-run --json
case $? in
  0) echo "delete completed" ;;  # 这不会发生 dry-run 模式下
  10) echo "dry-run preview, no change" ;;
  3) echo "asset not found" ;;
  1) echo "general failure" ;;
esac
```

### usage error vs validation error

`asset get <无效 UUID>` → `error.code == "validation"` + exit 2（usage error）
`asset get <格式正确但不存在的 UUID>` → `error.code == "not_found"` + exit 3

区分通过 `handle_domain_errors(json_output, exit_2_on_validation=True)` 在 cli/deps.py::parse_uuid 内启用。

### 恢复建议（v1.0 状态 / v1.1 计划）

当前 `error.message` 自带恢复建议（如 `"CHECKOUT_INTERNAL 必须提供 to_holder"`）。v1.1 计划升级为 `{code, message, hint, fields_missing?, ...}` 结构化（与 simplify §T `IllegalTransitionError.detail` 同 PR），届时 message 与 hint 分离。

`serve doctor` 的 `data.checks[].fix_hint` 是局部 hint 实现样本——不在 `error.hint` 而在 `data.checks[]` 因为 doctor success 路径下多 issue 聚合渲染。
```

### Task 22: 写 references/workflows.md

**Files:**
- Create: `references/workflows.md`

- [ ] **Step 22.1: 写完整 references/workflows.md**

```markdown
# workflows reference

> 端到端任务流（含 --json 输出对照样本）。SKILL.md 主体的"常见任务流"补充。

5 个端到端流程，每个流的命令链 + 关键 --json 响应字段。

## 流 1: 登记一台带照片的笔记本

```bash
# 步骤 1 · 定义类型（如已存在跳过）
uv run asset-hub type define --from examples/types/laptop.json --json
# data.id = <type_id>

# 步骤 2 · 登记资产
uv run asset-hub asset register \
    --name "ThinkPad X1 Carbon" \
    --type-id <type_id> \
    --sn "PF-1234" \
    --custom '{"brand":"Lenovo","os":"Windows","ram_gb":16}' \
    --json
# data.id = <asset_id>

# 步骤 3 · 上传照片
uv run asset-hub attachment upload <asset_id> --path ~/Pictures/laptop.jpg --json
# data.id = <attachment_id>; data.sha256 = ...

# 步骤 4 · 验证
uv run asset-hub asset get <asset_id> --json
# data.status = "IDLE"; data.attachments 含 1 个
```

## 流 2: 派发 + 归还闭环

```bash
# 派发给张三（北京办公室），期望 30 天归还
uv run asset-hub asset transition checkout <asset_id> \
    --kind internal \
    --to-holder "张三" \
    --to-location "北京办公室" \
    --due-at "2026-06-01T00:00:00Z" \
    --json
# data.kind = "CHECKOUT_INTERNAL"; data.to_status = "IN_USE"

# 张三离职，物归仓管李四（上海仓库）
uv run asset-hub asset transition return <asset_id> \
    --to-holder "李四" \
    --to-location "上海仓库" \
    --note "归还" \
    --json
# data.kind = "RETURN"; data.from_status = "IN_USE"; data.to_status = "IDLE"; data.closes_transition_id = <CHECKOUT_INTERNAL.id>
```

## 流 3: 送修 + 维修完成

```bash
# 屏幕坏了，送修（联系王五）
uv run asset-hub asset transition send-to-maintenance <asset_id> \
    --to-holder "王五（客服）" \
    --to-location "上海联想售后" \
    --json
# data.to_status = "MAINTENANCE"

# 修好回库
uv run asset-hub asset transition recover <asset_id> \
    --to-location "上海仓库" \
    --json
# data.to_status = "IDLE"
```

## 流 4: 退役 + 重新启用 / 处置

```bash
# 暂时退役（备件）
uv run asset-hub asset transition retire <asset_id> --note "硬盘老化备件" --json
# data.to_status = "RETIRED"

# 决定复活
uv run asset-hub asset transition reinstate <asset_id> --to-holder "李四" --to-location "上海仓库" --json
# data.to_status = "IDLE"

# 或决定彻底处置（卖给二手商）
uv run asset-hub asset transition dispose <asset_id> --confirm 处置 --note "二手卖出" --json
# data.to_status = "DISPOSED"  ← 终态，不可回退

# 验证：DISPOSED 后即不出现在默认列表
uv run asset-hub asset list --json | jq '.data.items | length'
# 减 1
uv run asset-hub asset list --include-disposed --json | jq '.data.items | length'
# 不变（包含 DISPOSED）
```

## 流 5: 按筛选导出

```bash
# 当前所有 IDLE 资产，导出 XLSX
uv run asset-hub export --format xlsx --status IDLE --output /tmp/idle-assets.xlsx
# 期望：/tmp/idle-assets.xlsx 写出，含表头 + 5 态色条件格式

# 当前所有 张三 持有的资产，导出 CSV
uv run asset-hub export --format csv --holder "张三" --output /tmp/zhang-san.csv
# UTF-8 BOM + 10 列 + custom_fields 平铺

# 按当前关键词搜索 + 类型导出
uv run asset-hub export --format xlsx --q "ThinkPad" --type-id <laptop_type_id> --output /tmp/thinkpads.xlsx
```

## 流 6: 服务生命周期 + 故障诊断

```bash
# 验环境
uv run asset-hub serve doctor --json
# data.ok = true → 全过；false → data.checks[].code + .fix_hint 看哪一项

# 启动 dev（前后端同启）
uv run asset-hub serve start --mode dev --json
# data.backend.pid = ...; data.frontend.pid = ...

# 状态
uv run asset-hub serve status --json
# data.running = true; data.backend / .frontend 各含 pid/port/uptime/healthy

# 看后端日志
uv run asset-hub serve logs --service backend --lines 100 --json

# 跟踪日志
uv run asset-hub serve logs --service backend --follow

# 重启 prod
uv run asset-hub serve restart --mode prod --json

# 干净停掉
uv run asset-hub serve stop --json
```
```

### Task 23: 写 references/deploy.md（pointer 形式）

**Files:**
- Create: `references/deploy.md`

- [ ] **Step 23.1: 写 deploy.md（pointer + 关键速查）**

为避免与 `docs/deployment.md` 双源漂移，`references/deploy.md` 用 **pointer + Agent 速查精简版**形态：

```markdown
# deploy reference

> 完整部署文档：[../docs/deployment.md](../docs/deployment.md)。
> 此文为 Agent 速查精简版——避免 progressive disclosure 时多查 1 文件，关键命令直接落在此。

## 一句话速记

`uv sync && pnpm --dir frontend install && uv run alembic upgrade head && uv run asset-hub serve doctor && uv run asset-hub serve start --mode prod`

## serve doctor 检查项

7-8 项（mode=prod 7 项，mode=dev 8 项含 :5173）：

1. uv 可用 → 失败 code: `serve.uv_missing`，fix: `install uv`
2. pnpm 可用 → `serve.pnpm_missing`，fix: `npm install -g pnpm@9`
3. Python >= 3.12 → `serve.python_version_low`
4. data dir 可写 → `serve.data_unwritable`
5. alembic head → `serve.alembic_outdated`，fix: `uv run alembic upgrade head`
6. frontend/dist 存在（仅 prod 相关）→ `serve.dist_missing`，fix: `pnpm --dir frontend build`
7. :8000 可用 → `serve.port_occupied`
8. :5173 可用（仅 dev）→ 同上

## 故障排查速记

| 症状 | 检查 | 修复 |
|---|---|---|
| `serve start` 卡住后超时 | `serve.health_probe_timeout` | 检查 backend.log 看 uvicorn 启动错；db 是否就位（`alembic upgrade head`）|
| pid stale | `serve status` 显示 stale | `serve stop` 清理后重启 |
| `dist missing` | `serve.dist_missing` | `pnpm --dir frontend build` |
| 端口被占 | `serve.port_occupied` | `serve stop` 或 `--port 8001` 覆盖 |
| 数据库 lock | sqlite WAL 残留 | rm `data/asset_hub.db-shm` `data/asset_hub.db-wal`（先 stop 服务） |

## 数据备份 / 还原

```bash
# 备份
cp data/asset_hub.db data/asset_hub.db.<日期>.bak
tar czf attachments-<日期>.tgz data/attachments/

# 还原
cp data/asset_hub.db.<日期>.bak data/asset_hub.db
tar xzf attachments-<日期>.tgz
```

## Windows 单机部署要点

- PowerShell 7+ 推荐
- 配 `setx ASSET_HUB_DATA_DIR "C:\path\to\data"`
- 防火墙允许 `:8000`（prod 单端口）/ `:5173`（dev）
- 详见 `../docs/deployment.md`
```

### Task 24: 写 docs/deployment.md（人类稳定文档）

**Files:**
- Create: `docs/deployment.md`

- [ ] **Step 24.1: 读 Settings 字段**

```bash
cat src/asset_hub/config.py
```

记录所有 ASSET_HUB_* 字段名 + 默认值。

- [ ] **Step 24.2: 写 docs/deployment.md**

```markdown
# 部署指南

asset-hub 的 v1.0 部署文档。Windows 单机首选；Linux 真机烟测推 v1.1。

## 环境要求

| 工具 | 版本 |
|---|---|
| Python | 3.12+ |
| Node.js | 20+ |
| uv | 0.4+ |
| pnpm | 9+ |
| OS | Windows 11（推荐） / Linux（v1.1 真机验证） / macOS（开发用） |

## 安装步骤

```bash
git clone <repo-url>
cd asset-hub
uv sync                                     # 安装 Python 依赖
pnpm --dir frontend install                 # 安装前端依赖
cp .env.example .env                        # 配置（见下节）
uv run alembic upgrade head                 # 建数据库
uv run asset-hub serve doctor               # 验证环境
uv run asset-hub serve start --mode prod    # 启动
```

## 配置项（.env）

[列 Settings 所有字段：data_dir / logs_dir / database_url / backend_port / frontend_port / mode / ...（实施期对照 `src/asset_hub/config.py::Settings` 全枚举）]

## 数据维护

| 资源 | 路径 |
|---|---|
| 数据库 | `data/asset_hub.db`（SQLite 单文件） |
| 附件 | `data/attachments/<yyyy>/<mm>/<sha256>.<ext>` |
| 日志 | `data/logs/{backend,frontend}.log`（+ `.1` 上一会话） |
| pid | `data/pids/{backend,frontend}.pid` |

**备份建议**：每日 + 升级前

```bash
cp data/asset_hub.db data/asset_hub.db.$(date +%Y%m%d).bak
tar czf attachments-$(date +%Y%m%d).tgz data/attachments/
```

## 升级

```bash
git pull
uv sync
pnpm --dir frontend install
uv run alembic upgrade head
uv run asset-hub serve doctor               # 验证升级后状态
uv run asset-hub serve restart --mode prod  # 重启服务
```

## 故障排查

### `serve start` 失败

跑 `asset-hub serve doctor --json` 看 data.checks 哪项 fail，按 fix_hint 修。常见：
- `serve.dist_missing` → `pnpm --dir frontend build`
- `serve.alembic_outdated` → `uv run alembic upgrade head`
- `serve.port_occupied` → 看 :8000 / :5173 是否被占；先 `serve stop` 或 `--port 覆盖`

### pid 残留

`serve status` 显示 stale → 之前进程异常退出。`serve stop` 清理。

### 数据库 lock

`sqlite3.OperationalError: database is locked` → WAL 文件残留：

```bash
asset-hub serve stop
rm -f data/asset_hub.db-shm data/asset_hub.db-wal
asset-hub serve start --mode prod
```

### 日志位置

- backend: `data/logs/backend.log`（+ `.1`）
- frontend: `data/logs/frontend.log`
- `asset-hub serve logs --service backend --lines 200 --follow`

## Windows 单机部署补充

- PowerShell 7+：`winget install --id Microsoft.PowerShell --source winget`
- 系统环境变量：`setx ASSET_HUB_DATA_DIR "C:\path\to\data"`
- 防火墙：开 `:8000`（prod 模式单端口） / `:5173`（dev 模式额外）
- 不要把 `data/` 放云盘（OneDrive / iCloud）—— SQLite WAL 与同步冲突会损坏数据库
```

### Task 25: 重写 README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 25.1: 全量替换 README.md**

```markdown
# asset-hub

> 小组资产管理工具。双接口：Web GUI 面向人类，CLI 面向 AI Agent。

## 核心能力

- **资产 CRUD** + 类型驱动的自定义字段（string / int / float / bool / enum / multi_enum / date / text / url）
- **状态机**：5 态（闲置中 / 使用中 / 维修中 / 已退役 / 已处置）
- **10 种 transition**：派发（组内/外借）/ 归还 / 送修 / 维修完成 / 退役 / 重新启用 / 处置 / 变更位置 / 变更保管人
- **看板**：4 段聚合（类型分布 / 状态分布 / 保管人 Top 10 / 闲置时长 Top 10）
- **导出**：CSV / XLSX，按当前筛选透传
- **附件管理**：照片 / 发票，CLI + Web 都可上传
- **服务生命周期管理**：`serve start / stop / status / restart / logs / doctor`

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.12+ · FastAPI · SQLModel · SQLite · Typer · Alembic · openpyxl |
| 前端 | React 19 · Vite · TanStack Router · TanStack Table · TanStack Query · RHF + Zod · Tailwind v4 · shadcn/ui · Recharts |
| 测试 | pytest（unit / api / cli 三层）· vitest（unit / hooks / components）· playwright（e2e CI） |
| 工具链 | uv · pnpm · ruff · openapi-typescript / openapi-fetch |

## 架构

```
Web GUI (React) ──HTTP──┐
                        ├──► FastAPI ──► Service 层（唯一事实）──► Repository / SQLModel / FS
CLI (Typer) ────import──┘
```

CLI 直接 `from asset_hub.services import ...` 调用 service 层，**不**通过 HTTP 调自己的 API。

## 快速开始

```bash
# 前置：uv / pnpm / Python 3.12+ / Node 20+
uv sync
pnpm --dir frontend install
cp .env.example .env
uv run alembic upgrade head

# dev 模式（前后端并发，Vite 代理 /api → :8000）
uv run asset-hub serve start --mode dev
# 访问 http://127.0.0.1:5173

# prod 模式（自动 build 前端 + 单端口 :8000）
uv run asset-hub serve start --mode prod
# 访问 http://127.0.0.1:8000
```

## CLI 示例（v1.0 GA 命令）

```bash
# 定义类型
uv run asset-hub type define --from examples/types/laptop.json --json

# 登记资产（含照片）
uv run asset-hub asset register \
    --name "ThinkPad X1 Carbon" \
    --type-id <uuid> --sn "PF-1234" \
    --custom '{"brand":"Lenovo","ram_gb":16}' --json
uv run asset-hub attachment upload <asset_id> --path photo.jpg --json

# 状态流转
uv run asset-hub asset transition checkout <asset_id> --kind internal --to-holder "张三" --to-location "北京办公室"
uv run asset-hub asset transition return <asset_id> --to-holder "李四" --to-location "上海仓库"

# 列表 + 筛选
uv run asset-hub asset list --status IDLE --json

# 看板
uv run asset-hub stats --json

# 导出
uv run asset-hub export --format xlsx --status IDLE --output /tmp/idle.xlsx

# 诊断环境
uv run asset-hub serve doctor --json
```

## 路线图

| 里程碑 | 目标 | 状态 |
|---|---|---|
| **M1 · 骨架** | service/repo 抽象、CLI CRUD、FastAPI 端点、前端脚手架 | ✅ 已完成 |
| **M2 · 核心流程 + 视觉收尾** | checkout/return/history、附件、Web 列表 + 详情 + 动态表单、视觉打磨 | ✅ 已完成 |
| **M3a · 状态机基建** | 5 态 + 10 transition + StateTransitionRecord + 7 dialog | ✅ 已完成 |
| **M3b · 看板 + /api/stats** | 4 张图表 + ChartTokenProvider | ✅ 已完成 |
| **M3c · CSV/XLSX 导出** | /api/export + ExportButton + 5 态色条件格式 | ✅ 已完成 |
| **M3d · timeline 视觉重构** | Group rail + 月份分段 + 派出类型染色 + 超长派发预警 | ✅ 已完成 |
| **M3e · v1.0 GA 收口** | SKILL.md + envelope 统一 + serve doctor + Windows 部署 + e2e CI | ✅ 已完成 |
| **M4 · UI 打磨** | 配色 / 间距 / 动效达 frontend-design 审美标准；A3 dialog 合并；§S/§U/§W | ⏳ 规划中 |
| **M5 · People 实体化** | holder/location 实体化 + 重名/改名管理 | ⏳ 规划中 |

## 文档

- AI Agent 入口：[SKILL.md](./SKILL.md)（含 5 态 + 10 transition + envelope + 命令速查 + 任务流）
- 部署指南：[docs/deployment.md](./docs/deployment.md)
- v1.0 升级指南：[docs/superpowers/release-notes-v1.0.md](./docs/superpowers/release-notes-v1.0.md)
- 设计文档：[docs/superpowers/specs/](./docs/superpowers/specs/)
```

### Task 26: 写 docs/superpowers/release-notes-v1.0.md

**Files:**
- Create: `docs/superpowers/release-notes-v1.0.md`

- [ ] **Step 26.1: 写完整 release notes**

按 spec §4.4 的草稿落地。**实施期填实际 m3e merge commit hash**：

```markdown
# v1.0 GA 发版升级指南

## 概览（v1.0 = M2d 之后所有里程碑）

| 里程碑 | 主线交付 | merge commit |
|---|---|---|
| M3a | 5 态状态机 + 10 transition + StateTransitionRecord 重构 + CLI 9 子命令 + 7 dialog | a360e04 + bc084e5 |
| M3b | /api/stats + 看板 4 图表 + ChartTokenProvider | c21ae55 + 98052dc |
| M3c | /api/export CSV/XLSX + ExportButton | a55beec + 5c5bab0 |
| M3d | timeline Group rail + 月份分段 + 派出类型染色 + 超长派发预警 + simplify §7 | 5320804 |
| M3e | SKILL.md + envelope 统一 + serve doctor + 5 态文案对齐 + Windows 部署文档 + playwright e2e CI | <m3e-merge>（实施期回填） |

## Breaking changes

- HTTP API：废 `POST /api/assets/{id}/checkout` / `/return` / 散点 PATCH status；统一 `POST /api/assets/{id}/transitions { kind, ... }`（M3a）
- 数据库：drop `checkout_records` 表 + drop `Asset.current_checkout_id`；add `state_transition_records` + `Asset.status` enum 加 DISPOSED（M3a migration，单向不可回数据）
- CLI envelope：error 字段从 plain string 升级为 `{code, message}` 结构化（M3e）
- 5 态文案：在用→使用中、闲置→闲置中（M3e；前端 + 导出列文案，**不影响 API 枚举值**）

## 升级前

1. 备份数据库：`cp data/asset_hub.db data/asset_hub.db.$(date +%Y%m%d).bak`
2. 备份附件：`tar czf attachments-$(date +%Y%m%d).tgz data/attachments/`
3. 如有自定义 dev 脚本，确认调用 `uv run asset-hub serve start --mode dev`

## 升级

```bash
git pull
# 或：git fetch && git checkout v1.0.0
uv sync
pnpm --dir frontend install
uv run alembic upgrade head        # M3a migration 含 drop checkout_records — 单向不可回数据
uv run asset-hub serve doctor      # 验证升级后状态
uv run asset-hub serve restart --mode prod
```

## 升级后验证

### 1. 自动化测试

```bash
uv run pytest                   # 期望全绿
pnpm --dir frontend test --run  # 期望全绿
uv run ruff check .             # 期望 clean
pnpm --dir frontend lint        # 期望 clean
```

### 2. CI e2e workflow

PR 与 main push 都会触发 GitHub Actions e2e workflow（ubuntu-latest，4-7 分钟）。v1.0.0 tag push 后也会跑——观察是否绿。

### 3. Windows 烟测 checklist

- [ ] `register / list / get`
- [ ] `transition checkout / return` 闭环
- [ ] `transition send-to-maintenance / recover` 维修闭环
- [ ] `transition retire / reinstate` 退役复活闭环
- [ ] `transition retire → dispose`（终态锁，输 "处置" 解锁）
- [ ] `export csv` / `export xlsx` 含 5 态色条件格式
- [ ] dashboard `/dashboard` 加载 4 张图，状态分布显示新文案
- [ ] `serve doctor` 全 ✓
- [ ] `serve start / stop / status / restart / logs`

## 已知 gap（推 v1.1+）

- Linux 真机烟测（v1 用户场景就是 Windows 单机；v1.1 补 Linux）
- Lighthouse a11y 全站扫描 + 修复（v1 单用户作者自用，可预见时间内无视障用户；v1.1 系统化补）
- M2d 残：多代日志轮转 / `serve build` 独立子命令 / `--workers` flag（触发条件出现后）
- M3 残：A3 dialog 合并 / §S Toggle 视觉态 / §T `IllegalTransitionError.detail` 结构化 payload / §U KIND_META 跨文件合一 / §V `Settings.mode` 字段 / §W types/assets 风格统一 / §X dispose-dialog RHF / §Y `findOpenCheckout` 抽工具 / §Z `formatRelative` 小时级粒度
- envelope error 结构化升级：`{code, message}` → `{code, message, hint, fields_missing?, ...}`（v1.1 与 §T 同 PR）
- `--help --json` 双模 / `--fields` 字段掩码（v1.1，agent-native 检查清单候选项）
- SKILL.md description trigger eval（v1.1 用 skill-creator 的 description optimization loop 跑 5 iteration）

## 回滚

```bash
git checkout <pre-v1.0-commit>
cp data/asset_hub.db.$(date +%Y%m%d).bak data/asset_hub.db   # 用备份还原（alembic downgrade 不能恢复 drop 的 checkout_records 数据）
uv run asset-hub serve restart --mode prod
```
```

- [ ] **Step 26.2: commit Phase 3**

```bash
git add SKILL.md references/ docs/deployment.md README.md docs/superpowers/release-notes-v1.0.md
git commit -m "$(cat <<'EOF'
docs: M3e 文档全集 (SKILL.md + references/ + deployment.md + README + release-notes-v1.0)

仓库根 SKILL.md (agent-native frontmatter + 5 态/10 transition/envelope 速查/命令速查/Gotchas) 主体 ≤ 200 行；progressive disclosure 拆 references/ 4 文件 (transitions/envelope/workflows/deploy)。
references/deploy.md 走 pointer + Agent 速查精简版形态，避与 docs/deployment.md 双源漂移。
docs/deployment.md 给人类作者看（Windows 单机首选 + 配置 + 备份 + 故障排查）。
README.md 全量重写：路线图 M1-M3e ✅；CLI 示例从 2 条扩到 7 条；技术栈补 alembic / openpyxl / playwright / TanStack 全家桶；删 ./scripts/dev.sh。
release-notes-v1.0.md 集成 M2d 之后所有里程碑变更 + Breaking changes + 升级前/升级/验证/Windows 烟测/已知 gap/回滚。
EOF
)"
```

---

## Phase 4 · playwright e2e + GitHub Actions

### Task 27: 安装 @playwright/test + 写 playwright.config.ts

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/playwright.config.ts`

- [ ] **Step 27.1: 安装依赖**

```bash
pnpm --dir frontend add -D @playwright/test
```

- [ ] **Step 27.2: 创建 playwright.config.ts**

```ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-teardown.ts",
  use: {
    baseURL: "http://127.0.0.1:8000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "uv run asset-hub serve start --mode prod --json",
    url: "http://127.0.0.1:8000/api/healthz",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
```

- [ ] **Step 27.3: 加 npm script**

修改 `frontend/package.json` 加入：

```json
{
  "scripts": {
    "e2e": "playwright test",
    "e2e:debug": "playwright test --debug"
  }
}
```

- [ ] **Step 27.4: 安装 playwright 浏览器**

```bash
pnpm --dir frontend exec playwright install chromium
```

### Task 28: 写 global-setup / teardown / fixtures

**Files:**
- Create: `frontend/e2e/global-setup.ts`
- Create: `frontend/e2e/global-teardown.ts`
- Create: `frontend/e2e/fixtures/laptop.json`
- Create: `frontend/e2e/fixtures/photo-sample.png`

- [ ] **Step 28.1: 写 global-setup.ts**

```ts
import { execSync } from "node:child_process";

export default async function globalSetup() {
  const dataDir = process.env.ASSET_HUB_DATA_DIR;
  if (!dataDir) {
    throw new Error("ASSET_HUB_DATA_DIR must be set for e2e (typically a tmp dir)");
  }

  console.log(`[e2e setup] using ASSET_HUB_DATA_DIR=${dataDir}`);

  // 1. alembic upgrade
  execSync("uv run alembic upgrade head", {
    stdio: "inherit",
    env: process.env,
    cwd: "..", // playwright 在 frontend/ 跑，但 alembic 在仓库根
  });

  // 2. seed laptop type
  const result = execSync(
    "uv run asset-hub type define --from frontend/e2e/fixtures/laptop.json --json",
    { env: process.env, cwd: ".." },
  ).toString();
  const parsed = JSON.parse(result);
  if (!parsed.success) {
    throw new Error(`seed type failed: ${JSON.stringify(parsed.error)}`);
  }
  process.env.E2E_LAPTOP_TYPE_ID = parsed.data.id;
  console.log(`[e2e setup] seeded laptop type id=${parsed.data.id}`);
}
```

- [ ] **Step 28.2: 写 global-teardown.ts**

```ts
import { rmSync } from "node:fs";

export default async function globalTeardown() {
  const dataDir = process.env.ASSET_HUB_DATA_DIR;
  if (dataDir && process.env.CI) {
    try {
      rmSync(dataDir, { recursive: true, force: true });
      console.log(`[e2e teardown] cleaned ${dataDir}`);
    } catch (e) {
      console.warn(`[e2e teardown] failed to rm ${dataDir}: ${e}`);
    }
  }
}
```

- [ ] **Step 28.3: 写 fixtures/laptop.json**

```json
{
  "name": "Laptop",
  "icon": "laptop",
  "custom_fields": [
    { "key": "brand", "label": "品牌", "type": "string", "required": true },
    { "key": "os", "label": "操作系统", "type": "enum", "options": ["Windows", "macOS", "Linux"], "required": false },
    { "key": "ram_gb", "label": "内存 (GB)", "type": "int", "min": 4, "max": 256, "required": false }
  ]
}
```

- [ ] **Step 28.4: 创建 photo-sample.png**

用一个 1x1 透明 PNG（任何小图都行）：

```bash
python -c "
import base64
data = base64.b64decode(b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
with open('frontend/e2e/fixtures/photo-sample.png', 'wb') as f:
    f.write(data)
"
```

### Task 29: 写 helpers (register-asset / assert-status)

**Files:**
- Create: `frontend/e2e/helpers/register-asset.ts`
- Create: `frontend/e2e/helpers/assert-status.ts`

- [ ] **Step 29.1: 写 register-asset.ts**

```ts
import { execSync } from "node:child_process";

export interface RegisteredAsset {
  id: string;
  name: string;
  status: string;
}

/**
 * 通过 CLI 直接登记一台资产，返回 id。
 * 比走 UI 表单稳定（UI 表单后续会变，CLI 契约稳定）。
 */
export function registerAsset(opts: {
  name: string;
  sn: string;
  custom?: Record<string, unknown>;
}): RegisteredAsset {
  const typeId = process.env.E2E_LAPTOP_TYPE_ID;
  if (!typeId) throw new Error("E2E_LAPTOP_TYPE_ID not set (global-setup ran?)");

  const customJson = JSON.stringify(opts.custom ?? { brand: "Lenovo", ram_gb: 16 });
  const cmd = [
    "uv run asset-hub asset register",
    `--name ${JSON.stringify(opts.name)}`,
    `--type-id ${typeId}`,
    `--sn ${JSON.stringify(opts.sn)}`,
    `--custom ${JSON.stringify(customJson)}`,
    "--json",
  ].join(" ");

  const out = execSync(cmd, { env: process.env, cwd: ".." }).toString();
  const parsed = JSON.parse(out);
  if (!parsed.success) throw new Error(`register failed: ${JSON.stringify(parsed.error)}`);
  return parsed.data;
}
```

- [ ] **Step 29.2: 写 assert-status.ts**

```ts
import { expect, type Page } from "@playwright/test";

const STATUS_LABELS: Record<string, string> = {
  IDLE: "闲置中",
  IN_USE: "使用中",
  MAINTENANCE: "维修中",
  RETIRED: "已退役",
  DISPOSED: "已处置",
};

/**
 * 在资产详情页或列表行验证 status chip 文案与新 5 态对齐。
 * 不强匹配 chip 颜色（视觉测试归 vitest component 层）。
 */
export async function assertStatusChip(page: Page, status: keyof typeof STATUS_LABELS) {
  const expected = STATUS_LABELS[status];
  await expect(page.getByText(expected, { exact: true }).first()).toBeVisible();
}
```

### Task 30: 写 e2e spec 1 - register-and-list

**Files:**
- Create: `frontend/e2e/specs/01-register-and-list.spec.ts`

- [ ] **Step 30.1: 写 spec**

```ts
import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";
import { assertStatusChip } from "../helpers/assert-status";

test.describe("01 · register-and-list", () => {
  test("CLI 登记资产 + UI 列表可见", async ({ page }) => {
    const asset = registerAsset({ name: "X1 测试机 01", sn: "PF-E2E-01" });
    expect(asset.id).toBeTruthy();
    expect(asset.status).toBe("IDLE");

    await page.goto("/");
    await expect(page.getByText("X1 测试机 01")).toBeVisible();
    await page.getByText("X1 测试机 01").click();

    // 详情页打开
    await expect(page.getByText("PF-E2E-01")).toBeVisible();
    await assertStatusChip(page, "IDLE");
  });
});
```

### Task 31: 写 e2e spec 2 - checkout-return-internal

**Files:**
- Create: `frontend/e2e/specs/02-checkout-return-internal.spec.ts`

- [ ] **Step 31.1: 写 spec**

```ts
import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";
import { assertStatusChip } from "../helpers/assert-status";

test.describe("02 · checkout-return-internal", () => {
  test("CHECKOUT_INTERNAL → RETURN 闭环", async ({ page }) => {
    const asset = registerAsset({ name: "X1 测试机 02", sn: "PF-E2E-02" });
    await page.goto(`/assets/${asset.id}`);
    await assertStatusChip(page, "IDLE");

    // 点 "派发" 按钮（CHECKOUT dialog）
    await page.getByRole("button", { name: /派发/i }).click();
    await page.getByLabel(/保管人/i).fill("张三");
    await page.getByLabel(/位置/i).fill("北京办公室");
    await page.getByRole("button", { name: /确定|提交|确认/i }).click();

    // status 变 IN_USE
    await assertStatusChip(page, "IN_USE");

    // 归还
    await page.getByRole("button", { name: /归还/i }).click();
    await page.getByLabel(/接收人|保管人/i).fill("李四");
    await page.getByLabel(/位置/i).fill("上海仓库");
    await page.getByRole("button", { name: /确定|提交|确认/i }).click();

    await assertStatusChip(page, "IDLE");

    // timeline 应有 CHECKOUT_INTERNAL + RETURN 两条
    await expect(page.getByText(/派发/i)).toBeVisible();
    await expect(page.getByText(/归还/i)).toBeVisible();
  });
});
```

实施时 verify dialog button label / form field label 实际值，按需调整 selector。

### Task 32: 写 e2e spec 3 - maintenance-cycle

**Files:**
- Create: `frontend/e2e/specs/03-maintenance-cycle.spec.ts`

- [ ] **Step 32.1: 写 spec**

```ts
import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";
import { assertStatusChip } from "../helpers/assert-status";

test.describe("03 · maintenance-cycle", () => {
  test("SEND_TO_MAINTENANCE → RECOVER_FROM_MAINTENANCE", async ({ page }) => {
    const asset = registerAsset({ name: "X1 测试机 03", sn: "PF-E2E-03" });
    await page.goto(`/assets/${asset.id}`);

    // 送修
    await page.getByRole("button", { name: /送修/i }).click();
    await page.getByRole("button", { name: /确定|提交|确认/i }).click();
    await assertStatusChip(page, "MAINTENANCE");

    // 维修完成
    await page.getByRole("button", { name: /维修完成|修好|完成/i }).click();
    await page.getByRole("button", { name: /确定|提交|确认/i }).click();
    await assertStatusChip(page, "IDLE");
  });
});
```

### Task 33: 写 e2e spec 4 - retire-reinstate

**Files:**
- Create: `frontend/e2e/specs/04-retire-reinstate.spec.ts`

- [ ] **Step 33.1: 写 spec**

```ts
import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";
import { assertStatusChip } from "../helpers/assert-status";

test.describe("04 · retire-reinstate", () => {
  test("RETIRE → REINSTATE（验可复活）", async ({ page }) => {
    const asset = registerAsset({ name: "X1 测试机 04", sn: "PF-E2E-04" });
    await page.goto(`/assets/${asset.id}`);

    // 退役（AlertDialog）
    await page.getByRole("button", { name: /退役/i }).click();
    await page.getByRole("button", { name: /确定|确认/i }).click();
    await assertStatusChip(page, "RETIRED");

    // 默认列表不见
    await page.goto("/");
    await expect(page.getByText("X1 测试机 04")).not.toBeVisible();

    // 切回详情，重新启用
    await page.goto(`/assets/${asset.id}`);
    await page.getByRole("button", { name: /重新启用|启用/i }).click();
    await page.getByRole("button", { name: /确定|提交|确认/i }).click();
    await assertStatusChip(page, "IDLE");
  });
});
```

### Task 34: 写 e2e spec 5 - retire-then-dispose

**Files:**
- Create: `frontend/e2e/specs/05-retire-then-dispose.spec.ts`

- [ ] **Step 34.1: 写 spec**

```ts
import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";
import { assertStatusChip } from "../helpers/assert-status";

test.describe("05 · retire-then-dispose", () => {
  test("RETIRE → DISPOSE（终态锁）", async ({ page }) => {
    const asset = registerAsset({ name: "X1 测试机 05", sn: "PF-E2E-05" });
    await page.goto(`/assets/${asset.id}`);

    // 必须先 RETIRE
    await page.getByRole("button", { name: /退役/i }).click();
    await page.getByRole("button", { name: /确定|确认/i }).click();
    await assertStatusChip(page, "RETIRED");

    // 处置：输 "处置" 解锁
    await page.getByRole("button", { name: /处置/i }).click();
    const confirmInput = page.getByLabel(/输入.*处置.*解锁|确认输入/i);
    // 不输 / 输错 → 提交按钮 disabled
    await confirmInput.fill("处置");
    await page.getByRole("button", { name: /确定|确认/i }).click();
    await assertStatusChip(page, "DISPOSED");

    // 验证终态：列表不见 + include-disposed 才见
    await page.goto("/");
    await expect(page.getByText("X1 测试机 05")).not.toBeVisible();
  });
});
```

### Task 35: 写 e2e spec 6 - export-csv-xlsx

**Files:**
- Create: `frontend/e2e/specs/06-export-csv-xlsx.spec.ts`

- [ ] **Step 35.1: 写 spec**

```ts
import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";

test.describe("06 · export-csv-xlsx", () => {
  test("seed 3 asset → 列表点 export CSV + XLSX", async ({ page }) => {
    registerAsset({ name: "Export A", sn: "PF-EXP-A" });
    registerAsset({ name: "Export B", sn: "PF-EXP-B" });
    registerAsset({ name: "Export C", sn: "PF-EXP-C" });

    await page.goto("/");

    // 点 export csv
    const [downloadCsv] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: /导出.*CSV/i }).click(),
    ]);
    expect(downloadCsv.suggestedFilename()).toMatch(/\.csv$/);

    // 点 export xlsx
    const [downloadXlsx] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: /导出.*XLSX/i }).click(),
    ]);
    expect(downloadXlsx.suggestedFilename()).toMatch(/\.xlsx$/);
  });
});
```

实施时 verify export 按钮 label / 下拉菜单形态（grep ExportButton.tsx），按需调整。

### Task 36: 写 e2e spec 7 - dashboard-loads

**Files:**
- Create: `frontend/e2e/specs/07-dashboard-loads.spec.ts`

- [ ] **Step 36.1: 写 spec**

```ts
import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";

test.describe("07 · dashboard-loads", () => {
  test("/dashboard 4 张图都渲染", async ({ page }) => {
    // seed 至少 1 个资产，避免空盘面
    registerAsset({ name: "Dash A", sn: "PF-DASH-A" });

    await page.goto("/dashboard");

    // 4 张图标题 / 容器
    await expect(page.getByText(/类型分布/i)).toBeVisible();
    await expect(page.getByText(/状态分布/i)).toBeVisible();
    await expect(page.getByText(/保管人/i)).toBeVisible();
    await expect(page.getByText(/闲置时长|闲置 Top/i)).toBeVisible();

    // 状态分布应显示新文案
    await expect(page.getByText(/闲置中/i)).toBeVisible();
  });
});
```

### Task 37: 写 GitHub Actions e2e workflow

**Files:**
- Create: `.github/workflows/e2e.yml`

- [ ] **Step 37.1: 写 workflow**

```yaml
name: e2e
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          version: "0.5.x"
          enable-cache: true
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
          cache-dependency-path: frontend/pnpm-lock.yaml
      - run: uv sync
      - run: pnpm --dir frontend install --frozen-lockfile
      - run: pnpm --dir frontend exec playwright install --with-deps chromium
      # alembic upgrade + seed 由 frontend/e2e/global-setup.ts 统一处理
      - name: Run e2e
        run: pnpm --dir frontend exec playwright test
        env:
          ASSET_HUB_DATA_DIR: ${{ runner.temp }}/asset-hub-e2e-${{ github.run_id }}
      - if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-trace
          path: frontend/playwright-report/
          retention-days: 7
```

- [ ] **Step 37.2: 本地跑一遍 e2e 确认全绿**

```bash
ASSET_HUB_DATA_DIR=$(mktemp -d) pnpm --dir frontend exec playwright test
```

预期：7 spec 全 PASS。

如有 fail：playwright 会在 `frontend/playwright-report/` 留 trace；用 `pnpm --dir frontend exec playwright show-report` 查看。

- [ ] **Step 37.3: commit Phase 4**

```bash
git add frontend/package.json frontend/playwright.config.ts frontend/e2e/ \
        frontend/pnpm-lock.yaml \
        .github/workflows/e2e.yml
git commit -m "$(cat <<'EOF'
test(e2e): playwright 7 spec + GitHub Actions e2e workflow

@playwright/test 安装 + frontend/e2e/ 目录 + global-setup (alembic + seed laptop type) + global-teardown (rm tmpdir)。
helpers/register-asset (CLI 直登记) + helpers/assert-status (5 态新文案对齐)。
7 spec 覆盖 7/10 transition kind: register-and-list / checkout-return-internal / maintenance-cycle / retire-reinstate / retire-then-dispose / export-csv-xlsx / dashboard-loads。
webServer 走 serve start --mode prod，顺手覆盖 Phase 1 envelope/serve 改造。
GitHub Actions ubuntu-latest runner，PR + push to main 触发，4-7 min；trace artifact 上传 on failure。
EOF
)"
```

---

## Phase 5 · 收尾

### Task 38: 更新 followup 文档 + 推 PR

**Files:**
- Modify: `docs/superpowers/followup-allocation.md`
- Modify: `docs/superpowers/simplify-followups.md`

- [ ] **Step 38.1: followup-allocation.md 摘要表 M3e 行回填**

把 §M3e 行的 "⏳ 待启动" 改 "✅ 已完成（2026-05-XX，merge `<m3e-merge>`）"（提交时填实际日期，merge commit 在 PR 合并后再补）。

- [ ] **Step 38.2: simplify-followups.md 加 §9 M3e 范围**

参考 §7 / §8 形态，加：

```markdown
## §9 M3e 范围（2026-05-XX）

M3e 子里程碑（v1.0 GA 收口）单 PR 完成（feat/m3e-ga，4 phase commit）：

- Phase 1 envelope 升级 + serve doctor
- Phase 2 5 态文案对齐 + 薄弱点补测
- Phase 3 文档全集（SKILL.md + references/ + deployment.md + README + release-notes-v1.0）
- Phase 4 playwright e2e 7 spec + GitHub Actions

### 闭环条目

| 条目 | 状态 | commit ref |
|---|---|---|
| K1 envelope 统一（HIGH 优先级 follow-up） | ✅ 已闭环 | M3e Phase 1 |
| M2d serve doctor known gap | ✅ 已闭环 | M3e Phase 1 |
| 5 态文案 3 字对齐（IDLE/IN_USE 改） | ✅ 已闭环 | M3e Phase 2 |
| 5 态 filter include_retired/disposed 测试薄弱点 | ✅ 已闭环 | M3e Phase 2 |
| SKILL.md 起草 + references/ 4 文件 | ✅ 已闭环 | M3e Phase 3 |
| Windows 部署文档 + README 全量重写 + release-notes-v1.0 | ✅ 已闭环 | M3e Phase 3 |
| playwright e2e CI 7 spec + GitHub Actions | ✅ 已闭环 | M3e Phase 4 |

### 推 v1.1 的 follow-up

- envelope error 结构化升级 `{code, message, hint, fields_missing?}`（与 simplify §T 同 PR）
- `--help --json` 双模 / `--fields` 字段掩码（agent-native checklist 候选）
- SKILL.md description trigger eval（用 skill-creator description optimization loop 跑 5 iteration）
- references/ staleness 检查 helper（与 spec / 代码同步）
```

- [ ] **Step 38.3: commit followup 回填**

```bash
git add docs/superpowers/followup-allocation.md docs/superpowers/simplify-followups.md
git commit -m "docs(followup): M3e 落地后文档回填"
```

- [ ] **Step 38.4: 跑全套测试（最后一次兜底）**

```bash
uv run pytest tests/ 2>&1 | tail -10
pnpm --dir frontend test --run 2>&1 | tail -10
uv run ruff check .
pnpm --dir frontend lint
pnpm --dir frontend tsc -b
```

预期：全 PASS / clean / 0 错。

- [ ] **Step 38.5: 本地 e2e 兜底**

```bash
ASSET_HUB_DATA_DIR=$(mktemp -d) pnpm --dir frontend exec playwright test
```

预期：7 spec 全 PASS。

- [ ] **Step 38.6: push + 开 PR**

```bash
git push -u origin feat/m3e-ga
gh pr create --title "M3e: SKILL.md + 部署 + 测试基建 (v1.0 GA 收口)" --body "$(cat <<'EOF'
## Summary
- Phase 1 envelope 统一 (主 CLI + serve 单一 contract `{code, message}`) + serve doctor 7 检查项
- Phase 2 5 态文案 3 字对齐 (闲置中 / 使用中) + 5 态 filter 9 case 薄弱点补测
- Phase 3 SKILL.md (agent-native + references/) + docs/deployment.md + README 全量重写 + release-notes-v1.0
- Phase 4 playwright e2e 7 spec + GitHub Actions ubuntu-latest

零数据库 schema 改动；零 HTTP API 契约破坏；零前端 generated schema 改动。

详见 [`docs/superpowers/specs/2026-05-09-m3e-skill-and-deploy-design.md`](./docs/superpowers/specs/2026-05-09-m3e-skill-and-deploy-design.md)。

## Test plan
- [ ] `uv run pytest` 全绿（含新 envelope/doctor 测试 + 5 态 filter 8 case）
- [ ] `pnpm --dir frontend test --run` 全绿（含 assets-filters Toggle URL sync）
- [ ] `uv run ruff check .` clean
- [ ] `pnpm --dir frontend lint` clean
- [ ] `pnpm --dir frontend tsc -b` 0 error
- [ ] CI e2e workflow 在 PR 触发后跑通（7 spec 全绿）
- [ ] Windows 烟测（合并主干后用户人工执行 release-notes-v1.0.md 内 checklist）
- [ ] `serve doctor` 在干净环境全 ✓
- [ ] `serve start --mode prod` → `error.code == "serve.already_running"` 重复启动场景验证
EOF
)"
```

---

## 自审清单（spec 覆盖对账）

逐节复核 spec 是否被本计划覆盖：

| spec 段 | 任务 |
|---|---|
| §2.1 envelope error inventory | T2 + T3 (`_DOMAIN_ERROR_CODES` dict 实现) |
| §2.2 envelope.py 改动 | T2 (test) + T3 (实现) |
| §2.3 serve/cmd.py 重写 | T7 |
| §2.4 serve doctor 7 检查项 | T10 (实现 + test) + T11 (CLI 注册 + test) |
| §2.5 测试改动面 12-18 处 | T4 |
| §2.6 Phase 1 验收 | T2/3/4/5/6/7/8/9/10/11 全部覆盖 |
| §3.1 5 态文案修订（IN_USE → 使用中、IDLE → 闲置中）| T12 (前端 SoT) + T15 (后端 SoT) + T13/T14 (字面量替换) |
| §3.2 薄弱点补测 6 unit + 2 api + 1 frontend | T16 (unit) + T17 (api + frontend) |
| §3.3 Phase 2 commit 切分 | T18 |
| §4.1 SKILL.md frontmatter + 主体 ≤200 行 | T19 |
| §4.1.3 references/ 4 文件 + "何时读" 指引 | T20/T21/T22/T23 |
| §4.2 docs/deployment.md | T24 |
| §4.3 README 全量重写 | T25 |
| §4.4 release-notes-v1.0.md | T26 |
| §5.1 e2e 7 场景集 | T30-T36 |
| §5.2 playwright 配置 | T27 |
| §5.3 seed/cleanup global-setup/teardown | T28 |
| §5.4 helpers / fixtures 组织 | T28 + T29 |
| §5.5 GitHub Actions workflow | T37 |
| §7.4 followup-allocation + simplify §9 回填 | T38 |
| §6.4 phase 内 commit 切分 | 各 phase 末尾 commit task |
| §6.5 v1.0 tag 不进 PR/plan | （明确不在本 plan，由用户 PR 合并后人工 tag）|

**v1.1 follow-up 在 release-notes-v1.0.md "已知 gap" 章节登记**（T26 已包含）。

---

## 执行选择

**Plan complete and saved to `docs/superpowers/plans/2026-05-09-m3e-skill-and-deploy.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - 每 task 派一个 fresh subagent，review 间隔短，迭代快

**2. Inline Execution** - 当前会话内 batch 执行，checkpoint 处 review

**Which approach?**
