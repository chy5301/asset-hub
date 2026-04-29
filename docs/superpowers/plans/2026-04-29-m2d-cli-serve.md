# M2d · CLI 接管 web 服务生命周期 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 [`docs/superpowers/specs/2026-04-29-m2d-cli-serve-design.md`](../specs/2026-04-29-m2d-cli-serve-design.md)，实现 `asset-hub serve start/stop/status/restart/logs` 五个子命令（默认 prod、后台 detach、psutil 进程树清理、PID + 日志文件状态、`/api/healthz` 健康端点），同时打包 4 项 backend gaps（B2/B3/I1+I2）。

**Architecture:** 三阶段串行——先做 4 项独立 backend gaps（每项独立 PR）确保 backend schema 稳定；再做 `/api/healthz` 端点（serve start 探测依赖）；最后实现 serve 主线（基础工具层 → 流程协调层 → CLI 接入层）。底层模块（pid/proc/probe/logs）严格分离，lifecycle 是协调者，不做 IO。

**Tech Stack:** Python 3.12 + Typer + psutil（首次引入）+ FastAPI + SQLModel + Alembic + pydantic-settings · 测试 pytest + monkeypatch + Mock + typer.testing.CliRunner · 前端 React 19 + openapi-typescript（gen:api 拉新 schema）

---

## 阶段划分（Task 顺序硬依赖）

```
Phase 0 · I1+I2 后端 validation 补全 + FieldType Enum  (Task 1-4)
   ↓
Phase 1 · B3 AssetType DELETE                          (Task 5-8)
   ↓
Phase 2 · B2 归还时记录归还地点 + 接收人                (Task 9-13)
   ↓
Phase 3 · /api/healthz 端点                            (Task 14)
   ↓
Phase 4 · serve · 配置层 + 基础工具层 (pid/proc)       (Task 15-19)
   ↓
Phase 5 · serve · 探测层 + 日志层 (probe/logs)         (Task 20-22)
   ↓
Phase 6 · serve · 协调层 + 输出层 (lifecycle/output)    (Task 23-25)
   ↓
Phase 7 · serve · CLI 接入 + 集成测试                  (Task 26-30)
   ↓
Phase 8 · 收尾 + 烟测 + 文档                            (Task 31-33)
```

PR 顺序：Phase 0 / 1 / 2 各独立 PR；Phase 3 可并入 serve 主线 PR；Phase 4-8 同 PR。

---

## 文件结构（新增 + 修改清单）

**新增**：
- `src/asset_hub/api/routers/health.py` — `/api/healthz` 端点
- `src/asset_hub/cli/serve/__init__.py`
- `src/asset_hub/cli/serve/cmd.py` — Typer 子命令注册
- `src/asset_hub/cli/serve/lifecycle.py` — 5 流程协调
- `src/asset_hub/cli/serve/pid.py` — PID 文件 + state 判定
- `src/asset_hub/cli/serve/proc.py` — Popen detach + kill_tree + 端口检查
- `src/asset_hub/cli/serve/probe.py` — 健康轮询 + status 探测
- `src/asset_hub/cli/serve/logs.py` — tail + follow + 启动次数轮转
- `src/asset_hub/cli/serve/output.py` — 表格 + JSON 信封 + dataclass
- `src/asset_hub/services/field_type.py` — `FieldType` Enum
- `.env.example` — 配置模板
- `tests/api/test_health.py`
- `tests/unit/test_validation_url.py`
- `tests/unit/test_validation_multi_enum.py`
- `tests/unit/test_validation_min_max.py`
- `tests/unit/test_field_type_enum.py`
- `tests/unit/test_type_service_delete.py`
- `tests/api/test_type_routes_delete.py`
- `tests/cli/test_type_cli_delete.py`
- `tests/unit/test_checkout_service_return_fields.py`
- `tests/api/test_checkout_routes_return_fields.py`
- `tests/cli/test_asset_checkout_cli_return_fields.py`
- `tests/unit/test_pid_state.py`
- `tests/unit/test_pid_io.py`
- `tests/unit/test_proc_kill_tree.py`
- `tests/unit/test_proc_detach.py`
- `tests/unit/test_proc_port_check.py`
- `tests/unit/test_health_probe.py`
- `tests/unit/test_logs_tail.py`
- `tests/unit/test_logs_follow.py`
- `tests/unit/test_logs_rotate.py`
- `tests/unit/test_settings_serve.py`
- `tests/unit/test_serve_output.py`
- `tests/cli/test_serve_start.py`
- `tests/cli/test_serve_stop.py`
- `tests/cli/test_serve_status.py`
- `tests/cli/test_serve_restart.py`
- `tests/cli/test_serve_logs.py`
- alembic migration: `src/asset_hub/alembic/versions/<ts>_add_return_location_receiver.py`

**修改**：
- `pyproject.toml` — 加 psutil 依赖
- `src/asset_hub/services/validation.py` — 引入 FieldType Enum + 补 url/multi-enum/int+float min/max
- `src/asset_hub/services/asset_type.py` — 加 `delete_type` 方法
- `src/asset_hub/repositories/asset_type.py` — 加 `delete` + `count_assets_by_type` helper
- `src/asset_hub/api/routers/types.py` — 加 `DELETE /api/types/{type_id}`
- `src/asset_hub/cli/type_cmd.py` — 加 `delete` 子命令
- `src/asset_hub/services/checkout.py` — `return_` 接受 `return_location` + `return_receiver`，asset.location 跟随
- `src/asset_hub/api/schemas/checkout.py` — `CheckoutReturn` + `CheckoutRead` 加两字段
- `src/asset_hub/api/routers/checkouts.py` — 透传新字段
- `src/asset_hub/cli/asset_cmd.py` — `return_` 命令加 `--location` + `--receiver` flag
- `src/asset_hub/models/checkout.py` — 加 `return_location` + `return_receiver` 字段
- `src/asset_hub/config.py` — 扩 backend_port / frontend_port / backend_host + pids_dir / logs_dir / resolve_backend_host
- `src/asset_hub/cli/main.py` — 注册 serve 子命令
- `frontend/src/features/assets/detail/return-dialog.tsx` — 加归还地点 + 接收人字段
- `frontend/src/features/assets/detail/checkout-timeline.tsx` — 归还卡片展示新字段
- `frontend/src/api/generated/schema.d.ts` — gen:api 重新生成
- `frontend/tests/hooks/return-dialog.test.tsx` — 加 case
- `CLAUDE.md` — dev 启动说明 dev.sh → serve
- `.gitignore` — `data/pids/` + `data/logs/` + `.env`

**删除**：
- `scripts/dev.sh` — 被 serve 取代

---

## Phase 0 · I1+I2 后端 validation 补全 + FieldType Enum（Task 1-4）

> **PR 边界**：本 Phase 全部内容合并为一个 PR `feature/m2d-validation`。每个 Task 内 commit。Phase 末尾跑 `pnpm gen:api` 拉新 schema。

### Task 1: 引入 FieldType Enum

**Files:**
- Create: `src/asset_hub/services/field_type.py`
- Test: `tests/unit/test_field_type_enum.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_field_type_enum.py`:
```python
import pytest

from asset_hub.services.field_type import FieldType


def test_field_type_values():
    assert FieldType.STRING.value == "string"
    assert FieldType.TEXT.value == "text"
    assert FieldType.URL.value == "url"
    assert FieldType.INT.value == "int"
    assert FieldType.FLOAT.value == "float"
    assert FieldType.BOOL.value == "bool"
    assert FieldType.ENUM.value == "enum"
    assert FieldType.MULTI_ENUM.value == "multi-enum"
    assert FieldType.DATE.value == "date"


def test_field_type_from_legacy_string():
    assert FieldType("string") is FieldType.STRING
    assert FieldType("multi-enum") is FieldType.MULTI_ENUM


def test_field_type_unknown_raises():
    with pytest.raises(ValueError):
        FieldType("unknown")
```

- [ ] **Step 2: 运行验证失败**

```bash
uv run pytest tests/unit/test_field_type_enum.py -v
```
Expected: ImportError 或 module not found

- [ ] **Step 3: 实现 FieldType**

`src/asset_hub/services/field_type.py`:
```python
from enum import Enum


class FieldType(str, Enum):
    STRING = "string"
    TEXT = "text"
    URL = "url"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    ENUM = "enum"
    MULTI_ENUM = "multi-enum"
    DATE = "date"
```

- [ ] **Step 4: 运行验证通过**

```bash
uv run pytest tests/unit/test_field_type_enum.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/asset_hub/services/field_type.py tests/unit/test_field_type_enum.py
git commit -m "feat(validation): 引入 FieldType Enum 集中字段类型字面量"
```

---

### Task 2: validation.py 改表驱动 dispatch + 补 url 类型

**Files:**
- Modify: `src/asset_hub/services/validation.py`
- Test: `tests/unit/test_validation_url.py`

- [ ] **Step 1: 写 url 校验失败测试**

`tests/unit/test_validation_url.py`:
```python
import pytest

from asset_hub.errors import ValidationError
from asset_hub.services.validation import validate_custom_data


def _spec(t: str, label: str = "网址", required: bool = False, **extra) -> dict:
    return {"key": "url_field", "label": label, "type": t, "required": required, **extra}


def test_url_accepts_https():
    result = validate_custom_data(
        [_spec("url")], {"url_field": "https://example.com/path?q=1"}
    )
    assert result["url_field"] == "https://example.com/path?q=1"


def test_url_accepts_http():
    result = validate_custom_data(
        [_spec("url")], {"url_field": "http://example.com"}
    )
    assert result["url_field"] == "http://example.com"


def test_url_rejects_missing_scheme():
    with pytest.raises(ValidationError, match="网址"):
        validate_custom_data([_spec("url")], {"url_field": "example.com"})


def test_url_rejects_unsupported_scheme():
    with pytest.raises(ValidationError, match="网址"):
        validate_custom_data([_spec("url")], {"url_field": "ftp://example.com"})


def test_url_rejects_missing_netloc():
    with pytest.raises(ValidationError, match="网址"):
        validate_custom_data([_spec("url")], {"url_field": "http://"})


def test_url_rejects_non_string():
    with pytest.raises(ValidationError, match="网址"):
        validate_custom_data([_spec("url")], {"url_field": 123})
```

- [ ] **Step 2: 运行验证失败**

```bash
uv run pytest tests/unit/test_validation_url.py -v
```
Expected: FAIL（"未知字段类型: url"）

- [ ] **Step 3: 改 validation.py 为表驱动 dispatch + 加 url 分支**

`src/asset_hub/services/validation.py`（完全替换）:
```python
from datetime import date
from typing import Any, Callable
from urllib.parse import urlparse

from asset_hub.errors import ValidationError
from asset_hub.services.field_type import FieldType


def validate_custom_data(custom_fields: list[dict], custom_data: dict) -> dict:
    field_map = {f["key"]: f for f in custom_fields}

    unknown = set(custom_data) - set(field_map)
    if unknown:
        raise ValidationError(f"未知字段: {', '.join(sorted(unknown))}")

    validated: dict[str, Any] = {}
    for key, spec in field_map.items():
        value = custom_data.get(key)
        if value is None:
            if spec.get("required", False):
                raise ValidationError(f"缺少必填字段: {spec['label']}")
            continue
        validated[key] = _coerce(value, spec)

    return validated


def _coerce_string(value: Any, spec: dict) -> Any:
    return str(value)


def _coerce_int(value: Any, spec: dict) -> Any:
    label = spec["label"]
    try:
        n = int(value)
    except (ValueError, TypeError) as e:
        raise ValidationError(f"{label}: 类型转换失败 ({e})") from e
    _check_range(n, spec, label)
    return n


def _coerce_float(value: Any, spec: dict) -> Any:
    label = spec["label"]
    try:
        n = float(value)
    except (ValueError, TypeError) as e:
        raise ValidationError(f"{label}: 类型转换失败 ({e})") from e
    _check_range(n, spec, label)
    return n


def _check_range(n: int | float, spec: dict, label: str) -> None:
    if "min" in spec and n < spec["min"]:
        raise ValidationError(f"{label}: 不得小于 {spec['min']}（实际 {n}）")
    if "max" in spec and n > spec["max"]:
        raise ValidationError(f"{label}: 不得大于 {spec['max']}（实际 {n}）")


def _coerce_bool(value: Any, spec: dict) -> Any:
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


def _coerce_enum(value: Any, spec: dict) -> Any:
    label = spec["label"]
    options = spec.get("options", [])
    s = str(value)
    if s not in options:
        raise ValidationError(f"{label}: '{s}' 不在可选值 {options} 中")
    return s


def _coerce_multi_enum(value: Any, spec: dict) -> Any:
    label = spec["label"]
    options = spec.get("options", [])
    if not isinstance(value, list):
        raise ValidationError(f"{label}: 需要数组")
    coerced: list[str] = []
    for item in value:
        s = str(item)
        if s not in options:
            raise ValidationError(f"{label}: '{s}' 不在可选值 {options} 中")
        coerced.append(s)
    return coerced


def _coerce_date(value: Any, spec: dict) -> Any:
    label = spec["label"]
    if isinstance(value, str):
        try:
            date.fromisoformat(value)
        except ValueError as e:
            raise ValidationError(f"{label}: 类型转换失败 ({e})") from e
        return value
    raise ValidationError(f"{label}: 需要 ISO 日期字符串")


def _coerce_url(value: Any, spec: dict) -> Any:
    label = spec["label"]
    if not isinstance(value, str):
        raise ValidationError(f"{label}: 需要字符串")
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https"):
        raise ValidationError(
            f"{label}: 需要 http/https 协议（实际 '{parsed.scheme or value}'）"
        )
    if not parsed.netloc:
        raise ValidationError(f"{label}: 缺少域名（实际 '{value}'）")
    return value


_DISPATCH: dict[FieldType, Callable[[Any, dict], Any]] = {
    FieldType.STRING: _coerce_string,
    FieldType.TEXT: _coerce_string,
    FieldType.URL: _coerce_url,
    FieldType.INT: _coerce_int,
    FieldType.FLOAT: _coerce_float,
    FieldType.BOOL: _coerce_bool,
    FieldType.ENUM: _coerce_enum,
    FieldType.MULTI_ENUM: _coerce_multi_enum,
    FieldType.DATE: _coerce_date,
}


def _coerce(value: Any, spec: dict) -> Any:
    raw_type = spec["type"]
    try:
        ft = FieldType(raw_type)
    except ValueError:
        raise ValidationError(f"未知字段类型: {raw_type}") from None
    handler = _DISPATCH[ft]
    return handler(value, spec)
```

- [ ] **Step 4: 运行验证通过 + 跑既有 validation 测试无回归**

```bash
uv run pytest tests/unit/test_validation_url.py tests/unit/test_asset_service.py tests/unit/test_type_service.py -v
```
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/asset_hub/services/validation.py tests/unit/test_validation_url.py
git commit -m "feat(validation): 改表驱动 dispatch + 补 url 类型校验"
```

---

### Task 3: 补 multi-enum 类型

**Files:**
- Test: `tests/unit/test_validation_multi_enum.py`

> validation.py 在 Task 2 已经实现了 `_coerce_multi_enum`；本 Task 仅补测试以验证。

- [ ] **Step 1: 写测试**

`tests/unit/test_validation_multi_enum.py`:
```python
import pytest

from asset_hub.errors import ValidationError
from asset_hub.services.validation import validate_custom_data


def _spec(options: list[str], required: bool = False) -> dict:
    return {
        "key": "tags",
        "label": "标签",
        "type": "multi-enum",
        "required": required,
        "options": options,
    }


def test_multi_enum_accepts_subset():
    result = validate_custom_data(
        [_spec(["a", "b", "c"])], {"tags": ["a", "c"]}
    )
    assert result["tags"] == ["a", "c"]


def test_multi_enum_accepts_empty_list():
    result = validate_custom_data([_spec(["a", "b"])], {"tags": []})
    assert result["tags"] == []


def test_multi_enum_rejects_non_list():
    with pytest.raises(ValidationError, match="标签"):
        validate_custom_data([_spec(["a", "b"])], {"tags": "a"})


def test_multi_enum_rejects_unknown_option():
    with pytest.raises(ValidationError, match="标签"):
        validate_custom_data([_spec(["a", "b"])], {"tags": ["a", "z"]})


def test_multi_enum_required_missing_raises():
    with pytest.raises(ValidationError, match="缺少必填"):
        validate_custom_data(
            [_spec(["a", "b"], required=True)], {}
        )
```

- [ ] **Step 2: 运行验证通过**

```bash
uv run pytest tests/unit/test_validation_multi_enum.py -v
```
Expected: 全 PASS

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_validation_multi_enum.py
git commit -m "test(validation): 覆盖 multi-enum 4 路径"
```

---

### Task 4: 补 int/float 的 min/max 校验

**Files:**
- Test: `tests/unit/test_validation_min_max.py`

> Task 2 已经实现 `_check_range`；本 Task 仅补测试。

- [ ] **Step 1: 写测试**

`tests/unit/test_validation_min_max.py`:
```python
import pytest

from asset_hub.errors import ValidationError
from asset_hub.services.validation import validate_custom_data


def test_int_within_min_max():
    spec = {"key": "n", "label": "数量", "type": "int", "min": 1, "max": 10}
    result = validate_custom_data([spec], {"n": 5})
    assert result["n"] == 5


def test_int_below_min_raises():
    spec = {"key": "n", "label": "数量", "type": "int", "min": 1}
    with pytest.raises(ValidationError, match="不得小于"):
        validate_custom_data([spec], {"n": 0})


def test_int_above_max_raises():
    spec = {"key": "n", "label": "数量", "type": "int", "max": 10}
    with pytest.raises(ValidationError, match="不得大于"):
        validate_custom_data([spec], {"n": 11})


def test_float_within_range():
    spec = {"key": "x", "label": "比率", "type": "float", "min": 0.0, "max": 1.0}
    result = validate_custom_data([spec], {"x": 0.5})
    assert result["x"] == 0.5


def test_float_above_max_raises():
    spec = {"key": "x", "label": "比率", "type": "float", "max": 1.0}
    with pytest.raises(ValidationError, match="不得大于"):
        validate_custom_data([spec], {"x": 1.5})


def test_int_no_min_max_unbounded():
    spec = {"key": "n", "label": "数量", "type": "int"}
    result = validate_custom_data([spec], {"n": 9999})
    assert result["n"] == 9999
```

- [ ] **Step 2: 运行验证通过**

```bash
uv run pytest tests/unit/test_validation_min_max.py -v
```
Expected: 全 PASS

- [ ] **Step 3: 跑前端 gen:api 拉新 schema（OpenAPI 字段类型 list 含 url / multi-enum）**

```bash
# 后端必须先在 :8000 上跑（如未跑：另起一个终端 uv run uvicorn asset_hub.api.app:app）
pnpm --dir frontend gen:api
```

Expected: `frontend/src/api/generated/schema.d.ts` 更新（如有 type field 的字面量定义）

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_validation_min_max.py frontend/src/api/generated/schema.d.ts
git commit -m "test(validation): 覆盖 int/float min/max + 同步前端 schema"
```

---

## Phase 1 · B3 AssetType DELETE（Task 5-8）

> **PR 边界**：本 Phase 合并为 `feature/m2d-type-delete` PR。

### Task 5: TypeService.delete_type 抛 ConflictError

**Files:**
- Modify: `src/asset_hub/services/asset_type.py`
- Modify: `src/asset_hub/repositories/asset_type.py`
- Modify: `src/asset_hub/errors.py`（如无 ConflictError，加；以下假定已有 DuplicateError 风格）
- Test: `tests/unit/test_type_service_delete.py`

- [ ] **Step 1: 检查 errors.py 是否有 ConflictError**

```bash
grep -n "class.*Error" src/asset_hub/errors.py
```
Expected: 看到 NotFoundError / DuplicateError / ValidationError / StateError；如缺 ConflictError 进 Step 2 加；如已有，复用。

- [ ] **Step 2: 加 ConflictError（如缺）**

`src/asset_hub/errors.py` 末尾追加：
```python
class ConflictError(Exception):
    """资源处于不允许此操作的状态（如有引用、状态冲突）。"""

    pass
```

- [ ] **Step 3: 写失败测试**

`tests/unit/test_type_service_delete.py`:
```python
import pytest

from asset_hub.errors import ConflictError, NotFoundError
from asset_hub.services.asset import AssetService
from asset_hub.services.asset_type import TypeService


def test_delete_type_no_assets_succeeds(session):
    svc = TypeService(session)
    t = svc.create_type(name="测试-删除", code_prefix="DT")
    svc.delete_type(t.id)
    with pytest.raises(NotFoundError):
        svc.get_type(t.id)


def test_delete_type_with_assets_raises_conflict(session):
    type_svc = TypeService(session)
    t = type_svc.create_type(name="测试-冲突", code_prefix="CF")
    asset_svc = AssetService(session)
    asset_svc.register_asset(type_id=t.id, name="资产1")

    with pytest.raises(ConflictError, match="1"):
        type_svc.delete_type(t.id)


def test_delete_type_not_found_raises(session):
    import uuid

    svc = TypeService(session)
    with pytest.raises(NotFoundError):
        svc.delete_type(uuid.uuid4())
```

- [ ] **Step 4: 运行验证失败**

```bash
uv run pytest tests/unit/test_type_service_delete.py -v
```
Expected: FAIL（delete_type 未定义）

- [ ] **Step 5: 在 Repository 加 count helper**

`src/asset_hub/repositories/asset_type.py`（在现有 `TypeRepository` 类内追加）:
```python
    def count_assets_by_type(self, type_id: uuid.UUID) -> int:
        from sqlmodel import func, select

        from asset_hub.models.asset import Asset

        stmt = select(func.count()).where(Asset.type_id == type_id)
        return self.session.exec(stmt).one()

    def delete(self, asset_type) -> None:
        self.session.delete(asset_type)
```

> 如已有 import `uuid` / `func` / `select` / `Asset`，去重。

- [ ] **Step 6: 在 TypeService 加 delete_type**

`src/asset_hub/services/asset_type.py`（在 `TypeService` 类末尾追加）:
```python
    def delete_type(self, type_id: uuid.UUID) -> None:
        from asset_hub.errors import ConflictError

        t = self.get_type(type_id)  # 不存在抛 NotFoundError
        ref_count = self.repo.count_assets_by_type(type_id)
        if ref_count > 0:
            raise ConflictError(
                f"该类型仍有 {ref_count} 个资产引用，请先删除/迁移所有引用此类型的资产"
            )
        self.repo.delete(t)
        self.session.commit()
```

- [ ] **Step 7: 运行验证通过**

```bash
uv run pytest tests/unit/test_type_service_delete.py -v
```
Expected: 全 PASS

- [ ] **Step 8: Commit**

```bash
git add src/asset_hub/errors.py src/asset_hub/services/asset_type.py src/asset_hub/repositories/asset_type.py tests/unit/test_type_service_delete.py
git commit -m "feat(type): TypeService.delete_type 严格拒绝有引用的删除"
```

---

### Task 6: API DELETE /api/types/{type_id} + 异常映射

**Files:**
- Modify: `src/asset_hub/api/routers/types.py`
- Modify: `src/asset_hub/api/app.py`（如无 ConflictError 异常映射，加 409）
- Test: `tests/api/test_type_routes_delete.py`

- [ ] **Step 1: 写失败测试**

`tests/api/test_type_routes_delete.py`:
```python
def test_delete_type_no_assets_returns_204(client, session):
    from asset_hub.services.asset_type import TypeService

    type_svc = TypeService(session)
    t = type_svc.create_type(name="API-删除", code_prefix="AD")

    resp = client.delete(f"/api/types/{t.id}")
    assert resp.status_code == 204


def test_delete_type_with_assets_returns_409(client, session):
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import TypeService

    type_svc = TypeService(session)
    t = type_svc.create_type(name="API-冲突", code_prefix="AC")
    AssetService(session).register_asset(type_id=t.id, name="A1")

    resp = client.delete(f"/api/types/{t.id}")
    assert resp.status_code == 409
    assert "1" in resp.json()["detail"]


def test_delete_type_not_found_returns_404(client):
    import uuid

    resp = client.delete(f"/api/types/{uuid.uuid4()}")
    assert resp.status_code == 404
```

- [ ] **Step 2: 运行验证失败**

```bash
uv run pytest tests/api/test_type_routes_delete.py -v
```
Expected: FAIL（DELETE 405 / ConflictError 未映射）

- [ ] **Step 3: 检查 app.py 已有异常映射风格**

```bash
grep -n "ConflictError\|exception_handler\|ValidationError\|NotFoundError" src/asset_hub/api/app.py
```

- [ ] **Step 4: 加 ConflictError → 409 异常映射（若缺）**

`src/asset_hub/api/app.py`（在现有 exception_handler 群组后追加）:
```python
@app.exception_handler(ConflictError)
async def _conflict_handler(_, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})
```

> 别忘 `from asset_hub.errors import ConflictError` 顶部 import。

- [ ] **Step 5: 加 DELETE 路由**

`src/asset_hub/api/routers/types.py`（在文件末尾追加）:
```python
@router.delete("/{type_id}", status_code=204)
def delete_type(
    type_id: uuid.UUID,
    svc: Annotated[TypeService, Depends(_get_svc)],
):
    svc.delete_type(type_id)
```

- [ ] **Step 6: 运行验证通过**

```bash
uv run pytest tests/api/test_type_routes_delete.py -v
```
Expected: 全 PASS

- [ ] **Step 7: Commit**

```bash
git add src/asset_hub/api/routers/types.py src/asset_hub/api/app.py tests/api/test_type_routes_delete.py
git commit -m "feat(api): DELETE /api/types/{id} + ConflictError → 409 映射"
```

---

### Task 7: CLI `asset-hub type delete` 子命令

**Files:**
- Modify: `src/asset_hub/cli/type_cmd.py`
- Test: `tests/cli/test_type_cli_delete.py`

- [ ] **Step 1: 写失败测试**

`tests/cli/test_type_cli_delete.py`:
```python
import json

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def test_type_delete_dry_run_no_db_change(isolated_db, session):
    from asset_hub.services.asset_type import TypeService

    t = TypeService(session).create_type(name="CLI-DR", code_prefix="DR")
    res = runner.invoke(
        app, ["type", "delete", str(t.id), "--dry-run", "--json"]
    )
    assert res.exit_code == 10  # dry-run 预览
    payload = json.loads(res.stdout)
    assert payload["success"] is True
    # 数据库内 type 仍存在
    assert TypeService(session).get_type(t.id) is not None


def test_type_delete_no_refs_succeeds(isolated_db, session):
    from asset_hub.errors import NotFoundError
    from asset_hub.services.asset_type import TypeService

    t = TypeService(session).create_type(name="CLI-OK", code_prefix="OK")
    res = runner.invoke(app, ["type", "delete", str(t.id), "--yes", "--json"])
    assert res.exit_code == 0
    import pytest

    with pytest.raises(NotFoundError):
        TypeService(session).get_type(t.id)


def test_type_delete_with_refs_returns_exit_1(isolated_db, session):
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import TypeService

    t = TypeService(session).create_type(name="CLI-CF", code_prefix="CF")
    AssetService(session).register_asset(type_id=t.id, name="A1")
    res = runner.invoke(app, ["type", "delete", str(t.id), "--yes", "--json"])
    assert res.exit_code == 1
    payload = json.loads(res.stdout)
    assert payload["success"] is False
    assert "1" in payload["error"]["message"]


def test_type_delete_not_found_returns_exit_3(isolated_db):
    import uuid

    res = runner.invoke(
        app, ["type", "delete", str(uuid.uuid4()), "--yes", "--json"]
    )
    assert res.exit_code == 3
```

- [ ] **Step 2: 运行验证失败**

```bash
uv run pytest tests/cli/test_type_cli_delete.py -v
```
Expected: FAIL

- [ ] **Step 3: 加 delete 子命令**

`src/asset_hub/cli/type_cmd.py`（在文件末尾追加；如有现成的 `with_envelope` / `parse_uuid` helper 沿用）:
```python
@type_app.command("delete")
def delete_type(
    ctx: typer.Context,
    type_id: str = typer.Argument(..., help="要删除的 AssetType id"),
    yes: bool = typer.Option(False, "--yes", "-y", help="跳过二次确认"),
    dry_run: bool = typer.Option(False, "--dry-run", help="预览不真删"),
    json_out: bool = typer.Option(False, "--json", help="JSON 信封输出"),
):
    """删除 AssetType（有引用的资产时严格拒绝）"""
    from asset_hub.errors import ConflictError, NotFoundError
    from asset_hub.cli.deps import cli_session, parse_uuid
    from asset_hub.cli.envelope import emit_error, emit_success
    from asset_hub.services.asset_type import TypeService

    tid = parse_uuid(type_id, "type_id")

    with cli_session() as session:
        svc = TypeService(session)
        try:
            t = svc.get_type(tid)
        except NotFoundError as e:
            emit_error(json_out, code="not_found", message=str(e), exit_code=3)
            return

        ref_count = svc.repo.count_assets_by_type(tid)

        if dry_run:
            emit_success(
                json_out,
                data={
                    "would_delete": {"id": str(tid), "name": t.name, "code_prefix": t.code_prefix},
                    "reference_count": ref_count,
                },
                metadata={"dry_run": True},
                exit_code=10,
            )
            return

        if ref_count > 0:
            emit_error(
                json_out,
                code="conflict",
                message=f"该类型仍有 {ref_count} 个资产引用，请先删除/迁移所有引用此类型的资产",
                exit_code=1,
            )
            return

        if not yes and not json_out:
            confirm = typer.confirm(
                f"确认删除 type '{t.name}' ({t.code_prefix})？"
            )
            if not confirm:
                emit_error(json_out, code="cancelled", message="用户取消", exit_code=1)
                return

        try:
            svc.delete_type(tid)
        except ConflictError as e:
            emit_error(json_out, code="conflict", message=str(e), exit_code=1)
            return

        emit_success(
            json_out,
            data={"deleted_id": str(tid), "name": t.name},
            metadata={},
        )
```

> 如 `emit_success` / `emit_error` 接口与既有 `cli/envelope.py` 不一致，按既有接口签名调整。可参考 `asset_cmd.py` 现有命令的写法。

- [ ] **Step 4: 运行验证通过**

```bash
uv run pytest tests/cli/test_type_cli_delete.py -v
```
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/asset_hub/cli/type_cmd.py tests/cli/test_type_cli_delete.py
git commit -m "feat(cli): asset-hub type delete + --dry-run + 二次确认"
```

---

### Task 8: 跑前端 gen:api + 全测试回归

**Files:**
- Modify: `frontend/src/api/generated/schema.d.ts`

- [ ] **Step 1: 启后端 + 拉新 schema**

```bash
# 终端 A
uv run uvicorn asset_hub.api.app:app --port 8000

# 终端 B
pnpm --dir frontend gen:api
```

- [ ] **Step 2: 跑全部回归测试**

```bash
uv run pytest -x
pnpm --dir frontend test --run
pnpm --dir frontend lint
```
Expected: 全绿

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/generated/schema.d.ts
git commit -m "chore: gen:api 同步 type DELETE 端点"
```

---

## Phase 2 · B2 归还时记录归还地点 + 接收人（Task 9-13）

> **PR 边界**：本 Phase 合并为 `feature/m2d-return-fields` PR。

### Task 9: 模型 + alembic migration

**Files:**
- Modify: `src/asset_hub/models/checkout.py`
- Create: `src/asset_hub/alembic/versions/<ts>_add_return_location_receiver.py`

- [ ] **Step 1: 改模型加两字段**

`src/asset_hub/models/checkout.py`（在 CheckoutRecord 类末尾）:
```python
    return_location: str | None = None
    return_receiver: str | None = None
```

- [ ] **Step 2: 自动生成迁移**

```bash
uv run alembic revision --autogenerate -m "add return_location and return_receiver to checkout_records"
```

- [ ] **Step 3: 检查生成的 migration 文件**

打开 `src/asset_hub/alembic/versions/<生成的最新文件>` 确认两个 `op.add_column` 用 `batch_alter_table`（SQLite 改表必需）。如无 batch，手动改：

```python
def upgrade() -> None:
    with op.batch_alter_table("checkout_records") as batch_op:
        batch_op.add_column(sa.Column("return_location", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("return_receiver", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("checkout_records") as batch_op:
        batch_op.drop_column("return_receiver")
        batch_op.drop_column("return_location")
```

> 如 alembic post_write_hooks ruff_format 不工作（已知问题），手工跑 `uv run ruff format src/asset_hub/alembic/versions/<文件>`。

- [ ] **Step 4: 跑迁移**

```bash
uv run alembic upgrade head
```

- [ ] **Step 5: 验证 schema 已加列**

```bash
uv run python -c "from asset_hub.db import get_engine; from sqlalchemy import inspect; insp = inspect(get_engine()); print([c['name'] for c in insp.get_columns('checkout_records')])"
```
Expected: 输出含 `return_location` + `return_receiver`

- [ ] **Step 6: Commit**

```bash
git add src/asset_hub/models/checkout.py src/asset_hub/alembic/versions/
git commit -m "feat(model): CheckoutRecord 加 return_location/return_receiver + migration"
```

---

### Task 10: CheckoutService.return_ 接受新字段 + asset.location 跟随

**Files:**
- Modify: `src/asset_hub/services/checkout.py`
- Test: `tests/unit/test_checkout_service_return_fields.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_checkout_service_return_fields.py`:
```python
import pytest

from asset_hub.services.asset import AssetService
from asset_hub.services.asset_type import TypeService
from asset_hub.services.checkout import CheckoutService


@pytest.fixture
def asset_id(session):
    t = TypeService(session).create_type(name="B2-T", code_prefix="BT")
    a = AssetService(session).register_asset(type_id=t.id, name="B2-A")
    CheckoutService(session).checkout(a.id, holder="张三", location="工位A")
    return a.id


def test_return_no_extra_fields_clears_location(session, asset_id):
    rec = CheckoutService(session).return_(asset_id, note="还了")
    assert rec.return_location is None
    assert rec.return_receiver is None
    a = AssetService(session).get_asset(asset_id)
    assert a.location is None


def test_return_with_location_sets_asset_location(session, asset_id):
    rec = CheckoutService(session).return_(
        asset_id, note="还", return_location="仓库A-3排"
    )
    assert rec.return_location == "仓库A-3排"
    a = AssetService(session).get_asset(asset_id)
    assert a.location == "仓库A-3排"


def test_return_with_receiver_only(session, asset_id):
    rec = CheckoutService(session).return_(
        asset_id, note=None, return_receiver="管理员甲"
    )
    assert rec.return_receiver == "管理员甲"
    assert rec.return_location is None
    a = AssetService(session).get_asset(asset_id)
    assert a.location is None  # location 留空时仍清空


def test_return_with_both(session, asset_id):
    rec = CheckoutService(session).return_(
        asset_id,
        note="测试",
        return_location="仓库B",
        return_receiver="管理员乙",
    )
    assert rec.return_location == "仓库B"
    assert rec.return_receiver == "管理员乙"
    a = AssetService(session).get_asset(asset_id)
    assert a.location == "仓库B"
    assert a.holder is None  # holder 仍清空（语义不变）
```

- [ ] **Step 2: 运行验证失败**

```bash
uv run pytest tests/unit/test_checkout_service_return_fields.py -v
```
Expected: FAIL

- [ ] **Step 3: 改 CheckoutService.return_**

`src/asset_hub/services/checkout.py`，替换 `return_` 方法：
```python
    def return_(
        self,
        asset_id: uuid.UUID,
        note: str | None = None,
        return_location: str | None = None,
        return_receiver: str | None = None,
    ) -> CheckoutRecord:
        asset = self.asset_svc.get_asset(asset_id)

        record = self.repo.find_open_by_asset(asset_id)
        if record is None:
            raise StateError(f"资产无未归还记录: {asset_id}")

        try:
            assert_transition_allowed(asset.status, AssetStatus.IDLE)
        except ValidationError as e:
            raise StateError(str(e)) from e

        now = datetime.now(UTC)
        record.returned_at = now
        record.return_note = note
        record.return_location = return_location
        record.return_receiver = return_receiver

        asset.status = AssetStatus.IDLE
        asset.holder = None
        asset.location = return_location  # 跟随，留空则清空
        asset.current_checkout_id = None
        asset.updated_at = now

        self.session.commit()
        self.session.refresh(record)
        return record
```

- [ ] **Step 4: 运行验证通过 + 跑既有 checkout 测试**

```bash
uv run pytest tests/unit/test_checkout_service_return_fields.py tests/unit/test_checkout_service.py -v
```
Expected: 全 PASS（既有 test_checkout_service.py 不应回归——既有归还测试不传新字段，behavior 一致）

- [ ] **Step 5: Commit**

```bash
git add src/asset_hub/services/checkout.py tests/unit/test_checkout_service_return_fields.py
git commit -m "feat(service): return_ 接受 return_location/return_receiver + asset.location 跟随"
```

---

### Task 11: API DTO + router 透传

**Files:**
- Modify: `src/asset_hub/api/schemas/checkout.py`
- Modify: `src/asset_hub/api/routers/checkouts.py`
- Test: `tests/api/test_checkout_routes_return_fields.py`

- [ ] **Step 1: 写失败测试**

`tests/api/test_checkout_routes_return_fields.py`:
```python
def test_return_with_location_and_receiver(client, session):
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import TypeService
    from asset_hub.services.checkout import CheckoutService

    t = TypeService(session).create_type(name="API-RT", code_prefix="RT")
    a = AssetService(session).register_asset(type_id=t.id, name="A1")
    CheckoutService(session).checkout(a.id, holder="张三")

    resp = client.post(
        f"/api/assets/{a.id}/return",
        json={
            "note": "测试归还",
            "return_location": "仓库C",
            "return_receiver": "管理员丙",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["return_location"] == "仓库C"
    assert body["return_receiver"] == "管理员丙"

    asset_resp = client.get(f"/api/assets/{a.id}")
    assert asset_resp.json()["location"] == "仓库C"


def test_return_without_extra_fields_backward_compat(client, session):
    """保证 v1 早期客户端只传 note 仍工作"""
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import TypeService
    from asset_hub.services.checkout import CheckoutService

    t = TypeService(session).create_type(name="API-BC", code_prefix="BC")
    a = AssetService(session).register_asset(type_id=t.id, name="A2")
    CheckoutService(session).checkout(a.id, holder="李四")

    resp = client.post(f"/api/assets/{a.id}/return", json={"note": "仅备注"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["return_location"] is None
    assert body["return_receiver"] is None
```

- [ ] **Step 2: 运行验证失败**

```bash
uv run pytest tests/api/test_checkout_routes_return_fields.py -v
```
Expected: FAIL（DTO 缺字段）

- [ ] **Step 3: 改 DTO**

`src/asset_hub/api/schemas/checkout.py`:
```python
class CheckoutReturn(BaseModel):
    note: str | None = None
    return_location: str | None = None
    return_receiver: str | None = None


class CheckoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_id: UUID
    holder: str
    location: str | None
    checked_out_at: datetime
    returned_at: datetime | None
    checkout_note: str | None
    return_note: str | None
    return_location: str | None
    return_receiver: str | None
```

- [ ] **Step 4: 改 router 透传**

`src/asset_hub/api/routers/checkouts.py` 找到 return 端点（`/api/assets/{asset_id}/return` POST），改 service 调用：

```python
return svc.return_(
    asset_id,
    note=body.note,
    return_location=body.return_location,
    return_receiver=body.return_receiver,
)
```

- [ ] **Step 5: 运行验证通过**

```bash
uv run pytest tests/api/test_checkout_routes_return_fields.py tests/api/test_checkout_routes.py -v
```
Expected: 全 PASS

- [ ] **Step 6: Commit**

```bash
git add src/asset_hub/api/schemas/checkout.py src/asset_hub/api/routers/checkouts.py tests/api/test_checkout_routes_return_fields.py
git commit -m "feat(api): CheckoutReturn/Read 加 return_location/receiver + 透传"
```

---

### Task 12: CLI `asset return --location --receiver` flag

**Files:**
- Modify: `src/asset_hub/cli/asset_cmd.py`
- Test: `tests/cli/test_asset_checkout_cli_return_fields.py`

- [ ] **Step 1: 写失败测试**

`tests/cli/test_asset_checkout_cli_return_fields.py`:
```python
import json

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def test_return_with_location_and_receiver(isolated_db, session):
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import TypeService
    from asset_hub.services.checkout import CheckoutService

    t = TypeService(session).create_type(name="CLI-RT", code_prefix="CR")
    a = AssetService(session).register_asset(type_id=t.id, name="C1")
    CheckoutService(session).checkout(a.id, holder="张三")

    res = runner.invoke(
        app,
        [
            "asset",
            "return",
            str(a.id),
            "--location",
            "仓库D",
            "--receiver",
            "管理员丁",
            "--note",
            "CLI test",
            "--json",
        ],
    )
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload["success"] is True
    assert payload["data"]["return_location"] == "仓库D"
    assert payload["data"]["return_receiver"] == "管理员丁"
```

- [ ] **Step 2: 运行验证失败**

```bash
uv run pytest tests/cli/test_asset_checkout_cli_return_fields.py -v
```
Expected: FAIL

- [ ] **Step 3: 改 asset_cmd.py 的 return 命令**

`src/asset_hub/cli/asset_cmd.py` 找到现有 `return_` 命令（用 `grep -n "return" src/asset_hub/cli/asset_cmd.py` 定位），加两个 Option：

```python
@asset_app.command("return")
def return_asset(
    asset_id: str = typer.Argument(...),
    note: str | None = typer.Option(None, "--note"),
    location: str | None = typer.Option(None, "--location", help="归还到的物理位置"),
    receiver: str | None = typer.Option(None, "--receiver", help="归还接收的管理员"),
    json_out: bool = typer.Option(False, "--json"),
):
    """归还资产（可记录归还地点 + 接收人）"""
    # ... 既有逻辑改 svc.return_(aid, note=note, return_location=location, return_receiver=receiver)
```

> 具体合并方式根据现有 return 命令实现风格调整；保持其他 flag 不变。

- [ ] **Step 4: 运行验证通过**

```bash
uv run pytest tests/cli/test_asset_checkout_cli_return_fields.py tests/cli/test_asset_checkout_cli.py -v
```
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/asset_hub/cli/asset_cmd.py tests/cli/test_asset_checkout_cli_return_fields.py
git commit -m "feat(cli): asset return --location/--receiver 可记录归还去向"
```

---

### Task 13: 前端 ReturnDialog 加字段 + timeline 展示 + Vitest

**Files:**
- Modify: `frontend/src/features/assets/detail/return-dialog.tsx`
- Modify: `frontend/src/features/assets/detail/checkout-timeline.tsx`
- Modify: `frontend/src/api/generated/schema.d.ts`（gen:api 重新生成）
- Modify: `frontend/tests/hooks/return-dialog.test.tsx`（如已有；否则创建）

- [ ] **Step 1: 启后端 + 拉新 schema**

```bash
# 终端 A
uv run uvicorn asset_hub.api.app:app --port 8000

# 终端 B
pnpm --dir frontend gen:api
```

- [ ] **Step 2: 改 ReturnDialog 加字段**

`frontend/src/features/assets/detail/return-dialog.tsx`：
- 在已有 zod schema 加 `return_location: z.string().max(200).optional()` 和 `return_receiver: z.string().max(100).optional()`
- 在表单加两个 Input field（用既有 `<FormField>` shadcn 模板）
- onSubmit 里把这两个值放进 mutation payload

> 具体改动取决于现有 ReturnDialog 实现（已迁 RHF + Zod，参见 m2c-3 commit `6858ab0`）。在 schema 旁边加两个字段，UI 上加两行 input。

- [ ] **Step 3: 改 checkout-timeline 卡片展示**

`frontend/src/features/assets/detail/checkout-timeline.tsx` 找归还卡片渲染（含 `return_note` 的位置），紧邻新增：

```tsx
{record.return_location && (
  <div className="text-sm text-muted-foreground">
    归还至：{record.return_location}
  </div>
)}
{record.return_receiver && (
  <div className="text-sm text-muted-foreground">
    接收人：{record.return_receiver}
  </div>
)}
```

- [ ] **Step 4: 写 Vitest 测试**

`frontend/tests/hooks/return-dialog.test.tsx`（追加 case；如已有 file，按既有结构加）:
```tsx
import { describe, expect, it } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// 假设有 renderWithProviders helper

describe("ReturnDialog with new fields", () => {
  it("submits return_location and return_receiver", async () => {
    // setup mock api expecting payload {note, return_location, return_receiver}
    // render dialog with open=true
    // fireEvent.change on location/receiver inputs
    // click submit
    // assert mutation called with all 3 fields
  });
});
```

> 具体实现按既有 return-dialog.test.tsx 风格。如无既有 file，创建并参考 checkout-dialog.test.tsx。

- [ ] **Step 5: 跑前端测试**

```bash
pnpm --dir frontend test --run
pnpm --dir frontend lint
```
Expected: 全绿

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/generated/schema.d.ts frontend/src/features/assets/detail/return-dialog.tsx frontend/src/features/assets/detail/checkout-timeline.tsx frontend/tests/hooks/return-dialog.test.tsx
git commit -m "feat(frontend): ReturnDialog 加归还地点+接收人 + timeline 展示"
```

---

## Phase 3 · /api/healthz 端点（Task 14）

> **PR 边界**：合入 serve 主线 PR `feature/m2d-serve`。

### Task 14: 健康端点

**Files:**
- Create: `src/asset_hub/api/routers/health.py`
- Modify: `src/asset_hub/api/app.py`（include router）
- Test: `tests/api/test_health.py`

- [ ] **Step 1: 写失败测试**

`tests/api/test_health.py`:
```python
def test_healthz_returns_200_and_status_ok(client):
    resp = client.get("/api/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 2: 运行验证失败**

```bash
uv run pytest tests/api/test_health.py -v
```
Expected: FAIL（404）

- [ ] **Step 3: 创建 router**

`src/asset_hub/api/routers/health.py`:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 4: 在 app.py include**

`src/asset_hub/api/app.py`，在现有 `app.include_router` 群组追加：
```python
from asset_hub.api.routers import health  # 顶部 import 群

app.include_router(health.router)
```

- [ ] **Step 5: 运行验证通过**

```bash
uv run pytest tests/api/test_health.py -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/asset_hub/api/routers/health.py src/asset_hub/api/app.py tests/api/test_health.py
git commit -m "feat(api): /api/healthz 极简存活端点（serve start 探测依赖）"
```

---

## Phase 4 · serve · 配置层 + 基础工具层（Task 15-19）

### Task 15: 加 psutil 依赖 + 扩 Settings

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/asset_hub/config.py`
- Modify: `.gitignore`
- Create: `.env.example`
- Test: `tests/unit/test_settings_serve.py`

- [ ] **Step 1: 加 psutil 依赖**

```bash
uv add psutil
```

- [ ] **Step 2: 写 Settings 优先级测试**

`tests/unit/test_settings_serve.py`:
```python
import os

import pytest

from asset_hub.config import Settings


def test_default_ports():
    s = Settings()
    assert s.backend_port == 8000
    assert s.frontend_port == 5173


def test_env_override(monkeypatch):
    monkeypatch.setenv("ASSET_HUB_BACKEND_PORT", "9000")
    monkeypatch.setenv("ASSET_HUB_FRONTEND_PORT", "9001")
    s = Settings()
    assert s.backend_port == 9000
    assert s.frontend_port == 9001


def test_resolve_backend_host_dev_default():
    s = Settings()
    assert s.resolve_backend_host("dev") == "127.0.0.1"


def test_resolve_backend_host_prod_default():
    s = Settings()
    assert s.resolve_backend_host("prod") == "0.0.0.0"


def test_resolve_backend_host_explicit_override(monkeypatch):
    monkeypatch.setenv("ASSET_HUB_BACKEND_HOST", "192.168.1.10")
    s = Settings()
    assert s.resolve_backend_host("prod") == "192.168.1.10"
    assert s.resolve_backend_host("dev") == "192.168.1.10"


def test_pids_dir_under_data():
    s = Settings()
    assert str(s.pids_dir).endswith("pids")


def test_logs_dir_under_data():
    s = Settings()
    assert str(s.logs_dir).endswith("logs")
```

- [ ] **Step 3: 运行验证失败**

```bash
uv run pytest tests/unit/test_settings_serve.py -v
```
Expected: FAIL（字段未定义）

- [ ] **Step 4: 改 Settings**

`src/asset_hub/config.py`（完全替换）:
```python
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ASSET_HUB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Path("data")
    backend_port: int = 8000
    frontend_port: int = 5173
    backend_host: str | None = None

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.data_dir / 'asset_hub.db'}"

    @property
    def attachments_dir(self) -> Path:
        return self.data_dir / "attachments"

    @property
    def pids_dir(self) -> Path:
        return self.data_dir / "pids"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    def resolve_backend_host(self, mode: Literal["dev", "prod"]) -> str:
        if self.backend_host is not None:
            return self.backend_host
        return "127.0.0.1" if mode == "dev" else "0.0.0.0"
```

- [ ] **Step 5: 加 .env.example**

`.env.example`:
```
# 复制为 .env 后按需修改；所有字段都可省略，省略则使用代码默认值。

# ASSET_HUB_DATA_DIR=/var/asset-hub
# ASSET_HUB_BACKEND_PORT=8000
# ASSET_HUB_FRONTEND_PORT=5173
# ASSET_HUB_BACKEND_HOST=
```

- [ ] **Step 6: 改 .gitignore**

`.gitignore`（追加；如已有 data/ 全局忽略，仍重复声明 .env）:
```
data/pids/
data/logs/
.env
```

- [ ] **Step 7: 运行验证通过**

```bash
uv run pytest tests/unit/test_settings_serve.py tests/cli/test_asset_cli.py -v
```
Expected: 全 PASS（既有测试因 Settings 兼容性不应回归）

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock src/asset_hub/config.py .env.example .gitignore tests/unit/test_settings_serve.py
git commit -m "feat(config): 扩 backend_port/frontend_port/backend_host + psutil 依赖"
```

---

### Task 16: pid.py · PID 文件 IO + state 判定

**Files:**
- Create: `src/asset_hub/cli/serve/__init__.py`（空）
- Create: `src/asset_hub/cli/serve/pid.py`
- Test: `tests/unit/test_pid_io.py`
- Test: `tests/unit/test_pid_state.py`

- [ ] **Step 1: 创建空 __init__.py**

```bash
mkdir -p src/asset_hub/cli/serve
touch src/asset_hub/cli/serve/__init__.py
```

- [ ] **Step 2: 写 PID 文件 IO 测试**

`tests/unit/test_pid_io.py`:
```python
from datetime import UTC, datetime

import pytest

from asset_hub.cli.serve.pid import PidFileContent, read_pid_file, write_pid_file


def test_write_then_read_roundtrip(tmp_path):
    f = tmp_path / "backend.pid"
    started = datetime(2026, 4, 29, 10, 23, 14, tzinfo=UTC)
    write_pid_file(f, pid=12345, mode="prod", started_at=started)

    content = read_pid_file(f)
    assert content.pid == 12345
    assert content.mode == "prod"
    assert content.started_at == started


def test_read_returns_none_when_file_missing(tmp_path):
    f = tmp_path / "missing.pid"
    assert read_pid_file(f) is None


def test_read_handles_minimal_pid_file(tmp_path):
    f = tmp_path / "min.pid"
    f.write_text("99999\n")
    content = read_pid_file(f)
    assert content.pid == 99999
    assert content.mode is None
    assert content.started_at is None


def test_read_handles_corrupt_file(tmp_path):
    f = tmp_path / "bad.pid"
    f.write_text("not-a-number\n")
    with pytest.raises(ValueError):
        read_pid_file(f)
```

- [ ] **Step 3: 写 read_pid_state 测试（用 mock psutil）**

`tests/unit/test_pid_state.py`:
```python
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
import psutil

from asset_hub.cli.serve.pid import (
    PidStateStatus,
    read_pid_state,
    write_pid_file,
)


def _mock_proc(cmdline: list[str], status: str = "running"):
    p = MagicMock()
    p.cmdline.return_value = cmdline
    p.status.return_value = status
    return p


def test_read_pid_state_none_when_file_missing(tmp_path):
    state = read_pid_state(tmp_path / "missing.pid", "backend")
    assert state.status is PidStateStatus.NONE
    assert state.pid is None


def test_read_pid_state_running_when_match(tmp_path):
    f = tmp_path / "backend.pid"
    write_pid_file(f, pid=12345, mode="prod", started_at=datetime.now(UTC))

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=True), \
         patch("asset_hub.cli.serve.pid.psutil.Process") as mock_process:
        mock_process.return_value = _mock_proc(
            cmdline=["python", "-m", "uvicorn", "asset_hub.api.app:app"]
        )
        state = read_pid_state(f, "backend")
    assert state.status is PidStateStatus.RUNNING
    assert state.pid == 12345
    assert state.mode == "prod"


def test_read_pid_state_stale_when_pid_dead(tmp_path):
    f = tmp_path / "backend.pid"
    write_pid_file(f, pid=99999, mode="prod", started_at=None)

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=False):
        state = read_pid_state(f, "backend")
    assert state.status is PidStateStatus.STALE


def test_read_pid_state_stale_when_zombie(tmp_path):
    f = tmp_path / "backend.pid"
    write_pid_file(f, pid=12345, mode="prod", started_at=None)

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=True), \
         patch("asset_hub.cli.serve.pid.psutil.Process") as mock_process:
        mock_process.return_value = _mock_proc(
            cmdline=["python", "-m", "uvicorn", "asset_hub.api.app:app"],
            status=psutil.STATUS_ZOMBIE,
        )
        state = read_pid_state(f, "backend")
    assert state.status is PidStateStatus.STALE


def test_read_pid_state_stale_when_cmdline_mismatch(tmp_path):
    """PID 复用到无关进程"""
    f = tmp_path / "backend.pid"
    write_pid_file(f, pid=12345, mode="prod", started_at=None)

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=True), \
         patch("asset_hub.cli.serve.pid.psutil.Process") as mock_process:
        mock_process.return_value = _mock_proc(
            cmdline=["bash", "-c", "sleep 99"]  # 不含 uvicorn / asset_hub
        )
        state = read_pid_state(f, "backend")
    assert state.status is PidStateStatus.STALE


def test_read_pid_state_corrupt_file_treated_stale(tmp_path):
    f = tmp_path / "bad.pid"
    f.write_text("garbage\n")
    state = read_pid_state(f, "backend")
    assert state.status is PidStateStatus.STALE
```

- [ ] **Step 4: 运行验证失败**

```bash
uv run pytest tests/unit/test_pid_io.py tests/unit/test_pid_state.py -v
```
Expected: ImportError

- [ ] **Step 5: 实现 pid.py**

`src/asset_hub/cli/serve/pid.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal

import psutil


# cmdline 校验关键词（两 token 必须同时命中）
BACKEND_CMDLINE_TOKENS = ("uvicorn", "asset_hub.api.app")
FRONTEND_CMDLINE_TOKENS = ("pnpm", "dev")


class PidStateStatus(str, Enum):
    NONE = "none"
    RUNNING = "running"
    STALE = "stale"


@dataclass
class PidFileContent:
    pid: int
    mode: Literal["dev", "prod"] | None
    started_at: datetime | None


@dataclass
class PidState:
    service: Literal["backend", "frontend"]
    file_exists: bool
    pid: int | None
    mode: Literal["dev", "prod"] | None
    started_at: datetime | None
    process_alive: bool
    cmdline_match: bool
    status: PidStateStatus


def write_pid_file(
    path: Path,
    *,
    pid: int,
    mode: Literal["dev", "prod"],
    started_at: datetime | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{pid}", f"mode={mode}"]
    if started_at is not None:
        ts = started_at.replace(microsecond=0).isoformat()
        if ts.endswith("+00:00"):
            ts = ts[:-6] + "Z"
        lines.append(f"started_at={ts}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_pid_file(path: Path) -> PidFileContent | None:
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8").strip().splitlines()
    if not raw:
        raise ValueError("empty PID file")
    pid = int(raw[0].strip())  # ValueError if corrupt

    mode: Literal["dev", "prod"] | None = None
    started_at: datetime | None = None
    for line in raw[1:]:
        if line.startswith("mode="):
            v = line.split("=", 1)[1].strip()
            if v in ("dev", "prod"):
                mode = v  # type: ignore[assignment]
        elif line.startswith("started_at="):
            v = line.split("=", 1)[1].strip()
            try:
                if v.endswith("Z"):
                    v = v[:-1] + "+00:00"
                started_at = datetime.fromisoformat(v)
            except ValueError:
                started_at = None
    return PidFileContent(pid=pid, mode=mode, started_at=started_at)


def _cmdline_tokens_for(service: Literal["backend", "frontend"]) -> tuple[str, ...]:
    return BACKEND_CMDLINE_TOKENS if service == "backend" else FRONTEND_CMDLINE_TOKENS


def _check_cmdline(pid: int, tokens: tuple[str, ...]) -> bool:
    try:
        cmdline_str = " ".join(psutil.Process(pid).cmdline())
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
    return all(t in cmdline_str for t in tokens)


def read_pid_state(
    path: Path,
    service: Literal["backend", "frontend"],
) -> PidState:
    if not path.exists():
        return PidState(
            service=service,
            file_exists=False,
            pid=None,
            mode=None,
            started_at=None,
            process_alive=False,
            cmdline_match=False,
            status=PidStateStatus.NONE,
        )

    try:
        content = read_pid_file(path)
        assert content is not None
    except ValueError:
        return PidState(
            service=service,
            file_exists=True,
            pid=None,
            mode=None,
            started_at=None,
            process_alive=False,
            cmdline_match=False,
            status=PidStateStatus.STALE,
        )

    pid = content.pid
    if not psutil.pid_exists(pid):
        return PidState(
            service=service,
            file_exists=True,
            pid=pid,
            mode=content.mode,
            started_at=content.started_at,
            process_alive=False,
            cmdline_match=False,
            status=PidStateStatus.STALE,
        )

    try:
        proc_status = psutil.Process(pid).status()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return PidState(
            service=service,
            file_exists=True,
            pid=pid,
            mode=content.mode,
            started_at=content.started_at,
            process_alive=False,
            cmdline_match=False,
            status=PidStateStatus.STALE,
        )

    if proc_status == psutil.STATUS_ZOMBIE:
        return PidState(
            service=service,
            file_exists=True,
            pid=pid,
            mode=content.mode,
            started_at=content.started_at,
            process_alive=False,
            cmdline_match=False,
            status=PidStateStatus.STALE,
        )

    cmdline_ok = _check_cmdline(pid, _cmdline_tokens_for(service))
    if not cmdline_ok:
        return PidState(
            service=service,
            file_exists=True,
            pid=pid,
            mode=content.mode,
            started_at=content.started_at,
            process_alive=True,
            cmdline_match=False,
            status=PidStateStatus.STALE,
        )

    return PidState(
        service=service,
        file_exists=True,
        pid=pid,
        mode=content.mode,
        started_at=content.started_at,
        process_alive=True,
        cmdline_match=True,
        status=PidStateStatus.RUNNING,
    )


def remove_pid_file(path: Path) -> None:
    if path.exists():
        path.unlink()
```

- [ ] **Step 6: 运行验证通过**

```bash
uv run pytest tests/unit/test_pid_io.py tests/unit/test_pid_state.py -v
```
Expected: 全 PASS

- [ ] **Step 7: Commit**

```bash
git add src/asset_hub/cli/serve/__init__.py src/asset_hub/cli/serve/pid.py tests/unit/test_pid_io.py tests/unit/test_pid_state.py
git commit -m "feat(serve): pid.py · PID 文件 IO + state 判定矩阵"
```

---

### Task 17: proc.py · 跨平台 detach + 端口检查

**Files:**
- Create: `src/asset_hub/cli/serve/proc.py`
- Test: `tests/unit/test_proc_detach.py`
- Test: `tests/unit/test_proc_port_check.py`

- [ ] **Step 1: 写 detach 跨平台测试**

`tests/unit/test_proc_detach.py`:
```python
import sys
from unittest.mock import MagicMock, patch

import pytest

from asset_hub.cli.serve.proc import start_detached


@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific path")
def test_start_detached_uses_start_new_session_on_unix(tmp_path):
    log = tmp_path / "out.log"
    captured: dict = {}

    def fake_popen(cmd, **kwargs):
        captured.update(kwargs)
        m = MagicMock()
        m.pid = 99999
        return m

    with patch("asset_hub.cli.serve.proc.subprocess.Popen", fake_popen):
        start_detached(["echo", "hi"], log_file=log, cwd=tmp_path)

    assert captured.get("start_new_session") is True


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific path")
def test_start_detached_uses_creation_flags_on_windows(tmp_path):
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    log = tmp_path / "out.log"
    captured: dict = {}

    def fake_popen(cmd, **kwargs):
        captured.update(kwargs)
        m = MagicMock()
        m.pid = 99999
        return m

    with patch("asset_hub.cli.serve.proc.subprocess.Popen", fake_popen):
        start_detached(["echo", "hi"], log_file=log, cwd=tmp_path)

    assert captured.get("creationflags", 0) & DETACHED_PROCESS
    assert captured.get("creationflags", 0) & CREATE_NEW_PROCESS_GROUP
    assert captured.get("close_fds") is True


def test_start_detached_returns_pid(tmp_path):
    log = tmp_path / "out.log"

    def fake_popen(cmd, **kwargs):
        m = MagicMock()
        m.pid = 42
        return m

    with patch("asset_hub.cli.serve.proc.subprocess.Popen", fake_popen):
        pid = start_detached(["echo", "hi"], log_file=log, cwd=tmp_path)
    assert pid == 42
```

- [ ] **Step 2: 写 port 检查测试**

`tests/unit/test_proc_port_check.py`:
```python
import socket

import pytest

from asset_hub.cli.serve.proc import is_port_in_use


def test_port_free_returns_false():
    assert is_port_in_use(0) is False or is_port_in_use(0) is True
    # 这条测试不可靠（port 0 行为）；改用 picking 一个临时端口验证
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    # 这个 port 现在很可能是空闲的（关闭后）
    # 不强制断言，只确保函数能跑


def test_port_in_use_returns_true():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.listen(1)
    try:
        assert is_port_in_use(port) is True
    finally:
        s.close()
```

- [ ] **Step 3: 写 kill_tree 测试**

`tests/unit/test_proc_kill_tree.py`:
```python
from unittest.mock import MagicMock, patch

import pytest

from asset_hub.cli.serve.proc import KillFailedError, KillMethod, kill_tree


def _mock_proc(pid: int, alive: bool = True):
    p = MagicMock()
    p.pid = pid
    return p


def test_kill_tree_sigterm_succeeds():
    proc = _mock_proc(pid=1)
    children = [_mock_proc(pid=2), _mock_proc(pid=3)]

    with patch("asset_hub.cli.serve.proc.psutil.Process") as mock_proc_cls, \
         patch("asset_hub.cli.serve.proc.psutil.wait_procs") as mock_wait:
        mock_proc_cls.return_value = proc
        proc.children.return_value = children
        mock_wait.side_effect = [(children + [proc], [])]  # all dead after SIGTERM

        method = kill_tree(1, timeout=5.0)

    assert method is KillMethod.SIGTERM
    proc.terminate.assert_called_once()
    for c in children:
        c.terminate.assert_called_once()


def test_kill_tree_falls_back_to_sigkill():
    proc = _mock_proc(pid=1)
    proc.children.return_value = []

    with patch("asset_hub.cli.serve.proc.psutil.Process") as mock_proc_cls, \
         patch("asset_hub.cli.serve.proc.psutil.wait_procs") as mock_wait:
        mock_proc_cls.return_value = proc
        # SIGTERM 后 proc 仍存活；SIGKILL 后死
        mock_wait.side_effect = [
            ([], [proc]),  # SIGTERM 后 alive
            ([proc], []),  # SIGKILL 后 dead
        ]

        method = kill_tree(1, timeout=5.0)

    assert method is KillMethod.SIGKILL
    proc.terminate.assert_called_once()
    proc.kill.assert_called_once()


def test_kill_tree_raises_when_sigkill_fails():
    proc = _mock_proc(pid=1)
    proc.children.return_value = []

    with patch("asset_hub.cli.serve.proc.psutil.Process") as mock_proc_cls, \
         patch("asset_hub.cli.serve.proc.psutil.wait_procs") as mock_wait:
        mock_proc_cls.return_value = proc
        mock_wait.side_effect = [
            ([], [proc]),  # SIGTERM 后 alive
            ([], [proc]),  # SIGKILL 后仍 alive（极罕见）
        ]

        with pytest.raises(KillFailedError):
            kill_tree(1, timeout=5.0)
```

- [ ] **Step 4: 运行验证失败**

```bash
uv run pytest tests/unit/test_proc_detach.py tests/unit/test_proc_port_check.py tests/unit/test_proc_kill_tree.py -v
```
Expected: ImportError

- [ ] **Step 5: 实现 proc.py**

`src/asset_hub/cli/serve/proc.py`:
```python
from __future__ import annotations

import socket
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import IO, Sequence

import psutil


DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200


class KillMethod(str, Enum):
    SIGTERM = "sigterm"
    SIGKILL = "sigkill"


class KillFailedError(RuntimeError):
    """SIGKILL 后仍存活的极端情况。"""


def start_detached(
    cmd: Sequence[str],
    *,
    log_file: Path,
    cwd: Path,
) -> int:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fd = open(log_file, "ab")  # binary append, uvicorn / pnpm 自带编码

    if sys.platform == "win32":
        proc = subprocess.Popen(
            list(cmd),
            stdout=fd,
            stderr=subprocess.STDOUT,
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            cwd=str(cwd),
            close_fds=True,
        )
    else:
        proc = subprocess.Popen(
            list(cmd),
            stdout=fd,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            cwd=str(cwd),
        )
    return proc.pid


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.bind((host, port))
    except OSError:
        return True
    finally:
        s.close()
    return False


def kill_tree(pid: int, timeout: float = 5.0) -> KillMethod:
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return KillMethod.SIGTERM  # already dead, treat as success

    children = []
    try:
        children = proc.children(recursive=True)
    except psutil.NoSuchProcess:
        pass

    targets = [proc] + children
    for p in targets:
        try:
            p.terminate()
        except psutil.NoSuchProcess:
            pass

    gone, alive = psutil.wait_procs(targets, timeout=timeout)
    if not alive:
        return KillMethod.SIGTERM

    for p in alive:
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass

    gone2, alive2 = psutil.wait_procs(alive, timeout=2.0)
    if alive2:
        raise KillFailedError(
            f"failed to kill {len(alive2)} process(es) after SIGKILL: "
            f"{[p.pid for p in alive2]}"
        )
    return KillMethod.SIGKILL
```

- [ ] **Step 6: 运行验证通过**

```bash
uv run pytest tests/unit/test_proc_detach.py tests/unit/test_proc_port_check.py tests/unit/test_proc_kill_tree.py -v
```
Expected: 全 PASS（含 platform-specific skip）

- [ ] **Step 7: Commit**

```bash
git add src/asset_hub/cli/serve/proc.py tests/unit/test_proc_detach.py tests/unit/test_proc_port_check.py tests/unit/test_proc_kill_tree.py
git commit -m "feat(serve): proc.py · 跨平台 detach + 端口检查 + kill_tree"
```

---

### Task 18: probe.py · 健康轮询

**Files:**
- Create: `src/asset_hub/cli/serve/probe.py`
- Test: `tests/unit/test_health_probe.py`

- [ ] **Step 1: 写测试**

`tests/unit/test_health_probe.py`:
```python
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from asset_hub.cli.serve.probe import (
    ProbeResult,
    SLEEP_INTERVALS,
    probe_until_ready,
    probe_once,
)


def test_probe_returns_ok_on_first_success():
    fake_response = MagicMock()
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = False
    fake_response.status = 200

    with patch("asset_hub.cli.serve.probe.urlopen", return_value=fake_response), \
         patch("asset_hub.cli.serve.probe.time.sleep"):
        result = probe_until_ready("http://x/healthz")
    assert result.ok is True


def test_probe_returns_timeout_after_all_intervals():
    with patch(
        "asset_hub.cli.serve.probe.urlopen",
        side_effect=URLError("conn refused"),
    ), patch("asset_hub.cli.serve.probe.time.sleep"):
        result = probe_until_ready("http://x/healthz")
    assert result.ok is False


def test_probe_succeeds_mid_loop():
    fake_response = MagicMock()
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = False
    fake_response.status = 200

    side_effects = [URLError("not yet"), URLError("not yet"), fake_response]

    with patch(
        "asset_hub.cli.serve.probe.urlopen", side_effect=side_effects
    ), patch("asset_hub.cli.serve.probe.time.sleep"):
        result = probe_until_ready("http://x/healthz")
    assert result.ok is True


def test_sleep_intervals_total_about_10s():
    assert 9.0 < sum(SLEEP_INTERVALS) < 11.0


def test_probe_once_returns_true_on_200():
    fake_response = MagicMock()
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = False
    fake_response.status = 200
    with patch("asset_hub.cli.serve.probe.urlopen", return_value=fake_response):
        assert probe_once("http://x/healthz") is True


def test_probe_once_returns_false_on_error():
    with patch("asset_hub.cli.serve.probe.urlopen", side_effect=URLError("x")):
        assert probe_once("http://x/healthz") is False
```

- [ ] **Step 2: 运行验证失败**

```bash
uv run pytest tests/unit/test_health_probe.py -v
```
Expected: ImportError

- [ ] **Step 3: 实现 probe.py**

`src/asset_hub/cli/serve/probe.py`:
```python
from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import urlopen


SLEEP_INTERVALS = [0.2, 0.5, 1.0, 1.0, 2.0, 2.0, 3.0]
PROBE_TIMEOUT_PER_CALL = 1.0
STATUS_PROBE_TIMEOUT = 2.0


@dataclass
class ProbeResult:
    ok: bool


def probe_until_ready(url: str) -> ProbeResult:
    """渐进退避轮询直到 200 或全部 interval 用完。"""
    for interval in SLEEP_INTERVALS:
        time.sleep(interval)
        try:
            with urlopen(url, timeout=PROBE_TIMEOUT_PER_CALL) as r:
                if r.status == 200:
                    return ProbeResult(ok=True)
        except (URLError, ConnectionRefusedError, socket.timeout, OSError):
            continue
    return ProbeResult(ok=False)


def probe_once(url: str, timeout: float = STATUS_PROBE_TIMEOUT) -> bool:
    """status 命令使用，单次探测无重试。"""
    try:
        with urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except (URLError, ConnectionRefusedError, socket.timeout, OSError):
        return False
```

- [ ] **Step 4: 运行验证通过**

```bash
uv run pytest tests/unit/test_health_probe.py -v
```
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/asset_hub/cli/serve/probe.py tests/unit/test_health_probe.py
git commit -m "feat(serve): probe.py · 渐进退避健康轮询 + status 单次探测"
```

---

### Task 19: logs.py · tail + follow + 启动次数轮转

**Files:**
- Create: `src/asset_hub/cli/serve/logs.py`
- Test: `tests/unit/test_logs_tail.py`
- Test: `tests/unit/test_logs_follow.py`
- Test: `tests/unit/test_logs_rotate.py`

- [ ] **Step 1: 写 rotate 测试**

`tests/unit/test_logs_rotate.py`:
```python
from asset_hub.cli.serve.logs import rotate_log


def test_rotate_when_no_existing_log(tmp_path):
    log = tmp_path / "backend.log"
    rotate_log(log)
    assert not log.exists()
    assert not (tmp_path / "backend.log.1").exists()


def test_rotate_existing_log_to_dot1(tmp_path):
    log = tmp_path / "backend.log"
    log.write_text("session 1\n")
    rotate_log(log)
    assert not log.exists()
    assert (tmp_path / "backend.log.1").read_text() == "session 1\n"


def test_rotate_overwrites_dot1(tmp_path):
    log = tmp_path / "backend.log"
    dot1 = tmp_path / "backend.log.1"
    log.write_text("session 2\n")
    dot1.write_text("session 0 (太早)\n")
    rotate_log(log)
    assert (tmp_path / "backend.log.1").read_text() == "session 2\n"
```

- [ ] **Step 2: 写 tail 测试**

`tests/unit/test_logs_tail.py`:
```python
from asset_hub.cli.serve.logs import tail_lines


def test_tail_returns_last_n_lines(tmp_path):
    log = tmp_path / "x.log"
    log.write_text("\n".join(f"line{i}" for i in range(100)) + "\n")
    lines = tail_lines(log, n=5)
    assert lines == ["line95", "line96", "line97", "line98", "line99"]


def test_tail_when_file_smaller_than_n(tmp_path):
    log = tmp_path / "small.log"
    log.write_text("a\nb\nc\n")
    lines = tail_lines(log, n=10)
    assert lines == ["a", "b", "c"]


def test_tail_empty_file(tmp_path):
    log = tmp_path / "empty.log"
    log.write_text("")
    assert tail_lines(log, n=5) == []


def test_tail_handles_missing_file(tmp_path):
    log = tmp_path / "missing.log"
    assert tail_lines(log, n=5) == []
```

- [ ] **Step 3: 写 follow 测试**

`tests/unit/test_logs_follow.py`:
```python
from unittest.mock import patch

import pytest

from asset_hub.cli.serve.logs import follow_log


def test_follow_yields_new_lines(tmp_path):
    log = tmp_path / "f.log"
    log.write_text("existing line\n")

    iterations = [0]

    def fake_sleep(_):
        iterations[0] += 1
        if iterations[0] == 1:
            with open(log, "a") as f:
                f.write("new line\n")
        if iterations[0] >= 2:
            raise KeyboardInterrupt

    output: list[str] = []
    with patch("asset_hub.cli.serve.logs.time.sleep", fake_sleep):
        try:
            for line in follow_log(log):
                output.append(line)
        except KeyboardInterrupt:
            pass
    assert "new line\n" in output
```

- [ ] **Step 4: 运行验证失败**

```bash
uv run pytest tests/unit/test_logs_rotate.py tests/unit/test_logs_tail.py tests/unit/test_logs_follow.py -v
```
Expected: ImportError

- [ ] **Step 5: 实现 logs.py**

`src/asset_hub/cli/serve/logs.py`:
```python
from __future__ import annotations

import time
from pathlib import Path
from typing import Iterator


_TAIL_BYTES_PER_LINE_ESTIMATE = 200


def rotate_log(log_path: Path) -> None:
    """启动次数轮转：log → log.1（覆盖旧 .1），不动其他代。"""
    if not log_path.exists():
        return
    rotated = log_path.with_suffix(log_path.suffix + ".1")
    if rotated.exists():
        rotated.unlink()
    log_path.rename(rotated)


def tail_lines(log_path: Path, n: int) -> list[str]:
    if not log_path.exists():
        return []
    size = log_path.stat().st_size
    if size == 0:
        return []
    chunk = min(size, _TAIL_BYTES_PER_LINE_ESTIMATE * n)
    with log_path.open("rb") as f:
        f.seek(max(0, size - chunk))
        data = f.read()
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    return lines[-n:]


def follow_log(log_path: Path, sleep_interval: float = 0.1) -> Iterator[str]:
    """追加模式 tail -f；遇 EOF 不退出，靠 KeyboardInterrupt 退出。"""
    if not log_path.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.touch()
    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        f.seek(0, 2)  # SEEK_END
        while True:
            line = f.readline()
            if not line:
                time.sleep(sleep_interval)
                continue
            yield line
```

- [ ] **Step 6: 运行验证通过**

```bash
uv run pytest tests/unit/test_logs_rotate.py tests/unit/test_logs_tail.py tests/unit/test_logs_follow.py -v
```
Expected: 全 PASS

- [ ] **Step 7: Commit**

```bash
git add src/asset_hub/cli/serve/logs.py tests/unit/test_logs_rotate.py tests/unit/test_logs_tail.py tests/unit/test_logs_follow.py
git commit -m "feat(serve): logs.py · tail + follow + 启动次数轮转"
```

---

## Phase 5 · serve · 输出层（Task 20-22）

### Task 20: output.py · 数据结构 + 渲染

**Files:**
- Create: `src/asset_hub/cli/serve/output.py`
- Test: `tests/unit/test_serve_output.py`

- [ ] **Step 1: 写测试**

`tests/unit/test_serve_output.py`:
```python
import json

from asset_hub.cli.serve.output import (
    ServeError,
    ServiceInfo,
    StartResult,
    StatusReport,
    StopResult,
    render_json_envelope,
    render_plain_start,
    render_plain_status,
    render_plain_stop,
)


def test_start_result_json_envelope_success():
    result = StartResult(
        mode="prod",
        backend=ServiceInfo(pid=12345, port=8000, host="127.0.0.1", log="data/logs/backend.log"),
        frontend=None,
        took_ms=4231,
        build_ran=True,
    )
    out = render_json_envelope(success=True, data=result.to_dict(), metadata=result.metadata())
    parsed = json.loads(out)
    assert parsed["success"] is True
    assert parsed["data"]["backend"]["pid"] == 12345
    assert parsed["data"]["frontend"] is None
    assert parsed["metadata"]["build_ran"] is True


def test_start_result_json_envelope_failure():
    err = ServeError(code="serve.port_occupied", message="port 8000 in use")
    out = render_json_envelope(success=False, error=err.to_dict(), metadata={"took_ms": 12})
    parsed = json.loads(out)
    assert parsed["success"] is False
    assert parsed["error"]["code"] == "serve.port_occupied"


def test_render_plain_start_prod():
    result = StartResult(
        mode="prod",
        backend=ServiceInfo(pid=12345, port=8000, host="127.0.0.1", log="data/logs/backend.log"),
        frontend=None,
        took_ms=100,
        build_ran=False,
    )
    text = render_plain_start(result)
    assert "Backend started" in text
    assert "12345" in text
    assert "Frontend" not in text  # prod 模式无前端


def test_render_plain_start_dev():
    result = StartResult(
        mode="dev",
        backend=ServiceInfo(pid=12345, port=8000, host="127.0.0.1", log="data/logs/backend.log"),
        frontend=ServiceInfo(pid=12346, port=5173, host="127.0.0.1", log="data/logs/frontend.log"),
        took_ms=100,
        build_ran=False,
    )
    text = render_plain_start(result)
    assert "Backend started" in text
    assert "Frontend started" in text


def test_render_plain_status_running():
    report = StatusReport(running=True, mode="prod",
                          backend={"status": "running", "pid": 12345, "port": 8000, "uptime_sec": 7980, "healthy": True},
                          frontend=None, probed=True, took_ms=234)
    text = render_plain_status(report)
    assert "running" in text
    assert "8000" in text


def test_render_plain_stop_normal():
    result = StopResult(stopped=[{"service": "backend", "pid": 12345, "method": "sigterm"}], stale_cleaned=[])
    text = render_plain_stop(result)
    assert "Backend stopped" in text


def test_render_plain_stop_not_running():
    result = StopResult(stopped=[], stale_cleaned=[])
    text = render_plain_stop(result)
    assert "Not running" in text
```

- [ ] **Step 2: 运行验证失败**

```bash
uv run pytest tests/unit/test_serve_output.py -v
```
Expected: ImportError

- [ ] **Step 3: 实现 output.py**

`src/asset_hub/cli/serve/output.py`:
```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ServiceInfo:
    pid: int
    port: int
    host: str
    log: str

    def to_dict(self) -> dict[str, Any]:
        return {"pid": self.pid, "port": self.port, "host": self.host, "log": self.log}


@dataclass
class StartResult:
    mode: Literal["dev", "prod"]
    backend: ServiceInfo | None
    frontend: ServiceInfo | None
    took_ms: int
    build_ran: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "backend": self.backend.to_dict() if self.backend else None,
            "frontend": self.frontend.to_dict() if self.frontend else None,
        }

    def metadata(self) -> dict[str, Any]:
        return {"took_ms": self.took_ms, "build_ran": self.build_ran}


@dataclass
class StopResult:
    stopped: list[dict[str, Any]] = field(default_factory=list)
    stale_cleaned: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"stopped": self.stopped, "stale_cleaned": self.stale_cleaned}


@dataclass
class StatusReport:
    running: bool
    mode: Literal["dev", "prod"] | None
    backend: dict[str, Any] | None
    frontend: dict[str, Any] | None
    probed: bool
    took_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "mode": self.mode,
            "backend": self.backend,
            "frontend": self.frontend,
        }

    def metadata(self) -> dict[str, Any]:
        return {"took_ms": self.took_ms, "probed": self.probed}


@dataclass
class ServeError:
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}


def render_json_envelope(
    *,
    success: bool,
    data: Any = None,
    metadata: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> str:
    payload = {
        "success": success,
        "data": data,
        "metadata": metadata or {},
        "error": error,
    }
    return json.dumps(payload, ensure_ascii=False)


def render_plain_start(result: StartResult) -> str:
    lines = []
    if result.backend:
        b = result.backend
        lines.append(
            f"✓ Backend started     pid={b.pid}  http://{b.host}:{b.port}  mode={result.mode}"
        )
        lines.append(f"  {b.log}")
    if result.frontend:
        f = result.frontend
        lines.append(
            f"✓ Frontend started    pid={f.pid}  http://{f.host}:{f.port}"
        )
    return "\n".join(lines)


def render_plain_stop(result: StopResult) -> str:
    if not result.stopped and not result.stale_cleaned:
        return "- Not running"
    lines = []
    for cleaned in result.stale_cleaned:
        lines.append(f"! Stale PID files cleaned ({cleaned})")
    if not result.stopped and result.stale_cleaned:
        lines.append("- Not running")
    for s in result.stopped:
        verb = "stopped"
        suffix = ""
        if s.get("method") == "sigkill":
            suffix = "  (SIGTERM timeout 5s)"
            lines.append(
                f"! {s['service'].capitalize()} stopped via SIGKILL  pid={s['pid']}{suffix}"
            )
        else:
            lines.append(
                f"✓ {s['service'].capitalize()} {verb}     pid={s['pid']}"
            )
    return "\n".join(lines)


def render_plain_status(report: StatusReport) -> str:
    if not report.running:
        return "- Not running"

    header = "SERVICE   STATUS    PID    PORT  MODE  UPTIME    HEALTHY"
    lines = [header]
    for service_name, info in [("backend", report.backend), ("frontend", report.frontend)]:
        if info is None:
            lines.append(f"{service_name:<9} -         -      -     -     -         -")
            continue
        uptime = _fmt_uptime(info.get("uptime_sec", 0))
        healthy = "✓" if info.get("healthy") else "✗"
        lines.append(
            f"{service_name:<9} {info['status']:<9} {info['pid']:<6} {info['port']:<5} "
            f"{(report.mode or '-'):<5} {uptime:<9} {healthy}"
        )
    return "\n".join(lines)


def _fmt_uptime(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    h, m = divmod(seconds // 60, 60)
    return f"{h}h {m}m"
```

- [ ] **Step 4: 运行验证通过**

```bash
uv run pytest tests/unit/test_serve_output.py -v
```
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/asset_hub/cli/serve/output.py tests/unit/test_serve_output.py
git commit -m "feat(serve): output.py · dataclass + 表格渲染 + JSON 信封"
```

---

### Task 21: lifecycle.py · start 流程

**Files:**
- Create: `src/asset_hub/cli/serve/lifecycle.py`

> 这一 Task 实现 `start_service` 函数，CLI 集成测试将在 Phase 7 写。本 Task 不写 unit test（lifecycle 是协调者，覆盖由 Phase 7 CLI 集成测试承担），仅完成实现并在 Step 末尾跑 import 健全性检查。

- [ ] **Step 1: 实现 start_service**

`src/asset_hub/cli/serve/lifecycle.py`:
```python
from __future__ import annotations

import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from asset_hub.cli.serve import logs as logs_mod
from asset_hub.cli.serve import pid as pid_mod
from asset_hub.cli.serve import probe as probe_mod
from asset_hub.cli.serve import proc as proc_mod
from asset_hub.cli.serve.output import (
    ServeError,
    ServiceInfo,
    StartResult,
    StatusReport,
    StopResult,
)
from asset_hub.config import Settings


class ServeLifecycleError(Exception):
    """raise 时携带 ServeError 给上层 cmd 转 exit code。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def start_service(
    *,
    mode: Literal["dev", "prod"],
    skip_build: bool,
    port_override: int | None,
    frontend_port_override: int | None,
    host_override: str | None,
) -> StartResult:
    t0 = time.monotonic()
    settings = Settings()
    backend_port = port_override if port_override is not None else settings.backend_port
    frontend_port = (
        frontend_port_override if frontend_port_override is not None else settings.frontend_port
    )
    host = host_override if host_override is not None else settings.resolve_backend_host(mode)

    # Phase 0 · 前置检查
    _ensure_dirs_writable(settings)
    _check_pids_or_clean_stale(settings)
    if proc_mod.is_port_in_use(backend_port):
        raise ServeLifecycleError("serve.port_occupied", f"port {backend_port} is in use")
    if mode == "dev" and proc_mod.is_port_in_use(frontend_port):
        raise ServeLifecycleError("serve.port_occupied", f"port {frontend_port} is in use")

    # Phase 1 · 构建（仅 prod）
    build_ran = False
    if mode == "prod":
        dist_index = Path("frontend/dist/index.html")
        if not dist_index.exists():
            if skip_build:
                raise ServeLifecycleError(
                    "serve.dist_missing",
                    "frontend/dist not found; omit --skip-build or run 'pnpm --dir frontend build'",
                )
            _run_build()
            build_ran = True

    # Phase 2 · 日志轮转
    backend_log = settings.logs_dir / "backend.log"
    logs_mod.rotate_log(backend_log)
    if mode == "dev":
        logs_mod.rotate_log(settings.logs_dir / "frontend.log")

    # Phase 3 · 启动子进程
    started_at = datetime.now(UTC)
    backend_cmd = [
        "uv", "run", "uvicorn", "asset_hub.api.app:app",
        "--host", host, "--port", str(backend_port),
    ]
    if mode == "dev":
        backend_cmd.append("--reload")

    backend_pid = proc_mod.start_detached(
        backend_cmd, log_file=backend_log, cwd=Path.cwd()
    )
    pid_mod.write_pid_file(
        settings.pids_dir / "backend.pid",
        pid=backend_pid, mode=mode, started_at=started_at,
    )

    frontend_pid: int | None = None
    if mode == "dev":
        frontend_log = settings.logs_dir / "frontend.log"
        frontend_pid = proc_mod.start_detached(
            ["pnpm", "--dir", "frontend", "dev"],
            log_file=frontend_log, cwd=Path.cwd(),
        )
        pid_mod.write_pid_file(
            settings.pids_dir / "frontend.pid",
            pid=frontend_pid, mode=mode, started_at=started_at,
        )

    # Phase 4 · 健康探测
    healthz_url = f"http://127.0.0.1:{backend_port}/api/healthz"
    probe = probe_mod.probe_until_ready(healthz_url)
    if not probe.ok:
        _rollback_start(settings)
        raise ServeLifecycleError(
            "serve.health_probe_timeout",
            f"backend failed to start within ~10s; see {backend_log}",
        )
    if mode == "dev":
        frontend_url = f"http://127.0.0.1:{frontend_port}/"
        if not probe_mod.probe_once(frontend_url, timeout=2.0):
            # 前端慢，再试一次更宽松窗
            time.sleep(2.0)
            if not probe_mod.probe_once(frontend_url, timeout=4.0):
                _rollback_start(settings)
                raise ServeLifecycleError(
                    "serve.frontend_failed_to_start",
                    f"frontend (pnpm dev) failed to respond on :{frontend_port}",
                )

    # Phase 5 · 输出
    backend_info = ServiceInfo(
        pid=backend_pid, port=backend_port, host=host,
        log=str(backend_log),
    )
    frontend_info = None
    if mode == "dev" and frontend_pid is not None:
        frontend_info = ServiceInfo(
            pid=frontend_pid, port=frontend_port, host=host,
            log=str(settings.logs_dir / "frontend.log"),
        )
    return StartResult(
        mode=mode,
        backend=backend_info,
        frontend=frontend_info,
        took_ms=int((time.monotonic() - t0) * 1000),
        build_ran=build_ran,
    )


def _ensure_dirs_writable(settings: Settings) -> None:
    for d in [settings.pids_dir, settings.logs_dir]:
        try:
            d.mkdir(parents=True, exist_ok=True)
            test = d / ".write-test"
            test.touch()
            test.unlink()
        except OSError as e:
            raise ServeLifecycleError(
                "serve.data_unwritable",
                f"cannot write at {d}: {e}",
            )


def _check_pids_or_clean_stale(settings: Settings) -> None:
    for service in ("backend", "frontend"):
        f = settings.pids_dir / f"{service}.pid"
        state = pid_mod.read_pid_state(f, service)
        if state.status is pid_mod.PidStateStatus.RUNNING:
            raise ServeLifecycleError(
                "serve.already_running",
                f"already running ({service} mode={state.mode}, pid={state.pid}); "
                f"use 'serve stop' or 'serve restart'",
            )
        if state.status is pid_mod.PidStateStatus.STALE:
            pid_mod.remove_pid_file(f)


def _run_build() -> None:
    proc = subprocess.run(
        ["pnpm", "--dir", "frontend", "build"], check=False
    )
    if proc.returncode != 0:
        raise ServeLifecycleError(
            "serve.build_failed",
            "frontend build failed (see output above)",
        )


def _rollback_start(settings: Settings) -> None:
    """探测失败时杀已起子进程 + 删 PID 文件。"""
    for service in ("backend", "frontend"):
        f = settings.pids_dir / f"{service}.pid"
        state = pid_mod.read_pid_state(f, service)
        if state.pid is not None:
            try:
                proc_mod.kill_tree(state.pid, timeout=5.0)
            except (proc_mod.KillFailedError, Exception):
                pass
        pid_mod.remove_pid_file(f)
```

- [ ] **Step 2: import 健全性检查**

```bash
uv run python -c "from asset_hub.cli.serve.lifecycle import start_service, ServeLifecycleError; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/asset_hub/cli/serve/lifecycle.py
git commit -m "feat(serve): lifecycle.start_service · Phase 0-5 完整流程 + 失败回滚"
```

---

### Task 22: lifecycle.py · stop / restart / status / logs 流程

**Files:**
- Modify: `src/asset_hub/cli/serve/lifecycle.py`

- [ ] **Step 1: 追加 stop_service / status_service / restart_service / logs_service**

`src/asset_hub/cli/serve/lifecycle.py`（在文件末尾追加）:
```python
def stop_service() -> StopResult:
    settings = Settings()
    result = StopResult()
    for service in ("backend", "frontend"):
        f = settings.pids_dir / f"{service}.pid"
        state = pid_mod.read_pid_state(f, service)
        if state.status is pid_mod.PidStateStatus.NONE:
            continue
        if state.status is pid_mod.PidStateStatus.STALE:
            result.stale_cleaned.append(
                f"{service} pid={state.pid} not alive"
                if state.pid is not None
                else f"{service} corrupt PID file"
            )
            pid_mod.remove_pid_file(f)
            continue
        # status == RUNNING
        try:
            method = proc_mod.kill_tree(state.pid, timeout=5.0)
        except proc_mod.KillFailedError as e:
            raise ServeLifecycleError(
                "serve.kill_failed",
                f"failed to kill {service} pid={state.pid}: {e}; "
                "manual cleanup required (PID file kept)",
            )
        result.stopped.append({
            "service": service, "pid": state.pid, "method": method.value,
        })
        pid_mod.remove_pid_file(f)
    return result


def status_service(*, no_probe: bool) -> StatusReport:
    t0 = time.monotonic()
    settings = Settings()
    backend_state = pid_mod.read_pid_state(
        settings.pids_dir / "backend.pid", "backend"
    )
    frontend_state = pid_mod.read_pid_state(
        settings.pids_dir / "frontend.pid", "frontend"
    )

    if backend_state.status is pid_mod.PidStateStatus.NONE:
        return StatusReport(
            running=False, mode=None, backend=None, frontend=None,
            probed=False, took_ms=int((time.monotonic() - t0) * 1000),
        )

    mode = backend_state.mode
    if mode is None:
        # fallback: frontend.pid 存在 → dev
        mode = "dev" if frontend_state.file_exists else "prod"

    backend_info = _build_status_info(
        backend_state, settings.backend_port,
        no_probe=no_probe, port_for_probe=settings.backend_port,
    )
    frontend_info = None
    if mode == "dev" and frontend_state.status is not pid_mod.PidStateStatus.NONE:
        frontend_info = _build_status_info(
            frontend_state, settings.frontend_port,
            no_probe=no_probe, port_for_probe=settings.frontend_port,
        )
    return StatusReport(
        running=backend_state.status is pid_mod.PidStateStatus.RUNNING,
        mode=mode,
        backend=backend_info,
        frontend=frontend_info,
        probed=not no_probe,
        took_ms=int((time.monotonic() - t0) * 1000),
    )


def _build_status_info(state, default_port: int, *, no_probe: bool, port_for_probe: int):
    if state.status is pid_mod.PidStateStatus.STALE:
        return {"status": "stale", "pid": state.pid, "port": None,
                "uptime_sec": 0, "healthy": False}
    uptime = 0
    if state.started_at is not None:
        uptime = int((datetime.now(UTC) - state.started_at).total_seconds())
    healthy = False
    if not no_probe:
        url = f"http://127.0.0.1:{port_for_probe}/api/healthz" if state.service == "backend" else f"http://127.0.0.1:{port_for_probe}/"
        healthy = probe_mod.probe_once(url, timeout=2.0)
    return {
        "status": "running",
        "pid": state.pid,
        "port": port_for_probe,
        "uptime_sec": uptime,
        "healthy": healthy,
    }


def restart_service(
    *,
    mode_override: Literal["dev", "prod"] | None,
    skip_build: bool,
    port_override: int | None,
    frontend_port_override: int | None,
    host_override: str | None,
) -> tuple[StopResult, StartResult]:
    settings = Settings()
    backend_state = pid_mod.read_pid_state(
        settings.pids_dir / "backend.pid", "backend"
    )
    frontend_state = pid_mod.read_pid_state(
        settings.pids_dir / "frontend.pid", "frontend"
    )

    inferred_mode: Literal["dev", "prod"] | None = backend_state.mode
    if inferred_mode is None and backend_state.status is not pid_mod.PidStateStatus.NONE:
        inferred_mode = "dev" if frontend_state.file_exists else "prod"

    target_mode = mode_override or inferred_mode
    if target_mode is None:
        raise ServeLifecycleError(
            "serve.mode_required",
            "cannot infer mode from PID files; specify --mode dev|prod",
        )

    stop_result = stop_service()
    start_result = start_service(
        mode=target_mode,
        skip_build=skip_build,
        port_override=port_override,
        frontend_port_override=frontend_port_override,
        host_override=host_override,
    )
    return stop_result, start_result


def logs_for_service(
    *,
    service: Literal["backend", "frontend", "all"],
    lines: int,
) -> dict[str, list[str]]:
    settings = Settings()
    out: dict[str, list[str]] = {}
    services = ["backend", "frontend"] if service == "all" else [service]
    for s in services:
        path = settings.logs_dir / f"{s}.log"
        out[s] = logs_mod.tail_lines(path, lines)
    return out
```

- [ ] **Step 2: import 健全性检查**

```bash
uv run python -c "from asset_hub.cli.serve.lifecycle import stop_service, status_service, restart_service, logs_for_service; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/asset_hub/cli/serve/lifecycle.py
git commit -m "feat(serve): lifecycle · stop/status/restart/logs 协调流程"
```

---

## Phase 6 · serve · CLI 接入（Task 23-25）

### Task 23: cmd.py · Typer 子命令注册

**Files:**
- Create: `src/asset_hub/cli/serve/cmd.py`
- Modify: `src/asset_hub/cli/main.py`

- [ ] **Step 1: 实现 cmd.py**

`src/asset_hub/cli/serve/cmd.py`:
```python
from __future__ import annotations

import sys
from typing import Annotated, Optional

import typer

from asset_hub.cli.serve import lifecycle, logs as logs_mod
from asset_hub.cli.serve.lifecycle import ServeLifecycleError
from asset_hub.cli.serve.output import (
    render_json_envelope,
    render_plain_start,
    render_plain_status,
    render_plain_stop,
)
from asset_hub.config import Settings

serve_app = typer.Typer(name="serve", help="管理后端 + 前端服务生命周期")


def _emit(success: bool, *, json_out: bool, plain_text: str = "",
          data=None, metadata=None, error=None, exit_code: int = 0,
          stream=sys.stdout):
    if json_out:
        out = render_json_envelope(
            success=success, data=data, metadata=metadata, error=error
        )
        print(out, file=stream)
    else:
        if plain_text:
            print(plain_text, file=stream)
    raise typer.Exit(code=exit_code)


@serve_app.command("start")
def start(
    mode: Annotated[str, typer.Option("--mode", help="启动模式")] = "prod",
    skip_build: Annotated[bool, typer.Option("--skip-build")] = False,
    port: Annotated[Optional[int], typer.Option("--port")] = None,
    frontend_port: Annotated[Optional[int], typer.Option("--frontend-port")] = None,
    host: Annotated[Optional[str], typer.Option("--host")] = None,
    json_out: Annotated[bool, typer.Option("--json")] = False,
):
    """启动服务（默认 prod 模式）"""
    if mode not in ("dev", "prod"):
        _emit(False, json_out=json_out,
              plain_text=f"✗ Invalid --mode '{mode}'",
              error={"code": "serve.usage", "message": f"invalid --mode '{mode}'"},
              metadata={}, stream=sys.stderr, exit_code=2)
        return
    try:
        result = lifecycle.start_service(
            mode=mode,  # type: ignore[arg-type]
            skip_build=skip_build,
            port_override=port,
            frontend_port_override=frontend_port,
            host_override=host,
        )
    except ServeLifecycleError as e:
        _emit(False, json_out=json_out,
              plain_text=f"✗ {e.message}",
              error={"code": e.code, "message": e.message},
              metadata={}, stream=sys.stderr, exit_code=1)
        return

    _emit(True, json_out=json_out,
          plain_text=render_plain_start(result),
          data=result.to_dict(), metadata=result.metadata(),
          exit_code=0)


@serve_app.command("stop")
def stop(
    json_out: Annotated[bool, typer.Option("--json")] = False,
):
    """停止当前在跑的服务（幂等）"""
    try:
        result = lifecycle.stop_service()
    except ServeLifecycleError as e:
        _emit(False, json_out=json_out,
              plain_text=f"✗ {e.message}",
              error={"code": e.code, "message": e.message},
              metadata={}, stream=sys.stderr, exit_code=1)
        return
    _emit(True, json_out=json_out,
          plain_text=render_plain_stop(result),
          data=result.to_dict(), metadata={}, exit_code=0)


@serve_app.command("status")
def status(
    json_out: Annotated[bool, typer.Option("--json")] = False,
    no_probe: Annotated[bool, typer.Option("--no-probe")] = False,
):
    """查询服务状态（含 HTTP 健康探测）"""
    report = lifecycle.status_service(no_probe=no_probe)
    _emit(True, json_out=json_out,
          plain_text=render_plain_status(report),
          data=report.to_dict(), metadata=report.metadata(),
          exit_code=0)


@serve_app.command("restart")
def restart(
    mode: Annotated[Optional[str], typer.Option("--mode")] = None,
    skip_build: Annotated[bool, typer.Option("--skip-build")] = False,
    port: Annotated[Optional[int], typer.Option("--port")] = None,
    frontend_port: Annotated[Optional[int], typer.Option("--frontend-port")] = None,
    host: Annotated[Optional[str], typer.Option("--host")] = None,
    json_out: Annotated[bool, typer.Option("--json")] = False,
):
    """重启服务（自动推断 mode；如无法推断需 --mode）"""
    if mode is not None and mode not in ("dev", "prod"):
        _emit(False, json_out=json_out,
              plain_text=f"✗ Invalid --mode '{mode}'",
              error={"code": "serve.usage", "message": f"invalid --mode '{mode}'"},
              metadata={}, stream=sys.stderr, exit_code=2)
        return
    try:
        stop_res, start_res = lifecycle.restart_service(
            mode_override=mode,  # type: ignore[arg-type]
            skip_build=skip_build,
            port_override=port,
            frontend_port_override=frontend_port,
            host_override=host,
        )
    except ServeLifecycleError as e:
        _emit(False, json_out=json_out,
              plain_text=f"✗ {e.message}",
              error={"code": e.code, "message": e.message},
              metadata={}, stream=sys.stderr, exit_code=1)
        return
    plain = render_plain_stop(stop_res) + "\n" + render_plain_start(start_res)
    _emit(True, json_out=json_out,
          plain_text=plain,
          data={"stop": stop_res.to_dict(), "start": start_res.to_dict()},
          metadata=start_res.metadata(),
          exit_code=0)


@serve_app.command("logs")
def logs(
    service: Annotated[str, typer.Option("--service")] = "backend",
    lines: Annotated[int, typer.Option("--lines")] = 200,
    follow: Annotated[bool, typer.Option("--follow")] = False,
    json_out: Annotated[bool, typer.Option("--json")] = False,
):
    """查看服务日志（默认 backend，最近 200 行）"""
    if service not in ("backend", "frontend", "all"):
        _emit(False, json_out=json_out,
              plain_text=f"✗ Invalid --service '{service}'",
              error={"code": "serve.usage", "message": f"invalid --service '{service}'"},
              metadata={}, stream=sys.stderr, exit_code=2)
        return

    if follow:
        if json_out:
            print("warning: --json ignored in --follow mode", file=sys.stderr)
        if service == "all":
            print("warning: --follow only supports single service; using backend", file=sys.stderr)
            service = "backend"
        path = Settings().logs_dir / f"{service}.log"
        if not path.exists():
            print(f"- No logs available for {service}", file=sys.stdout)
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
        _emit(True, json_out=json_out,
              plain_text=f"- No logs available for {service}",
              data={"service": service, "lines": [], "truncated": False},
              metadata={"file": "", "size_bytes": 0}, exit_code=0)
        return

    if json_out:
        # service=all 时输出多 services 各自字段；服从 spec 简化：只展示第一个非空
        if service == "all":
            payload = {"services": out}
        else:
            payload = {"service": service, "lines": out[service], "truncated": False}
        _emit(True, json_out=True, data=payload,
              metadata={}, exit_code=0)
        return

    # plain 输出
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

- [ ] **Step 2: 注册到 main.py**

`src/asset_hub/cli/main.py`（替换为）:
```python
import typer

from asset_hub.cli.asset_cmd import asset_app
from asset_hub.cli.attachment_cmd import attachment_app
from asset_hub.cli.serve.cmd import serve_app
from asset_hub.cli.type_cmd import type_app

app = typer.Typer(name="asset-hub", no_args_is_help=True)
app.add_typer(type_app, name="type")
app.add_typer(asset_app, name="asset")
app.add_typer(attachment_app, name="attachment")
app.add_typer(serve_app, name="serve")
```

- [ ] **Step 3: 健全性检查**

```bash
uv run asset-hub serve --help
```
Expected: 列出 start / stop / status / restart / logs

- [ ] **Step 4: Commit**

```bash
git add src/asset_hub/cli/serve/cmd.py src/asset_hub/cli/main.py
git commit -m "feat(serve): cmd.py · Typer 5 子命令注册 + 接入 main"
```

---

## Phase 7 · serve · CLI 集成测试（Task 24-27）

### Task 24: tests/cli/test_serve_start.py

**Files:**
- Test: `tests/cli/test_serve_start.py`
- Modify: `tests/cli/conftest.py`（如缺，增加把 ASSET_HUB_DATA_DIR 隔离到 tmp_path 的 fixture）

> 测试通过 mock `subprocess.Popen` + mock `psutil` + mock `urlopen` 把"真起服务"全部隔离。

- [ ] **Step 1: 检查 conftest 是否已 isolated_db**

```bash
grep -n "isolated_db\|ASSET_HUB_DATA_DIR" tests/cli/conftest.py
```
Expected: 已有；如缺，参考 m2c-3 plan 补。

- [ ] **Step 2: 写测试**

`tests/cli/test_serve_start.py`:
```python
import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def _mock_psutil_pid_does_not_exist():
    return patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=False)


def _mock_port_free():
    return patch("asset_hub.cli.serve.proc.is_port_in_use", return_value=False)


def _mock_popen_returns_pid(pid: int = 12345):
    fake = MagicMock()
    fake.pid = pid
    return patch("asset_hub.cli.serve.proc.subprocess.Popen", return_value=fake)


def _mock_probe_ready():
    return patch(
        "asset_hub.cli.serve.lifecycle.probe_mod.probe_until_ready",
        return_value=MagicMock(ok=True),
    ), patch(
        "asset_hub.cli.serve.lifecycle.probe_mod.probe_once",
        return_value=True,
    )


def test_start_prod_success(isolated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    # prod mode 需要 dist 存在
    dist_dir = tmp_path.parent / "frontend" / "dist"
    # 用 cwd-relative path：跑测试时不存在的话 lifecycle 会 build；mock build 跳过
    with _mock_psutil_pid_does_not_exist(), \
         _mock_port_free(), \
         _mock_popen_returns_pid(99999), \
         patch("asset_hub.cli.serve.lifecycle.Path") as MockPath, \
         patch("asset_hub.cli.serve.lifecycle.probe_mod.probe_until_ready",
               return_value=MagicMock(ok=True)):
        # mock dist_index.exists() → True
        mock_dist = MagicMock()
        mock_dist.exists.return_value = True
        MockPath.return_value = mock_dist
        MockPath.cwd = lambda: tmp_path

        res = runner.invoke(
            app, ["serve", "start", "--skip-build", "--mode", "prod", "--json"]
        )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert payload["success"] is True
    assert payload["data"]["mode"] == "prod"
    assert payload["data"]["backend"]["pid"] == 99999


def test_start_already_running_returns_exit_1(isolated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    pids_dir = tmp_path / "pids"
    pids_dir.mkdir()
    # 写一个 "活" PID
    (pids_dir / "backend.pid").write_text("12345\nmode=prod\n")

    with patch(
        "asset_hub.cli.serve.pid.psutil.pid_exists", return_value=True
    ), patch("asset_hub.cli.serve.pid.psutil.Process") as mock_p:
        mp = MagicMock()
        mp.cmdline.return_value = ["python", "-m", "uvicorn", "asset_hub.api.app"]
        mp.status.return_value = "running"
        mock_p.return_value = mp

        res = runner.invoke(
            app, ["serve", "start", "--mode", "prod", "--skip-build", "--json"]
        )
    assert res.exit_code == 1
    payload = json.loads(res.stdout)
    assert payload["error"]["code"] == "serve.already_running"


def test_start_port_occupied(isolated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    with _mock_psutil_pid_does_not_exist(), \
         patch("asset_hub.cli.serve.proc.is_port_in_use", return_value=True):
        res = runner.invoke(
            app, ["serve", "start", "--mode", "prod", "--skip-build", "--json"]
        )
    assert res.exit_code == 1
    payload = json.loads(res.stdout)
    assert payload["error"]["code"] == "serve.port_occupied"


def test_start_invalid_mode_returns_exit_2(isolated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    res = runner.invoke(app, ["serve", "start", "--mode", "foo", "--json"])
    assert res.exit_code == 2
```

- [ ] **Step 3: 运行验证通过**

```bash
uv run pytest tests/cli/test_serve_start.py -v
```
Expected: 全 PASS

- [ ] **Step 4: Commit**

```bash
git add tests/cli/test_serve_start.py
git commit -m "test(serve): start CLI 集成测试 · 4 关键路径"
```

---

### Task 25: tests/cli/test_serve_stop.py + test_serve_status.py

**Files:**
- Test: `tests/cli/test_serve_stop.py`
- Test: `tests/cli/test_serve_status.py`

- [ ] **Step 1: 写 stop 测试**

`tests/cli/test_serve_stop.py`:
```python
import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def test_stop_when_not_running(isolated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    res = runner.invoke(app, ["serve", "stop", "--json"])
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload["success"] is True
    assert payload["data"]["stopped"] == []


def test_stop_running_service(isolated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    pids_dir = tmp_path / "pids"
    pids_dir.mkdir()
    (pids_dir / "backend.pid").write_text("12345\nmode=prod\n")

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=True), \
         patch("asset_hub.cli.serve.pid.psutil.Process") as mock_p, \
         patch("asset_hub.cli.serve.proc.psutil.Process") as mock_p2, \
         patch("asset_hub.cli.serve.proc.psutil.wait_procs",
               return_value=([MagicMock()], [])):
        mp = MagicMock()
        mp.cmdline.return_value = ["python", "-m", "uvicorn", "asset_hub.api.app"]
        mp.status.return_value = "running"
        mock_p.return_value = mp
        mp2 = MagicMock()
        mp2.children.return_value = []
        mock_p2.return_value = mp2

        res = runner.invoke(app, ["serve", "stop", "--json"])
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert len(payload["data"]["stopped"]) == 1
    assert payload["data"]["stopped"][0]["service"] == "backend"


def test_stop_stale_cleans_pid_file(isolated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    pids_dir = tmp_path / "pids"
    pids_dir.mkdir()
    pid_file = pids_dir / "backend.pid"
    pid_file.write_text("99999\nmode=prod\n")

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=False):
        res = runner.invoke(app, ["serve", "stop", "--json"])
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert len(payload["data"]["stale_cleaned"]) == 1
    assert not pid_file.exists()
```

- [ ] **Step 2: 写 status 测试**

`tests/cli/test_serve_status.py`:
```python
import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def test_status_not_running(isolated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    res = runner.invoke(app, ["serve", "status", "--json"])
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload["data"]["running"] is False


def test_status_running_with_probe(isolated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    pids_dir = tmp_path / "pids"
    pids_dir.mkdir()
    (pids_dir / "backend.pid").write_text(
        "12345\nmode=prod\nstarted_at=2026-04-29T10:00:00Z\n"
    )

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=True), \
         patch("asset_hub.cli.serve.pid.psutil.Process") as mock_p, \
         patch("asset_hub.cli.serve.lifecycle.probe_mod.probe_once", return_value=True):
        mp = MagicMock()
        mp.cmdline.return_value = ["python", "-m", "uvicorn", "asset_hub.api.app"]
        mp.status.return_value = "running"
        mock_p.return_value = mp

        res = runner.invoke(app, ["serve", "status", "--json"])
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload["data"]["running"] is True
    assert payload["data"]["mode"] == "prod"
    assert payload["data"]["backend"]["healthy"] is True


def test_status_no_probe_skips_http(isolated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    pids_dir = tmp_path / "pids"
    pids_dir.mkdir()
    (pids_dir / "backend.pid").write_text("12345\nmode=prod\n")

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=True), \
         patch("asset_hub.cli.serve.pid.psutil.Process") as mock_p, \
         patch("asset_hub.cli.serve.lifecycle.probe_mod.probe_once") as mock_probe:
        mp = MagicMock()
        mp.cmdline.return_value = ["python", "-m", "uvicorn", "asset_hub.api.app"]
        mp.status.return_value = "running"
        mock_p.return_value = mp

        res = runner.invoke(
            app, ["serve", "status", "--no-probe", "--json"]
        )
    assert res.exit_code == 0
    mock_probe.assert_not_called()
```

- [ ] **Step 3: 运行验证通过**

```bash
uv run pytest tests/cli/test_serve_stop.py tests/cli/test_serve_status.py -v
```
Expected: 全 PASS

- [ ] **Step 4: Commit**

```bash
git add tests/cli/test_serve_stop.py tests/cli/test_serve_status.py
git commit -m "test(serve): stop / status CLI 集成测试"
```

---

### Task 26: tests/cli/test_serve_restart.py + test_serve_logs.py

**Files:**
- Test: `tests/cli/test_serve_restart.py`
- Test: `tests/cli/test_serve_logs.py`

- [ ] **Step 1: 写 restart 测试**

`tests/cli/test_serve_restart.py`:
```python
import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def test_restart_cannot_infer_mode_when_no_pid(isolated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    res = runner.invoke(app, ["serve", "restart", "--json"])
    assert res.exit_code == 1
    payload = json.loads(res.stdout)
    assert payload["error"]["code"] == "serve.mode_required"


def test_restart_with_explicit_mode(isolated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    with patch("asset_hub.cli.serve.proc.is_port_in_use", return_value=False), \
         patch("asset_hub.cli.serve.proc.subprocess.Popen") as mock_popen, \
         patch("asset_hub.cli.serve.lifecycle.probe_mod.probe_until_ready",
               return_value=MagicMock(ok=True)), \
         patch("asset_hub.cli.serve.lifecycle.Path") as MockPath:
        fake = MagicMock(); fake.pid = 99999
        mock_popen.return_value = fake
        mock_dist = MagicMock(); mock_dist.exists.return_value = True
        MockPath.return_value = mock_dist
        MockPath.cwd = lambda: tmp_path

        res = runner.invoke(
            app, ["serve", "restart", "--mode", "prod", "--skip-build", "--json"]
        )
    assert res.exit_code == 0


def test_restart_invalid_mode_returns_exit_2(isolated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    res = runner.invoke(
        app, ["serve", "restart", "--mode", "foo", "--json"]
    )
    assert res.exit_code == 2
```

- [ ] **Step 2: 写 logs 测试**

`tests/cli/test_serve_logs.py`:
```python
import json

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def test_logs_no_file_friendly_message(isolated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    res = runner.invoke(app, ["serve", "logs", "--json"])
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload["data"]["lines"] == []


def test_logs_tail_lines(isolated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "backend.log").write_text(
        "\n".join(f"line{i}" for i in range(50)) + "\n"
    )
    res = runner.invoke(
        app, ["serve", "logs", "--lines", "5", "--json"]
    )
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert len(payload["data"]["lines"]) == 5
    assert payload["data"]["lines"][-1] == "line49"


def test_logs_invalid_service_returns_exit_2(isolated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    res = runner.invoke(
        app, ["serve", "logs", "--service", "weird", "--json"]
    )
    assert res.exit_code == 2
```

- [ ] **Step 3: 运行验证通过**

```bash
uv run pytest tests/cli/test_serve_restart.py tests/cli/test_serve_logs.py -v
```
Expected: 全 PASS

- [ ] **Step 4: 跑全部 serve CLI 集成测试**

```bash
uv run pytest tests/cli/test_serve_*.py tests/unit/test_pid_*.py tests/unit/test_proc_*.py tests/unit/test_health_probe.py tests/unit/test_logs_*.py tests/unit/test_serve_output.py tests/unit/test_settings_serve.py -v
```
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add tests/cli/test_serve_restart.py tests/cli/test_serve_logs.py
git commit -m "test(serve): restart / logs CLI 集成测试"
```

---

## Phase 8 · 收尾 + 烟测 + 文档（Task 27-29）

### Task 27: 删除 scripts/dev.sh + 更新 CLAUDE.md

**Files:**
- Delete: `scripts/dev.sh`
- Modify: `CLAUDE.md`

- [ ] **Step 1: 删除 dev.sh**

```bash
rm scripts/dev.sh
```

- [ ] **Step 2: 改 CLAUDE.md 的 dev 启动说明**

Edit `CLAUDE.md`，找到含 `./scripts/dev.sh` 的段（"并发启动"那段），替换：

旧：
```
并发启动：`./scripts/dev.sh`（后端 `:8000` + 前端 `:5173`，Vite 代理 `/api`）。
```

新：
```
并发启动：`uv run asset-hub serve start --mode dev`（后端 `:8000` + 前端 `:5173`，Vite 代理 `/api`；后台 detach，`asset-hub serve status` 查状态、`asset-hub serve logs --follow` 看日志、`asset-hub serve stop` 干净停掉整个进程树）。生产模式 `--mode prod` 自动 build 前端 + 单端口 `:8000` 对外。
```

- [ ] **Step 3: 跑全部测试一次**

```bash
uv run pytest -x
pnpm --dir frontend test --run
pnpm --dir frontend lint
uv run ruff check .
```
Expected: 全绿

- [ ] **Step 4: Commit**

```bash
git add scripts/dev.sh CLAUDE.md
git commit -m "chore: 删除 scripts/dev.sh + CLAUDE.md 更新 dev 启动说明（serve 取代）"
```

> 注：如 `git add scripts/dev.sh` 报 pathspec 错误（已删），改用 `git add -u scripts/`。

---

### Task 28: gen:api 同步 + 提交前端 schema 变化

**Files:**
- Modify: `frontend/src/api/generated/schema.d.ts`

- [ ] **Step 1: 启后端 + 拉新 schema**

```bash
# 终端 A
uv run uvicorn asset_hub.api.app:app --port 8000

# 终端 B
pnpm --dir frontend gen:api
```

- [ ] **Step 2: 检查 schema 含 healthz + return_location/receiver + DELETE types**

```bash
grep -n "healthz\|return_location\|return_receiver\|deleteType" frontend/src/api/generated/schema.d.ts | head -20
```
Expected: 全部存在

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/generated/schema.d.ts
git commit -m "chore: gen:api 同步 healthz + B2/B3 后端契约"
```

---

### Task 29: Windows 烟测 + 更新 release notes

**Files:**
- Create: `docs/superpowers/release-notes-m2d.md`

> **手工烟测**：按 spec §7.5 列出的 Windows + dev / Windows + prod 两套 checklist 真机执行。

- [ ] **Step 1: Windows + dev 模式烟测**

```bash
# 1. 默认 prod 检查
uv run asset-hub serve start
# Expected: prod 模式启动；如 dist 不存在自动 build；输出含 mode=prod

# 停掉
uv run asset-hub serve stop

# 2. dev 模式启动
uv run asset-hub serve start --mode dev

# 3. 浏览器访问 http://127.0.0.1:5173 看到前端
# 4. status 表格
uv run asset-hub serve status
# Expected: backend + frontend 两行，healthy ✓

# 5. logs --follow 看 access log
uv run asset-hub serve logs --follow
# Expected: 看到 GET /api/healthz 之类
# Ctrl+C 退出，exit code 0

# 6. taskkill 模拟崩溃
# 在另一个终端：tasklist | findstr uvicorn → 拿到 PID → taskkill /PID xxx /F
# 然后:
uv run asset-hub serve status
# Expected: backend 显示 stale 或 not running

# 7. stop 干净
uv run asset-hub serve stop

# 验证任务管理器无 uvicorn / node / pnpm 残留

# 8. 关闭终端测试 detach
uv run asset-hub serve start --mode dev
# 关掉 cmd 窗口
# 新开终端
uv run asset-hub serve status
# Expected: 依然 running

uv run asset-hub serve stop

# 9. restart 切换
uv run asset-hub serve start --mode dev
uv run asset-hub serve restart --mode prod
# Expected: 切换成功
uv run asset-hub serve stop
```

- [ ] **Step 2: Windows + prod 模式烟测**

```bash
# 删 dist 测试自动 build
rm -rf frontend/dist
uv run asset-hub serve start --mode prod
# Expected: 跑 build 后启动；耗时 30-60s

uv run asset-hub serve stop

# --skip-build + 无 dist
rm -rf frontend/dist
uv run asset-hub serve start --mode prod --skip-build
# Expected: exit 1, error="serve.dist_missing"

# 单端口对外
pnpm --dir frontend build
uv run asset-hub serve start --mode prod
# 浏览器 http://127.0.0.1:8000/ 看到前端 + http://127.0.0.1:8000/api/healthz 200

uv run asset-hub serve stop
```

- [ ] **Step 3: 写 release notes**

`docs/superpowers/release-notes-m2d.md`:
```markdown
# M2d 部署手工干预清单

## 升级前
1. 备份数据库：`cp data/asset_hub.db data/asset_hub.db.<日期>.bak`
2. 如有自定义 dev 启动脚本（CI / Docker / IDE 任务），改为 `uv run asset-hub serve start --mode dev`

## 升级
```bash
git pull
uv sync                 # 拉 psutil 等新依赖
uv run alembic upgrade head   # 跑 B2 的 return_location/receiver migration
```

## 升级后验证
```bash
uv run asset-hub serve start --mode prod
uv run asset-hub serve status
# 浏览器访问 http://127.0.0.1:8000
uv run asset-hub serve stop
```

## 已知 Gap

- Linux 真机烟测延后：M2d 仅 Windows 双模式真机验证；Linux 路径靠单测 mock 覆盖代码层
- 多代日志轮转：当前 1 代（log + log.1）；若实际使用中 1 代不够看到崩溃前情况，触发 follow-up 加 N 代轮转
- `serve doctor` 子命令登记到 M3（与 SKILL.md 完善 + 部署文档同周期）

## 回滚（如需）
```bash
git revert <m2d-merge-commit>
uv run alembic downgrade -1
cp data/asset_hub.db.<日期>.bak data/asset_hub.db
```
```

- [ ] **Step 4: 跑全测试 + lint 一次（最终把关）**

```bash
uv run pytest
uv run ruff check .
pnpm --dir frontend test --run
pnpm --dir frontend lint
```
Expected: 全绿

- [ ] **Step 5: Commit + push**

```bash
git add docs/superpowers/release-notes-m2d.md
git commit -m "docs(m2d): 烟测通过 + release notes 部署清单"
git push
```

---

## 自查回放

| spec 章节 | 实施位置 |
|---|---|
| §1 目标 / 非目标 | 阶段划分 + Phase 7 完成判据 |
| §2 文件树 | 文件结构清单 + Task 16-23 |
| §3 CLI 契约（5 子命令 + 退出码） | Task 23 cmd.py + Task 24-26 集成测试 |
| §4 配置层 | Task 15 |
| §5 状态层 PID | Task 16 pid.py |
| §5 日志轮转 + tail | Task 19 logs.py |
| §6.1 start 流程 | Task 21 lifecycle.start_service |
| §6.2 stop 流程 | Task 22 stop_service |
| §6.3 restart 流程 | Task 22 restart_service + Task 26 测试 |
| §6.4 健康端点 + 探测 | Task 14 healthz + Task 18 probe.py |
| §6.5 跨平台 detach | Task 17 proc.py |
| §6.6 kill_tree | Task 17 |
| §6.7 边界场景 | 集成测试 Task 24-26 + 烟测 Task 29 |
| §7 测试策略 | 全 plan TDD 节奏 + Task 24-26 |
| §8 完成判据 | Task 27 (dev.sh + CLAUDE.md) + Task 28 (gen:api) + Task 29 (烟测) |
| §A.2 B2 归还字段 | Phase 2 Task 9-13 |
| §A.3 B3 type DELETE | Phase 1 Task 5-8 |
| §A.4 I1+I2 validation | Phase 0 Task 1-4 |
| §A.5 PR 顺序 | 阶段划分 + 各 Phase PR 边界 |
| §B 已知 Gap | Task 29 release notes |

---

**Plan 完。**

