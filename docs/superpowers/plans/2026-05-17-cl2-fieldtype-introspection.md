# CL-2 · CLI `--help-json` 暴露 FieldType 枚举 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩 `asset-hub type define --help-json` 输出，在 `--fields` 参数条目下嵌套 `valid_field_types` 数组（9 个值，来自 `FieldType` enum），让 Agent 通过自描述就能知道 custom field 合法 type 值，无需读源码。

**Architecture:** 在 `cli/deps.py::print_help_json` 加一个轻量"param enrichment registry"——`dict[(command_path, param_name), extra_dict]`；`type_cmd.py` 在模块加载时调用 `register_param_enrichment` 把 FieldType 枚举注册给 `(type define, --fields)`。注册接口预留给后续命令复用，但本 PR 只接 1 处。

**Tech Stack:** Python `dict` 模块级 registry、`FieldType` enum（`services/field_type.py`）、现有 `print_help_json`（`cli/deps.py:198-235`）。

**Spec 来源**：`docs/superpowers/specs/2026-05-17-m4-batch-plan-design.md` CL-2 段。

**预期开销**：单 PR / 3 task / commit `feat(cli): --help-json 暴露 type define --fields 的 valid_field_types`。SemVer MINOR（CLI 新增 introspection 字段）。

---

## Phase 1：registry 基建 + type define 注册

### Task 1：写 failing test —— `type define --help-json` 输出含 valid_field_types

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\tests\cli\test_type_cmd.py`（在文件末尾追加新 case）

- [ ] **Step 1：写测试**

```python
def test_type_define_help_json_includes_valid_field_types(cli_runner):
    """type define --help-json 应在 --fields 参数下嵌套 valid_field_types（FieldType 9 个枚举值）。"""
    from asset_hub.services.field_type import FieldType
    from asset_hub.cli.main import app
    import json

    result = cli_runner.invoke(app, ["type", "define", "--help-json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    fields_param = next(
        (p for p in payload["params"] if p["name"] == "--fields"), None
    )
    assert fields_param is not None, f"未找到 --fields 参数：{payload}"
    assert "valid_field_types" in fields_param, (
        f"--fields 参数缺 valid_field_types：{fields_param}"
    )
    assert fields_param["valid_field_types"] == [t.value for t in FieldType]
    # 显式列 9 个值，防 FieldType 未来漂移悄悄改变 contract
    assert set(fields_param["valid_field_types"]) == {
        "string", "text", "url", "int", "float",
        "bool", "enum", "multi-enum", "date",
    }


def test_other_commands_help_json_no_valid_field_types(cli_runner):
    """非 type define 命令的 --help-json 不应被污染（registry 只匹配特定 command）。"""
    from asset_hub.cli.main import app
    import json

    result = cli_runner.invoke(app, ["asset", "register", "--help-json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    for p in payload["params"]:
        assert "valid_field_types" not in p, (
            f"asset register 的 {p['name']} 不应有 valid_field_types"
        )
```

如 `test_type_cmd.py` 没有 `cli_runner` fixture，参考其他 `tests/cli/*.py` 的 fixture 路径（如 `tests/cli/conftest.py`）并对齐 import。

- [ ] **Step 2：跑 test 看 fail**

```bash
uv run pytest tests/cli/test_type_cmd.py::test_type_define_help_json_includes_valid_field_types -v
uv run pytest tests/cli/test_type_cmd.py::test_other_commands_help_json_no_valid_field_types -v
```

期望：第 1 个 FAIL（`--fields` 参数缺 valid_field_types）；第 2 个 PASS（meaningful 通过——其他命令默认就没有 valid_field_types）。

### Task 2：实现 registry + 注册逻辑

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\src\asset_hub\cli\deps.py`（在 `print_help_json` 之前加 registry；在 `print_help_json` 内合并 enrichment）
- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\src\asset_hub\cli\type_cmd.py`（在模块加载时调用 `register_param_enrichment`）

- [ ] **Step 1：在 `deps.py` 加 registry**

在 `cli/deps.py` 的 `_type_name` 函数定义之前（约第 157 行 "# --- --help-json 双模" 注释**之前**或之后）加：

```python
# --- --help-json param enrichment registry ---


_PARAM_ENRICHMENTS: dict[tuple[str, str], dict[str, object]] = {}


def register_param_enrichment(
    command_path: str, param_name: str, extra: dict[str, object]
) -> None:
    """为指定 (command_path, param_name) 注册附加元数据，--help-json 输出时自动合并。

    command_path: 完整 click 命令路径，如 "asset-hub type define"。
    param_name:   首个 long option / argument metavar，如 "--fields"。
    extra:        会被浅合并到 param dict（覆盖同名 key）。
    """
    _PARAM_ENRICHMENTS[(command_path, param_name)] = extra
```

然后修改 `print_help_json` 函数（行 198-235）中构造 param dict 的循环，在 `params.append(...)` **之后**注入合并逻辑。原代码：

```python
        params.append(
            {
                "name": name,
                "type": _type_name(p.type),
                "default": _default_value(p.default),
                "required": bool(getattr(p, "required", False)),
                "help": getattr(p, "help", None) or "",
            }
        )
```

改成：

```python
        entry: dict[str, object] = {
            "name": name,
            "type": _type_name(p.type),
            "default": _default_value(p.default),
            "required": bool(getattr(p, "required", False)),
            "help": getattr(p, "help", None) or "",
        }
        # 合并 registry 中针对当前 (command_path, name) 的 enrichment
        cmd_path = ctx.command_path or cmd.name or ""
        extra = _PARAM_ENRICHMENTS.get((cmd_path, name))
        if extra:
            entry.update(extra)
        params.append(entry)
```

**说明**：

- 浅合并（`entry.update(extra)`）：extra 同名 key 覆盖默认 key。本 PR 不需要覆盖（仅新增 `valid_field_types`），但语义干净
- 用 `ctx.command_path` 与注册时的 command_path 字符串严格匹配（注册时必须用完整路径，如 `"asset-hub type define"`）

- [ ] **Step 2：在 `type_cmd.py` 注册**

在 `cli/type_cmd.py` 文件**末尾**（所有 `@type_app.command(...)` 装饰函数定义之后）加：

```python
# --- --help-json registry: 暴露 FieldType 枚举给 Agent ---
from asset_hub.services.field_type import FieldType  # noqa: E402
from asset_hub.cli.deps import register_param_enrichment  # noqa: E402


register_param_enrichment(
    "asset-hub type define",
    "--fields",
    {"valid_field_types": [t.value for t in FieldType]},
)
```

**说明**：

- `# noqa: E402` 因为 import 在文件末尾不符 PEP 8，但本块意在"模块加载时副作用注册"，写底部更清晰
- `"asset-hub type define"` 是 `ctx.command_path` 在 typer / click 下的实际值（CliRunner 测会验证，如不对则改成实际值——可用 print debug）

- [ ] **Step 3：跑 test 看 pass**

```bash
uv run pytest tests/cli/test_type_cmd.py::test_type_define_help_json_includes_valid_field_types tests/cli/test_type_cmd.py::test_other_commands_help_json_no_valid_field_types -v
```

期望两个全 PASS。

**如 `test_type_define_help_json_includes_valid_field_types` 仍 FAIL**：

- 用 print debug 确认 `ctx.command_path` 真值，可能不是 `"asset-hub type define"` 而是 `"type define"` 或 `"asset_hub type define"`
- 调 `register_param_enrichment` 第一个参数对齐实际值

### Task 3：lint + 全测 + commit

- [ ] **Step 1：跑全测**

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

期望全绿。特别注意：

- `tests/cli/test_help_json_*.py`（spec scan §17 提到 `--help-json` 现有覆盖范围）应**全部保持 PASS**——本 PR 没改 print_help_json 的现有 contract，只加新 key

- [ ] **Step 2：commit**

```bash
git add src/asset_hub/cli/deps.py src/asset_hub/cli/type_cmd.py tests/cli/test_type_cmd.py
git commit -m "feat(cli): --help-json 暴露 type define --fields 的 valid_field_types

Agent 设计 AssetType 时常错填 type: \"boolean\"（合法值是 bool）——v2.0.2 skill 验证已实测。
deps.py 加 _PARAM_ENRICHMENTS registry + register_param_enrichment(command_path, param_name, extra)；
type_cmd.py 模块加载时注册 (asset-hub type define, --fields) → valid_field_types = FieldType 9 个枚举值。
不改 Pydantic CustomFieldDef.type 仍 str（业务约束保留 service 层架构）。"
```

---

## Phase 2：smoke + PR

### Task 4：本地 smoke + PR

**Files:** （无代码改动）

- [ ] **Step 1：本地 smoke**

```bash
uv run asset-hub type define --help-json | python -m json.tool
```

期望 stdout 含：

```json
{
  "command": "asset-hub type define",
  "params": [
    ...
    {
      "name": "--fields",
      "type": "str",
      "default": null,
      "required": false,
      "help": "自定义字段 JSON 数组",
      "valid_field_types": ["string", "text", "url", "int", "float", "bool", "enum", "multi-enum", "date"]
    },
    ...
  ]
}
```

另跑：

```bash
uv run asset-hub asset register --help-json | python -m json.tool | grep valid_field_types
```

期望：无输出（其他命令不应有 valid_field_types）。

- [ ] **Step 2：开 PR**

```bash
git push -u origin <branch-name>
gh pr create --title "feat(cli): --help-json 暴露 type define --fields 的 valid_field_types" --body "$(cat <<'EOF'
## Summary
- deps.py 新增 _PARAM_ENRICHMENTS registry + register_param_enrichment public API
- type_cmd.py 模块加载时注册 (type define, --fields) → FieldType 9 个枚举值
- print_help_json 输出时浅合并 enrichment 到对应 param dict

## Test plan
- [x] test_type_define_help_json_includes_valid_field_types PASS
- [x] test_other_commands_help_json_no_valid_field_types PASS（防 enrichment 误污染其他命令）
- [x] 本地 smoke：asset-hub type define --help-json | jq '.params[] | select(.name=="--fields")'

闭环 issue #12（CLI 暴露 FieldType 枚举）。
spec：docs/superpowers/specs/2026-05-17-m4-batch-plan-design.md CL-2 段。
EOF
)"
```

- [ ] **Step 3：等 CI + merge**

```bash
gh pr checks <pr-number>
gh pr merge --squash --delete-branch
```

---

## Self-Review Checklist

- [x] Spec coverage：spec §CL-4 的"扩 --help-json 输出 / FieldType 9 个值 / 不动 Pydantic CustomFieldDef.type" 全在 Task 1-3
- [x] 不在 scope：未加独立 `type fields list` 子命令（spec 方案 B 明示不做）；未把 FieldType 升为 Literal/Enum 类型校验（Pydantic 业务约束保留 service 层）
- [x] 无 placeholder：registry 实现 / 注册代码 / 测试 / commit msg 全完整
- [x] 类型一致：`register_param_enrichment(command_path, param_name, extra)` 在 deps.py 定义、type_cmd.py 调用，签名一致

## 风险

- **`ctx.command_path` 字符串值**：依赖 typer / click 在 CliRunner 下的实际值。如不是 `"asset-hub type define"`，需调 `register_param_enrichment` 第一个参数对齐——本 plan Task 2 Step 3 已含 fallback 调整指引
- **registry 是模块级全局可变状态**：当前 1 处注册不冲突；未来若多处注册同 (command_path, param_name) 会后注册覆盖前注册——可接受（无 use case），加 doctring 提醒即可
- **enrichment 不参与 stable contract**：未来 FieldType 加一个枚举值（如 `"json"`）时 `valid_field_types` 数组会自动变长——Agent 应解析数组而非硬编码 9 个值。SKILL.md 后续如显式列出这 9 个值需同步更新
