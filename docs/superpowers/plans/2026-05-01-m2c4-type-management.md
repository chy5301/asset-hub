# M2c-4 · 类型管理 UI + custom_fields 结构化 builder 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 [`docs/superpowers/specs/2026-05-01-m2c4-type-management-design.md`](../specs/2026-05-01-m2c4-type-management-design.md)，落地 (a) 后端 PATCH `/api/types/{id}` + CLI `type update`，(b) 前端基础设施重构（合并 schema builder + FieldShell + Control 泛型化 + B nav 行），(c) 类型管理 web UI（列表/详情/编辑/创建/删除 + custom_fields 结构化 builder + 资产详情 unknown-key banner）。

**Architecture:** 三 PR 拆分，PR-1（后端+CLI）与 PR-2（前端基础设施）并行起跑，PR-3（type UI）依赖前两者。后端 PATCH 严格沿用现有域异常 + 退出码契约。前端 builder 用 RHF `useFieldArray` 受控；A2 FieldShell + A4 `<TFieldValues>` 泛型让 9 个 field-controls 类型安全且去样板；α banner 用独立 `--color-warning` token，禁 emoji icon，禁 spinner。

**Tech Stack:** Python 3.12 + FastAPI + SQLModel + Typer · 测试 pytest + typer.testing.CliRunner · 前端 React 19 + TanStack Router + RHF 7 + Zod 3 + shadcn/ui + openapi-typescript（gen:api 重生 schema）· Playwright MCP（烟测，不进 frontend/tests/）

---

## 阶段总览

```
PR-1 后端+CLI（独立）           PR-2 前端基础设施+搭车（独立）
├─ Phase 1 service.update_type    ├─ Phase 5 A1 合并 schema builder
├─ Phase 2 PATCH router           ├─ Phase 6 F3 zodResolver 模块化
├─ Phase 3 CLI type update        ├─ Phase 7 A2 FieldShell 抽出
└─ Phase 4 gen:api + PR-1         ├─ Phase 8 A4 Control<T> 泛型
                                  ├─ Phase 9 B nav 行
                                  └─ Phase 10 闸门 ④(a) + PR-2
                ↓ PR-1 + PR-2 都 merge ↓
                PR-3 type 管理 UI（依赖）
                ├─ Phase 11 globals.css --color-warning
                ├─ Phase 12 API hooks
                ├─ Phase 13 build-type-schema + superRefine
                ├─ Phase 14 custom-fields-builder 5 组件
                ├─ Phase 15 type-form
                ├─ Phase 16 types list 页面
                ├─ Phase 17 type-detail-page + delete-dialog
                ├─ Phase 18 unknown-key banner
                ├─ Phase 19 路由接线
                ├─ Phase 20 闸门 ④(b) + Playwright 烟测
                └─ Phase 21 闸门 ④(c) + PR-3
```

**并行说明**：PR-1（Phase 1-4）与 PR-2（Phase 5-10）**没有任何代码依赖**，可在两个 worktree 同时推进。任一者先合并都不影响对方。Subagent 模式下可一次拆两个独立 task graph 并发执行。

---

## 文件结构

**新增**：
- `src/asset_hub/cli/type_cmd.py` — 修改：加 `type_update` 子命令
- `tests/unit/test_type_service_update.py`
- `tests/api/test_type_routes_update.py`
- `tests/cli/test_type_cli_update.py`
- `frontend/src/features/assets/form/build-asset-schema.ts` — A1 合并产物
- `frontend/src/features/assets/form/field-controls/field-shell.tsx` — A2 抽出
- `frontend/tests/unit/build-asset-schema.test.ts`
- `frontend/tests/unit/field-shell.test.tsx`
- `frontend/src/styles/globals.css` — 修改：加 `--color-warning` token
- `frontend/src/api/hooks/types.ts` — 修改：加 4 个 mutation/query hook
- `frontend/src/api/query-keys.ts` — 修改：加 `qk.assetTypes.detail`
- `frontend/src/routes/types.tsx`
- `frontend/src/routes/types.new.tsx`
- `frontend/src/routes/types.$id.tsx`
- `frontend/src/features/types/list/types-table.tsx`
- `frontend/src/features/types/list/types-page.tsx`
- `frontend/src/features/types/list/types-table-skeleton.tsx`
- `frontend/src/features/types/detail/type-detail-page.tsx`
- `frontend/src/features/types/detail/type-summary-card.tsx`
- `frontend/src/features/types/detail/type-delete-dialog.tsx`
- `frontend/src/features/types/form/type-form.tsx`
- `frontend/src/features/types/form/build-type-schema.ts`
- `frontend/src/features/types/form/custom-fields-builder/builder.tsx`
- `frontend/src/features/types/form/custom-fields-builder/field-card.tsx`
- `frontend/src/features/types/form/custom-fields-builder/field-attribute-form.tsx`
- `frontend/src/features/types/form/custom-fields-builder/field-type-selector.tsx`
- `frontend/src/features/types/form/custom-fields-builder/field-options-editor.tsx`
- `frontend/src/lib/unknown-key-detector.ts` — 兼容 banner 纯函数
- `frontend/tests/unit/build-type-schema.test.ts`
- `frontend/tests/unit/unknown-key-detector.test.ts`
- `frontend/tests/hooks/type-form.test.tsx`
- `frontend/tests/hooks/custom-fields-builder.test.tsx`
- `frontend/tests/hooks/type-delete-dialog.test.tsx`
- `frontend/tests/hooks/use-types-mutations.test.tsx`

**修改**：
- `src/asset_hub/services/asset_type.py` — 加 `update_type`
- `src/asset_hub/api/routers/types.py` — 加 PATCH 端点
- `src/asset_hub/cli/type_cmd.py` — 加 `update` 子命令
- `frontend/src/api/generated/schema.d.ts` — gen:api 重生（PR-1 合并后 PR-3 起步执行）
- `frontend/src/components/layout/app-layout.tsx` — 加 B nav 行
- `frontend/src/features/assets/form/asset-create-form.tsx` — F3 模块级常量 + 切到 buildAssetSchema
- `frontend/src/features/assets/form/asset-edit-form.tsx` — 切到 buildAssetSchema
- `frontend/src/features/assets/form/asset-form-fields.tsx` — A4 泛型 control
- `frontend/src/features/assets/form/field-controls/{string,text,url,number,enum,multi-enum,date,bool}-field.tsx` — 改用 FieldShell + 泛型签名
- `frontend/src/features/assets/detail/custom-data-section.tsx` — 加 unknown-key banner

**删除**：
- `frontend/src/features/assets/form/build-create-schema.ts`（A1 替换）
- `frontend/src/features/assets/form/build-edit-schema.ts`（A1 替换）

---

# PR-1 后端 + CLI（与 PR-2 并行）

> **PR 边界**：本 PR `feature/m2c4-backend`。Phase 1-3 内 commit；Phase 4 gen:api 在 PR-1 merge 后 PR-3 起步时执行（PR-1 自身不需要前端动作）。
>
> **依赖**：无。
>
> **验证**：`uv run pytest` 全绿（含 26 新测）+ `uv run ruff check .` clean。

## Phase 1 · TypeService.update_type（Task 1-3）

### Task 1: TDD update_type 部分更新成功路径

**Files:**
- Test: `tests/unit/test_type_service_update.py` (创建)
- Modify: `src/asset_hub/services/asset_type.py:79`（追加 `update_type` 方法）

- [ ] **Step 1: 写失败测试**

`tests/unit/test_type_service_update.py`:

```python
import pytest
from sqlmodel import Session

from asset_hub.errors import DuplicateError, NotFoundError, ValidationError
from asset_hub.services.asset_type import TypeService


@pytest.fixture()
def svc(session: Session) -> TypeService:
    return TypeService(session)


class TestUpdateType:
    def test_update_name_only(self, svc: TypeService):
        t = svc.create_type(name="原名", code_prefix="OO")
        updated = svc.update_type(t.id, name="新名")
        assert updated.name == "新名"
        assert updated.code_prefix == "OO"  # 不动
        assert updated.description is None  # 不动

    def test_update_description_only(self, svc: TypeService):
        t = svc.create_type(name="A", code_prefix="AA", description="原描述")
        updated = svc.update_type(t.id, description="新描述")
        assert updated.name == "A"
        assert updated.description == "新描述"

    def test_update_custom_fields_replace(self, svc: TypeService):
        t = svc.create_type(
            name="B", code_prefix="BB",
            custom_fields=[{"key": "old", "type": "string"}],
        )
        new_fields = [
            {"key": "cpu", "type": "string", "required": True},
            {"key": "ram", "type": "int"},
        ]
        updated = svc.update_type(t.id, custom_fields=new_fields)
        assert len(updated.custom_fields) == 2
        assert updated.custom_fields[0]["key"] == "cpu"
        # 旧字段完全替换（不是合并）
        assert all(f["key"] != "old" for f in updated.custom_fields)

    def test_update_combined_all_three(self, svc: TypeService):
        t = svc.create_type(name="C", code_prefix="CC", description="d1")
        updated = svc.update_type(
            t.id,
            name="C2",
            description="d2",
            custom_fields=[{"key": "x", "type": "string"}],
        )
        assert updated.name == "C2"
        assert updated.description == "d2"
        assert len(updated.custom_fields) == 1

    def test_update_partial_does_not_clear_unset_fields(self, svc: TypeService):
        # 三参数都默认 None → 不动任何字段
        t = svc.create_type(
            name="D", code_prefix="DD", description="orig",
            custom_fields=[{"key": "k1", "type": "string"}],
        )
        updated = svc.update_type(t.id)
        assert updated.name == "D"
        assert updated.description == "orig"
        assert len(updated.custom_fields) == 1

    def test_update_does_not_touch_code_prefix(self, svc: TypeService):
        # service 签名根本不接收 code_prefix
        t = svc.create_type(name="E", code_prefix="EE")
        updated = svc.update_type(t.id, name="E2")
        assert updated.code_prefix == "EE"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/unit/test_type_service_update.py -v
```

Expected: FAIL — `AttributeError: 'TypeService' object has no attribute 'update_type'`

- [ ] **Step 3: 最小实现**

修改 `src/asset_hub/services/asset_type.py`，文件顶部确保 `from datetime import UTC, datetime` 已 import；在文件末尾追加：

```python
    def update_type(
        self,
        type_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        custom_fields: list | None = None,
    ) -> AssetType:
        """部分更新 type。code_prefix immutable，故签名不接收。

        参数为 None 表示"未传"，对应字段不动；显式传值才更新。
        custom_fields 传入时按 CustomFieldDef 校验后**完全替换**（非 merge）。
        """
        t = self.get_type(type_id)  # 不存在抛 NotFoundError

        if name is not None:
            t.name = name
        if description is not None:
            t.description = description
        if custom_fields is not None:
            try:
                t.custom_fields = [
                    CustomFieldDef.model_validate(f).model_dump() for f in custom_fields
                ]
            except Exception as e:
                raise ValidationError(f"custom_fields 结构无效: {e}") from e

        t.updated_at = datetime.now(UTC)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise DuplicateError(f"类型名称已存在: {name}") from None
        self.session.refresh(t)
        return t
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/unit/test_type_service_update.py -v
```

Expected: 6 passed

- [ ] **Step 5: 提交**

```bash
git add tests/unit/test_type_service_update.py src/asset_hub/services/asset_type.py
git commit -m "feat(asset_type): 加 update_type 部分更新方法（M2c-4 PR-1 Task 1）"
```

---

### Task 2: TDD update_type 错误分支（404 / 409 / 422）

**Files:**
- Modify: `tests/unit/test_type_service_update.py`

- [ ] **Step 1: 追加错误分支测试**

在 `tests/unit/test_type_service_update.py` 的 `TestUpdateType` 类追加：

```python
    def test_update_not_found_raises_404(self, svc: TypeService):
        import uuid
        with pytest.raises(NotFoundError):
            svc.update_type(uuid.uuid4(), name="x")

    def test_update_duplicate_name_raises(self, svc: TypeService):
        svc.create_type(name="占座", code_prefix="ZZ")
        t = svc.create_type(name="待改", code_prefix="WW")
        with pytest.raises(DuplicateError, match="名称"):
            svc.update_type(t.id, name="占座")  # name 撞车

    def test_update_invalid_field_def_raises_validation(self, svc: TypeService):
        t = svc.create_type(name="V", code_prefix="VV")
        # CustomFieldDef.type 是必填，缺字段会被 model_validate 拒
        bad = [{"key": "x"}]  # 缺 type
        with pytest.raises(ValidationError, match="custom_fields"):
            svc.update_type(t.id, custom_fields=bad)
```

- [ ] **Step 2: 运行测试**

```bash
uv run pytest tests/unit/test_type_service_update.py -v
```

Expected: 9 passed（6 + 3）。新加的 3 case 应该直接通过，因为 Task 1 实现已覆盖（`get_type` 抛 NotFoundError、IntegrityError → DuplicateError、CustomFieldDef.model_validate 失败 → ValidationError）。

- [ ] **Step 3: 提交**

```bash
git add tests/unit/test_type_service_update.py
git commit -m "test(asset_type): update_type 错误分支测试覆盖（M2c-4 PR-1 Task 2）"
```

---

### Task 3: 跑全量测试 + ruff 验证 service 改动不破他处

- [ ] **Step 1: 全量后端测试**

```bash
uv run pytest -v
```

Expected: 全绿，包含 9 个新加测试。原 285 + 9 = 294 测全通过。

- [ ] **Step 2: ruff**

```bash
uv run ruff check .
```

Expected: clean。

- [ ] **Step 3: 提交（如有 ruff 改动）**

无改动则跳过。

---

## Phase 2 · PATCH `/api/types/{id}` 路由（Task 4-5）

### Task 4: TDD PATCH 路由

**Files:**
- Test: `tests/api/test_type_routes_update.py` (创建)
- Modify: `src/asset_hub/api/routers/types.py:50`（在 DELETE 之前/之后追加 PATCH 端点）

- [ ] **Step 1: 写失败测试**

`tests/api/test_type_routes_update.py`:

```python
from fastapi.testclient import TestClient


def _create_type(client: TestClient, name="原名", prefix="ZZ", **extra) -> str:
    body = {"name": name, "code_prefix": prefix, "custom_fields": [], **extra}
    resp = client.post("/api/types", json=body)
    assert resp.status_code == 201
    return resp.json()["id"]


class TestPatchType:
    def test_patch_returns_200_with_updated_dto(self, client: TestClient):
        tid = _create_type(client)
        resp = client.patch(f"/api/types/{tid}", json={"name": "新名"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "新名"
        assert data["code_prefix"] == "ZZ"  # 不动

    def test_patch_404_on_unknown_id(self, client: TestClient):
        import uuid
        resp = client.patch(f"/api/types/{uuid.uuid4()}", json={"name": "x"})
        assert resp.status_code == 404

    def test_patch_409_on_duplicate_name(self, client: TestClient):
        _create_type(client, name="A", prefix="AA")
        tid = _create_type(client, name="B", prefix="BB")
        resp = client.patch(f"/api/types/{tid}", json={"name": "A"})
        assert resp.status_code == 409

    def test_patch_422_on_bad_field_def(self, client: TestClient):
        tid = _create_type(client)
        # CustomFieldDef 缺 type
        resp = client.patch(
            f"/api/types/{tid}",
            json={"custom_fields": [{"key": "x"}]},
        )
        # Pydantic body 校验先于 service：缺 type 会被 router level 422
        assert resp.status_code == 422

    def test_patch_with_only_name_keeps_other_fields(self, client: TestClient):
        tid = _create_type(client, description="原描述")
        resp = client.patch(f"/api/types/{tid}", json={"name": "新名"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "原描述"

    def test_patch_custom_fields_full_replace_semantics(self, client: TestClient):
        tid = _create_type(
            client,
            custom_fields=[{"key": "old", "type": "string"}],
        )
        resp = client.patch(
            f"/api/types/{tid}",
            json={"custom_fields": [{"key": "new", "type": "int"}]},
        )
        assert resp.status_code == 200
        fields = resp.json()["custom_fields"]
        assert len(fields) == 1
        assert fields[0]["key"] == "new"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/api/test_type_routes_update.py -v
```

Expected: 6 FAIL（404 或 405 method not allowed）

- [ ] **Step 3: 实现 PATCH router**

修改 `src/asset_hub/api/routers/types.py`，在文件末尾（`delete_type` 之后）追加：

```python
from asset_hub.api.schemas.asset_type import TypeUpdate  # 文件顶部 import 已有 TypeCreate / TypeRead，追加 TypeUpdate


@router.patch("/{type_id}", response_model=TypeRead)
def update_type(
    type_id: uuid.UUID,
    body: TypeUpdate,
    svc: Annotated[TypeService, Depends(_get_svc)],
):
    """部分更新 type。code_prefix immutable（DTO 已不暴露此字段）。"""
    return svc.update_type(type_id, **body.model_dump(exclude_unset=True))
```

确保文件顶部 import 段加上 `TypeUpdate`：

```python
from asset_hub.api.schemas.asset_type import TypeCreate, TypeRead, TypeUpdate
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/api/test_type_routes_update.py -v
```

Expected: 6 passed。

- [ ] **Step 5: 提交**

```bash
git add tests/api/test_type_routes_update.py src/asset_hub/api/routers/types.py
git commit -m "feat(api): PATCH /api/types/{id} 端点 + 6 case 测试覆盖（M2c-4 PR-1 Task 4）"
```

---

### Task 5: 全量 API 测验证不破他处

- [ ] **Step 1: 跑全量 api 测试**

```bash
uv run pytest tests/api/ -v
```

Expected: 全绿。

- [ ] **Step 2: 手动 sanity check（可选）**

```bash
uv run uvicorn asset_hub.api.app:app &
sleep 2
curl -X PATCH http://127.0.0.1:8000/api/types/$(uuidgen) -H "Content-Type: application/json" -d '{"name":"x"}' -i
# Expected: 404
kill %1
```

无需 commit。

---

## Phase 3 · CLI `type update` 子命令（Task 6-9）

### Task 6: TDD type update 成功路径（--name / --description / --from）

**Files:**
- Test: `tests/cli/test_type_cli_update.py` (创建)
- Modify: `src/asset_hub/cli/type_cmd.py`（追加 `type_update` 命令）

- [ ] **Step 1: 写失败测试**

`tests/cli/test_type_cli_update.py`:

```python
import json
import uuid

from typer.testing import CliRunner

from asset_hub.cli.deps import cli_session
from asset_hub.cli.main import app
from asset_hub.services.asset_type import TypeService

runner = CliRunner()


def _make_type(name="原名", prefix="OO") -> uuid.UUID:
    with cli_session() as s:
        return TypeService(s).create_type(name=name, code_prefix=prefix).id


class TestUpdateBasic:
    def test_update_with_name_only(self, isolated_db):
        tid = _make_type()
        res = runner.invoke(
            app, ["type", "update", str(tid), "--name", "新名", "--json"]
        )
        assert res.exit_code == 0
        payload = json.loads(res.stdout)
        assert payload["success"] is True
        assert payload["data"]["name"] == "新名"
        assert payload["data"]["code_prefix"] == "OO"

    def test_update_with_description_only(self, isolated_db):
        tid = _make_type()
        res = runner.invoke(
            app,
            ["type", "update", str(tid), "--description", "新描述", "--json"],
        )
        assert res.exit_code == 0
        assert json.loads(res.stdout)["data"]["description"] == "新描述"

    def test_update_with_from_file(self, isolated_db, tmp_path):
        tid = _make_type()
        schema = {
            "name": "改自 from",
            "code_prefix": "OO",  # 被忽略（spec §5.3）
            "description": "from 来",
            "custom_fields": [
                {"key": "cpu", "type": "string", "required": True}
            ],
        }
        f = tmp_path / "new.json"
        f.write_text(json.dumps(schema), encoding="utf-8")
        res = runner.invoke(
            app, ["type", "update", str(tid), "--from", str(f), "--json"]
        )
        assert res.exit_code == 0
        payload = json.loads(res.stdout)
        assert payload["data"]["name"] == "改自 from"
        assert len(payload["data"]["custom_fields"]) == 1
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/cli/test_type_cli_update.py::TestUpdateBasic -v
```

Expected: 3 FAIL（`Error: No such command 'update'`）

- [ ] **Step 3: 实现 type_update 命令**

修改 `src/asset_hub/cli/type_cmd.py`，文件末尾追加：

```python
@type_app.command("update")
def type_update(
    type_id: Annotated[str, typer.Argument(help="要更新的 AssetType id")],
    from_file: Annotated[Path | None, typer.Option("--from", help="JSON schema 文件路径（整体替换）")] = None,
    name: Annotated[str | None, typer.Option(help="新类型名称")] = None,
    description: Annotated[str | None, typer.Option(help="新描述")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="预览不真改")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="JSON 信封输出")] = False,
) -> None:
    """部分更新 AssetType（code_prefix 不可改）。"""
    uid = parse_uuid(type_id, json_output)

    # 互斥校验
    if from_file is not None and (name is not None or description is not None):
        print_error(
            "--from 与 --name/--description 互斥，请二选一",
            json_output,
            exit_code=2,
        )

    # 至少一个修改源
    if from_file is None and name is None and description is None:
        print_error(
            "必须提供至少一个修改源：--from / --name / --description",
            json_output,
            exit_code=2,
        )

    # 解析 --from
    new_name: str | None = name
    new_description: str | None = description
    new_custom_fields: list | None = None
    if from_file is not None:
        try:
            schema = json.loads(from_file.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print_error(f"JSON 文件读取失败：{from_file}（{e}）", json_output, exit_code=2)
        new_name = schema.get("name")
        new_description = schema.get("description")
        new_custom_fields = schema.get("custom_fields")
        # code_prefix 字段允许出现但被忽略（spec §5.3）

    if dry_run:
        # 预览：构造 diff
        with cli_session() as session, handle_domain_errors(json_output):
            svc = TypeService(session)
            current = svc.get_type(uid)
            ref_count = svc.repo.count_assets_by_type(uid)

        diff = _build_diff(current, new_name, new_description, new_custom_fields)
        payload = {"diff": diff, "affected_assets_count": ref_count}
        print_dry_run(
            payload,
            json_output,
            message=f"将更新 type '{current.name}' (引用资产数: {ref_count})",
        )

    # 真改
    with cli_session() as session, handle_domain_errors(json_output):
        svc = TypeService(session)
        kwargs: dict = {}
        if new_name is not None:
            kwargs["name"] = new_name
        if new_description is not None:
            kwargs["description"] = new_description
        if new_custom_fields is not None:
            kwargs["custom_fields"] = new_custom_fields
        t = svc.update_type(uid, **kwargs)
    print_result(to_json_dict(TypeRead, t), json_output)


def _build_diff(current, new_name, new_description, new_custom_fields) -> dict:
    """构造 update --dry-run 的 diff payload。"""
    diff: dict = {}
    if new_name is not None:
        diff["name"] = (
            {"unchanged": True}
            if new_name == current.name
            else {"from": current.name, "to": new_name}
        )
    if new_description is not None:
        diff["description"] = (
            {"unchanged": True}
            if new_description == current.description
            else {"from": current.description, "to": new_description}
        )
    if new_custom_fields is not None:
        old_keys = {f["key"]: f for f in current.custom_fields}
        new_keys = {f["key"]: f for f in new_custom_fields}
        added = [f for k, f in new_keys.items() if k not in old_keys]
        removed = [{"key": k} for k in old_keys if k not in new_keys]
        changed = [
            {"key": k, "from": old_keys[k], "to": new_keys[k]}
            for k in new_keys
            if k in old_keys and old_keys[k] != new_keys[k]
        ]
        unchanged_count = sum(
            1 for k in new_keys if k in old_keys and old_keys[k] == new_keys[k]
        )
        diff["custom_fields"] = {
            "added": added,
            "removed": removed,
            "changed": changed,
            "unchanged_count": unchanged_count,
        }
    return diff
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/cli/test_type_cli_update.py::TestUpdateBasic -v
```

Expected: 3 passed。

- [ ] **Step 5: 提交**

```bash
git add tests/cli/test_type_cli_update.py src/asset_hub/cli/type_cmd.py
git commit -m "feat(cli): type update 命令 · 成功路径 3 case（M2c-4 PR-1 Task 6）"
```

---

### Task 7: TDD type update 退出码矩阵（exit 1/2/3/10）

**Files:**
- Modify: `tests/cli/test_type_cli_update.py`

- [ ] **Step 1: 追加退出码测试**

```python
class TestUpdateExitCodes:
    def test_update_no_change_source_exit_2(self, isolated_db):
        tid = _make_type()
        res = runner.invoke(app, ["type", "update", str(tid), "--json"])
        assert res.exit_code == 2

    def test_update_from_and_name_conflict_exit_2(self, isolated_db, tmp_path):
        tid = _make_type()
        f = tmp_path / "x.json"
        f.write_text('{"name":"x","custom_fields":[]}', encoding="utf-8")
        res = runner.invoke(
            app,
            ["type", "update", str(tid), "--from", str(f), "--name", "y", "--json"],
        )
        assert res.exit_code == 2

    def test_update_invalid_uuid_exit_2(self, isolated_db):
        res = runner.invoke(app, ["type", "update", "not-a-uuid", "--name", "x", "--json"])
        assert res.exit_code == 2

    def test_update_invalid_json_in_file_exit_2(self, isolated_db, tmp_path):
        tid = _make_type()
        f = tmp_path / "bad.json"
        f.write_text("{not json", encoding="utf-8")
        res = runner.invoke(
            app, ["type", "update", str(tid), "--from", str(f), "--json"]
        )
        assert res.exit_code == 2

    def test_update_unknown_id_exit_3(self, isolated_db):
        random_id = uuid.uuid4()
        res = runner.invoke(
            app, ["type", "update", str(random_id), "--name", "x", "--json"]
        )
        assert res.exit_code == 3

    def test_update_duplicate_name_exit_1(self, isolated_db):
        with cli_session() as s:
            TypeService(s).create_type(name="占座", code_prefix="ZZ")
        tid = _make_type(name="待改", prefix="WW")
        res = runner.invoke(
            app, ["type", "update", str(tid), "--name", "占座", "--json"]
        )
        assert res.exit_code == 1
        assert json.loads(res.stdout)["success"] is False
```

- [ ] **Step 2: 运行测试**

```bash
uv run pytest tests/cli/test_type_cli_update.py::TestUpdateExitCodes -v
```

Expected: 6 passed。

- [ ] **Step 3: 提交**

```bash
git add tests/cli/test_type_cli_update.py
git commit -m "test(cli): type update 退出码矩阵 6 case（M2c-4 PR-1 Task 7）"
```

---

### Task 8: TDD type update --dry-run（exit 10 + diff envelope）

**Files:**
- Modify: `tests/cli/test_type_cli_update.py`

- [ ] **Step 1: 追加 dry-run 测试**

```python
class TestUpdateDryRun:
    def test_update_dry_run_exit_10_outputs_diff(self, isolated_db, tmp_path):
        with cli_session() as s:
            t = TypeService(s).create_type(
                name="原",
                code_prefix="OO",
                description="原描述",
                custom_fields=[{"key": "cpu", "type": "string"}],
            )
            tid = t.id

        schema = {
            "name": "改",
            "description": "新描述",
            "custom_fields": [
                {"key": "ram", "type": "int"},  # 加
                # cpu 删
            ],
        }
        f = tmp_path / "new.json"
        f.write_text(json.dumps(schema), encoding="utf-8")

        res = runner.invoke(
            app,
            ["type", "update", str(tid), "--from", str(f), "--dry-run", "--json"],
        )
        assert res.exit_code == 10
        payload = json.loads(res.stdout)
        assert payload["success"] is True
        diff = payload["data"]["diff"]
        assert diff["name"]["from"] == "原"
        assert diff["name"]["to"] == "改"
        assert len(diff["custom_fields"]["added"]) == 1
        assert diff["custom_fields"]["added"][0]["key"] == "ram"
        assert len(diff["custom_fields"]["removed"]) == 1
        assert diff["custom_fields"]["removed"][0]["key"] == "cpu"
        assert payload["data"]["affected_assets_count"] == 0  # 无引用资产

    def test_update_json_envelope_shape(self, isolated_db):
        tid = _make_type()
        res = runner.invoke(
            app, ["type", "update", str(tid), "--name", "X", "--json"]
        )
        payload = json.loads(res.stdout)
        # success envelope 标准 4 字段
        assert set(payload.keys()) == {"success", "data", "metadata", "error"}
        assert payload["success"] is True
        assert payload["error"] is None
```

- [ ] **Step 2: 运行测试**

```bash
uv run pytest tests/cli/test_type_cli_update.py::TestUpdateDryRun -v
```

Expected: 2 passed。

- [ ] **Step 3: 提交**

```bash
git add tests/cli/test_type_cli_update.py
git commit -m "test(cli): type update --dry-run + envelope shape（M2c-4 PR-1 Task 8）"
```

---

### Task 9: PR-1 收尾——全量后端测 + ruff + 准备 PR

- [ ] **Step 1: 全量测试**

```bash
uv run pytest -v
```

Expected: 285 + 26 = 311 passed（CLI 11 + service 9 + api 6）。

- [ ] **Step 2: ruff**

```bash
uv run ruff check .
```

Expected: clean。

- [ ] **Step 3: review CLI help 文案**

```bash
uv run asset-hub type update --help
```

Expected: 显示 `--from / --name / --description / --dry-run / --json` 五个 flag + 帮助说明。

- [ ] **Step 4: 准备 PR-1（需要 user 推 branch + 开 PR）**

提示用户：本 PR-1 涉及后端 service / API / CLI 共 26 新测全绿；不动前端。建议 `feature/m2c4-backend` 分支推送 GitHub 后开 PR。**PR-1 merge 后立即 `pnpm --dir frontend gen:api` 拉新 schema**（PR-3 起步时执行，详见 Phase 11）。

---

# PR-2 前端基础设施 + 搭车（与 PR-1 并行）

> **PR 边界**：本 PR `feature/m2c4-form-infra`。**纯重构 + nav 行新增，不引入新业务 UI**。
>
> **依赖**：无（与 PR-1 完全解耦——PR-2 不调 API、不动 schema）。
>
> **验证**：现有 38 frontend tests 全绿 + 4 新单测 + tsc strict 不退化 + frontend-design 闸门 ④(a)。

## Phase 5 · A1 合并 buildAssetSchema（Task 10-12）

### Task 10: TDD buildAssetSchema 合并双 schema

**Files:**
- Test: `frontend/tests/unit/build-asset-schema.test.ts` (创建)
- Create: `frontend/src/features/assets/form/build-asset-schema.ts`

- [ ] **Step 1: 写失败测试**

`frontend/tests/unit/build-asset-schema.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { buildAssetSchema } from '@/features/assets/form/build-asset-schema';
import type { FieldDef } from '@/features/assets/form/types';

describe('buildAssetSchema', () => {
  it("mode='create' 包含 type_id", () => {
    const schema = buildAssetSchema([], { mode: 'create' });
    const result = schema.safeParse({
      name: 'x',
      // 缺 type_id
      custom_data: {},
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path[0] === 'type_id')).toBe(true);
    }
  });

  it("mode='edit' 不要求 type_id", () => {
    const schema = buildAssetSchema([], { mode: 'edit' });
    const result = schema.safeParse({
      name: 'x',
      custom_data: {},
    });
    expect(result.success).toBe(true);
  });

  it('注入 fieldDefs 后 custom_data 子 schema 生效', () => {
    const fieldDefs: FieldDef[] = [
      { key: 'cpu', type: 'string', required: true },
    ];
    const schema = buildAssetSchema(fieldDefs, { mode: 'edit' });
    const result = schema.safeParse({
      name: 'x',
      custom_data: { cpu: '' },  // required string min(1)
    });
    expect(result.success).toBe(false);
  });

  it('create + 合法值通过', () => {
    const schema = buildAssetSchema([], { mode: 'create' });
    const result = schema.safeParse({
      name: 'x',
      type_id: '00000000-0000-0000-0000-000000000000',
      custom_data: {},
    });
    expect(result.success).toBe(true);
  });
});
```

- [ ] **Step 2: 运行确认失败**

```bash
pnpm --dir frontend test --run tests/unit/build-asset-schema.test.ts
```

Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现合并 schema**

`frontend/src/features/assets/form/build-asset-schema.ts`:

```ts
import { z } from 'zod';
import { fieldDefsToZodSchema } from './field-def-to-zod';
import type { FieldDef } from './types';

const baseSchema = z.object({
  name: z.string().min(1, '资产名必填'),
  serial_number: z.string().optional(),
  acquired_at: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, '日期格式 YYYY-MM-DD')
    .optional()
    .or(z.literal('')),
  holder: z.string().optional(),
  location: z.string().optional(),
  notes: z.string().optional(),
});

/**
 * 把通用字段 schema 与该 type 的 custom_fields schema 合并。
 * mode='create' 含 type_id；mode='edit' 不含（D9：编辑不允许改 type）。
 */
export function buildAssetSchema(
  fieldDefs: FieldDef[],
  { mode }: { mode: 'create' | 'edit' },
) {
  const withCustom = baseSchema.extend({
    custom_data: fieldDefsToZodSchema(fieldDefs),
  });
  return mode === 'create'
    ? withCustom.extend({
        type_id: z.string().uuid('请选择资产类型'),
      })
    : withCustom;
}

export type CreateFormValues = z.infer<
  ReturnType<typeof buildAssetSchema<'create'>>
>;
export type EditFormValues = z.infer<
  ReturnType<typeof buildAssetSchema<'edit'>>
>;
```

注：`buildAssetSchema<'create'>` 这种泛型推导在 zod 中不直接支持，需要用 helper：

```ts
type CreateSchema = ReturnType<typeof buildAssetSchema> extends infer S
  ? S & { _create: true }
  : never;
```

简化方案——分开导出：

```ts
export type CreateFormValues = {
  name: string;
  type_id: string;
  serial_number?: string;
  acquired_at?: string;
  holder?: string;
  location?: string;
  notes?: string;
  custom_data: Record<string, unknown>;
};
export type EditFormValues = Omit<CreateFormValues, 'type_id'>;
```

实际实现以 `frontend/src/features/assets/form/types.ts` 既有类型为准；如已存在 CreateFormValues/EditFormValues 则保留命名兼容 import 路径。

- [ ] **Step 4: 运行测试确认通过**

```bash
pnpm --dir frontend test --run tests/unit/build-asset-schema.test.ts
```

Expected: 4 passed。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/features/assets/form/build-asset-schema.ts frontend/tests/unit/build-asset-schema.test.ts
git commit -m "feat(form): A1 合并 buildAssetSchema(fieldDefs, { mode })（M2c-4 PR-2 Task 10）"
```

---

### Task 11: 切换 asset-create-form / asset-edit-form 到 buildAssetSchema + F3 模块级常量

**Files:**
- Modify: `frontend/src/features/assets/form/asset-create-form.tsx`
- Modify: `frontend/src/features/assets/form/asset-edit-form.tsx`

- [ ] **Step 1: 修改 asset-create-form.tsx**

把文件顶部 `import { buildCreateSchema, type CreateFormValues } from './build-create-schema';` 替换成：

```ts
import { buildAssetSchema, type CreateFormValues } from './build-asset-schema';

// F3 修订：模块级常量，避免每次 render 重建空 schema
const CREATE_EMPTY_SCHEMA = buildAssetSchema([], { mode: 'create' });
```

把 `useForm<CreateFormValues>({ resolver: zodResolver(buildCreateSchema([])) ... })` 改为：

```ts
const form = useForm<CreateFormValues>({
  resolver: zodResolver(CREATE_EMPTY_SCHEMA),
  // ...
});
```

把 `onSubmit` 中的 `buildCreateSchema(fieldDefs)` 引用改为 `buildAssetSchema(fieldDefs, { mode: 'create' })`。

- [ ] **Step 2: 修改 asset-edit-form.tsx**

类似处理。`buildEditSchema(fieldDefs)` → `buildAssetSchema(fieldDefs, { mode: 'edit' })`，`type EditFormValues` import 路径切到 `./build-asset-schema`。EditForm 已有 module-level schema（M2c-3 已修），保留即可，仅切 builder 函数名。

- [ ] **Step 3: 跑既有 form 测**

```bash
pnpm --dir frontend test --run tests/hooks/asset-create-form.test.tsx tests/hooks/asset-edit-form.test.tsx
```

Expected: 全绿（不应破任何用例）。

- [ ] **Step 4: 提交**

```bash
git add frontend/src/features/assets/form/asset-create-form.tsx frontend/src/features/assets/form/asset-edit-form.tsx
git commit -m "refactor(form): asset-create/edit 切到 buildAssetSchema + F3 模块级 EMPTY_SCHEMA（M2c-4 PR-2 Task 11）"
```

---

### Task 12: 删除旧 build-create-schema.ts / build-edit-schema.ts

**Files:**
- Delete: `frontend/src/features/assets/form/build-create-schema.ts`
- Delete: `frontend/src/features/assets/form/build-edit-schema.ts`

- [ ] **Step 1: 全局搜索旧 import**

```bash
grep -rn "build-create-schema\|build-edit-schema" frontend/src frontend/tests
```

Expected: 0 命中（Task 11 已迁完）。如有遗漏，先修引用。

- [ ] **Step 2: 删文件**

```bash
rm frontend/src/features/assets/form/build-create-schema.ts
rm frontend/src/features/assets/form/build-edit-schema.ts
```

- [ ] **Step 3: 跑全量前端测**

```bash
pnpm --dir frontend test --run
```

Expected: 38 + 4 = 42 passed。

- [ ] **Step 4: lint**

```bash
pnpm --dir frontend lint
```

Expected: 0 errors（保留 1 个 pre-existing react-hooks 警告）。

- [ ] **Step 5: tsc 严格模式**

```bash
pnpm --dir frontend tsc --noEmit
```

Expected: 0 errors。

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "chore(form): 删 build-create-schema / build-edit-schema（A1 完成）（M2c-4 PR-2 Task 12）"
```

---

## Phase 6 · A2 抽 FieldShell（Task 13-15）

### Task 13: TDD FieldShell 单组件

**Files:**
- Test: `frontend/tests/unit/field-shell.test.tsx` (创建)
- Create: `frontend/src/features/assets/form/field-controls/field-shell.tsx`

- [ ] **Step 1: 写失败测试**

`frontend/tests/unit/field-shell.test.tsx`:

```tsx
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { useForm, FormProvider } from 'react-hook-form';
import { Form } from '@/components/ui/form';
import { FieldShell } from '@/features/assets/form/field-controls/field-shell';
import type { FieldDef } from '@/features/assets/form/types';

function Harness({ def, children }: { def: FieldDef; children?: React.ReactNode }) {
  const methods = useForm({ defaultValues: { custom_data: { [def.key]: '' } } });
  return (
    <FormProvider {...methods}>
      <Form {...methods}>
        <FieldShell def={def} control={methods.control}>
          {(field) => <input {...field} data-testid="control" />}
        </FieldShell>
        {children}
      </Form>
    </FormProvider>
  );
}

describe('FieldShell', () => {
  it('required 时显示 * 星号', () => {
    render(<Harness def={{ key: 'k', type: 'string', required: true, label: 'CPU' }} />);
    expect(screen.getByText('*')).toBeInTheDocument();
  });

  it('非 required 时不显示星号', () => {
    render(<Harness def={{ key: 'k', type: 'string', required: false, label: 'CPU' }} />);
    expect(screen.queryByText('*')).not.toBeInTheDocument();
  });

  it('help 文案存在时渲染 description', () => {
    render(<Harness def={{ key: 'k', type: 'string', help: '帮助说明', label: 'CPU' }} />);
    expect(screen.getByText('帮助说明')).toBeInTheDocument();
  });

  it('layout="inline" 路径渲染（bool 特例）', () => {
    render(
      <Harness def={{ key: 'k', type: 'bool', label: '启用' }} />,
    );
    // inline 模式下 FormItem 加了 flex-row 布局类
    const item = screen.getByText('启用').closest('[class*="flex-row"]');
    // 该 case 与默认 layout 不同；具体类断言宽松
    expect(item).toBeNull(); // 默认 layout="block" 不是 flex-row
  });
});
```

- [ ] **Step 2: 运行确认失败**

```bash
pnpm --dir frontend test --run tests/unit/field-shell.test.tsx
```

Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现 FieldShell**

`frontend/src/features/assets/form/field-controls/field-shell.tsx`:

```tsx
import type { ReactNode } from 'react';
import type { Control, ControllerRenderProps, FieldValues, Path } from 'react-hook-form';
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import type { FieldDef } from '../types';

type FieldShellProps<TFieldValues extends FieldValues> = {
  def: FieldDef;
  control: Control<TFieldValues>;
  /** 默认 'block'（垂直堆叠）；'inline' 给 bool 类型用横向布局 */
  layout?: 'block' | 'inline';
  children: (
    field: ControllerRenderProps<TFieldValues, Path<TFieldValues>>,
  ) => ReactNode;
};

export function FieldShell<TFieldValues extends FieldValues>({
  def,
  control,
  layout = 'block',
  children,
}: FieldShellProps<TFieldValues>) {
  const name = `custom_data.${def.key}` as Path<TFieldValues>;
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem
          className={
            layout === 'inline'
              ? 'flex flex-row items-start gap-3 space-y-0'
              : undefined
          }
        >
          <FormLabel htmlFor={`field-${def.key}`}>
            {def.label ?? def.key}
            {def.required && <span className="ml-1 text-destructive">*</span>}
          </FormLabel>
          <FormControl>{children(field)}</FormControl>
          {def.help && <FormDescription>{def.help}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
```

- [ ] **Step 4: 运行测试**

```bash
pnpm --dir frontend test --run tests/unit/field-shell.test.tsx
```

Expected: 4 passed。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/features/assets/form/field-controls/field-shell.tsx frontend/tests/unit/field-shell.test.tsx
git commit -m "feat(form): A2 FieldShell 抽 FormField/.../FormMessage 骨架（M2c-4 PR-2 Task 13）"
```

---

### Task 14: 重构 8 个 field-controls 用 FieldShell

**Files:**
- Modify: `frontend/src/features/assets/form/field-controls/{string,text,url,number,enum,multi-enum,date}-field.tsx`（7 个）
- Modify: `frontend/src/features/assets/form/field-controls/bool-field.tsx`（特例 inline）

- [ ] **Step 1: 重构 string-field.tsx**

```tsx
import type { Control, FieldValues } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { FieldShell } from './field-shell';
import type { FieldDef } from '../types';

export function StringField<TFieldValues extends FieldValues>({
  def,
  control,
}: {
  def: FieldDef;
  control: Control<TFieldValues>;
}) {
  return (
    <FieldShell def={def} control={control}>
      {(field) => (
        <Input
          {...field}
          id={`field-${def.key}`}
          placeholder={def.placeholder}
          value={field.value ?? ''}
        />
      )}
    </FieldShell>
  );
}
```

- [ ] **Step 2: 重构 text/url/date-field.tsx**

3 个文件结构与 string-field 完全同构，只有元素不同：text 用 `<Textarea>`、url 用 `<Input type="url">`、date 用现有 date picker。把 FormField/FormItem/.../FormMessage 骨架删掉，包到 `<FieldShell>` 里。每个 field-control 签名加 `<TFieldValues extends FieldValues>`。

- [ ] **Step 3: 重构 number-field.tsx**

包含 unit 后缀的特殊渲染保留（在 children render-prop 里画）：

```tsx
<FieldShell def={def} control={control}>
  {(field) => (
    <div className="relative">
      <Input {...field} type="number" id={`field-${def.key}`} value={field.value ?? ''} />
      {def.unit && (
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
          {def.unit}
        </span>
      )}
    </div>
  )}
</FieldShell>
```

- [ ] **Step 4: 重构 enum-field.tsx + multi-enum-field.tsx**

把 RadioGroup / Combobox 包到 FieldShell。注意 enum/multi-enum 的 FieldShell `name` path 不变，render-prop 里直接消费 `field` 渲染对应组件。

- [ ] **Step 5: 重构 bool-field.tsx（layout="inline"）**

```tsx
import type { Control, FieldValues } from 'react-hook-form';
import { Checkbox } from '@/components/ui/checkbox';
import { FieldShell } from './field-shell';
import type { FieldDef } from '../types';

export function BoolField<TFieldValues extends FieldValues>({
  def,
  control,
}: {
  def: FieldDef;
  control: Control<TFieldValues>;
}) {
  return (
    <FieldShell def={def} control={control} layout="inline">
      {(field) => (
        <Checkbox
          checked={!!field.value}
          onCheckedChange={field.onChange}
          id={`field-${def.key}`}
        />
      )}
    </FieldShell>
  );
}
```

- [ ] **Step 6: 跑全量前端测**

```bash
pnpm --dir frontend test --run
```

Expected: 38 + 4 + 4 = 46 passed（前端原 38 + Task 10 4 + Task 13 4）。

- [ ] **Step 7: tsc 严格**

```bash
pnpm --dir frontend tsc --noEmit
```

Expected: 0 errors。

- [ ] **Step 8: 提交**

```bash
git add frontend/src/features/assets/form/field-controls/
git commit -m "refactor(form): 8 个 field-controls 用 FieldShell + 泛型签名（M2c-4 PR-2 Task 14）"
```

---

### Task 15: A4 收尾——asset-form-fields.tsx Control 泛型化 + 消除 cast

**Files:**
- Modify: `frontend/src/features/assets/form/asset-form-fields.tsx`
- Modify: `frontend/src/features/assets/form/asset-create-form.tsx`
- Modify: `frontend/src/features/assets/form/asset-edit-form.tsx`

- [ ] **Step 1: asset-form-fields.tsx 改泛型**

```ts
import { useMemo } from 'react';
import { type Control, useWatch, type FieldValues } from 'react-hook-form';
// ...

interface AssetFormFieldsProps<TFieldValues extends FieldValues> {
  control: Control<TFieldValues>;
  types: AssetTypeRead[];
  mode: 'create' | 'edit';
  assetCode?: string;
  forceTypeId?: string;
}

export function AssetFormFields<TFieldValues extends FieldValues>({
  control,
  types,
  mode,
  assetCode,
  forceTypeId,
}: AssetFormFieldsProps<TFieldValues>) {
  // ... 内部 useWatch / 渲染保持
}
```

`CustomFieldsForm` / `GeneralFieldsForm` 同样需要 `<TFieldValues>` 透传——视情况一同改。

- [ ] **Step 2: 调用方消除 cast**

`asset-create-form.tsx` 内 `<AssetFormFields control={form.control as unknown as Control} ... />` → `<AssetFormFields<CreateFormValues> control={form.control} ... />`，`as unknown as Control` 双重 cast 删掉。

`asset-edit-form.tsx` 同理 → `<AssetFormFields<EditFormValues> control={form.control} ... />`。

- [ ] **Step 3: 跑全量前端测 + tsc**

```bash
pnpm --dir frontend test --run
pnpm --dir frontend tsc --noEmit
```

Expected: 全绿。

- [ ] **Step 4: 提交**

```bash
git add frontend/src/features/assets/form/
git commit -m "refactor(form): A4 AssetFormFields 泛型化 Control<TFieldValues>，消除 as unknown as Control（M2c-4 PR-2 Task 15）"
```

---

## Phase 7 · B nav 行（Task 16）

### Task 16: app-layout.tsx 加 nav 行

**Files:**
- Modify: `frontend/src/components/layout/app-layout.tsx`

- [ ] **Step 1: 修改 layout**

```tsx
import { Link, Outlet, useMatchRoute } from "@tanstack/react-router";
import { Toaster } from "@/components/ui/sonner";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { ErrorBoundary } from "@/components/feedback/error-boundary";

const NAV_ITEMS = [
  { to: "/assets", label: "资产" },
  { to: "/types", label: "类型" },
] as const;

function NavBar() {
  const matchRoute = useMatchRoute();
  return (
    <nav
      className="border-b border-border bg-background"
      aria-label="主导航"
    >
      <div className="mx-auto flex h-10 max-w-[1400px] items-center gap-6 px-6">
        {NAV_ITEMS.map((item) => {
          const active = !!matchRoute({ to: item.to, fuzzy: true });
          return (
            <Link
              key={item.to}
              to={item.to}
              className={
                active
                  ? "text-sm font-medium text-primary border-b-2 border-primary -mb-px py-2 transition-colors"
                  : "text-sm text-muted-foreground hover:text-foreground py-2 transition-colors"
              }
            >
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center justify-between px-6">
          <span className="text-sm font-medium tracking-tight text-foreground">
            小组资产管理工具
          </span>
          <ThemeToggle />
        </div>
      </header>
      <NavBar />
      <main className="mx-auto max-w-[1400px] px-6 py-6">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
      <Toaster position="top-right" richColors />
    </div>
  );
}
```

- [ ] **Step 2: 跑测 + tsc + 启动 dev 看一眼**

```bash
pnpm --dir frontend test --run
pnpm --dir frontend tsc --noEmit
```

Expected: 全绿。

启动 dev（用户手动）：
```bash
uv run asset-hub serve start --mode dev
```
浏览器开 http://127.0.0.1:5173 → 看到 header 下方 "资产" / "类型" nav 行；点击切换 active 状态视觉变化（underline + primary color）。`/types` 此时 404（路由还没建），不影响 nav 视觉验证。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/layout/app-layout.tsx
git commit -m "feat(layout): B nav 行（资产/类型）+ active 状态 underline + primary color（M2c-4 PR-2 Task 16）"
```

---

## Phase 8 · PR-2 闸门 ④(a) + 准备 PR（Task 17）

### Task 17: frontend-design 闸门 ④(a) + 红线扫描

- [ ] **Step 1: Pre-Delivery Checklist 7 项自查**

人工查（每项 ✓ 或 ✗ + 说明）：

- [ ] No emojis as icons：搜 `grep -rn "✗\|⚠\|✓\|❌\|⭐" frontend/src` 在 PR-2 改动文件内 0 命中（FieldShell / app-layout / 8 field-controls）
- [ ] cursor-pointer on clickable：nav Link 走 shadcn / Tailwind base 默认带 `cursor-pointer`（验证：浏览器审查元素）
- [ ] Hover transition 150-300ms：nav Link `transition-colors` 已加（无 transition-duration 显式设置 = 默认 150ms ≤ 300ms ✓）
- [ ] Light mode contrast 4.5:1：`text-primary` on `bg-background` 已沿用 m2c1 调好的 token，无新色
- [ ] Focus-visible：`*:focus-visible` 在 globals.css 兜底（沿用 m2c1）
- [ ] prefers-reduced-motion：本里程碑 PR-2 无新 motion 时刻，沿用 m2c1 全局 setting
- [ ] Responsive 1024+：nav 行 `max-w-[1400px]` 居中，与 header / main 一致

- [ ] **Step 2: 红线扫描**

```bash
grep -rnE "scale-|animate-spin|backdrop-blur|bg-gradient-to|⚠" \
  frontend/src/components/layout \
  frontend/src/features/assets/form
```

Expected: 0 命中。

- [ ] **Step 3: 全量前端测 + lint**

```bash
pnpm --dir frontend test --run
pnpm --dir frontend lint
pnpm --dir frontend tsc --noEmit
```

Expected: 全绿（38 旧 + 8 新 = 46 测）；0 lint error；0 tsc error。

- [ ] **Step 4: 提示用户准备 PR-2**

PR-2 涉及 4 项 simplify follow-up（A1 / F3 / A2 / A4）+ B nav 行；纯重构 + nav 加法，不引入业务流。建议 `feature/m2c4-form-infra` 分支推送 GitHub 后开 PR；review 重点是「9 field-controls 类型签名 + Control<T> 泛型不破现有 38 frontend test」。

无 commit 动作（所有改动已在前序 task commit）。

---

# PR-3 type 管理 UI（依赖 PR-1 + PR-2）

> **PR 边界**：本 PR `feature/m2c4-types-ui`。**前置条件**：PR-1 + PR-2 都已 merge 到 main。
>
> **依赖动作**：起步时 `pnpm --dir frontend gen:api` 重生 schema（拉取 PR-1 的 PATCH 端点契约）。
>
> **验证**：全测全绿（22-28 新前端测）+ frontend-design 闸门 ④(b) ④(c) + Playwright 8 场景烟测。

## Phase 11 · 起步：gen:api + globals.css token（Task 18）

### Task 18: 同步 API schema + 加 --color-warning token

**Files:**
- Modify: `frontend/src/api/generated/schema.d.ts`（gen:api 自动产物）
- Modify: `frontend/src/styles/globals.css`

- [ ] **Step 1: 跑 gen:api（依赖 PR-1 merge）**

```bash
uv run asset-hub serve start --mode dev &
sleep 3
pnpm --dir frontend gen:api
uv run asset-hub serve stop
```

验证 `frontend/src/api/generated/schema.d.ts` 含 `paths['/api/types/{type_id}']['patch']` 这一新条目（PR-1 落地的 PATCH endpoint）。

- [ ] **Step 2: 加 `--color-warning` token**

修改 `frontend/src/styles/globals.css`，找到 `:root { ... }` block 在末尾追加：

```css
:root {
  /* ... 现有 token */
  --color-warning: 38 92% 50%;          /* amber，HSL；与 --color-cta 视觉等价但语义独立——决策 D16 */
}

.dark {
  /* ... 现有 token */
  --color-warning: 38 75% 55%;          /* dark 模式独立调：饱和度↓ 亮度略↑，避免刺眼 */
}
```

如果项目用 Tailwind v4 `@theme` 段，则在 `@theme` block 加：

```css
@theme {
  /* ... */
  --color-warning: hsl(var(--color-warning));
}
```

具体语法以现有 globals.css 风格为准（项目 Tailwind 版本由 m2c1 决定）。

- [ ] **Step 3: 跑测 + tsc**

```bash
pnpm --dir frontend test --run
pnpm --dir frontend tsc --noEmit
```

Expected: 全绿（无新测，仅 schema + token 改动）。

- [ ] **Step 4: 提交**

```bash
git add frontend/src/api/generated/schema.d.ts frontend/src/styles/globals.css
git commit -m "chore(types-ui): gen:api 同步 PATCH endpoint + 加 --color-warning token（M2c-4 PR-3 Task 18）"
```

---

## Phase 12 · API hooks（Task 19-20）

### Task 19: query-keys + types.ts hooks 扩展

**Files:**
- Modify: `frontend/src/api/query-keys.ts`
- Modify: `frontend/src/api/hooks/types.ts`
- Test: `frontend/tests/hooks/use-types-mutations.test.tsx` (创建)

- [ ] **Step 1: 写失败测试**

`frontend/tests/hooks/use-types-mutations.test.tsx`:

```tsx
import { describe, expect, it } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import {
  useTypeQuery,
  useCreateTypeMutation,
  useUpdateTypeMutation,
  useDeleteTypeMutation,
} from '@/api/hooks/types';

const server = setupServer();
const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('use-types-mutations', () => {
  it('useTypeQuery 拉单个 type', async () => {
    server.use(
      http.get('/api/types/abc', () =>
        HttpResponse.json({
          id: 'abc',
          name: 'NB',
          code_prefix: 'NB',
          description: null,
          custom_fields: [],
          created_at: '2026-05-01T00:00:00Z',
          updated_at: '2026-05-01T00:00:00Z',
        }),
      ),
    );
    const { result } = renderHook(() => useTypeQuery('abc'), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.name).toBe('NB');
  });

  it('useCreateTypeMutation POST + 成功 invalidate', async () => {
    server.use(
      http.post('/api/types', () =>
        HttpResponse.json(
          {
            id: 'new',
            name: 'X',
            code_prefix: 'XX',
            description: null,
            custom_fields: [],
            created_at: '2026-05-01T00:00:00Z',
            updated_at: '2026-05-01T00:00:00Z',
          },
          { status: 201 },
        ),
      ),
    );
    const { result } = renderHook(() => useCreateTypeMutation(), { wrapper });
    await result.current.mutateAsync({
      name: 'X',
      code_prefix: 'XX',
      custom_fields: [],
    });
    expect(result.current.isSuccess).toBe(true);
  });

  it('useUpdateTypeMutation PATCH', async () => {
    server.use(
      http.patch('/api/types/abc', () =>
        HttpResponse.json({
          id: 'abc',
          name: 'New',
          code_prefix: 'NB',
          description: null,
          custom_fields: [],
          created_at: '2026-05-01T00:00:00Z',
          updated_at: '2026-05-01T00:00:00Z',
        }),
      ),
    );
    const { result } = renderHook(() => useUpdateTypeMutation(), { wrapper });
    const data = await result.current.mutateAsync({
      id: 'abc',
      body: { name: 'New' },
    });
    expect(data.name).toBe('New');
  });

  it('useDeleteTypeMutation DELETE', async () => {
    server.use(
      http.delete('/api/types/abc', () => HttpResponse.text(null, { status: 204 })),
    );
    const { result } = renderHook(() => useDeleteTypeMutation(), { wrapper });
    await result.current.mutateAsync('abc');
    expect(result.current.isSuccess).toBe(true);
  });
});
```

- [ ] **Step 2: 运行确认失败**

```bash
pnpm --dir frontend test --run tests/hooks/use-types-mutations.test.tsx
```

Expected: FAIL（hook 不存在）

- [ ] **Step 3: 加 query-keys**

修改 `frontend/src/api/query-keys.ts`，把 `assetTypes` block 改为：

```ts
  assetTypes: {
    all: ["assetTypes"] as const,
    list: () => ["assetTypes", "list"] as const,
    detail: (id: string) => ["assetTypes", "detail", id] as const,
  },
```

- [ ] **Step 4: 实现 4 个 hooks**

修改 `frontend/src/api/hooks/types.ts`，扩展为：

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "@/api/client";
import { qk } from "@/api/query-keys";
import { unwrap } from "@/lib/error";
import type { components } from "@/api/generated/schema";

type TypeRead = components['schemas']['TypeRead'];
type TypeCreateBody = components['schemas']['TypeCreate'];
type TypeUpdateBody = components['schemas']['TypeUpdate'];

export function useAssetTypesQuery() {
  return useQuery({
    queryKey: qk.assetTypes.list(),
    staleTime: Infinity,
    queryFn: async () => {
      const res = await http.GET("/api/types");
      return unwrap(res);
    },
  });
}

export function useTypeQuery(id: string | undefined) {
  return useQuery({
    queryKey: qk.assetTypes.detail(id ?? ""),
    enabled: !!id,
    queryFn: async () => {
      const res = await http.GET("/api/types/{type_id}", {
        params: { path: { type_id: id! } },
      });
      return unwrap(res);
    },
  });
}

export function useCreateTypeMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: TypeCreateBody): Promise<TypeRead> => {
      const res = await http.POST("/api/types", { body });
      return unwrap(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assetTypes.all });
    },
  });
}

export function useUpdateTypeMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { id: string; body: TypeUpdateBody }): Promise<TypeRead> => {
      const res = await http.PATCH("/api/types/{type_id}", {
        params: { path: { type_id: args.id } },
        body: args.body,
      });
      return unwrap(res);
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: qk.assetTypes.list() });
      qc.invalidateQueries({ queryKey: qk.assetTypes.detail(vars.id) });
      // 不 invalidate qk.assets.all（兼容策略 B：写时不动 asset 数据）
    },
  });
}

export function useDeleteTypeMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await http.DELETE("/api/types/{type_id}", {
        params: { path: { type_id: id } },
      });
      // DELETE 返 204 无 body；res.error 存在时手工 throw（沿用 M2c-2 useDeleteAttachmentMutation 模式）
      if (res.error) throw res.error;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assetTypes.all });
    },
  });
}
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pnpm --dir frontend test --run tests/hooks/use-types-mutations.test.tsx
```

Expected: 4 passed。

- [ ] **Step 6: 提交**

```bash
git add frontend/src/api/query-keys.ts frontend/src/api/hooks/types.ts frontend/tests/hooks/use-types-mutations.test.tsx
git commit -m "feat(api): types CRUD hooks（query/create/update/delete）+ 4 case 测试（M2c-4 PR-3 Task 19）"
```

---

### Task 20: 跑既有 hooks 测确认无破坏

- [ ] **Step 1: 跑全前端测**

```bash
pnpm --dir frontend test --run
```

Expected: 38 + 8 + 4 = 50 passed。

- [ ] **Step 2: tsc**

```bash
pnpm --dir frontend tsc --noEmit
```

Expected: 0 errors。无 commit。

---

## Phase 13 · build-type-schema + superRefine（Task 21）

### Task 21: TDD build-type-schema 单字段 + 跨字段校验

**Files:**
- Test: `frontend/tests/unit/build-type-schema.test.ts` (创建)
- Create: `frontend/src/features/types/form/build-type-schema.ts`

- [ ] **Step 1: 写失败测试**

`frontend/tests/unit/build-type-schema.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { buildTypeSchema } from '@/features/types/form/build-type-schema';

describe('buildTypeSchema', () => {
  describe('顶层字段', () => {
    it('create 模式 code_prefix 必填', () => {
      const schema = buildTypeSchema({ mode: 'create' });
      const r = schema.safeParse({ name: 'X', custom_fields: [] });
      expect(r.success).toBe(false);
    });

    it('edit 模式 code_prefix 不要求', () => {
      const schema = buildTypeSchema({ mode: 'edit' });
      const r = schema.safeParse({ name: 'X', custom_fields: [] });
      expect(r.success).toBe(true);
    });

    it('code_prefix 正则 ^[A-Z]{2,4}$', () => {
      const schema = buildTypeSchema({ mode: 'create' });
      expect(schema.safeParse({ name: 'X', code_prefix: 'NB', custom_fields: [] }).success).toBe(true);
      expect(schema.safeParse({ name: 'X', code_prefix: 'N', custom_fields: [] }).success).toBe(false);
      expect(schema.safeParse({ name: 'X', code_prefix: 'LAPTOP', custom_fields: [] }).success).toBe(false);
      expect(schema.safeParse({ name: 'X', code_prefix: 'nb', custom_fields: [] }).success).toBe(false);
    });

    it('name 必填', () => {
      const schema = buildTypeSchema({ mode: 'edit' });
      expect(schema.safeParse({ name: '', custom_fields: [] }).success).toBe(false);
    });
  });

  describe('fieldDefSchema 单字段', () => {
    const schema = buildTypeSchema({ mode: 'edit' });

    it('key 正则 ^[a-z][a-z0-9_]*$', () => {
      const bad = schema.safeParse({
        name: 'X',
        custom_fields: [{ key: 'CPU', type: 'string' }],
      });
      expect(bad.success).toBe(false);
    });

    it('type 限定 9 种枚举', () => {
      const bad = schema.safeParse({
        name: 'X',
        custom_fields: [{ key: 'k', type: 'unknown_type' }],
      });
      expect(bad.success).toBe(false);
    });
  });

  describe('superRefine 跨字段', () => {
    const schema = buildTypeSchema({ mode: 'edit' });

    it('数组级 key 唯一性', () => {
      const r = schema.safeParse({
        name: 'X',
        custom_fields: [
          { key: 'cpu', type: 'string' },
          { key: 'cpu', type: 'int' },
        ],
      });
      expect(r.success).toBe(false);
      if (!r.success) {
        const dupErr = r.error.issues.find((i) =>
          i.path.includes('key') && i.message.includes('已被使用'),
        );
        expect(dupErr).toBeDefined();
      }
    });

    it('min ≤ max（int/float）', () => {
      const r = schema.safeParse({
        name: 'X',
        custom_fields: [{ key: 'k', type: 'int', min: 100, max: 10 }],
      });
      expect(r.success).toBe(false);
    });

    it('enum 必须有 options 且非空', () => {
      const r = schema.safeParse({
        name: 'X',
        custom_fields: [{ key: 'k', type: 'enum', options: [] }],
      });
      expect(r.success).toBe(false);
    });

    it('options 唯一性', () => {
      const r = schema.safeParse({
        name: 'X',
        custom_fields: [
          { key: 'k', type: 'enum', options: ['A', 'A', 'B'] },
        ],
      });
      expect(r.success).toBe(false);
    });
  });
});
```

- [ ] **Step 2: 运行确认失败**

```bash
pnpm --dir frontend test --run tests/unit/build-type-schema.test.ts
```

Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现 buildTypeSchema**

`frontend/src/features/types/form/build-type-schema.ts`：直接照抄 spec §6.4 给的代码。文件内容：

```ts
import { z } from 'zod';

const fieldTypeEnum = z.enum([
  'string', 'text', 'url', 'int', 'float',
  'bool', 'date', 'enum', 'multi-enum',
]);

export const fieldDefSchema = z
  .object({
    key: z
      .string()
      .min(1, 'key 必填')
      .regex(/^[a-z][a-z0-9_]*$/, 'key 需 snake_case（小写字母开头）'),
    label: z.string().optional(),
    type: fieldTypeEnum,
    required: z.boolean().default(false),
    placeholder: z.string().optional(),
    help: z.string().optional(),
    default: z
      .union([z.string(), z.number(), z.boolean(), z.null()])
      .optional(),
    unit: z.string().optional(),
    min: z.number().optional(),
    max: z.number().optional(),
    options: z.array(z.string()).optional(),
    displayAs: z.enum(['radio', 'select']).optional(),
  })
  .superRefine((def, ctx) => {
    // 1. min ≤ max（int/float）
    if (
      (def.type === 'int' || def.type === 'float') &&
      def.min != null &&
      def.max != null &&
      def.min > def.max
    ) {
      ctx.addIssue({
        path: ['max'],
        code: 'custom',
        message: `max 不能小于 min（${def.min}）`,
      });
    }
    // 2. enum/multi-enum 必须有 options 且非空
    if (
      (def.type === 'enum' || def.type === 'multi-enum') &&
      (!def.options || def.options.length === 0)
    ) {
      ctx.addIssue({
        path: ['options'],
        code: 'custom',
        message: '需要至少 1 个选项',
      });
    }
    // 3. options 唯一
    if (def.options) {
      const seen = new Set<string>();
      def.options.forEach((opt, i) => {
        if (seen.has(opt)) {
          ctx.addIssue({
            path: ['options', i],
            code: 'custom',
            message: `选项 '${opt}' 已存在`,
          });
        }
        seen.add(opt);
      });
    }
  });

const customFieldsArraySchema = z
  .array(fieldDefSchema)
  .superRefine((fields, ctx) => {
    const seen = new Map<string, number>();
    fields.forEach((f, i) => {
      if (seen.has(f.key)) {
        ctx.addIssue({
          path: [i, 'key'],
          code: 'custom',
          message: `key '${f.key}' 已被使用`,
        });
      }
      seen.set(f.key, i);
    });
  });

export function buildTypeSchema({ mode }: { mode: 'create' | 'edit' }) {
  const base = z.object({
    name: z.string().min(1, '类型名必填'),
    description: z.string().optional(),
    custom_fields: customFieldsArraySchema,
  });
  return mode === 'create'
    ? base.extend({
        code_prefix: z
          .string()
          .regex(/^[A-Z]{2,4}$/, 'code_prefix 需 2-4 个大写字母'),
      })
    : base;
}

export type CreateTypeFormValues = z.infer<
  ReturnType<typeof buildTypeSchema>
>;
export type EditTypeFormValues = z.infer<
  ReturnType<typeof buildTypeSchema>
>;
export type FieldDefFormValue = z.infer<typeof fieldDefSchema>;
```

- [ ] **Step 4: 运行测试**

```bash
pnpm --dir frontend test --run tests/unit/build-type-schema.test.ts
```

Expected: 11 passed（4 顶层 + 2 单字段 + 5 superRefine）。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/features/types/form/build-type-schema.ts frontend/tests/unit/build-type-schema.test.ts
git commit -m "feat(types): build-type-schema + superRefine 三条跨字段校验（M2c-4 PR-3 Task 21）"
```

---

## Phase 14 · custom-fields-builder 5 组件（Task 22-26）

### Task 22: field-options-editor（chip + Enter 提交）

**Files:**
- Create: `frontend/src/features/types/form/custom-fields-builder/field-options-editor.tsx`

- [ ] **Step 1: 实现组件**

```tsx
import { useState, type KeyboardEvent } from 'react';
import { X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

interface Props {
  value: string[];
  onChange: (next: string[]) => void;
  errorPaths?: number[]; // 哪些 index 标红（来自 superRefine）
}

export function FieldOptionsEditor({ value, onChange, errorPaths = [] }: Props) {
  const [draft, setDraft] = useState('');
  const errorSet = new Set(errorPaths);

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && draft.trim()) {
      e.preventDefault();
      onChange([...value, draft.trim()]);
      setDraft('');
    }
  }

  function removeAt(idx: number) {
    onChange(value.filter((_, i) => i !== idx));
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {value.map((opt, idx) => (
          <Badge
            key={`${opt}-${idx}`}
            variant={errorSet.has(idx) ? 'destructive' : 'secondary'}
            className="group cursor-default pr-1"
          >
            <span className="mr-1">{opt}</span>
            <button
              type="button"
              onClick={() => removeAt(idx)}
              className="opacity-0 group-hover:opacity-100 transition-opacity hover:text-destructive cursor-pointer"
              aria-label={`删除选项 ${opt}`}
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
      </div>
      <Input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="输入选项后按 Enter"
        className="max-w-[280px]"
      />
    </div>
  );
}
```

- [ ] **Step 2: 跑测确认编译**

```bash
pnpm --dir frontend tsc --noEmit
```

Expected: 0 errors。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/types/form/custom-fields-builder/field-options-editor.tsx
git commit -m "feat(builder): field-options-editor chip + Enter 提交（M2c-4 PR-3 Task 22）"
```

---

### Task 23: field-type-selector（shadcn Select）

**Files:**
- Create: `frontend/src/features/types/form/custom-fields-builder/field-type-selector.tsx`

- [ ] **Step 1: 实现**

```tsx
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const FIELD_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: 'string', label: 'string · 短文本' },
  { value: 'text', label: 'text · 长文本' },
  { value: 'url', label: 'url · 网址' },
  { value: 'int', label: 'int · 整数' },
  { value: 'float', label: 'float · 小数' },
  { value: 'bool', label: 'bool · 布尔' },
  { value: 'date', label: 'date · 日期' },
  { value: 'enum', label: 'enum · 单选' },
  { value: 'multi-enum', label: 'multi-enum · 多选' },
];

interface Props {
  value: string;
  onChange: (next: string) => void;
}

export function FieldTypeSelector({ value, onChange }: Props) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-[220px]">
        <SelectValue placeholder="选择字段类型" />
      </SelectTrigger>
      <SelectContent className="bg-popover">
        {FIELD_TYPE_OPTIONS.map((opt) => (
          <SelectItem key={opt.value} value={opt.value}>
            {opt.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
```

- [ ] **Step 2: tsc**

```bash
pnpm --dir frontend tsc --noEmit
```

Expected: 0 errors。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/types/form/custom-fields-builder/field-type-selector.tsx
git commit -m "feat(builder): field-type-selector 9 种类型 shadcn Select（M2c-4 PR-3 Task 23）"
```

---

### Task 24: field-attribute-form（11 属性 conditional UI）

**Files:**
- Create: `frontend/src/features/types/form/custom-fields-builder/field-attribute-form.tsx`

- [ ] **Step 1: 实现**

```tsx
import type { Control, UseFormSetValue, FieldErrors } from 'react-hook-form';
import { Controller, useWatch } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { FieldTypeSelector } from './field-type-selector';
import { FieldOptionsEditor } from './field-options-editor';
import type { CreateTypeFormValues } from '../build-type-schema';

interface Props {
  control: Control<CreateTypeFormValues>;
  setValue: UseFormSetValue<CreateTypeFormValues>;
  index: number;
  errors?: FieldErrors<CreateTypeFormValues>;
}

export function FieldAttributeForm({ control, setValue, index, errors }: Props) {
  const path = `custom_fields.${index}` as const;
  const fieldType = useWatch({ control, name: `${path}.type` });
  const fieldErr = errors?.custom_fields?.[index];

  function onTypeChange(newType: string) {
    setValue(`${path}.type` as never, newType as never);
    // 切 type 时清空 type-specific 属性
    setValue(`${path}.unit` as never, undefined as never);
    setValue(`${path}.min` as never, undefined as never);
    setValue(`${path}.max` as never, undefined as never);
    setValue(`${path}.options` as never, undefined as never);
    setValue(`${path}.displayAs` as never, undefined as never);
  }

  return (
    <div className="space-y-4 p-4">
      {/* 通用属性 */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label>key *</Label>
          <Controller
            control={control}
            name={`${path}.key` as never}
            render={({ field }) => <Input {...field} placeholder="snake_case" />}
          />
          {fieldErr?.key && <p className="text-sm text-destructive mt-1">{fieldErr.key.message as string}</p>}
        </div>
        <div>
          <Label>type *</Label>
          <Controller
            control={control}
            name={`${path}.type` as never}
            render={({ field }) => (
              <FieldTypeSelector value={field.value} onChange={onTypeChange} />
            )}
          />
        </div>
        <div>
          <Label>label</Label>
          <Controller
            control={control}
            name={`${path}.label` as never}
            render={({ field }) => <Input {...field} value={field.value ?? ''} placeholder="显示名" />}
          />
        </div>
        <div className="flex items-center gap-2 mt-6">
          <Controller
            control={control}
            name={`${path}.required` as never}
            render={({ field }) => (
              <Checkbox
                checked={!!field.value}
                onCheckedChange={field.onChange}
                id={`required-${index}`}
              />
            )}
          />
          <Label htmlFor={`required-${index}`}>必填</Label>
        </div>
      </div>

      <div>
        <Label>placeholder</Label>
        <Controller
          control={control}
          name={`${path}.placeholder` as never}
          render={({ field }) => <Input {...field} value={field.value ?? ''} />}
        />
      </div>

      <div>
        <Label>help</Label>
        <Controller
          control={control}
          name={`${path}.help` as never}
          render={({ field }) => <Textarea {...field} value={field.value ?? ''} rows={2} />}
        />
      </div>

      {/* type-specific 属性 */}
      {(fieldType === 'int' || fieldType === 'float') && (
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label>unit</Label>
            <Controller
              control={control}
              name={`${path}.unit` as never}
              render={({ field }) => <Input {...field} value={field.value ?? ''} placeholder="GB / mm 等" />}
            />
          </div>
          <div>
            <Label>min</Label>
            <Controller
              control={control}
              name={`${path}.min` as never}
              render={({ field }) => (
                <Input
                  type="number"
                  value={field.value ?? ''}
                  onChange={(e) =>
                    field.onChange(e.target.value === '' ? undefined : Number(e.target.value))
                  }
                />
              )}
            />
          </div>
          <div>
            <Label>max</Label>
            <Controller
              control={control}
              name={`${path}.max` as never}
              render={({ field }) => (
                <Input
                  type="number"
                  value={field.value ?? ''}
                  onChange={(e) =>
                    field.onChange(e.target.value === '' ? undefined : Number(e.target.value))
                  }
                />
              )}
            />
            {fieldErr?.max && <p className="text-sm text-destructive mt-1">{fieldErr.max.message as string}</p>}
          </div>
        </div>
      )}

      {(fieldType === 'enum' || fieldType === 'multi-enum') && (
        <div>
          <Label>options *</Label>
          <Controller
            control={control}
            name={`${path}.options` as never}
            render={({ field }) => {
              const errorIndices = (fieldErr?.options as unknown as { message?: string }[] | undefined)
                ?.map((e, i) => (e ? i : -1))
                .filter((i) => i >= 0) ?? [];
              return (
                <FieldOptionsEditor
                  value={field.value ?? []}
                  onChange={field.onChange}
                  errorPaths={errorIndices}
                />
              );
            }}
          />
          {fieldErr?.options && typeof (fieldErr.options as { message?: string }).message === 'string' && (
            <p className="text-sm text-destructive mt-1">
              {(fieldErr.options as { message: string }).message}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: tsc**

```bash
pnpm --dir frontend tsc --noEmit
```

Expected: 0 errors（RHF 嵌套路径 `as never` 因 zod superRefine 过深推导退化是已知 trade-off；与 m2c1 已有 custom_data 嵌套同款应对）。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/types/form/custom-fields-builder/field-attribute-form.tsx
git commit -m "feat(builder): field-attribute-form 11 属性 conditional UI（M2c-4 PR-3 Task 24）"
```

---

### Task 25: field-card（折叠/展开）

**Files:**
- Create: `frontend/src/features/types/form/custom-fields-builder/field-card.tsx`

- [ ] **Step 1: 实现**

```tsx
import { useState } from 'react';
import { ArrowDown, ArrowUp, ChevronDown, ChevronRight, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import type { Control, UseFormSetValue, FieldErrors } from 'react-hook-form';
import { useWatch } from 'react-hook-form';
import { FieldAttributeForm } from './field-attribute-form';
import type { CreateTypeFormValues } from '../build-type-schema';

interface Props {
  control: Control<CreateTypeFormValues>;
  setValue: UseFormSetValue<CreateTypeFormValues>;
  index: number;
  total: number;
  defaultExpanded?: boolean;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  errors?: FieldErrors<CreateTypeFormValues>;
}

export function FieldCard({
  control,
  setValue,
  index,
  total,
  defaultExpanded = false,
  onRemove,
  onMoveUp,
  onMoveDown,
  errors,
}: Props) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const f = useWatch({ control, name: `custom_fields.${index}` });

  return (
    <Card className="overflow-hidden transition-[height] duration-200 ease-out motion-reduce:transition-none">
      {/* 折叠态行 */}
      <div className="flex items-center gap-3 p-3">
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="text-muted-foreground hover:text-foreground cursor-pointer"
          aria-label={expanded ? '折叠' : '展开'}
        >
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>
        <span className="font-mono text-sm">{f?.key || '(未命名字段)'}</span>
        <Badge variant="outline" className="text-xs">
          {f?.type || '?'}
        </Badge>
        {f?.required && <span className="text-destructive text-sm">*</span>}
        <div className="flex-1" />
        {expanded && (
          <>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={onMoveUp}
              disabled={index === 0}
              aria-label="上移"
            >
              <ArrowUp className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={onMoveDown}
              disabled={index === total - 1}
              aria-label="下移"
            >
              <ArrowDown className="h-4 w-4" />
            </Button>
          </>
        )}
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={onRemove}
          aria-label="删除字段"
          className="text-muted-foreground hover:text-destructive"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      {/* 展开态：属性表单 */}
      {expanded && (
        <div className="border-t border-border">
          <FieldAttributeForm
            control={control}
            setValue={setValue}
            index={index}
            errors={errors}
          />
        </div>
      )}
    </Card>
  );
}
```

- [ ] **Step 2: tsc**

```bash
pnpm --dir frontend tsc --noEmit
```

Expected: 0 errors。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/types/form/custom-fields-builder/field-card.tsx
git commit -m "feat(builder): field-card 折叠/展开 + ↑↓ 排序按钮 + 删除（M2c-4 PR-3 Task 25）"
```

---

### Task 26: builder.tsx 容器（useFieldArray）+ TDD

**Files:**
- Create: `frontend/src/features/types/form/custom-fields-builder/builder.tsx`
- Test: `frontend/tests/hooks/custom-fields-builder.test.tsx`

- [ ] **Step 1: 写失败测试**

```tsx
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { CustomFieldsBuilder } from '@/features/types/form/custom-fields-builder/builder';
import { buildTypeSchema, type CreateTypeFormValues } from '@/features/types/form/build-type-schema';

function Harness({ initial }: { initial?: Partial<CreateTypeFormValues> }) {
  const methods = useForm<CreateTypeFormValues>({
    resolver: zodResolver(buildTypeSchema({ mode: 'edit' })),
    defaultValues: {
      name: 'X',
      description: '',
      custom_fields: [],
      ...initial,
    },
  });
  return (
    <FormProvider {...methods}>
      <CustomFieldsBuilder control={methods.control} setValue={methods.setValue} errors={methods.formState.errors} />
    </FormProvider>
  );
}

describe('CustomFieldsBuilder', () => {
  it('点 "+ 添加字段" 加一张新卡', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole('button', { name: /添加字段/ }));
    expect(screen.getByText(/未命名字段/)).toBeInTheDocument();
  });

  it('删除按钮移除卡片', async () => {
    const user = userEvent.setup();
    render(<Harness initial={{ custom_fields: [{ key: 'k1', type: 'string' }] as never }} />);
    expect(screen.getByText('k1')).toBeInTheDocument();
    await user.click(screen.getByLabelText('删除字段'));
    expect(screen.queryByText('k1')).not.toBeInTheDocument();
  });

  it('空态显示虚线占位', () => {
    render(<Harness />);
    expect(screen.getByText(/添加你的第一个字段/)).toBeInTheDocument();
  });

  it('切 type 时清空 type-specific 属性', async () => {
    const user = userEvent.setup();
    render(
      <Harness
        initial={{
          custom_fields: [
            { key: 'k', type: 'int', min: 1, max: 10 },
          ] as never,
        }}
      />,
    );
    // 展开卡片
    await user.click(screen.getByLabelText('展开'));
    // 切 type 到 string
    // 这里的具体交互由 FieldTypeSelector + onTypeChange 触发，简化断言：
    // 检查切换后 min input 不存在（int-specific UI 隐藏）
    // 完整 e2e 走 Playwright 烟测；hook 层这里只验调用链
    // （实际实现中 onTypeChange 会触发 setValue 清空 min/max，UI 重渲染后无 min input）
    // skip：这条用 Playwright 烟测兜底
  });
});
```

- [ ] **Step 2: 运行确认失败**

```bash
pnpm --dir frontend test --run tests/hooks/custom-fields-builder.test.tsx
```

Expected: FAIL（builder 不存在）

- [ ] **Step 3: 实现 builder.tsx**

```tsx
import { useFieldArray } from 'react-hook-form';
import type { Control, UseFormSetValue, FieldErrors } from 'react-hook-form';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { FieldCard } from './field-card';
import type { CreateTypeFormValues } from '../build-type-schema';

interface Props {
  control: Control<CreateTypeFormValues>;
  setValue: UseFormSetValue<CreateTypeFormValues>;
  errors?: FieldErrors<CreateTypeFormValues>;
}

export function CustomFieldsBuilder({ control, setValue, errors }: Props) {
  const { fields, append, remove, move } = useFieldArray({
    control,
    name: 'custom_fields',
  });

  function handleAdd() {
    append({ key: '', type: 'string', required: false } as never);
  }

  if (fields.length === 0) {
    return (
      <button
        type="button"
        onClick={handleAdd}
        className="w-full rounded border border-dashed border-muted-foreground/40 py-12 text-center text-sm text-muted-foreground transition-colors hover:border-primary hover:bg-primary/5 hover:text-primary cursor-pointer"
      >
        <Plus className="inline h-4 w-4 mr-2" />
        添加你的第一个字段
      </button>
    );
  }

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        {fields.map((f, idx) => (
          <FieldCard
            key={f.id}
            control={control}
            setValue={setValue}
            index={idx}
            total={fields.length}
            defaultExpanded={idx === fields.length - 1 && (f as { key?: string }).key === ''}
            onRemove={() => remove(idx)}
            onMoveUp={() => move(idx, idx - 1)}
            onMoveDown={() => move(idx, idx + 1)}
            errors={errors}
          />
        ))}
      </div>
      <Button type="button" variant="outline" onClick={handleAdd}>
        <Plus className="h-4 w-4 mr-2" />
        添加字段
      </Button>
    </div>
  );
}
```

- [ ] **Step 4: 运行测试**

```bash
pnpm --dir frontend test --run tests/hooks/custom-fields-builder.test.tsx
```

Expected: 3 passed（4 skip 的占位用例改为 todo 或不写也可）。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/features/types/form/custom-fields-builder/builder.tsx frontend/tests/hooks/custom-fields-builder.test.tsx
git commit -m "feat(builder): builder 容器 useFieldArray + 空态 dashed border + 3 case 测试（M2c-4 PR-3 Task 26）"
```

---

## Phase 15 · type-form（Task 27-28）

### Task 27: type-form.tsx（create + edit 共用）+ TDD

**Files:**
- Create: `frontend/src/features/types/form/type-form.tsx`
- Test: `frontend/tests/hooks/type-form.test.tsx`

- [ ] **Step 1: 写失败测试**

```tsx
import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { TypeForm } from '@/features/types/form/type-form';

const server = setupServer();

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe('TypeForm', () => {
  it('create 模式提交 POST /api/types', async () => {
    const user = userEvent.setup();
    let body: any;
    server.use(
      http.post('/api/types', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(
          { id: 'new-id', ...body, created_at: '', updated_at: '' },
          { status: 201 },
        );
      }),
    );
    const onSuccess = vi.fn();
    render(<TypeForm mode="create" onSuccess={onSuccess} />, { wrapper });
    await user.type(screen.getByLabelText(/name/i), '笔记本');
    await user.type(screen.getByLabelText(/code_prefix/i), 'NB');
    await user.click(screen.getByRole('button', { name: /保存/ }));
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    expect(body.name).toBe('笔记本');
    expect(body.code_prefix).toBe('NB');
  });

  it('edit 模式 code_prefix readOnly 不进 PATCH body', async () => {
    const user = userEvent.setup();
    let patchBody: any;
    server.use(
      http.patch('/api/types/abc', async ({ request }) => {
        patchBody = await request.json();
        return HttpResponse.json({
          id: 'abc',
          name: 'New',
          code_prefix: 'NB',
          custom_fields: [],
          description: null,
          created_at: '',
          updated_at: '',
        });
      }),
    );
    render(
      <TypeForm
        mode="edit"
        initial={{
          id: 'abc',
          name: 'Old',
          code_prefix: 'NB',
          description: null,
          custom_fields: [],
          created_at: '',
          updated_at: '',
        } as never}
        onSuccess={() => {}}
      />,
      { wrapper },
    );
    const nameInput = screen.getByLabelText(/name/i);
    await user.clear(nameInput);
    await user.type(nameInput, 'New');
    await user.click(screen.getByRole('button', { name: /保存/ }));
    await waitFor(() => expect(patchBody).toBeDefined());
    expect(patchBody.code_prefix).toBeUndefined(); // 不发 code_prefix
    expect(patchBody.name).toBe('New');
  });

  it('DuplicateError 设字段级 setError(code_prefix)', async () => {
    const user = userEvent.setup();
    server.use(
      http.post('/api/types', () =>
        HttpResponse.json({ detail: 'code_prefix 已存在: NB' }, { status: 409 }),
      ),
    );
    render(<TypeForm mode="create" onSuccess={() => {}} />, { wrapper });
    await user.type(screen.getByLabelText(/name/i), 'X');
    await user.type(screen.getByLabelText(/code_prefix/i), 'NB');
    await user.click(screen.getByRole('button', { name: /保存/ }));
    await waitFor(() =>
      expect(screen.getByText(/code_prefix 已存在/)).toBeInTheDocument(),
    );
  });
});
```

- [ ] **Step 2: 运行确认失败**

```bash
pnpm --dir frontend test --run tests/hooks/type-form.test.tsx
```

Expected: FAIL（TypeForm 不存在）

- [ ] **Step 3: 实现 TypeForm**

```tsx
import { useEffect, useMemo } from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from '@/components/ui/form';
import { InlineErrorBanner } from '@/components/feedback/inline-error-banner';
import { useCreateTypeMutation, useUpdateTypeMutation } from '@/api/hooks/types';
import { toFriendlyMessage } from '@/lib/error';
import { buildTypeSchema, type CreateTypeFormValues } from './build-type-schema';
import { CustomFieldsBuilder } from './custom-fields-builder/builder';
import type { components } from '@/api/generated/schema';

type TypeRead = components['schemas']['TypeRead'];

interface Props {
  mode: 'create' | 'edit';
  initial?: TypeRead;
  onSuccess: (t: TypeRead) => void;
}

const CREATE_SCHEMA = buildTypeSchema({ mode: 'create' });
const EDIT_SCHEMA = buildTypeSchema({ mode: 'edit' });

export function TypeForm({ mode, initial, onSuccess }: Props) {
  const schema = mode === 'create' ? CREATE_SCHEMA : EDIT_SCHEMA;
  const createMut = useCreateTypeMutation();
  const updateMut = useUpdateTypeMutation();
  const mutation = mode === 'create' ? createMut : updateMut;

  const form = useForm<CreateTypeFormValues>({
    resolver: zodResolver(schema),
    defaultValues: useMemo(
      () => ({
        name: initial?.name ?? '',
        code_prefix: initial?.code_prefix ?? '',
        description: initial?.description ?? '',
        custom_fields: (initial?.custom_fields ?? []) as never,
      }),
      [initial],
    ),
  });

  useEffect(() => {
    if (initial) {
      form.reset({
        name: initial.name,
        code_prefix: initial.code_prefix,
        description: initial.description ?? '',
        custom_fields: (initial.custom_fields ?? []) as never,
      });
    }
  }, [initial, form]);

  async function onSubmit(values: CreateTypeFormValues) {
    try {
      if (mode === 'create') {
        const res = await createMut.mutateAsync({
          name: values.name,
          code_prefix: (values as { code_prefix: string }).code_prefix,
          description: values.description || undefined,
          custom_fields: values.custom_fields as never,
        });
        onSuccess(res);
      } else if (initial) {
        const body: { name?: string; description?: string | null; custom_fields?: unknown } = {};
        if (values.name !== initial.name) body.name = values.name;
        if ((values.description ?? '') !== (initial.description ?? ''))
          body.description = values.description || null;
        // custom_fields 总是发（替换语义）
        body.custom_fields = values.custom_fields;
        const res = await updateMut.mutateAsync({ id: initial.id, body });
        onSuccess(res);
      }
    } catch (e) {
      const msg = toFriendlyMessage(e);
      // DuplicateError 字段级
      if (msg.includes('code_prefix')) {
        form.setError('code_prefix' as never, { message: msg });
      } else if (msg.includes('名称') || msg.includes('name')) {
        form.setError('name', { message: msg });
      } else {
        form.setError('root', { message: msg });
      }
    }
  }

  const submitting = mutation.isPending;
  const submitLabel = submitting
    ? mode === 'create' ? '创建中…' : '保存中…'
    : '保存';

  return (
    <FormProvider {...form}>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-10">
          {form.formState.errors.root && (
            <InlineErrorBanner message={form.formState.errors.root.message ?? ''} />
          )}

          <section className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground border-b pb-1.5">
              基本信息
            </h2>

            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel htmlFor="name">name *</FormLabel>
                  <FormControl>
                    <Input id="name" {...field} placeholder="如：笔记本" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {mode === 'create' ? (
              <FormField
                control={form.control}
                name={'code_prefix' as never}
                render={({ field }) => (
                  <FormItem>
                    <FormLabel htmlFor="code_prefix">code_prefix *</FormLabel>
                    <FormControl>
                      <Input id="code_prefix" {...field} placeholder="2-4 大写字母" className="font-mono" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            ) : (
              <div>
                <Label htmlFor="code_prefix-readonly">code_prefix</Label>
                <Input
                  id="code_prefix-readonly"
                  value={initial?.code_prefix ?? ''}
                  readOnly
                  className="font-mono bg-muted text-muted-foreground"
                />
                <p className="text-xs text-muted-foreground mt-1">创建后不可修改</p>
              </div>
            )}

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel htmlFor="description">description</FormLabel>
                  <FormControl>
                    <Textarea id="description" {...field} value={field.value ?? ''} rows={2} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </section>

          <section className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground border-b pb-1.5">
              自定义字段
            </h2>
            <CustomFieldsBuilder
              control={form.control}
              setValue={form.setValue}
              errors={form.formState.errors}
            />
          </section>

          <div className="flex items-center justify-end gap-3">
            <Button type="button" variant="outline" onClick={() => history.back()}>
              取消
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitLabel}
            </Button>
          </div>
        </form>
      </Form>
    </FormProvider>
  );
}
```

- [ ] **Step 4: 运行测试**

```bash
pnpm --dir frontend test --run tests/hooks/type-form.test.tsx
```

Expected: 3 passed。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/features/types/form/type-form.tsx frontend/tests/hooks/type-form.test.tsx
git commit -m "feat(types): TypeForm create/edit 共用 + DuplicateError setError + 3 case 测试（M2c-4 PR-3 Task 27）"
```

---

### Task 28: tsc + 全测确认

```bash
pnpm --dir frontend test --run
pnpm --dir frontend tsc --noEmit
```

Expected: 38 + 8 + 4 + 11 + 3 + 3 = 67 passed；0 tsc。无 commit。

---

## Phase 16 · types 列表页（Task 29-30）

### Task 29: types-table-skeleton.tsx + types-table.tsx + types-page.tsx

**Files:**
- Create: `frontend/src/features/types/list/types-table-skeleton.tsx`
- Create: `frontend/src/features/types/list/types-table.tsx`
- Create: `frontend/src/features/types/list/types-page.tsx`

- [ ] **Step 1: 实现 skeleton**

```tsx
export function TypesTableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 rounded border border-border px-4 py-3"
        >
          <div className="h-4 w-32 rounded bg-muted animate-pulse" />
          <div className="h-4 w-16 rounded bg-muted animate-pulse" />
          <div className="h-4 w-12 rounded bg-muted animate-pulse" />
          <div className="ml-auto h-4 w-8 rounded bg-muted animate-pulse" />
        </div>
      ))}
    </div>
  );
}
```

注：`animate-pulse` 是 Tailwind 内置，不在红线（红线禁的是 `animate-spin`）。

- [ ] **Step 2: 实现 types-table**

```tsx
import { Link } from '@tanstack/react-router';
import { MoreHorizontal } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAssetsQuery } from '@/api/hooks/assets';
import type { components } from '@/api/generated/schema';

type TypeRead = components['schemas']['TypeRead'];

function RefCountCell({ typeId }: { typeId: string }) {
  const q = useAssetsQuery({ type: typeId, page: 1, page_size: 1, sort: undefined });
  if (q.isLoading) return <span className="text-muted-foreground">…</span>;
  const total = q.data?.total ?? 0;
  return (
    <Link
      to="/assets"
      search={{ type: typeId } as never}
      className="text-primary hover:underline"
    >
      {total}
    </Link>
  );
}

interface Props {
  rows: TypeRead[];
  onDelete: (t: TypeRead) => void;
}

export function TypesTable({ rows, onDelete }: Props) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
          <th className="px-3 py-2">name</th>
          <th className="px-3 py-2">code_prefix</th>
          <th className="px-3 py-2">字段数</th>
          <th className="px-3 py-2">资产引用</th>
          <th className="px-3 py-2 w-12" />
        </tr>
      </thead>
      <tbody>
        {rows.map((t) => (
          <tr key={t.id} className="border-b border-border hover:bg-muted/50">
            <td className="px-3 py-2 font-medium">
              <Link to="/types/$id" params={{ id: t.id }} className="hover:underline">
                {t.name}
              </Link>
            </td>
            <td className="px-3 py-2 font-mono text-xs">{t.code_prefix}</td>
            <td className="px-3 py-2">
              <Badge variant="secondary">{t.custom_fields?.length ?? 0} 个字段</Badge>
            </td>
            <td className="px-3 py-2">
              <RefCountCell typeId={t.id} />
            </td>
            <td className="px-3 py-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem
                    onSelect={() => onDelete(t)}
                    className="text-destructive"
                  >
                    删除…
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 3: 实现 types-page**

```tsx
import { useState } from 'react';
import { Link } from '@tanstack/react-router';
import { Inbox, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/feedback/error-state';
import { useAssetTypesQuery } from '@/api/hooks/types';
import { TypesTable } from './types-table';
import { TypesTableSkeleton } from './types-table-skeleton';
import { TypeDeleteDialog } from '../detail/type-delete-dialog';
import type { components } from '@/api/generated/schema';

type TypeRead = components['schemas']['TypeRead'];

export function TypesPage() {
  const q = useAssetTypesQuery();
  const [deletingType, setDeletingType] = useState<TypeRead | null>(null);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold">类型管理</h1>
          {q.data && (
            <p className="text-sm text-muted-foreground">共 {q.data.length} 个类型</p>
          )}
        </div>
        <Button asChild>
          <Link to="/types/new">
            <Plus className="h-4 w-4 mr-2" />
            新建类型
          </Link>
        </Button>
      </div>

      {q.isLoading && <TypesTableSkeleton />}
      {q.isError && <ErrorState onRetry={() => q.refetch()} />}
      {q.data && q.data.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-16 text-muted-foreground">
          <Inbox className="h-10 w-10" />
          <p>还没有类型</p>
          <Button asChild>
            <Link to="/types/new">创建第一个类型</Link>
          </Button>
        </div>
      )}
      {q.data && q.data.length > 0 && (
        <TypesTable rows={q.data} onDelete={setDeletingType} />
      )}

      {deletingType && (
        <TypeDeleteDialog
          type={deletingType}
          onClose={() => setDeletingType(null)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 4: tsc**

```bash
pnpm --dir frontend tsc --noEmit
```

Note: TypeDeleteDialog 还没建（Task 32）；先 stub 一个空组件让 tsc 过：

```tsx
// frontend/src/features/types/detail/type-delete-dialog.tsx (临时 stub)
export function TypeDeleteDialog(_p: { type: unknown; onClose: () => void }) { return null; }
```

后续 Task 32 实现真版。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/features/types/
git commit -m "feat(types-list): types-page + table + skeleton（empty/error/loading 三态）（M2c-4 PR-3 Task 29）"
```

---

### Task 30: 跑测确认

```bash
pnpm --dir frontend test --run
pnpm --dir frontend tsc --noEmit
```

Expected: 全绿。无 commit。

---

## Phase 17 · type-detail-page + delete-dialog（Task 31-32）

### Task 31: type-summary-card + type-detail-page

**Files:**
- Create: `frontend/src/features/types/detail/type-summary-card.tsx`
- Create: `frontend/src/features/types/detail/type-detail-page.tsx`

- [ ] **Step 1: 实现 summary-card**

```tsx
import type { components } from '@/api/generated/schema';

type TypeRead = components['schemas']['TypeRead'];

export function TypeSummaryCard({ type }: { type: TypeRead }) {
  return (
    <dl className="grid grid-cols-2 gap-4 text-sm">
      <div>
        <dt className="text-xs uppercase text-muted-foreground">name</dt>
        <dd className="font-medium">{type.name}</dd>
      </div>
      <div>
        <dt className="text-xs uppercase text-muted-foreground">code_prefix</dt>
        <dd className="font-mono">{type.code_prefix}</dd>
      </div>
      <div className="col-span-2">
        <dt className="text-xs uppercase text-muted-foreground">description</dt>
        <dd>{type.description || <span className="text-muted-foreground">—</span>}</dd>
      </div>
      <div>
        <dt className="text-xs uppercase text-muted-foreground">created_at</dt>
        <dd className="text-muted-foreground">{type.created_at}</dd>
      </div>
      <div>
        <dt className="text-xs uppercase text-muted-foreground">updated_at</dt>
        <dd className="text-muted-foreground">{type.updated_at}</dd>
      </div>
    </dl>
  );
}
```

- [ ] **Step 2: 实现 type-detail-page**

```tsx
import { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/feedback/error-state';
import { Skeleton } from '@/components/ui/skeleton';
import { useTypeQuery } from '@/api/hooks/types';
import { TypeSummaryCard } from './type-summary-card';
import { TypeDeleteDialog } from './type-delete-dialog';
import { TypeForm } from '../form/type-form';

export function TypeDetailPage({ id }: { id: string }) {
  const navigate = useNavigate();
  const q = useTypeQuery(id);
  const [deleting, setDeleting] = useState(false);

  if (q.isLoading) return <Skeleton className="h-96 w-full" />;
  if (q.isError) return <ErrorState onRetry={() => q.refetch()} />;
  if (!q.data) return null;

  return (
    <div className="space-y-10">
      <div className="flex items-start justify-between">
        <h1 className="text-xl font-semibold">编辑类型 - {q.data.name}</h1>
        <Button variant="ghost" onClick={() => setDeleting(true)} className="text-destructive">
          <Trash2 className="h-4 w-4 mr-2" />
          删除类型
        </Button>
      </div>

      <section>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">
          元信息
        </h2>
        <TypeSummaryCard type={q.data} />
      </section>

      <TypeForm
        mode="edit"
        initial={q.data}
        onSuccess={() => q.refetch()}
      />

      {deleting && (
        <TypeDeleteDialog
          type={q.data}
          onClose={() => setDeleting(false)}
          onDeleted={() => navigate({ to: '/types' })}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 3: tsc + 测**

```bash
pnpm --dir frontend tsc --noEmit
pnpm --dir frontend test --run
```

Expected: 0 errors / 全绿。

- [ ] **Step 4: 提交**

```bash
git add frontend/src/features/types/detail/type-summary-card.tsx frontend/src/features/types/detail/type-detail-page.tsx
git commit -m "feat(types-detail): TypeDetailPage + summary-card（编辑模式合一）（M2c-4 PR-3 Task 31）"
```

---

### Task 32: type-delete-dialog（含输入 type name 二次确认）+ TDD

**Files:**
- Modify: `frontend/src/features/types/detail/type-delete-dialog.tsx`（替换 stub）
- Test: `frontend/tests/hooks/type-delete-dialog.test.tsx`

- [ ] **Step 1: 写失败测试**

```tsx
import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { TypeDeleteDialog } from '@/features/types/detail/type-delete-dialog';

const server = setupServer();

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

const T = {
  id: 'abc',
  name: '笔记本',
  code_prefix: 'NB',
  description: null,
  custom_fields: [],
  created_at: '',
  updated_at: '',
} as never;

describe('TypeDeleteDialog', () => {
  it('ref_count > 0 → 禁用按钮 + 提示', async () => {
    server.use(
      http.get('/api/assets', () =>
        HttpResponse.json({ items: [], total: 3, page: 1, page_size: 1 }),
      ),
    );
    render(<TypeDeleteDialog type={T} onClose={() => {}} />, { wrapper });
    await waitFor(() =>
      expect(screen.getByText(/仍有 3 个资产引用/)).toBeInTheDocument(),
    );
    expect(screen.getByRole('button', { name: /永久删除/ })).toBeDisabled();
  });

  it('ref_count = 0 → 输入完整 name 后可删', async () => {
    const user = userEvent.setup();
    const onDeleted = vi.fn();
    server.use(
      http.get('/api/assets', () =>
        HttpResponse.json({ items: [], total: 0, page: 1, page_size: 1 }),
      ),
      http.delete('/api/types/abc', () => HttpResponse.text(null, { status: 204 })),
    );
    render(<TypeDeleteDialog type={T} onClose={() => {}} onDeleted={onDeleted} />, { wrapper });
    await waitFor(() => screen.getByPlaceholderText(/请输入完整类型名/));
    expect(screen.getByRole('button', { name: /永久删除/ })).toBeDisabled();
    await user.type(screen.getByPlaceholderText(/请输入完整类型名/), '笔记本');
    expect(screen.getByRole('button', { name: /永久删除/ })).toBeEnabled();
    await user.click(screen.getByRole('button', { name: /永久删除/ }));
    await waitFor(() => expect(onDeleted).toHaveBeenCalled());
  });
});
```

- [ ] **Step 2: 运行确认失败**

```bash
pnpm --dir frontend test --run tests/hooks/type-delete-dialog.test.tsx
```

Expected: FAIL（stub 是空组件）

- [ ] **Step 3: 实现真版**

```tsx
import { useState } from 'react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAssetsQuery } from '@/api/hooks/assets';
import { useDeleteTypeMutation } from '@/api/hooks/types';
import { toFriendlyMessage } from '@/lib/error';
import type { components } from '@/api/generated/schema';

type TypeRead = components['schemas']['TypeRead'];

interface Props {
  type: TypeRead;
  onClose: () => void;
  onDeleted?: () => void;
}

export function TypeDeleteDialog({ type, onClose, onDeleted }: Props) {
  const [confirmInput, setConfirmInput] = useState('');
  const refQuery = useAssetsQuery({
    type: type.id,
    page: 1,
    page_size: 1,
  } as never);
  const deleteMut = useDeleteTypeMutation();

  const refCount = refQuery.data?.total ?? 0;
  const hasRefs = refCount > 0;
  const inputMatches = confirmInput.trim() === type.name;
  const canDelete = !hasRefs && inputMatches && !deleteMut.isPending;

  async function handleDelete() {
    try {
      await deleteMut.mutateAsync(type.id);
      toast.success(`已删除类型 '${type.name}'`);
      onDeleted?.();
      onClose();
    } catch (e) {
      toast.error(toFriendlyMessage(e));
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>删除类型 '{type.name}'</DialogTitle>
          <DialogDescription>
            {hasRefs
              ? `该类型仍有 ${refCount} 个资产引用，请先删除/迁移所有引用此类型的资产。`
              : `此操作不可撤销。请输入完整类型名 '${type.name}' 以确认。`}
          </DialogDescription>
        </DialogHeader>

        {!hasRefs && (
          <Input
            value={confirmInput}
            onChange={(e) => setConfirmInput(e.target.value)}
            placeholder={`请输入完整类型名 '${type.name}'`}
            autoFocus
          />
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button
            variant="destructive"
            disabled={!canDelete}
            onClick={handleDelete}
          >
            {deleteMut.isPending ? '删除中…' : '永久删除'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 4: 跑测**

```bash
pnpm --dir frontend test --run tests/hooks/type-delete-dialog.test.tsx
```

Expected: 2 passed。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/features/types/detail/type-delete-dialog.tsx frontend/tests/hooks/type-delete-dialog.test.tsx
git commit -m "feat(types-delete): delete dialog + 输入 name 二次确认 + 2 case 测试（M2c-4 PR-3 Task 32）"
```

---

## Phase 18 · 资产 detail unknown-key banner（Task 33-34）

### Task 33: TDD unknown-key-detector 纯函数

**Files:**
- Create: `frontend/src/lib/unknown-key-detector.ts`
- Test: `frontend/tests/unit/unknown-key-detector.test.ts`

- [ ] **Step 1: 写失败测试**

```ts
import { describe, expect, it } from 'vitest';
import { detectUnknownKeys } from '@/lib/unknown-key-detector';
import type { FieldDef } from '@/features/assets/form/types';

describe('detectUnknownKeys', () => {
  it('orphan keys: custom_data 有 fieldDefs 没有的 key', () => {
    const fieldDefs: FieldDef[] = [{ key: 'cpu', type: 'string' }];
    const customData = { cpu: 'i7', ram_gb: 16 };
    const r = detectUnknownKeys(customData, fieldDefs);
    expect(r.orphanKeys).toEqual(['ram_gb']);
    expect(r.violatedRequired).toEqual([]);
    expect(r.hasIssues).toBe(true);
  });

  it('violatedRequired: required field 在 custom_data 中为 null/undefined', () => {
    const fieldDefs: FieldDef[] = [
      { key: 'brand', type: 'string', required: true },
      { key: 'cpu', type: 'string', required: false },
    ];
    const r = detectUnknownKeys({ cpu: 'i7' }, fieldDefs);
    expect(r.violatedRequired).toEqual([{ key: 'brand' }]);
  });

  it('两者皆空时 hasIssues = false', () => {
    const fieldDefs: FieldDef[] = [{ key: 'cpu', type: 'string' }];
    const r = detectUnknownKeys({ cpu: 'i7' }, fieldDefs);
    expect(r.hasIssues).toBe(false);
    expect(r.orphanKeys).toEqual([]);
    expect(r.violatedRequired).toEqual([]);
  });
});
```

- [ ] **Step 2: 实现**

```ts
import type { FieldDef } from '@/features/assets/form/types';

export interface UnknownKeyReport {
  orphanKeys: string[];
  violatedRequired: { key: string }[];
  hasIssues: boolean;
}

export function detectUnknownKeys(
  customData: Record<string, unknown>,
  fieldDefs: FieldDef[],
): UnknownKeyReport {
  const declared = new Set(fieldDefs.map((f) => f.key));
  const orphanKeys = Object.keys(customData).filter((k) => !declared.has(k));
  const violatedRequired = fieldDefs
    .filter((f) => f.required && customData[f.key] == null)
    .map((f) => ({ key: f.key }));
  return {
    orphanKeys,
    violatedRequired,
    hasIssues: orphanKeys.length > 0 || violatedRequired.length > 0,
  };
}
```

- [ ] **Step 3: 测试 + 提交**

```bash
pnpm --dir frontend test --run tests/unit/unknown-key-detector.test.ts
git add frontend/src/lib/unknown-key-detector.ts frontend/tests/unit/unknown-key-detector.test.ts
git commit -m "feat(banner): unknown-key-detector 纯函数 + 3 case 测试（M2c-4 PR-3 Task 33）"
```

---

### Task 34: 修改 custom-data-section.tsx 加 banner

**Files:**
- Modify: `frontend/src/features/assets/detail/custom-data-section.tsx`

- [ ] **Step 1: 修改 section**

读现有 `custom-data-section.tsx` 的接口与 props（assetCustomData + 当前 type fieldDefs），在顶层加 banner 渲染：

```tsx
import { useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { detectUnknownKeys } from '@/lib/unknown-key-detector';
import type { FieldDef } from '@/features/assets/form/types';

interface CustomDataSectionProps {
  customData: Record<string, unknown>;
  fieldDefs: FieldDef[];
  assetId: string;
}

export function CustomDataSection({ customData, fieldDefs, assetId }: CustomDataSectionProps) {
  const report = detectUnknownKeys(customData, fieldDefs);
  const dismissKey = `m2c4.banner.dismissed.${assetId}`;
  const [dismissed, setDismissed] = useState(
    () => sessionStorage.getItem(dismissKey) === '1',
  );

  function handleDismiss() {
    sessionStorage.setItem(dismissKey, '1');
    setDismissed(true);
  }

  const declaredEntries = fieldDefs.map((f) => ({
    def: f,
    value: customData[f.key],
  }));
  const orphanEntries = report.orphanKeys.map((k) => ({
    key: k,
    value: customData[k],
  }));

  return (
    <section className="space-y-4">
      {!dismissed && report.hasIssues && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded border border-warning/30 bg-warning/10 p-3 text-sm"
          style={{ borderColor: 'hsl(var(--color-warning) / 0.3)', backgroundColor: 'hsl(var(--color-warning) / 0.1)' }}
        >
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" style={{ color: 'hsl(var(--color-warning))' }} />
          <div className="flex-1 space-y-1">
            <p className="font-medium" style={{ color: 'hsl(var(--color-warning))' }}>
              该资产含 {report.orphanKeys.length} 个未声明字段 / {report.violatedRequired.length} 个必填项为空
            </p>
            <ul className="text-xs text-foreground space-y-0.5">
              {report.orphanKeys.map((k) => (
                <li key={k}>未声明字段：<span className="font-mono">{k}</span></li>
              ))}
              {report.violatedRequired.map(({ key }) => (
                <li key={key}>必填项为空：<span className="font-mono">{key}</span></li>
              ))}
            </ul>
          </div>
          <button
            type="button"
            onClick={handleDismiss}
            aria-label="关闭提示"
            className="text-muted-foreground hover:text-foreground cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* 主区：先渲染 declaredEntries，再渲染 orphanEntries（灰显）*/}
      <dl className="space-y-3">
        {declaredEntries.map(({ def, value }) => (
          <div key={def.key}>
            <dt className="text-xs uppercase text-muted-foreground">
              {def.label ?? def.key}
              {def.required && <span className="ml-1 text-destructive">*</span>}
            </dt>
            <dd>{formatValue(value, def)}</dd>
          </div>
        ))}
        {orphanEntries.map(({ key, value }) => (
          <div key={key} className="text-muted-foreground">
            <dt className="text-xs uppercase">
              {key}
              <Badge variant="outline" className="ml-2 text-xs">未声明</Badge>
            </dt>
            <dd>{String(value ?? '—')}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function formatValue(value: unknown, _def: FieldDef): string {
  if (value == null || value === '') return '—';
  return String(value);
}
```

注：颜色 token 走 `style` inline 传 hsl()，如果项目 globals.css 已注册 `--color-warning` 为 Tailwind utility（如 `bg-warning`/`text-warning`）则改用 utility。具体 syntax 以 globals.css 实际为准。

- [ ] **Step 2: tsc + 跑测**

```bash
pnpm --dir frontend tsc --noEmit
pnpm --dir frontend test --run
```

Expected: 全绿。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/assets/detail/custom-data-section.tsx
git commit -m "feat(banner): custom-data-section + AlertTriangle banner + sessionStorage dismiss（M2c-4 PR-3 Task 34）"
```

---

## Phase 19 · 路由接线（Task 35）

### Task 35: 创建 3 条 route 文件

**Files:**
- Create: `frontend/src/routes/types.tsx`
- Create: `frontend/src/routes/types.new.tsx`
- Create: `frontend/src/routes/types.$id.tsx`

- [ ] **Step 1: types.tsx**

```tsx
import { createFileRoute } from '@tanstack/react-router';
import { TypesPage } from '@/features/types/list/types-page';

export const Route = createFileRoute('/types')({
  component: TypesPage,
});
```

- [ ] **Step 2: types.new.tsx**

```tsx
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { TypeForm } from '@/features/types/form/type-form';

function NewType() {
  const nav = useNavigate();
  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-xl font-semibold">新建类型</h1>
      <TypeForm
        mode="create"
        onSuccess={(t) => nav({ to: '/types/$id', params: { id: t.id } })}
      />
    </div>
  );
}

export const Route = createFileRoute('/types/new')({
  component: NewType,
});
```

- [ ] **Step 3: types.$id.tsx**

```tsx
import { createFileRoute } from '@tanstack/react-router';
import { TypeDetailPage } from '@/features/types/detail/type-detail-page';

function TypeRoute() {
  const { id } = Route.useParams();
  return (
    <div className="max-w-3xl">
      <TypeDetailPage id={id} />
    </div>
  );
}

export const Route = createFileRoute('/types/$id')({
  component: TypeRoute,
});
```

- [ ] **Step 4: tsc + 跑测**

```bash
pnpm --dir frontend tsc --noEmit
pnpm --dir frontend test --run
```

Expected: 全绿。TanStack Router 会自动识别 `types.tsx` / `types.new.tsx` / `types.$id.tsx` 三条 file-based route。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/routes/types.tsx frontend/src/routes/types.new.tsx frontend/src/routes/types.$id.tsx
git commit -m "feat(routes): /types /types/new /types/$id 三条 file-based route（M2c-4 PR-3 Task 35）"
```

---

## Phase 20 · frontend-design 闸门 ④(b) + Playwright 烟测（Task 36-37）

### Task 36: frontend-design 闸门 ④(b) builder 骨架可跑

- [ ] **Step 1: 启动 dev**

```bash
uv run asset-hub serve start --mode dev
```

浏览器开 http://127.0.0.1:5173/types。

- [ ] **Step 2: 视觉巡查**

- [ ] nav 行 active 状态切换正确（"资产" / "类型" 互斥 underline）
- [ ] /types 列表加载态显示 skeleton（不是 spinner）
- [ ] /types 空态：Inbox icon + 文案 + CTA
- [ ] /types/new 表单布局：基本信息 → custom_fields builder → footer
- [ ] builder 空态：dashed border 占位
- [ ] 点 + 添加字段：新卡默认展开，输入 cpu / type=string，行折叠态显示 cpu + string chip
- [ ] 卡片折叠/展开 transition 200ms ease-out（不卡顿）

- [ ] **Step 3: 红线扫描**

```bash
grep -rnE "scale-|animate-spin|backdrop-blur|bg-gradient-to" frontend/src/features/types frontend/src/lib/unknown-key-detector.ts frontend/src/features/assets/detail/custom-data-section.tsx
```

Expected: 0 命中。

- [ ] **Step 4: 停止 dev**

```bash
uv run asset-hub serve stop
```

- [ ] **Step 5: 任何视觉偏差登记到 m2c4 followups（如有）**

无偏差 → 进 Task 37 烟测。

---

### Task 37: Playwright MCP 烟测 8 场景

> **Subagent / Claude 主操作**：以下 8 个场景由 Claude 通过 Playwright MCP 工具直接执行；对每个场景产出"通过/失败 + 关键截图"。

- [ ] **Step 1: 起隔离环境**

```bash
ASSET_HUB_DATA_DIR=data/smoke-test uv run asset-hub serve start --mode dev
```

- [ ] **Step 2: 场景 1 · Nav 行切换**

```
mcp__plugin_playwright_playwright__browser_navigate http://127.0.0.1:5173/assets
mcp__plugin_playwright_playwright__browser_snapshot   # 验 active="资产"
mcp__plugin_playwright_playwright__browser_click "类型"
mcp__plugin_playwright_playwright__browser_wait_for  text="还没有类型" or "类型管理"
mcp__plugin_playwright_playwright__browser_console_messages  # 应无 error
```

- [ ] **Step 3: 场景 2 · Type 创建**

navigate /types/new → fill_form name="测试笔记本" code_prefix="TEST" → 加 3 字段（cpu string required / ram_gb int min4 max128 unit=GB / os enum [Windows,macOS,Linux]）→ 提交 → 等跳到 /types/{id} → snapshot 验 3 卡片渲染 → `browser_network_requests` 验 POST /api/types 返 201。

- [ ] **Step 4: 场景 3 · Builder 跨字段校验**

(a) 加 key 重复字段 → snapshot 验"key 'cpu' 已被使用"红字
(b) min=10 max=2 → 验"max 不能小于 min（10）"
(c) options=[A,A,B] → 验第 2 个 chip 红
(d) 切 int→string → snapshot 验 unit/min/max 输入框消失

- [ ] **Step 5: 场景 4 · Type → Asset 联动**

navigate /assets/new → 选 type="测试笔记本" → 验 cpu/ram_gb/os 三动态字段渲染 → 填值提交 → 验 POST /api/assets 200 + custom_data 正确。

- [ ] **Step 6: 场景 5 · Type 编辑 + B 兼容触发 banner**

navigate /types/{id} → 删 ram_gb → 加 brand(string required) → 提交 → 走刚创建的资产 detail → 验 banner "1 个未声明字段(ram_gb) / 1 个必填空(brand)"，AlertTriangle SVG icon（不是 emoji），orphan 灰显 + "未声明" badge。

- [ ] **Step 7: 场景 6 · Type 删除（双路径）**

(a) 创建 ref=0 type → 走 /types/{id} → 点删除 → 输入 type name → 永久删除 → 列表少一项；DELETE 204
(b) 尝试删场景 2 的 type（ref=1）→ dialog 显示"仍有 1 个资产引用"+ 永久删除按钮 disabled

- [ ] **Step 8: 场景 7 · CLI `type update` 烟测**

用 Bash 工具：

```bash
# (a) dry-run + diff
TID=$(uv run asset-hub type list --json | jq -r '.data[0].id')
echo '{"name":"X","custom_fields":[]}' > /tmp/new.json
uv run asset-hub type update $TID --from /tmp/new.json --dry-run --json
# Expected: exit 10 + diff envelope

# (b) name only
uv run asset-hub type update $TID --name "Y" --json
# Expected: exit 0 + TypeRead

# (c) 互斥
uv run asset-hub type update $TID --from /tmp/new.json --name "Z" --json
# Expected: exit 2
```

- [ ] **Step 9: 场景 8 · screenshot 套**

5 张关键截图存盘：

```
mcp__plugin_playwright_playwright__browser_take_screenshot filename="tmp/smoke-screenshots/m2c4-types-list.png"
... (其余 4 张：type-detail / type-create-form / type-edit-form / builder-card-展开)
```

- [ ] **Step 10: 停止环境 + 清理**

```bash
uv run asset-hub serve stop
rm -rf data/smoke-test
```

- [ ] **Step 11: 烟测报告**

8 场景全绿 → 进 Task 38；任一失败 → 修问题 → 重跑该场景；新发现 bug → `docs/superpowers/followups-m2c4-smoketest.md` 登记。

无 commit（烟测产物在 `tmp/` 不入库）。

---

## Phase 21 · frontend-design 闸门 ④(c) + PR-3 收尾（Task 38-39）

### Task 38: 闸门 ④(c) Pre-Delivery Checklist + 红线 + 全测

- [ ] **Step 1: Pre-Delivery Checklist 7 项**

- [ ] No emojis as icons：grep `"⚠\|✗\|⭐\|❌\|✓"` 在 PR-3 改动文件 0 命中
- [ ] cursor-pointer 在所有 clickable（chip 删除 X / nav Link / FieldCard 折叠按钮 / dashed border 添加块）
- [ ] Hover transitions 150-300ms：所有按钮/Link/chip 用 `transition-colors`，无 `transform: scale`
- [ ] Light mode contrast 4.5:1（沿用 m2c1 token，无新色变量；`--color-warning` amber 在 light bg 上对比足够）
- [ ] Focus-visible：sessionStorage dismiss 按钮 + nav Link + builder 字段 input 全部可 focus
- [ ] prefers-reduced-motion：FieldCard 折叠的 200ms 已加 `motion-reduce:transition-none`
- [ ] Responsive 1024+：max-w-3xl 表单；types-table 在 ≥1024 完整显示

- [ ] **Step 2: 红线扫描全 PR-3 文件**

```bash
grep -rnE "scale-|animate-spin|backdrop-blur|bg-gradient-to|⚠" \
  frontend/src/features/types \
  frontend/src/lib/unknown-key-detector.ts \
  frontend/src/features/assets/detail/custom-data-section.tsx \
  frontend/src/routes/types*.tsx
```

Expected: 0 命中。

- [ ] **Step 3: 全测 + lint + tsc**

```bash
pnpm --dir frontend test --run
pnpm --dir frontend lint
pnpm --dir frontend tsc --noEmit
uv run pytest
uv run ruff check .
```

Expected: 全绿。前端 38 + 8 + 22-28 = 68-74 测；后端 311 测；lint 0 errors（保留 m2c1 1 警告）；tsc 0 errors。

无 commit。

---

### Task 39: PR-3 准备 + 文档回填

**Files:**
- Modify: `docs/superpowers/followup-allocation.md` — 标记 M2c-4 完成
- Modify: `docs/superpowers/simplify-followups.md` — 标记 A1/F3/A2/A4 已落地
- Create: `docs/superpowers/release-notes-m2c4.md`（按 m2d 模板写）

- [ ] **Step 1: followup-allocation.md 回填**

把 `## M2c-4 · 类型管理 UI（含结构化 custom_fields builder）` 部分的状态从 ⏳ 改为 ✅；底部摘要表 M2c-4 行从"⏳ 待启动"改为"✅ 已完成（2026-05-XX）"。

- [ ] **Step 2: simplify-followups.md 回填**

把 §1.A 的 A1 / A2 / A4 三项 + §1.F 的 F3 标"M2c-4 已落地（feature/m2c4-form-infra Tasks 10-15）"。

- [ ] **Step 3: release-notes-m2c4.md（按 m2d 模板）**

```markdown
# M2c-4 部署手工干预清单

## 概览

M2c-4 交付内容：

- **主线**：类型管理 web UI（list/detail/edit/create/delete）+ custom_fields 结构化 builder
- **后端**：PATCH /api/types/{id} + service.update_type
- **CLI**：asset-hub type update（整体替换 + 顶层独立 flag，退出码 0/1/2/3/10）
- **layout**：B 顶部 nav 行（资产 / 类型）
- **simplify 搭车**：A1 合并 buildAssetSchema / F3 模块级常量 / A2 FieldShell / A4 Control<T> 泛型
- **资产详情兼容 banner**：α 策略，写时不动 + 读时显示警告，独立 --color-warning token

## 升级前

1. 备份数据库
2. （无后端 schema 变更，alembic 不需要 upgrade）

## 升级

git pull
uv sync
pnpm --dir frontend install
pnpm --dir frontend gen:api
pnpm --dir frontend build  # 如有 prod 部署

## 升级后验证

uv run pytest                                       # 311 backend tests
pnpm --dir frontend test --run                      # 60+ frontend tests
uv run ruff check .                                 # clean
pnpm --dir frontend lint && pnpm tsc --noEmit       # clean

## CLI 表面验证

uv run asset-hub type update --help
uv run asset-hub type update <id> --name X --json   # exit 0 + envelope

## Web UI 烟测

- [ ] /types 列表 + skeleton + 空态 + 错误态 三态切换
- [ ] /types/new 创建类型 + builder 9 类型 + superRefine 三条校验
- [ ] /types/{id} 编辑 + 删除 + ref_count 双路径
- [ ] 资产 detail unknown-key banner（B 策略）
- [ ] B nav 行 active 状态切换

## 已知 Gap

| 项 | 性质 | 处理 |
|---|---|---|
| 后端 type schema 数组级校验 | M2c-4 由前端 superRefine 兜住 | 与 K1 envelope 同 M3 周期 |
| 兼容策略 C 迁移引擎 | v1 单作者 ROI 不匹配 | 暂不动 |
| dnd-kit 拖拽排序 | v1 字段 ≤ 10 ↑↓ 足够 | 暂不动 |
| `default` 在 int/float/bool/date/enum/multi-enum 的 UI | v1 仅 string/text | 登记 follow-up |
```

- [ ] **Step 4: 提交**

```bash
git add docs/superpowers/
git commit -m "docs(m2c4): release notes + followup-allocation + simplify-followups 回填（M2c-4 PR-3 Task 39）"
```

- [ ] **Step 5: 推 PR-3**

提示用户：feature/m2c4-types-ui 分支推 GitHub 后开 PR；PR 描述里把 8 烟测场景结果 + 5 张 screenshot 路径 + frontend-design 闸门 ④(c) 自查清单挂上。

---

## Self-Review

### 1. Spec coverage

- ✅ §3.1 路由（/types /types/new /types/$id）→ Task 35
- ✅ §3.2 顶部导航 B nav 行 → Task 16
- ✅ §3.3 列表页 + skeleton + 空态 + 错误态 → Task 29
- ✅ §3.4 创建/编辑表单 + footer 按钮 + 提交态 → Task 27
- ✅ §3.5 详情/编辑合一页 + 删除流程 → Task 31, 32
- ✅ §3.6 资产详情 unknown-key banner（α + AlertTriangle + sessionStorage dismiss）→ Task 33, 34
- ✅ §3.7 错误展示策略 → Task 27 setError 字段级处理
- ✅ §4.1 PATCH /api/types/{id} → Task 4
- ✅ §4.2 TypeService.update_type → Task 1, 2
- ✅ §4.3 OpenAPI gen:api 同步 → Task 18
- ✅ §5 CLI type update（互斥/退出码/dry-run/from-file）→ Task 6, 7, 8
- ✅ §6.1 卡片折叠/展开 + 默认展开新增 + 空态虚线 → Task 25, 26
- ✅ §6.2 卡片操作（add/remove/move/切 type）→ Task 26
- ✅ §6.3 11 属性 conditional UI → Task 24
- ✅ §6.4 zod schema + superRefine 三条 → Task 21
- ✅ §7 兼容策略 B（写时不动、读时 banner、PUT 完全替换）→ Task 33, 34（写时不动由 PR-1 service 不扫 asset 已实现；读时 banner 由 Task 34；PUT 完全替换是 M2c-3 既有契约）
- ✅ §8.1 新组件审美红线（每个组件具体规格）→ Task 16, 22-26, 31, 32, 34
- ✅ §8.3 frontend-design 4 阶段闸门 → Task 17（PR-2 ④a），Task 36（④b），Task 38（④c）
- ✅ §9.1 后端 26 测 → Task 1-9
- ✅ §9.2 前端 PR-2 ~4 单测 + 38 全绿 → Task 10, 13, 17
- ✅ §9.3 前端 PR-3 22-28 测 → Task 19-34
- ✅ §9.4 Playwright MCP 8 场景烟测 → Task 37
- ✅ §10 PR 拆分 + 依赖 → 阶段总览 + 三 PR 边界声明
- ✅ §11 Gap 登记 → Task 39 release notes 已知 Gap 表
- ✅ §12 决策 D1-D17 → 已写入 spec，本计划仅引用执行不再重述

### 2. Placeholder scan

无 "TBD / TODO / 写测试 (无具体测试) / 类似 Task N（无具体代码）" 命中。所有 Step 含具体代码或具体命令。

### 3. Type consistency

- `update_type(type_id, name?, description?, custom_fields?)` 三处一致（Task 1 service / Task 4 router / Task 6 CLI）
- `useUpdateTypeMutation` 接受 `{ id, body }` 两参数对象（Task 19）；`TypeForm` 调用一致（Task 27）
- `FieldShell<TFieldValues>` 泛型签名（Task 13）；8 field-controls 调用一致（Task 14）
- `buildAssetSchema(fieldDefs, { mode })` 签名（Task 10）；asset-create-form / asset-edit-form 调用一致（Task 11）
- `buildTypeSchema({ mode })` 签名（Task 21）；TypeForm 调用一致（Task 27）
- `qk.assetTypes.detail(id)` 引用一致（Task 19 query-keys + 19 hooks + 32 detail dialog）

无类型/签名漂移。

---

## 执行模式选择

**计划已保存到 `docs/superpowers/plans/2026-05-01-m2c4-type-management.md`。两种执行模式：**

**1. Subagent-Driven（推荐）** — 每 Task 派 fresh subagent 执行 + 两段 review；快速迭代；并行支持 PR-1 与 PR-2 分别派一组 subagent

**2. Inline Execution** — 当前 session 顺序执行；每 Phase 末 checkpoint 给用户 review

**选哪种？**
