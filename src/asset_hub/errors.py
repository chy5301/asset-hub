"""asset-hub 域异常 base class + 6 子类（v2.0 引入结构化字段）。

v2.0 §4.2：每个异常实例可携带可选 hint / fields_missing / fields_invalid /
affected_resource_id，由 api/app.py + cli/envelope.py 在序列化时 exclude None
读出，agent 可结构化消费。

backward compat：所有可选参数都 keyword-only，positional 仍只接受 message——
现有 40 处 `raise XxxError("<msg>")` 调用站点零改动。
"""

from __future__ import annotations


class AssetHubError(Exception):
    code: str = ""  # 子类必须 override

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        fields_missing: list[str] | None = None,
        fields_invalid: dict[str, str] | None = None,
        affected_resource_id: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.fields_missing = fields_missing
        self.fields_invalid = fields_invalid
        self.affected_resource_id = affected_resource_id


class NotFoundError(AssetHubError):
    code = "not_found"


class DuplicateError(AssetHubError):
    code = "duplicate"


class ValidationError(AssetHubError):
    code = "validation"


class StateError(AssetHubError):
    """业务规则冲突：对象存在，但当前状态不允许此操作。

    例：对 IN_USE 资产再次派发；对无未归还记录的资产归还。"""

    code = "state_conflict"


class ConflictError(AssetHubError):
    """资源被其他对象引用，无法执行删除/修改。

    例：删除仍有资产引用的 AssetType。
    与 StateError 区别：StateError 是单对象生命周期/状态机不允许；
    ConflictError 是跨对象引用关系不允许。"""

    code = "conflict"


class IllegalTransitionError(AssetHubError):
    """状态机拒绝当前 transition。映射 HTTP 409 Conflict。"""

    code = "illegal_transition"
