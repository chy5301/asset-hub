# M3a · 状态机基建设计文档

- **日期**：2026-05-03
- **状态**：初稿，待实施
- **作者**：conghaoyangbobby@gmail.com（与 Claude 协同 brainstorm）
- **范围**：M3a 子里程碑落地细节，承接 [`2026-05-03-m3-overview-design.md`](./2026-05-03-m3-overview-design.md)
- **依赖**：M3 总览 §2（5 态状态机 + 10 transition）、§3 M3a 段（边界承诺）

## 0. 与 M3 总览的关系

本文是 M3a 子 spec，**总览先行，子 spec 落地**。总览拍板的核心决策（5 态枚举、10 transition kind、StateTransitionRecord 激进合并、API 不向后兼容、CLI 9 子命令骨架）不在本文重新讨论；本文负责落地细节：

- PR 拆分与边界
- 数据模型字段定义、状态机校验层 SoT
- API / CLI / 前端契约的具体形态
- 强搭车 follow-up 的具体闭环方式（C1 / §J / §L / §14.3 / §14.6 / §14.7 / §14.1 / smoketest B1）
- design-system 视觉约束（按 MASTER.md 反 AI-slop 红线）

**对 M3 总览的修订项**集中在本文 §7 列出，与本子 spec 同 commit 写回总览文件。

---

## 1. 架构总览

### 1.1 范围

**包**：

- alembic schema migration（**纯 schema 变更**，不迁移测试数据）
  1. `Asset.status` enum 加 `DISPOSED`（5 态）
  2. 建 `state_transition_records` 表
  3. drop `checkout_records` 表
  4. drop `Asset.current_checkout_id` 字段
- `StateTransitionRecord` 模型 + service `record_transition()` + 状态机校验层（C1 SoT 闭环）
- 后端 API：废 `/checkout` `/return` `/history` 散点端点，统一 `POST/GET /api/assets/{id}/transitions`
- CLI：保留命令名 `asset checkout / return / history`（实现切换）；删 `asset change-status`；新加 7 个命令（`send-to-maintenance / recover / retire / reinstate / dispose / relocate / transfer-holder`）
- 前端：7 个 dialog 组件（6 个独立 dialog + 1 个 SimpleTransitionDialog 共用组件服务 3 个简单 kind；按 status token 染色 + AlertDialog/Dialog 按可逆性区分） + 列表 2 个 status-token Toggle chip + timeline 10 kind icon×token 配置 + 新增 `--status-disposed` token pair
- 5 态文案修订（在用/闲置/维修中/已退役/已处置）
- 强搭车 follow-up：simplify C1 / §J / §L / smoketest B1 / §14.3 / §14.6 / §14.7 / §14.1 / Asset.holder 在 RETURN 后跟随 to_holder（修订 M2d 行为）

**不包**：

- §14.8 timeline 视觉重构（时间渐隐 + 派出类型染色 + 超长预警）→ M3d
- §14.4 People 实体化 → M5
- 看板 / 导出 / SKILL.md → M3b/c/e
- ARCHIVED 状态（已被 RETIRED+DISPOSED 二分覆盖）
- simplify A3（CheckoutDialog/ReturnDialog 合并 useFormDialog）→ 推迟 M4 UI 打磨期，避免 M3a PR-2 范围膨胀 + 避免落入模板脸

### 1.2 PR 拆分

**PR-1（后端契约 + schema migration）**

包含：alembic migration + StateTransitionRecord model + service + state machine validation + IllegalTransitionError + API router 重构 + CLI 重构 + 测试三层全覆盖。

合并后 main 上的前端会临时 broken（`pnpm gen:api` 后旧 `CheckoutRead` import 全部失效）——这是预期态，PR-2 修复。

**PR-2（前端切换 + UX 完整）**

包含：dialog 改造 + 列表 toggle + timeline 10 kind 视觉 + design-system token 扩展 + status-labels 修订 + simplify §J/§L 顺手清理 + playwright MCP 烟测。

**PR 拆分理由**：

1. M2 单人项目实践已经证明"后端契约 + 前端消费"分两 PR 合理（M2c-3 / M2c-4 / M2d 都是这个 pattern）
2. PR-1 边界清晰：所有"接受新端点契约"的代码（migration / model / service / router / CLI）一起；PR-2 边界清晰：所有"消费新端点契约"的代码（前端）
3. 不存在"phase 1+2 合 main 后旧端点未废"的语义飘移中间态
4. 单人项目，PR-1 期间 main 前端 broken 1-2 天可接受

### 1.3 三层架构遵守 CLAUDE.md 强约束

```
Web GUI ──HTTP──┐
                ├──► FastAPI (transitions router) ──► TransitionService ──► StateTransitionRepository/SQLModel
CLI ────import──┘                                  └──► AssetService（更新 status/holder/location）
```

- Service 层 `TransitionService.record_transition()` 是唯一事实源
- ORM (`StateTransitionRecord`) 与 DTO (`TransitionRead/TransitionCreate`) 严格隔离
- CLI `from asset_hub.services.transition import TransitionService`，不走 HTTP
- 所有 transition 写入是单事务（state machine 校验 → INSERT transition row → UPDATE asset 字段 → COMMIT）

---

## 2. 数据模型与状态机定义

### 2.1 AssetStatus（5 态枚举）

```python
class AssetStatus(StrEnum):
    IDLE = "IDLE"               # 闲置
    IN_USE = "IN_USE"           # 在用
    MAINTENANCE = "MAINTENANCE" # 维修中
    RETIRED = "RETIRED"         # 已退役（可复活）
    DISPOSED = "DISPOSED"       # 已处置（终态）
```

**中文文案修订**（前端 `status-labels.ts` + 总览 §2.1 同步）：

| status | M3a 修订前 | M3a 修订后 |
|---|---|---|
| IDLE | 闲置 | **闲置**（不变） |
| IN_USE | 在用 | **在用**（不变） |
| MAINTENANCE | 维护 | **维修中** |
| RETIRED | 退役 | **已退役** |
| DISPOSED | （新） | **已处置** |

**修订理由**：

- 5 态文案分两组：持续状态组（闲置/在用/维修中）+ 完成态组（已退役/已处置）
- "维修中" 比 "维护" 精准（v1 实际场景 95% 是故障维修；"维护" 在 IT 圈强烈关联系统运维）
- "已退役" 比 "退役" 加完成态前缀，与 "已处置" 对仗

### 2.2 TransitionKind（10 个）

```python
class TransitionKind(StrEnum):
    CHECKOUT_INTERNAL = "CHECKOUT_INTERNAL"
    CHECKOUT_EXTERNAL = "CHECKOUT_EXTERNAL"
    RETURN = "RETURN"
    SEND_TO_MAINTENANCE = "SEND_TO_MAINTENANCE"
    RECOVER_FROM_MAINTENANCE = "RECOVER_FROM_MAINTENANCE"
    RETIRE = "RETIRE"
    REINSTATE = "REINSTATE"
    DISPOSE = "DISPOSE"
    RELOCATE = "RELOCATE"
    TRANSFER_HOLDER = "TRANSFER_HOLDER"
```

### 2.3 状态机合法 from→to 矩阵

| kind | 合法 from | to_status | to_holder 规则 | to_location 规则 |
|---|---|---|---|---|
| CHECKOUT_INTERNAL | IDLE | IN_USE | required | optional |
| CHECKOUT_EXTERNAL | IDLE | IN_USE | required | optional |
| RETURN | IN_USE | IDLE | optional（NULL=无人值守；非空=接收人/仓管） | optional |
| SEND_TO_MAINTENANCE | IDLE | MAINTENANCE | optional | optional |
| RECOVER_FROM_MAINTENANCE | MAINTENANCE | IDLE | optional | optional |
| RETIRE | IDLE / MAINTENANCE | RETIRED | optional | optional |
| REINSTATE | RETIRED | IDLE | optional | optional |
| DISPOSE | RETIRED / MAINTENANCE | DISPOSED | forced_null | forced_null |
| RELOCATE | IDLE / IN_USE / MAINTENANCE / RETIRED | 同当前 | ignored（保持现 holder） | required |
| TRANSFER_HOLDER | IDLE / IN_USE / MAINTENANCE / RETIRED | 同当前 | required | optional（同时改位置） |

**关键边界拍板**：

- **归还不按 kind 拆**（单一 RETURN，kind 跟随对应 OPEN checkout）
- **IN_USE → MAINTENANCE / RETIRED 直跳走两步显式**（dialog 提示，service 层不提供复合方法；前端顺序调两个 mutation）
- **DISPOSED 是终态**，无任何出口
- **RELOCATE / TRANSFER_HOLDER 不改 status**，仅改字段
- **MAINTENANCE 在 RELOCATE/TRANSFER_HOLDER 合法 from 内**（维修台搬迁 / 维修联系人变更是真实场景）
- **DISPOSE 强制清 holder/location**（service 层覆盖请求值）
- **RELOCATE 不接受 to_holder 入参**（传了忽略；保持现 holder）

### 2.4 StateTransitionRecord model

```python
class StateTransitionRecord(SQLModel, table=True):
    __tablename__ = "state_transition_records"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    asset_id: uuid.UUID = Field(foreign_key="assets.id", index=True)
    kind: TransitionKind
    from_status: AssetStatus
    to_status: AssetStatus
    from_holder: str | None = None
    to_holder: str | None = None
    from_location: str | None = None
    to_location: str | None = None
    note: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)

    # CHECKOUT_* 专用
    due_at: datetime | None = None

    # RETURN 专用，指回闭合的 CHECKOUT_* 行 id
    closes_transition_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="state_transition_records.id",
        index=True,
    )
```

**字段说明**：

- **删 actor 字段**（M3a 决议；YAGNI；v1 单用户无来源区分需求；M5 People 实体化时再加）
- `from_status` / `to_status` 改为 NOT NULL（M3a 后所有新行都有值）
- 索引：`(asset_id, created_at DESC)` 复合索引为 timeline 主查询路径优化
- `closes_transition_id` 自引用 FK，支持 timeline O(1) 配对查询

### 2.5 Asset 模型变更

```python
class Asset(SQLModel, table=True):
    # ... 现有字段保留 ...
    status: AssetStatus = Field(default=AssetStatus.IDLE)  # enum 扩 5 态
    holder: str | None = None
    location: str | None = None

    # 删除：current_checkout_id（不再反规范化）
```

**`current_checkout_id` 字段删除**：

- 旧用途是 CheckoutRecord 反规范化指针
- 新模型下 timeline 直接 query `state_transition_records WHERE asset_id ORDER BY created_at DESC`，O(N) 但 N 小（v1 单 asset 历史 < 100 条）
- 真要 O(1) 拿"当前 OPEN checkout"，新方案是 `WHERE asset_id = ? AND kind IN (CHECKOUT_*) AND closes_transition_id IS NULL`，加 partial index 即可，不需要反规范化字段

### 2.6 状态机校验层（C1 闭环 SoT）

`src/asset_hub/services/state_machine.py` 重写为单一 SoT：

```python
class TransitionRule(NamedTuple):
    valid_from: frozenset[AssetStatus]
    to_status: AssetStatus | None  # None 表示 to_status = from_status（RELOCATE/TRANSFER_HOLDER）
    holder_rule: Literal["required", "optional", "forced_null", "ignored"]
    location_rule: Literal["required", "optional", "forced_null"]


TRANSITION_RULES: dict[TransitionKind, TransitionRule] = {
    TransitionKind.CHECKOUT_INTERNAL: TransitionRule(
        valid_from=frozenset({AssetStatus.IDLE}),
        to_status=AssetStatus.IN_USE,
        holder_rule="required",
        location_rule="optional",
    ),
    # ... 10 个 kind 完整表，遵循 §2.3 矩阵 ...
}


def validate_transition(
    current_status: AssetStatus,
    kind: TransitionKind,
    to_holder: str | None,
    to_location: str | None,
) -> AssetStatus:
    """返回 to_status；非法抛 IllegalTransitionError。"""
    rule = TRANSITION_RULES[kind]
    if current_status not in rule.valid_from:
        raise IllegalTransitionError(
            f"{kind.value} 不能从 {current_status.value} 出发"
        )
    if rule.holder_rule == "required" and not to_holder:
        raise IllegalTransitionError(f"{kind.value} 必须提供 to_holder")
    if rule.location_rule == "required" and not to_location:
        raise IllegalTransitionError(f"{kind.value} 必须提供 to_location")
    return rule.to_status if rule.to_status else current_status
```

**simplify C1 闭环**：`TRANSITION_RULES` 是合法性的唯一来源；service 层不再写 if-block 双层防御；新加状态/kind 只改这一个 dict。

### 2.7 IllegalTransitionError + API 映射

`src/asset_hub/errors.py` 新加：

```python
class IllegalTransitionError(Exception):
    """状态机拒绝当前 transition。映射 HTTP 409 Conflict。"""
```

`src/asset_hub/api/app.py` 异常 handler 增加：

```python
@app.exception_handler(IllegalTransitionError)
async def illegal_transition_handler(request, exc):
    return JSONResponse(status_code=409, content={"detail": str(exc)})
```

**HTTP 409 选择理由**：

- 资源当前状态与请求 transition 冲突 = HTTP 409 Conflict 的标准语义
- 与 M2d ConflictError（类型有引用拒删）形成"资源状态冲突"统一语义类
- 不选 422（语法/格式错）：transition 请求格式合法，是状态语义冲突

CLI envelope 映射 IllegalTransitionError → exit 1 + `{"success": false, "error": {...}}`，error.message 透传。

---

## 3. Service 层与事务边界

### 3.1 TransitionService（新建 `src/asset_hub/services/transition.py`）

```python
class TransitionService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = TransitionRepository(session)
        self.asset_svc = AssetService(session)

    def record_transition(
        self,
        asset_id: uuid.UUID,
        kind: TransitionKind,
        *,
        to_holder: str | None = None,
        to_location: str | None = None,
        note: str | None = None,
        due_at: datetime | None = None,
    ) -> StateTransitionRecord:
        """单事务：state machine 校验 → INSERT transition → UPDATE asset。

        非法 from_status / 必填字段缺失 → IllegalTransitionError。
        """
        asset = self.asset_svc.get_asset(asset_id)

        # state machine SoT 校验
        to_status = validate_transition(asset.status, kind, to_holder, to_location)

        rule = TRANSITION_RULES[kind]

        # forced_null / ignored 规则
        if rule.holder_rule == "forced_null":
            to_holder_final = None
        elif rule.holder_rule == "ignored":
            to_holder_final = asset.holder  # RELOCATE：保持现 holder
        else:
            to_holder_final = to_holder

        if rule.location_rule == "forced_null":
            to_location_final = None
        else:
            to_location_final = to_location

        # 闭合最近一条 OPEN CHECKOUT_*（仅 RETURN 用）
        closes_id = None
        if kind == TransitionKind.RETURN:
            closes_id = self.repo.find_open_checkout_id(asset_id)
            if closes_id is None:
                raise IllegalTransitionError(f"资产无未归还的派发记录: {asset_id}")

        record = StateTransitionRecord(
            asset_id=asset_id,
            kind=kind,
            from_status=asset.status,
            to_status=to_status,
            from_holder=asset.holder,
            to_holder=to_holder_final,
            from_location=asset.location,
            to_location=to_location_final,
            note=note,
            due_at=due_at if kind in (TransitionKind.CHECKOUT_INTERNAL, TransitionKind.CHECKOUT_EXTERNAL) else None,
            closes_transition_id=closes_id,
        )
        self.repo.add(record)
        self.session.flush()  # 拿到 record.id

        # 更新 asset 字段
        asset.status = to_status
        asset.holder = to_holder_final
        # location 跟随逻辑：transition 提供 to_location 才改；否则保持
        if to_location_final is not None or rule.location_rule == "forced_null":
            asset.location = to_location_final
        asset.updated_at = datetime.now(UTC)

        self.session.commit()
        self.session.refresh(record)
        return record

    def list_transitions(self, asset_id: uuid.UUID) -> list[StateTransitionRecord]:
        self.asset_svc.get_asset(asset_id)  # 404 兜底
        return self.repo.list_by_asset(asset_id)
```

### 3.2 location 跟随策略（修订 M2d 行为）

M2d 旧 `CheckoutService.return_()` 的行为是 `asset.location = return_location`（即使 return_location 是 None，也会清空 asset.location）。新 `TransitionService` 改为：

- `to_location is not None` → 写入 `asset.location = to_location`
- `to_location is None` → **保持** `asset.location` 不变（不清空）
- 例外：DISPOSE（rule.location_rule == "forced_null"）→ 强制 `asset.location = None`

**理由**：

- "可选位置 + 不传则保持" 比 "可选位置 + 不传则清空" 更符合直觉
- 旧行为是 M2d B2 局部决策，没有跨整个状态机考虑；M3a 借机统一

### 3.3 holder 跟随策略（M3a 决议落地）

- RETURN 后 `asset.holder = to_holder`（即便 to_holder 是 None 也写入 None）—— 因为 RETURN 必须明确"归还后是否有接收人"
- DISPOSE 后 `asset.holder = None`（forced_null）
- RELOCATE：`asset.holder` 不变（rule.holder_rule == "ignored"，service 层强制保留现 holder）
- 其他 kind：`asset.holder = to_holder_final`，按字段值写入

**修订 M2d 行为**：旧 CheckoutService.return_() 强制 `asset.holder = None`，与 M3 总览决议"holder 字段在所有非终态都可有值"冲突。新 TransitionService 修正这一行为。

### 3.4 IN_USE → MAINTENANCE / RETIRED 直跳的 service 接口

按总览 §2 决议（Q2=C）"显式两步，dialog 提示"。Service 层提供单步接口，**不**提供复合方法：

- 上层（CLI/前端 dialog）显式调两次 `record_transition()`：先 RETURN，再 SEND_TO_MAINTENANCE / RETIRE
- 两次调用是**独立事务**（每次 record_transition 内部 commit）
- 上层 dialog 显示"将先记 RETURN 再 SEND_TO_MAINTENANCE"，用户确认后顺序触发

**理由**：

- v1 单用户场景，两次连续 commit 中崩溃概率极低
- 即便发生（先 RETURN 写入但 SEND_TO_MAINTENANCE 失败），asset 处于 IDLE 是合法状态，用户可重试
- 不破坏 service 层 single-method 简洁性
- 前端 dialog 顺序调两个 mutation 即可，TanStack Query 原生支持 `mutateAsync` 串联

### 3.5 AssetService 改造

- **删除 `change_status()` 方法**（散点 PATCH status 路径，违反 §14.6 audit 化）
- **修订 `update_asset()`**：移除 `status` / `holder` / `location` 参数（这三个字段 M3a 后只能通过 transition 改）；保留 `name` / `serial_number` / `notes` / `custom_data` / `acquired_at` / `type_id`（不影响 audit 的字段）
- 删除 `current_checkout_id` 字段及相关读写
- `delete_asset()` cascade 改为删 `state_transition_records WHERE asset_id` 替代 `checkout_records WHERE asset_id`

### 3.6 删除 CheckoutService 链路

整体删除以下文件：

- `src/asset_hub/services/checkout.py`
- `src/asset_hub/repositories/checkout.py`
- `src/asset_hub/api/routers/checkouts.py`
- `src/asset_hub/api/schemas/checkout.py`
- `src/asset_hub/models/checkout.py`
- `tests/unit/test_checkout_*.py`
- `tests/api/test_checkout_*.py`
- `tests/cli/test_checkout_*.py`

旧 router 在 `app.py` 中的注册同步移除。

---

## 4. API 与 CLI 契约

### 4.1 API 端点

**新建 `src/asset_hub/api/routers/transitions.py`**：

```python
@router.post("/{asset_id}/transitions", status_code=201, response_model=TransitionRead)
def create_transition(
    asset_id: uuid.UUID,
    body: TransitionCreate,
    svc: Annotated[TransitionService, Depends(_get_svc)],
):
    return svc.record_transition(
        asset_id=asset_id,
        kind=body.kind,
        to_holder=body.to_holder,
        to_location=body.to_location,
        note=body.note,
        due_at=body.due_at,
    )


@router.get("/{asset_id}/transitions", response_model=list[TransitionRead])
def list_transitions(
    asset_id: uuid.UUID,
    svc: Annotated[TransitionService, Depends(_get_svc)],
):
    return svc.list_transitions(asset_id)
```

注册到 `app.py`：`app.include_router(transitions.router, prefix="/api/assets", tags=["transitions"])`

**删除**：`src/asset_hub/api/routers/checkouts.py` 整文件 + `app.py` 中 checkouts router 注册。

**异常映射**（`api/app.py`）：

- `IllegalTransitionError` → 409 Conflict（新加 handler）
- 现有 `NotFoundError` → 404 / `DuplicateError` → 409 / `ValidationError` → 422 不变
- router 不写 try/except，让域异常冒泡（CLAUDE.md 强约束）

### 4.2 DTO（`src/asset_hub/api/schemas/transition.py`）

```python
class TransitionCreate(BaseModel):
    kind: TransitionKind
    to_holder: str | None = None
    to_location: str | None = None
    note: str | None = None
    due_at: datetime | None = None


class TransitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_id: UUID
    kind: TransitionKind
    from_status: AssetStatus
    to_status: AssetStatus
    from_holder: str | None
    to_holder: str | None
    from_location: str | None
    to_location: str | None
    note: str | None
    due_at: datetime | None
    closes_transition_id: UUID | None
    created_at: datetime
```

**单一 body shape 选择理由**：

- service 层 `validate_transition` 已是字段组合校验的 SoT（C1 闭环要求），schema 层不应该再做一遍
- 错误文案在一个地方维护（service 层 IllegalTransitionError），不被 Pydantic 默认文案截胡
- 前端 generated types 一份，FE 写"按 kind 分支 dialog"时按业务逻辑分，不被 schema 层强行拆 10 份
- 业界范例：Stripe 等 API 大量端点是单 body shape + 字段按 mode 路由

**返回单条 transition 选择理由**：

- 与项目现有 mutation pattern 一致（`CheckoutService.return_()` 也是返回单条 CheckoutRead，前端用 invalidate）
- TanStack Query 原生范式：mutation 返回 created entity，onSuccess 用 `invalidateQueries` 触发后台 refetch
- 业界主流（Stripe / GitHub / Linear）：返回 created 资源，依赖客户端 cache invalidation 拿父资源新状态

### 4.3 CLI 命令编排（`src/asset_hub/cli/asset_cmd.py`）

**保留命令名（实现底层切换）**：

- `asset checkout <id> --kind internal|external --to <holder> [--location L] [--note N] [--due-at T]`（默认 `--kind internal`）
- `asset return <id> [--receiver R] [--location L] [--note N]`（旧 `--receiver` flag 保留向后兼容用户/Agent 习惯，实现层 receiver 直接传 to_holder）
- `asset history <id>`（实现切到 `svc.list_transitions(asset_id)`，输出 `TransitionRead` 列表）

**新增 7 个命令**：

- `asset send-to-maintenance <id> [--holder H] [--location L] [--note N]`
- `asset recover <id> [--holder H] [--location L] [--note N]`
- `asset retire <id> [--holder H] [--location L] [--note N] [--dry-run] [--yes]`
- `asset reinstate <id> [--holder H] [--location L] [--note N]`
- `asset dispose <id> [--note N] [--dry-run] [--yes]`（终态，强制二次确认）
- `asset relocate <id> --to-location L [--note N]`
- `asset transfer-holder <id> --to-holder H [--location L] [--note N]`

**删除**：`asset change-status` 命令（散点 PATCH status 路径，违反 §14.6 audit 化）。

**Envelope 信封**：

- 所有 transition 命令成功输出 `{"success": true, "data": <TransitionRead JSON>, ...}`，exit 0
- `asset history` 输出 `{"success": true, "data": [<TransitionRead>...], "metadata": {"count": N}}`
- `IllegalTransitionError` → exit 1 + `{"success": false, "error": {...}}`
- 复用现有 `cli/envelope.py` 的 `print_result` / `handle_domain_errors`

**实现复用决策**：

- 9 个命令的 typer wrapper 重复样板较多（参数解析 + cli_session + handle_domain_errors + record_transition + envelope）
- M3a 不抽 helper（simplify K2 触发条件未到），保持直白
- 9 个命令都遵守同一 pattern，PR-1 review 时按模板对照

### 4.4 OpenAPI / 前端类型同步

PR-1 后端 API 改完，**强制**跑：

```
pnpm --dir frontend gen:api
```

→ `frontend/src/api/generated/schema.d.ts` 重新生成。这是 CLAUDE.md 已硬约束。

PR-1 提交时 `schema.d.ts` 一同提交。前端在 PR-1 期间 ts 类型错（旧 `CheckoutRead` import 全部失效），是预期态——PR-2 修。

### 4.5 测试覆盖（PR-1）

按 CLAUDE.md 测试分层：

- **`tests/unit/test_state_machine.py`**：10 kind × 5 from_status 矩阵 = 50 case；holder/location 必填规则各覆盖；用 `pytest.parametrize`
- **`tests/unit/test_transition_service.py`**：每 kind 1-3 happy path + 关键 edge case（RETURN 找不到 OPEN CHECKOUT；DISPOSE forced_null holder/location；RELOCATE 不接受 to_holder；RETURN 后 asset.holder 跟随 to_holder）；总计约 25-35 case
- **`tests/api/test_transitions.py`**：POST/GET 端点 happy path + 409 IllegalTransitionError + 404 asset not found；约 15-20 case
- **`tests/cli/test_transition_cmds.py`**：9 命令各 1 happy path + envelope 校验 + exit code 校验；约 12-15 case

旧测试（`test_checkout_*.py` 等）整体重写，不拼凑保留。

PR-1 结束时全部测试绿，且覆盖率不下降（基线由当前 main 测试套件确定）。

---

## 5. 前端改造（PR-2）

### 5.1 design-system token 扩展

**`frontend/src/styles/globals.css`** 新增 light + dark 变体：

```css
/* light */
--status-disposed: oklch(0.95 0.000 0);     /* 完全去色相纯灰 */
--status-disposed-fg: oklch(0.35 0.000 0);

/* dark */
--status-disposed: oklch(0.18 0.000 0);
--status-disposed-fg: oklch(0.50 0.000 0);
```

`@theme` 段同步加 `--color-status-disposed` / `--color-status-disposed-fg`，与现有 4 套 token 命名一致。

**色调推理**：

- RETIRED（已退役，可复活）= 微蓝灰（chroma 0.005，保留蓝色相暗示可恢复）
- DISPOSED（已处置，终态）= 完全去色相纯灰（chroma 0.000，传达"无生气、终结"语义）
- 不用 destructive/红色 —— DISPOSE 是用户主动决策的归档动作，不是错误状态；红色保留给 dialog 主按钮

### 5.2 `frontend/src/features/assets/status-labels.ts` 修订

```typescript
export type AssetStatus = "IN_USE" | "IDLE" | "MAINTENANCE" | "RETIRED" | "DISPOSED";

export const STATUS_META: Record<AssetStatus, StatusMeta> = {
  IN_USE:      { label: "在用",     bgVar: "--status-in-use",      fgVar: "--status-in-use-fg",      Icon: CircleDot },
  IDLE:        { label: "闲置",     bgVar: "--status-idle",        fgVar: "--status-idle-fg",        Icon: Circle },
  MAINTENANCE: { label: "维修中",   bgVar: "--status-maintenance", fgVar: "--status-maintenance-fg", Icon: Wrench },
  RETIRED:     { label: "已退役",   bgVar: "--status-retired",     fgVar: "--status-retired-fg",     Icon: Moon },
  DISPOSED:    { label: "已处置",   bgVar: "--status-disposed",    fgVar: "--status-disposed-fg",    Icon: Archive },
};
```

修订项：

- MAINTENANCE label "维护" → **"维修中"**
- RETIRED label "退役" → **"已退役"** + Icon `MinusCircle` → **`Moon`**（"休眠待复活"语义，与 RETIRE transition icon 一致）
- 新增 DISPOSED：label "已处置"，Icon `Archive`（与 RETIRE 的 `Moon` 区分）

`AssetStatus` type 同步扩 5 态字面量。

### 5.3 列表 Toggle chip（非普通 checkbox）

**位置**：`frontend/src/features/assets/list/assets-filters.tsx` 新增两个 Toggle chip。

**实现**：

- 复用 shadcn `Toggle` 组件（如未装则 PR-2 引入，按 M2c-3 §3 4 项审查清单走）
- **off 态** (`data-state=off`)：`bg-muted text-muted-foreground border-border/40`，icon 也走 `text-muted-foreground`
- **on 态 (已退役)** (`data-state=on`)：`bg-status-retired/15 text-status-retired-fg border-status-retired/30`，icon 切到 `text-status-retired-fg`
- **on 态 (已处置)** (`data-state=on`)：`bg-status-disposed/15 text-status-disposed-fg border-status-disposed/30`，icon 切到 `text-status-disposed-fg`
- 圆角同 status pill（`rounded-full`），尺寸 `h-7 px-3 text-xs`
- 左侧带 status icon（`Moon` / `Archive`），右侧文字
- transitions: `transition-colors duration-200`（150-300ms 范围）
- **禁用**：`transform: scale`、`animate-pulse`、`animate-spin`

**搜索 schema**（`frontend/src/features/assets/list/search-schema.ts`）：

- 新增 `show_retired: z.boolean().default(false)` / `show_disposed: z.boolean().default(false)`
- TanStack Router URL search params 持久化

**API 集成**：

- 后端列表端点 `GET /api/assets` 新增 `include_retired: bool = False` / `include_disposed: bool = False` query param
- 默认 `WHERE status NOT IN ('RETIRED', 'DISPOSED')`
- toggle 开启时去掉对应 status 的过滤
- `AssetService.list_assets` 签名扩 `include_retired` / `include_disposed` 参数（PR-1 顺手做，schema.d.ts 同步）

### 5.4 6 个 dialog（按可逆性 + status token 染色）

**`AlertDialog` 形态（不可逆 / 高严肃度）**：

1. **`DisposeAlertDialog`**（新建）
   - 红色 destructive header + Trash2 icon
   - 文案 "确定处置 <asset_name>？此操作不可撤销。资产 holder 与 location 将被清空，状态置为已处置。"
   - 可选 note textarea
   - 二次确认（输入"处置"字符串解锁按钮，参考 `delete-asset-alert.tsx` pattern）
   - 主按钮 `variant="destructive"`，红色

2. **`RetireAlertDialog`**（新建，独立于 SimpleTransitionDialog 因为可选字段更多）
   - **冷蓝灰** header chip：`bg-status-retired/15 text-status-retired-fg` + Moon icon
   - 文案 "确定退役 <asset_name>？退役后可通过'重新启用'恢复至闲置状态。"
   - 可选字段：to_holder / to_location / note
   - 单击确认按钮，无二次确认（可逆）

**`Dialog` 形态（form / 可逆）**：

3. **`CheckoutDialog`**（升级现，共用 + `kind` prop 区分）
   - **派发/出借在详情页主按钮区拆为两个并列按钮**（CHECKOUT_INTERNAL default variant、CHECKOUT_EXTERNAL outline variant），不在 dialog 内 toggle 选择
     - 修订原因：原决议 dialog 内 ToggleGroup discoverability 不足，用户从主按钮看不到出借入口
   - 头部 chip：`bg-status-in-use/15 text-status-in-use-fg` + 按 kind 切 icon（CHECKOUT_INTERNAL=ArrowRightFromLine "派发"；CHECKOUT_EXTERNAL=Send "出借"）
   - 字段：to_holder（必填，label 按 kind 切"派发给"/"出借给"）/ to_location / due_at / note
   - 主按钮文案按 kind 切"确认派发"/"确认出借"

4. **`ReturnDialog`**（升级现）
   - 头部 chip：`bg-status-idle/15 text-status-idle-fg` + Undo2 icon + 文字"归还"
   - 字段：to_holder（即原 receiver，标签改"归还给"）/ to_location / note
   - 主按钮中性

5. **`RelocateDialog`**（新建）
   - 头部 chip：`bg-muted text-muted-foreground` + MapPin icon + 文字"变更位置"
   - 字段：to_location（必填）/ note
   - 主按钮中性

6. **`TransferHolderDialog`**（新建）
   - 头部 chip：`bg-muted text-muted-foreground` + UserCog icon + 文字"变更保管人"
   - 字段：to_holder（必填）/ to_location（可选）/ note
   - 主按钮中性

**`SimpleTransitionDialog`**（升级现 `state-change-alert.tsx`）

服务 3 个 kind：SEND_TO_MAINTENANCE / RECOVER_FROM_MAINTENANCE / REINSTATE。复用 AlertDialog 外壳 + 按 transition kind 配置 header chip / icon / 文案：

- SEND_TO_MAINTENANCE：琥珀 chip（`bg-status-maintenance/15 text-status-maintenance-fg`）+ Wrench icon + "送修"
- RECOVER_FROM_MAINTENANCE：闲置色 chip（`bg-status-idle/15 text-status-idle-fg`）+ CheckCircle2 icon + "维修完成"
- REINSTATE：闲置色 chip + Sun icon + "重新启用"

每个 kind 内的 form 字段（to_holder / to_location / note 都可选）共用一个简单 form。

**A3 simplify follow-up 推迟到 M4**：M3a PR-2 实际新增 ≥ 4 个 form dialog，A3 触发条件原文是"第 3 个 form dialog 出现"已满足，但本子 spec 决议**不抽 useFormDialog 通用壳**——保持各 dialog 视觉独立性，避免落入模板脸。simplify-followups 同步更新 A3 状态为"M4 UI 打磨期处理"。

### 5.5 详情页 ⋯ 菜单扩展

**位置**：`frontend/src/features/assets/detail/asset-header.tsx`

⋯ 菜单按当前 status 动态过滤可用项：

| 当前 status | 主按钮区 | ⋯ 菜单项 |
|---|---|---|
| IDLE | 派发 | 送修、退役、变更位置、变更保管人 |
| IN_USE | 归还 | 变更位置、变更保管人 |
| MAINTENANCE | 维修完成 | 退役、处置、变更位置、变更保管人 |
| RETIRED | 重新启用 | 处置、变更位置、变更保管人 |
| DISPOSED | （无） | （无 — 终态，详情页全只读） |

具体可见性由前端 `available-transitions.ts`（新建，简单 const map）静态定义；不写 simplify F1 的"运行时 filter"反模式。

DISPOSED 状态详情页全只读（隐藏所有 transition 入口、隐藏编辑按钮）。

**§14.3 IDLE location 独立 action 闭环**：⋯ 菜单"变更位置"项（RELOCATE）覆盖。

### 5.6 timeline 10 kind 视觉

**位置**：`frontend/src/features/assets/detail/checkout-timeline.tsx` 重命名为 `transition-timeline.tsx`，扩 kind 配置表：

```typescript
const KIND_META: Record<TransitionKind, { label: string; Icon: LucideIcon; bgVar: string; fgVar: string }> = {
  CHECKOUT_INTERNAL:        { label: "派发",       Icon: ArrowRightFromLine, bgVar: "--status-in-use",      fgVar: "--status-in-use-fg" },
  CHECKOUT_EXTERNAL:        { label: "出借",       Icon: Send,               bgVar: "--status-in-use",      fgVar: "--status-in-use-fg" },
  RETURN:                   { label: "归还",       Icon: Undo2,              bgVar: "--status-idle",        fgVar: "--status-idle-fg" },
  SEND_TO_MAINTENANCE:      { label: "送修",       Icon: Wrench,             bgVar: "--status-maintenance", fgVar: "--status-maintenance-fg" },
  RECOVER_FROM_MAINTENANCE: { label: "维修完成",   Icon: CheckCircle2,       bgVar: "--status-idle",        fgVar: "--status-idle-fg" },
  RETIRE:                   { label: "退役",       Icon: Moon,               bgVar: "--status-retired",     fgVar: "--status-retired-fg" },
  REINSTATE:                { label: "重新启用",   Icon: Sun,                bgVar: "--status-idle",        fgVar: "--status-idle-fg" },
  DISPOSE:                  { label: "处置",       Icon: Trash2,             bgVar: "--status-disposed",    fgVar: "--status-disposed-fg" },
  RELOCATE:                 { label: "变更位置",   Icon: MapPin,             bgVar: "--muted",              fgVar: "--muted-foreground" },
  TRANSFER_HOLDER:          { label: "变更保管人", Icon: UserCog,            bgVar: "--muted",              fgVar: "--muted-foreground" },
};
```

每条 timeline 行渲染：左侧 icon（染色） + 主文案 + 时间戳 + 可选 note。

**文案模板**（按 kind 走分支）：

```
- CHECKOUT_INTERNAL:        派发给 {to_holder}（如有 to_location → 加 " · 位置 {to_location}"）
- CHECKOUT_EXTERNAL:        出借给 {to_holder}（如有 to_location → 加 " · 位置 {to_location}"）
- RETURN:                   归还给 {to_holder ?? "无人值守"}
- SEND_TO_MAINTENANCE:      送修（可附 holder/location）
- RECOVER_FROM_MAINTENANCE: 维修完成
- RETIRE:                   退役
- REINSTATE:                重新启用
- DISPOSE:                  处置
- RELOCATE:                 变更位置至 {to_location}
- TRANSFER_HOLDER:          变更保管人 {from_holder ?? "无"} → {to_holder}
```

**视觉沿用 M2c-2 timeline 形态**（卡片堆叠 + 时间戳 + 状态 pill，无 vertical line + 圆点节点），不做 §14.8 重构（时间渐隐 / 派出类型染色 / 超长预警 → M3d）。

### 5.7 hooks / API client

**`frontend/src/api/hooks/transitions.ts`**（新建）：

- `useTransitionsQuery(assetId)` 查 `GET /api/assets/{id}/transitions`
- `useRecordTransitionMutation()` `POST /api/assets/{id}/transitions`，onSuccess 失效 `qk.assets.detail(id)` + `qk.assets.transitions(id)`

**`frontend/src/api/query-keys.ts`** 加 `qk.assets.transitions(id)` namespace（沿用现有 namespace pattern，与 detail/list/history 同级）。

**删除**：旧 `useCheckoutHistoryQuery` / checkout / return mutation hooks，全切到上面新 hook。

### 5.8 simplify §J / §L 顺手清理（PR-2）

PR-2 实施期顺手做（不另开 PR）：

- `frontend/src/features/assets/form/build-asset-schema.ts` 双函数 → 单 builder + 显式分支（消除 zod inference 丢 type_id 的 cast）
- `asset-create-form.tsx` 2 处 `as unknown as Resolver<>` cast 删除
- `type-form.tsx` 同款 cast 删除（M2c-4 PR-3 Task 27 重现的那处）
- 测试：现有 form 测试通过即合格

simplify-followups §J / §L 标记为 ✅ 闭环。

### 5.9 反 AI-slop 红线（PR-2 实施期 explicit 禁用清单）

**禁用**：

- spinner（loading 用 skeleton；mutation pending 用按钮文字切换 / 进度条 width transition）
- `backdrop-blur` / `backdrop-filter: blur`
- hover `transform: scale`
- hex fallback OKLCH token（如 `bg-[var(--xxx, #...)]/10`）
- emoji icon（用 lucide-react SVG）
- `bg-gradient-*`
- `animate-spin` / `animate-pulse`
- 模板脸通用 dialog 外壳（A3 useFormDialog 推迟 M4）

**红线扫描**（PR-2 合并前必跑，0 命中）：

```bash
grep -rnE 'scale-|animate-spin|animate-pulse|backdrop-blur|bg-gradient-to' frontend/src
```

### 5.10 shadcn 新组件 variant 审查 + 响应式

**shadcn Toggle 组件**（如 PR-2 新引入）必须 same-PR 审查（按 M2c-3 §3 4 项）：

- 删 `"use client"` 残留
- 用 token 而非 hex
- 不引入 next-themes 依赖
- focus-visible state 默认开启

如 Toggle 已在项目（grep 验证），跳过。

**响应式 baseline 沿用 1024+**（与 MASTER pre-delivery checklist 一致）。M3a PR-2 不动响应式 baseline；<1024 横向滚动 / 自动降列。

### 5.11 playwright MCP 烟测（PR-2 验收）

PR-2 合并前必跑（不进 CI；CI 的 e2e 留 M3e）：

**核心场景**：

1. 派发 → 归还 → 送修 → 维修完成 → 退役 → 重新启用 happy path
2. 处置（DISPOSE）二次确认 dialog 行为（输入"处置"解锁）
3. 列表两个 Toggle 显隐 RETIRED / DISPOSED 资产
4. RELOCATE / TRANSFER_HOLDER 走 ⋯ 菜单
5. timeline 10 kind 视觉差异化检查（每个 kind 截图对比）
6. dark mode + light mode 两轮（status-disposed token 视觉验证）

**Pre-Delivery Checklist 7 项**（沿用 M2c-1/2/3/M2 视觉收尾范本）：

- [ ] No emojis as icons（全 Lucide SVG）
- [ ] cursor-pointer on clickable elements
- [ ] Hover transitions smooth 150-300ms（`transition-colors`）
- [ ] Light mode text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive 1024+

**红线扫描结果**：grep 0 命中（见 §5.9）

**MASTER override 实施期纠偏段**：本 PR 写入 MASTER.md "实施期纠偏（M3a，<PR-2 合并日期>）"段，记录新增 override：

1. 新增 `--status-disposed` / `--status-disposed-fg` OKLCH token pair（含 light/dark）
2. Toggle chip 模式（filter 区使用 status token 染色的 Toggle，非普通 checkbox）
3. DisposeAlertDialog 二次确认形态（输入"处置"字符串解锁按钮，参考 delete-asset-alert.tsx）
4. timeline 10 kind icon × token 配置表（沿用 M2c-2 卡片堆叠形态，§14.8 高级视觉留 M3d）
5. RETIRED Icon 从 `MinusCircle` 改 `Moon`（"休眠待复活"语义，与 RETIRE transition icon 一致）

烟测在 PR-2 描述里贴截图 + 录屏。

---

## 6. 跨子里程碑约束 / 风险 / 回滚

### 6.1 数据迁移与回滚

- M3a 不做数据迁移（决议）。alembic migration 仅 schema 变更（add `DISPOSED` enum / create `state_transition_records` table / drop `checkout_records` table / drop `Asset.current_checkout_id` 字段）
- **PR-1 合并前用户手动**：`rm data/asset_hub.db` + 清空 `data/attachments/`
- **回滚**：alembic downgrade 自动反向；但 downgrade 后旧 db 已被清空，无现实意义——**M3a 不留 1 release 兜底，PR-1 即终局**

### 6.2 API 演进策略

- 不向后兼容（旧 `/checkout` `/return` `/history` 整体删除）
- 单仓库内 CLI / 前端 / 测试同 PR 切换
- 外部消费者（Agent SKILL.md）尚未发布，无破坏面
- **OpenAPI schema 同步（CLAUDE.md 硬约束）**：PR-1 后端改完必跑 `pnpm --dir frontend gen:api`，`schema.d.ts` 与 PR-1 同 commit
- **CLI envelope 格式不动**：M3a/b/c/d 期间沿用现状；K1 envelope 统一推到 M3e

### 6.3 测试基建时序

- **每个 PR 自带 TDD**（CLAUDE.md 测试分层）：
  - PR-1：service / API / CLI 三层全覆盖（约 50-70 case，详见 §4.5）
  - PR-2：前端单测（hooks + form + Toggle chip 等约 15-20 case）+ playwright MCP 烟测
- **playwright e2e CI 脚本**：M3a 不写（依赖 M3b/c 就位才能跑完整场景集），留给 M3e
- **playwright MCP 烟测保留**：PR-2 合并前必跑（不进 CI）；场景集见 §5.11

### 6.4 K1 envelope 统一时机

- **M3a 期间不动 envelope**：仅消费当前 contract，9 个新 CLI 命令遵守现有 `print_result` / `handle_domain_errors` pattern
- 推到 M3e（与总览 §4.4 一致）

### 6.5 强搭车 follow-up 时机锁定

| follow-up | 落地 PR | 闭环形态 |
|---|---|---|
| simplify C1（双层防御统一） | M3a PR-1 | `TRANSITION_RULES` + `validate_transition` 成 SoT；删 service 层 if-block |
| simplify §J / §L（build-asset-schema 双函数 + zod cast） | M3a PR-2 | 实施期顺手清理，详见 §5.8 |
| smoketest B1（状态切换进流转记录） | M3a PR-1 | 被 §14.6 audit 化覆盖（每个 transition 都写 StateTransitionRecord 行） |
| §14.3 IDLE location 独立 action | M3a PR-2 | RELOCATE transition + 详情页 ⋯ 菜单 "变更位置" |
| §14.6 audit 化 | M3a PR-1+PR-2 | StateTransitionRecord 全覆盖 |
| §14.7 状态枚举完善 | M3a PR-1 | 5 态（DISPOSED 加入） |
| §14.1 派出类型 | M3a PR-1+PR-2 | CHECKOUT_INTERNAL / CHECKOUT_EXTERNAL 两 kind + dialog kind 选择器 |
| Asset.holder 在 RETURN 后跟随 to_holder（M2d 行为修订） | M3a PR-1 | TransitionService.record_transition 单事务写入 |
| simplify A3（CheckoutDialog/ReturnDialog 合并 useFormDialog） | **推迟 M4** | 避免落入模板脸 + PR-2 范围控制 |
| §14.8 timeline 视觉重构 | **M3d 主线** | 不在 M3a |

### 6.6 风险清单

| # | 风险 | 等级 | 缓解 |
|---|---|---|---|
| R1 | M3a 范围过大（5 态 + 10 transition + service + API + CLI 9 子命令 + 前端 6 dialog + 列表 toggle + timeline 视觉） | 高 | 拆 PR-1（后端）+ PR-2（前端）；PR-1 内顺序 phase 1（migration + model）→ phase 2（service + state machine）→ phase 3（API + CLI），单 PR 内分阶段 commit 但不分 PR |
| R2 | API 不向后兼容破坏外部消费者 | 低 | v1 GA 前单仓库内全控；SKILL.md 尚未发布 |
| R3 | 5 态文案修订（在用/闲置/维修中/已退役/已处置）破坏现有 UI 视觉一致性 | 低 | M2 视觉收尾后 status-labels.ts 是单一 SoT，修订时 grep 全前端确保无硬编码"派发中"等字面量 |
| R4 | timeline 显示历史 transition 时 to_holder/to_location 为 NULL 的渲染兜底 | 低 | 文案模板已写 `?? "无人值守"` 等兜底；测试覆盖 NULL 场景 |
| R5 | playwright MCP 烟测覆盖不全（Auto mode 单人执行） | 中 | 烟测清单（§5.11）显式列 6 个核心场景；不追求穷尽，覆盖 happy path |
| R6 | shadcn Toggle 组件未装 / 装时引入 next-themes 残留 | 低 | PR-2 实施期检查（grep `frontend/src/components/ui/toggle.tsx`；如新引入按 M2c-3 §3 4 项审查清单走） |
| R7 | DISPOSED 终态无回滚导致用户误处置 | 低 | DisposeAlertDialog 输入"处置"字符串解锁按钮 + state machine 强制 from RETIRED/MAINTENANCE（IDLE 不可直 DISPOSE） |
| R8 | RELOCATE / TRANSFER_HOLDER 高频暴露语义边界 case | 低 | 单测覆盖各 from-status 组合（state_machine.py 50 case 矩阵） |

### 6.7 不缓解的已知风险

- **§14.4 People 实体化推到 M5**：M3a holder 仍是 `str`，重名/改名仍无法处理；接受
- **DISPOSE 不可逆**：通过二次确认 + state machine 限制 from（RETIRED/MAINTENANCE 才能 DISPOSE）缓解但不消除
- **M3a PR-1 期间前端 broken**：`pnpm gen:api` 后 ts 报错；PR-2 修复期间任何 main 操作前端不可用——单人项目可接受
- **M2d 已落的 `return_location` / `return_receiver` schema 字段在 CheckoutRecord 表删除后失效**：相关字段语义在新模型下由 `to_location` / `to_holder` 承载（§3.3 决议）；旧 schema 字段不再消费

---

## 7. M3 总览修订项汇总

M3a 子 spec 落地需要回写 [`2026-05-03-m3-overview-design.md`](./2026-05-03-m3-overview-design.md) 以下条目，**与本子 spec 同 commit 提交**。

### 7.1 §2.1 状态枚举表"中文文案"列

| status | 修订前 | 修订后 |
|---|---|---|
| IDLE | 在库 | 闲置 |
| IN_USE | 派发中 | 在用 |
| MAINTENANCE | 维修中 | 维修中（不变） |
| RETIRED | 已退役 | 已退役（不变） |
| DISPOSED | 已处置 | 已处置（不变） |

### 7.2 §2.2 holder 字段语义那行

修订为：

> holder 字段在所有非终态都可有值。**RETURN 后 asset.holder = to_holder（不再清空）**：to_holder NULL 表示无人值守仓库；非 NULL 表示归还接收人 / 仓管，他成为新 holder。

### 7.3 §2.3 StateTransitionRecord model 定义

- **删除 `actor: str | None` 字段**
- 删除"M2a/M2d 已落的 return_location / return_receiver 字段映射到 to_location / to_holder，零语义损失"段
- 替换为："M3a 不迁移历史测试数据，PR-1 合并前用户手动清空 db；migration 仅 schema 变更"

### 7.4 §3 M3a 范围段

修订段：

- 子项 3（数据搬迁）— 整段删除
- 子项 4（保留旧 checkout_record 表 1 release 兜底）— 整段删除，改为"PR-1 同 migration 直接 drop checkout_records 表"
- 加："PR-1 同时 drop `Asset.current_checkout_id` 字段（不再反规范化）"
- 加："PR-1 修订 RETURN 后 asset.holder/location 行为：跟随 to_holder/to_location，不强制清空（修订 M2d 行为）"

### 7.5 §4.1 数据迁移与回滚段

大幅简化，替换为：

> **M3a 数据迁移与回滚**
>
> - PR-1 合并前手动清空测试数据（`rm data/asset_hub.db` + 清空 attachments）
> - alembic migration 仅 schema 变更（add DISPOSED enum / create state_transition_records / drop checkout_records / drop Asset.current_checkout_id）
> - alembic downgrade 自动反向，但 db 已清空，无现实回滚意义
> - M3a PR-1 即终局，不留 1 release 兜底

### 7.6 §5.1 风险清单

- R1（M3a 数据迁移破坏现有 checkout 历史）→ 整行删除（不再迁移数据）
- 替换为新 R1（M3a 范围过大）：见本 spec §6.6 R1
- 加 R3'（5 态文案修订破坏前端硬编码）：低
- 加 R6（shadcn Toggle variant 审查）：低
- 加 R7（DISPOSED 误处置）：低

### 7.7 §7 brainstorm 决策追踪表

加 5 行：

| 决策点 | 选择 | 备注 |
|---|---|---|
| M3a 数据迁移策略 | 不迁移 | 测试数据可清空重建；migration 仅 schema 变更 |
| StateTransitionRecord 是否含 actor 字段 | 否 | YAGNI；v1 单用户无来源区分需求；M5 People 实体化时再加 |
| RETURN 后 asset.holder 行为 | 跟随 to_holder | 修订 M2d 行为；NULL 表示无人值守仓库 |
| IllegalTransitionError HTTP 映射 | 409 Conflict | 与 ConflictError 同语义类；闭环 simplify C1 |
| 5 态中文文案 | 闲置/在用/维修中/已退役/已处置 | 修订 frontend 现有"在用/闲置/维护/退役"漂移 |

### 7.8 §6 后续工作段

- M3a 子 spec 文件路径锁定：[`2026-05-03-m3a-state-machine-design.md`](./2026-05-03-m3a-state-machine-design.md)（即本文件）
- 加："M3a 子 spec 写入后，本总览修订项与子 spec 同 commit 提交"

---

## 8. brainstorm 决策追踪

| 决策点 | 选择 | 备注 |
|---|---|---|
| PR 拆分 | 2 PR | PR-1 后端 + PR-2 前端；与 M2 实践一致 |
| 数据迁移策略 | 不迁移 | 旧测试数据清空重建；migration 仅 schema |
| StateTransitionRecord 含 actor 字段？ | 否 | YAGNI；v1 单用户无来源区分需求 |
| RETURN 后 asset.holder 行为 | 跟随 to_holder | 修订 M2d 行为 |
| IllegalTransitionError HTTP 状态码 | 409 Conflict | 与 ConflictError 同语义类 |
| API 请求 body 形态 | 单一 body shape | service 层 SoT 校验 |
| API 响应 body 形态 | 仅 transition row | 与项目现有 mutation pattern 一致；TanStack Query 原生范式 |
| API 端点路径 | `/api/assets/{id}/transitions` | nested resource，REST 习惯 |
| 旧端点处理 | 整体删除 | 不向后兼容 |
| CLI 命令编排 | 9 命令 + kind flag | CHECKOUT_INTERNAL/EXTERNAL 合 `asset checkout --kind`；其余各对一个 kind |
| CLI envelope exit code | exit 1（一般错误） | 与 ConflictError 一致 |
| `--dry-run` 范围 | DISPOSE / RETIRE | 破坏性命令必须支持 |
| dialog 数量 | 6 个独立 dialog | 各自视觉差异化；A3 推迟 M4 |
| RELOCATE/TRANSFER_HOLDER 入口 | ⋯ 菜单 | 与 M2c-2 视觉模式一致 |
| 列表 toggle UX | Toggle chip with status token | 非普通 checkbox |
| timeline 新 kind 视觉 | A 最简文案 + 显式 icon×token 表 | §14.8 高级视觉留 M3d |
| 5 态中文文案 | 闲置/在用/维修中/已退役/已处置 | 修订 frontend 漂移 |
| transition kind label | 派发/出借/归还/送修/维修完成/退役/重新启用/处置/变更位置/变更保管人 | 简洁 + 风格统一 |

---

## 9. 后续工作

- 本子 spec 提交后，进入 writing-plans skill，产出 M3a 实施计划（按 PR-1 / PR-2 拆 task）
- M3 总览修订项（本 spec §7）与本子 spec 同 commit 提交
- followup-allocation.md §M3 表格在子 spec 提交后同步更新（标记 simplify C1 / §J / §L / §14.3 / §14.6 / §14.7 / §14.1 / smoketest B1 已锁定到 M3a；A3 推迟 M4）
- M3b/c/d/e 子 spec 在各自启动时单独 brainstorm
