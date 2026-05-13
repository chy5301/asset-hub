# Follow-up 分配（M2d / M2c-4 / M3 / 暂不动）

**日期**：2026-04-28（M2d 启动前规划）
**M2d 完成回填**：2026-04-29
**输入**：[`followups-m2c3-smoketest.md`](./followups-m2c3-smoketest.md)（产品决策类 B1/B2/B3） + [`simplify-followups.md`](./simplify-followups.md)（重构清单 §1-§4）+ [`specs/2026-04-15-asset-hub-design.md`](./specs/2026-04-15-asset-hub-design.md) §11/§14 主线
**用途**：M2d 启动前确定 follow-up 落点，避免临时塞、避免漏。

判断准则：里程碑主题相关性 > 触发条件已就位 > 顺手成本最低。

---

## M2d · CLI 接管 web 服务生命周期 ✅ **已完成（2026-04-29）**

**主线**：spec §14.9 — `asset-hub serve start/stop/status/restart/logs`，psutil 进程树管理，PID/log 文件，dev/prod 模式。
→ ✅ 落地于 `feature/m2d-serve` (Phase 3-8, Tasks 14-29)。详见 [`specs/2026-04-29-m2d-cli-serve-design.md`](./specs/2026-04-29-m2d-cli-serve-design.md) + [`plans/2026-04-29-m2d-cli-serve.md`](./plans/2026-04-29-m2d-cli-serve.md)。

**搭车的小项**（与 M2d 主题无关，但可在同一里程碑独立 PR 顺手吃掉，不混进 serve spec）：

| 项 | 来源 | 状态 |
|---|---|---|
| **B2** 归还时记录归还地点 + 接收人（dialog 加 return_location / return_receiver 字段） | smoketest（按 spec §14.2 真实意图实施；smoketest 原文表述失真） | ✅ 落地于 `feature/m2d-return-fields` (Tasks 9-13)。M2d brainstorm 阶段澄清 smoketest 原文"直接转交"是表述失真。涉及 model + alembic migration + service + DTO + router + CLI + 前端 5 层；4 + 2 + 1 + 1 + 2 = 10 个新测试。**§14.2 完全被覆盖，从 M3 移除**；§14.3 残值缩小为"派发→归还之间需独立修改位置 action" |
| **B3** AssetType DELETE 端点（严格拒绝引用）+ CLI | smoketest | ✅ 落地于 `feature/m2d-type-delete` (Tasks 5-8)。ConflictError 域异常 + 三层贯通（errors → app.py 409 / envelope exit 1）；CLI 含 `--dry-run` / `--yes` / `--json`；3 + 3 + 5 = 11 个新测试 |
| **I1** 后端 validation 补 `url` / `multi-enum` / `int.min/max` | simplify §4 | ✅ 落地于 `feature/m2d-validation` (Tasks 1-4)。补 url（http/https + netloc）/ multi-enum / int+float min/max 校验；6 + 5 + 6 = 17 个新测试 |
| **I2** `FieldType` Enum + 表驱动 dispatch | simplify §4 | ✅ 落地于 `feature/m2d-validation` (Tasks 1-2)。引入 `FieldType StrEnum`（9 字段类型字面量集中）+ `_DISPATCH: dict[FieldType, Callable]` 替换 7 层 if 链 |

> 4 项均按计划独立 PR 实施，未混进 serve spec。**M2d 总计 38 commits，285 backend + 38 frontend tests 全绿。**

---

## M2c-4 · 类型管理 UI（含结构化 custom_fields builder）✅ **已完成（2026-05-02）**

**主线**：AssetType 列表 + 编辑 UI；`custom_fields` 从手撸 JSON → 结构化 builder（type 选择器、options 编辑、min/max/required 设置）。

→ ✅ 落地于三个分支合并：`feature/m2c4-backend`（PR-1，commit d47ce91）+ `feature/m2c4-form-infra`（PR-2，commit db9f946）+ `feature/m2c4-types-ui`（PR-3，2026-05-02 合并）。

**主题相关 follow-up**（落在 builder 同一改动面上）：

| 项 | 来源 | 理由 | 状态 |
|---|---|---|---|
| **A1** 合并 build-create-schema / build-edit-schema | simplify §1.A | builder 输出新 fieldDefs，schema builder 必然碰；顺手合 | ✅ 落地于 PR-2（feature/m2c4-form-infra Task 10-11，commit db9f946） |
| **F3** zodResolver 在 CreateForm 每次 render 重建 | simplify §1.F | 与 A1 同 PR | ✅ 落地于 PR-2（feature/m2c4-form-infra Task 10，commit db9f946） |
| **A2** 抽 `FieldShell` 收敛 9 个 field-control | simplify §1.A | builder 让"加 field type"成为运行时操作，9 外壳的稳定性会被持续打破 | ✅ 落地于 PR-2（feature/m2c4-form-infra Task 13-14，commit db9f946） |
| **A4** field-controls 泛型 `Control<TFieldValues>` | simplify §1.A | 已登记"与 A2 一起做最划算"，M2c-4 同周期 | ✅ 落地于 PR-2（feature/m2c4-form-infra Task 15，commit db9f946） |

> A2/A4 是必须项（不是顺手）：builder 让运行时增加 field type 成常态，9 个外壳会被反复触碰。

---

## M3 · 特性完整

**主线**：看板 4 图 + `/api/stats` + CSV/XLSX 导出 + SKILL.md + §14.1 派出类型 + §14.6 audit 化 + §14.7 状态枚举 + 基础测试 + README/部署。

**子里程碑划分**：M3a（状态机基建）→ M3b（看板）→ M3c（导出）→ M3d（高级视觉）→ M3e（部署）。

**已登记 / 主题强相关的 follow-up**：

| 项 | 来源 | 理由 / 状态 |
|---|---|---|
| **smoketest B1** 状态切换进流转记录 | smoketest | ✅ M3a 落地（PR-1 commit `e741efb` StateTransitionRecord + `fcdfb47` TransitionService） |
| **C1** checkout.py 与 state_machine 双层防御统一 | simplify §1.C | ✅ M3a 落地（PR-1 commit `42b6f46`） |
| **C3** detail page 多查 type 列表（detail DTO 补 type_name） | simplify §1.C | ⏳ M3b 详情页改动时顺手做 |
| **D1** generated schema 类型业务化 alias 层 | simplify §1.D | ⏳ M3 openapi 客户端选型决策时一并做（spec §13） |
| **H4** `error.ts` `unwrap` 签名抽 `OpenapiFetchResult<T>` | simplify §3.H | ⏳ 与 D1 同周期 |
| **§14.3** IDLE 资产显式 location 维护（独立"修改位置" action） | spec | ✅ M3a 落地（RELOCATE transition kind + RelocateDialog） |
| **§14.6** audit 化（StateTransitionRecord 单表） | spec | ✅ M3a 落地 |
| **§14.7** 状态枚举完善（5 态 + 10 transition kind） | spec | ✅ M3a 落地 |
| **§14.8** timeline 视觉重构（时间渐隐 + 派出类型染色 + 超长派发预警） | spec | ⏳ M3d 高级视觉做（M3a 沿用 M2c-2 卡片堆叠） |
| **§J/§L** form schema cast | simplify §6 | 🟡 M3a PR-2 部分闭环（schema 合一），顶层 Resolver cast 待 RHF/zod 升级 |
| **simplify §7（M1/M3/M4）** M2 视觉收尾审计未选项 | M2 视觉审计 | ⏳ M3b/M3d 启动时一并扫 |

---

## 暂不动（触发条件未到，不分配里程碑）

| 项 | 来源 | 触发条件 |
|---|---|---|
| A3 CheckoutDialog/ReturnDialog 合并 | simplify §1.A | M3a 引入 7 dialog 后时机到，但决议推迟 M4 UI 打磨期（避免落入 AI 模板脸） |
| B1（前端）useStateChangeRunner hook | simplify §1.B | 与 A3 同期 |
| C2 delete_asset cascade 事务边界 | simplify §1.C | 真出现批量删除场景时 |
| E1 AssetHeader 状态矩阵抽配置数组 | simplify §1.E | M3 状态扩到 5+（§14.7）落地后；不扩则不动 |
| F1 `availableStateChanges` 预算表 | simplify §1.F | 30+ 状态时 |
| F2 attachment 批量超限 toast 聚合 | simplify §1.F | UX 复盘时 |
| G1 mutation 工厂 helper | simplify §2 | mutation ≥ 10 时 |
| G2 invalidate 失效面收窄 | simplify §2 | list 缓存条目 >10 或操作可见闪屏时 |
| G3 general-fields schema-driven | simplify §2 | reuse + quality agent 共识不做 |
| H1 `<CenteredPanel>` 整合 4 个占位组件 | simplify §3 | 第 5 个占位场景出现时 |
| H2 双套防抖 / commit 逻辑统一 | simplify §3 | 第 3 个 filter 字段时 |
| H3 / H5 / H6 / I3 / I4 / I5 / I6 | simplify | 全部"决定不做"或微优化触发器极远 |
| §14.4 People 实体化 | spec | 独立 M5 大里程碑，§14.1 之后 |

---

## 关键非显然的判断

1. **smoketest B1 不要在 M2d 单独建表** —— 与 M3 §14.6 的 `StateTransitionRecord` 设计天然合并，先做 B1 等于自己挖坑给 §14.6 填。M2d 期间只做 B2+B3。
2. **simplify I1+I2 应跟 M2d 走** —— 不是主题相关，而是 I1 是用户可触发的运行时 bug，已经拖了 M2c-3；M2c-4 的 custom_fields builder 会更早暴露 url/multi-enum 在后端不认的事实，必须在 M2c-4 之前修。
3. **simplify A2+A4 必须挂 M2c-4** —— 不是顺手，而是 builder 让"运行时增加 field type"成为常态，9 个 field-control 外壳在 M2c-4 期间会被反复触碰，不抽 FieldShell 等于反复改 9 处。
4. **B2 真实意图 = spec §14.2**（2026-04-29 brainstorm 修正）—— smoketest 原文描述"A→甲→乙 直接转交"是失真表述；真实需求是"归还时记录归还到哪个地点 + 哪个管理员接收"。M2d B2 实施完成后 §14.2 完全覆盖，从 M3 移除；§14.3 残值缩小为"派发→归还之间需独立修改位置 action"。

---

## 摘要

| 里程碑 | 主线 | 强搭车项 | 数量 | 状态 |
|---|---|---|---|---|
| **M2d** | §14.9 serve | B2、B3、I1、I2 | 4 | ✅ 已完成（2026-04-29） |
| **M2c-4** | 类型管理 UI + custom_fields builder | A1、F3、A2、A4 | 4 | ✅ 已完成（2026-05-02） |
| **M3a** | 状态机基建（5 态 + 10 transition kind） | smoketest B1、C1、§14.3、§14.6、§14.7、§J、§L | 7 | ✅ 已完成（2026-05-04，merge `a360e04` + `bc084e5`） |
| **M3b** | 看板 + /api/stats | C3、D1、H4 | 3 | ✅ 已完成（2026-05-06，merge `c21ae55` + `98052dc`） |
| **M3c** | CSV/XLSX 导出 | — | 0 | ✅ 已完成（2026-05-07，merge `a55beec` + `5c5bab0`） |
| **M3d** | timeline 视觉重构 + simplify §7 搭车 | §14.8 染色 / §14.8 超长派发 / C-1 / C-2 / C-3 | 5 | ✅ 已完成（2026-05-07，单 PR feat/m3d-timeline-visual） |
| **M3e** | SKILL.md + 部署 + 测试基建 + K1 envelope 统一 | K1（HIGH）、A3（推迟 M4） | 2 | ✅ 已完成（2026-05-09，merge `98a3a80`） |
| 暂不动 | — | 13 项 | 13 | — |

---

## M2d 期间另登记的新 follow-up

M2d 实施 + final code review + simplify review 过程中又产生了一批新 follow-up，已分别登记到对应文档：

- [`simplify-followups.md` §5 M2d 范围](./simplify-followups.md#5-m2d-范围2026-04-29)：K1-K9（已落地 4 项，未修 9 项；其中 **K1 envelope 统一**为 HIGH 优先级，登记到 M3 SKILL.md 完善同周期）
- [`specs/2026-04-29-m2d-cli-serve-design.md` 附录 B](./specs/2026-04-29-m2d-cli-serve-design.md)：M2d 已知 Gap（Linux 真机烟测延后 / 多代日志轮转 / serve doctor / serve build 独立子命令 / --workers）
- [`release-notes-m2d.md`](./release-notes-m2d.md)：部署清单 + Windows 烟测 checklist

---

## v2.0 PR-1 · 状态机焕新 + 文案 + CLI flag 标准化 ✅ **已合并（2026-05-13）**

合并 commit：`b689148` (PR #3, Merge pull request from feat/v2-pr1-state-machine)
PR：https://github.com/chy5301/asset-hub/pull/3

落地范围：
- 6 态状态机（+ BROKEN）
- 12 transition kind（+REASSIGN / +REPORT_BROKEN / +DECLARE_UNREPAIRABLE / +DISMISS, - RELOCATE / -TRANSFER_HOLDER）
- keep rule 引入（_UNSET 哨兵 / model_dump exclude_unset 透传）
- 派出集 closes 通用化
- CLI flag 12 处 rename（统一 --to-holder / --to-location）
- 全 6 态文案两字对齐（DISPOSE：处置 → 注销）
- status-broken 色 token + 4 新 dialog + transition-timeline KIND_META v2
- e2e 4 新 spec（BROKEN 生命周期）
- SKILL.md / references v2 全面重写

搭车闭环 followup：
- KIND_META 跨文件合一（M3 §U）—— 部分闭环（KIND_META 重写时新增 4 kind 已对齐多文件，旧不一致仍存）
- 简化 CLI flag 不一致（M3 followup）—— 完全闭环

未解决 followup（PR-1 范围外）：
- ~~ReassignDialog 表单时序 bug~~ **已在 2026-05-13 /simplify pass 修复**（commit `6852a3a`）：用 `e.preventDefault()` 阻止 AlertDialogAction 默认 close + 手动 `onOpenChange(false)`（mutation 成功后才关），spec 11 e2e 已从 `test.skip` 改回 `test` 并验证通过。
- Dashboard 与列表 filter toggle 文案风格不统一（2026-05-13 visual smoke 发现）：`/dashboard` 顶部 toggle 是"已退役 / 已注销"（保留"已"前缀，过去时表达"已在此态"），而 `/` 列表的 filter toggle 是"显示退役 / 显示注销"（无"已"，动作 + 状态名）。两处都是用户可见 v2 文案，建议下一轮 polish 时统一为同一句式（推荐"显示退役 / 显示注销"句式，与 STATUS_META label 配套使用更清晰）。属 cosmetic 一致性问题，不阻塞 PR-1。
- `asset-hub serve stop` 不清非自管端口占用（2026-05-13 visual smoke 发现）：当 5173 端口被非 serve 拉起的旧 Vite 实例占住时，`serve start` 会让新 Vite 自动切到 5174，但 health probe 和提示信息仍按 5173 走 → 浏览器访问 5173 加载到旧 bundle，hot-reload 也不生效。`serve stop` 只 kill 自己 PID 文件里记的进程，不清这种"外部占用者"。修复方向：（a）`serve start` 启动前 probe `frontend_port`，若被外部进程占用应明确 fail 而不是放任 Vite 切端口；或（b）`serve doctor` 增加"端口占用者不在我管理范围"的检测项。
- 2026-05-13 /simplify pass 衍生 minor 项（reviewer 标 Minor，未修）：dialog test wrapper 重复（reassign/declare-unrepairable test 各自创建 QueryClient + provider，可抽 `createWrapper()`）；checkout 的 `to_holder` 不走 `parse_unset_or_value` 缺解释注释；test docstring `v2.0:` 前缀属变更日志噪音；`find_open_checkout_id` 2 次查询可合并为单次 LEFT JOIN；migration UPDATE / downgrade 全表扫描（无 `status`/`kind` 索引；对小团队工具可接受）；`useTransitionsQuery` 无分页（v2 后单资产 transition 数量上限可能↑）。
- `asset-header.test.tsx:225` "逾期 3 天" 测时间敏感 flaky（commit `3dcdf56` M3d 引入，main 也 fail，与 PR-1 无关）：测试构造 `due_at = Date.now() - 3*86400000` 解析时无时区导致按 local 时间偏移得到 3+ 天而非 3 天。修复方向：用 `vi.useFakeTimers()` 冻结时间，或断言 `/逾期 \d 天/` 正则（不强 3）。
- PR-1 visual smoke 手动 QA：已于 2026-05-13 用 Playwright MCP 完成，6 态 / 4 新 dialog / dispose phrase "注销" / BROKEN 资产 5 按钮路径全部对齐 v2 spec，详见 controller 烟测报告。

---

## v2.0 PR-2 · Agent-native 收口 ✅ **已合并（2026-05-13）**

合并 commit：`05345d2` (PR #4, Merge pull request from feat/v2-pr2-agent-native)
PR：https://github.com/chy5301/asset-hub/pull/4

落地范围（spec §4，共 8 commits 跨 6 phase）：

- **Phase 1** M3e Phase 1 三 followup：
  - `cancelled` error code exit_code 1 → 10 正式化（与 dry-run 同档信号化）
  - doctor `check_alembic_head` returncode + stderr 关键词分类（alembic 缺失 vs DB 落后于 head 分类 fix_hint）
  - doctor `check_frontend_dist` `Path(__file__).parents[4]` 解耦 CWD（agent 任意目录可调）
- **Phase 2** envelope error 深度结构化：
  - `errors.py` 6 子类加 `hint / fields_missing / fields_invalid / affected_resource_id` 可选 kwargs + class-level `code` 类属性
  - `api/app.py` exception handler 平铺新字段（保留 `detail` backward compat，前端 / 4 个现有 API 测零回归）
  - `cli/envelope.py` 删 `_DOMAIN_ERROR_CODES` dict 改用 `type(exc).code`；error 嵌套字典加新字段 exclude None
  - `services/transition.py` REASSIGN / RETURN raise 补 hint；`state_machine.py` validate_transition 3 raise 补 hint
- **Phase 3** `--help-json` 双模 agent 元数据导出：
  - 任意 CLI 命令传 `--help-json` 输出 `{command, help, params, examples}` JSON
  - Option D 实现：单点 monkeypatch `typer.main.get_command` + `typer.testing._get_command` 递归注入 hidden eager Click flag。typer pin 加 `<0.30` 上限缓解 private API 风险
- **Phase 4** `--fields` 字段掩码（API + CLI），节省 agent token 5-9×：
  - API `?fields=a,b,c` 4 endpoint（asset get/list + transition POST/GET）；Option B 保留 `response_model` + JSONResponse filter 分支（OpenAPI / 前端 gen:api 不受影响）
  - CLI `--fields` 14 asset 命令（list / show / history + 11 transition 写）；register/update/delete/type/attachment/stats/serve 不在 scope
  - unknown 字段 → ValidationError + fields_invalid + hint 列合法字段
  - dry-run + --fields：dry-run preview 不被 filter（contract test 锁）
- **Phase 5** SKILL.md description trigger eval：
  - 1-pass 分析式优化（正式 5-iter run_loop.py 需 host Claude Code 环境，本 background subagent 受限）
  - baseline 弱点：abstract 术语 / web image asset 歧义；优化版加"实物资产 + 硬件类型清单"、口语化触发词（坏了/修不好/换工位）、显式 pushy 句对抗 under-trigger、"不适用于" 黑名单
- **Phase 6** 收尾：references/envelope.md v2.0 章节补全（深度结构化 4 字段表 + 3 示例 + API/CLI shape 差异说明）

搭车闭环 followup：
- M3e Phase 1 三 followup（cancelled formalize / alembic_head 分类 / frontend_dist CWD）—— 完全闭环
- envelope error 深度结构化（K1 envelope 统一升级版）—— 完全闭环
- `--help-json` / `--fields` agent 友好层 —— v2.0 新基建
- doc-debt `_DOMAIN_ERROR_CODES` 残留清理 —— 闭环

未解决 followup（PR-2 范围外，留 v2.1 或 polish 期）：
- formal 5-iter description eval（需 host Claude Code 环境跑 `skill-creator/scripts/run_loop.py`，本 1-pass 分析估 hit rate 改善 ~4/15）
- typer private API 依赖（`typer.main.get_command` + `typer.testing._get_command`）—— 加了 `<0.30` 上限触发主动 revisit，但应在某次 typer 升级前考察更稳健的 Click 注入方案
- Phase 1 PR-1 衍生 minor 项（dialog test wrapper / find_open_checkout_id 2 查询合并 / migration UPDATE 全表扫描）—— 未在 PR-2 scope，留前端 polish 或独立 PR
- Dashboard vs 列表 filter toggle 文案不统一（PR-1 visual smoke 发现）—— 前端 cosmetic，未在 PR-2 scope（PR-2 零 frontend diff）
- `asset-hub serve stop` 不清外部端口占用（PR-1 visual smoke 发现）—— 未在 PR-2 scope（M3e Phase 1 三 followup 之外）
- asset-header.test.tsx 时间敏感 flaky（前端，PR-1 main 也 fail）—— 未在 PR-2 scope

---

## v2.0 PR-3 · Asset.model 字段拆列 ✅ **已合并（2026-05-13）**

合并 commit：`b1e7176` (PR #5, Merge pull request from feat/v2-pr3-asset-model-column)
PR：https://github.com/chy5301/asset-hub/pull/5

落地范围（spec + plan 27 task / 6 phase，共 11 commits）：

- **Phase 1** 数据模型：`Asset.model: str | None = Field(default=None, index=True)`（紧贴 name 之后）+ alembic v3 migration（`add_column` + `ix_assets_model` index + 反向 drop，用 batch_alter_table）+ 2 migration 测
- **Phase 2** Service：`register` / `update_asset` 加 model 参数（后者用 `UNSET` 哨兵区分"未传 vs null 清空"）；`SortByField` Literal + `SORT_FIELD_WHITELIST` frozenset + repository `_SORT_COLUMN_MAP` 三处都加 `model` + `serial_number`（顺修 v1 sn sortable 不一致——前端可点 header 但后端 422）；`list_filtered` q OR-chain 加 `Asset.model.contains(q)`（紧邻 sn 之后）
- **Phase 3** API DTO：`AssetCreate` / `AssetUpdate` / `AssetRead` 三件套加 model 字段（位置紧贴 sn）；`AssetUpdate` 沿用 v1 exclude_unset 风格不引入 `extra="forbid"`；router `create_asset` 加 `model=body.model` 透传到 service.register（隐含必要，DTO 接受 model 但 service 不收到会沉默丢失）；`pnpm --dir frontend gen:api` 重拉 schema.d.ts（顺带还了 PR-2 `--fields` 后未拉的 schema 债）
- **Phase 4** CLI：`asset register` 加 `--model <txt>` flag（位置紧邻 `--sn`，help="型号"）；`asset update` 复用 v1 `--set <JSON>` 模式自然支持 model 设值/null 清空/不传保持（不重构成分立 flag）；`asset list --sort` help text 补 `model` / `serial_number`
- **Phase 5** 前端：`types` `AssetRow` 加 model；表单 `general-fields-form` 在 name FormField 之后插入 model FormField（FormLabel "型号"、无 `*`、无 helper、placeholder "如 ThinkPad X1 Carbon Gen 9（可空）"）；详情 `asset-header` 副行加 `· model` 条件渲染（model 为 null 时整段不输出）；`general-fields` 在 "类型" 行之后插 "型号" 行（不用 CopyableText、空 "—"）；`assets-table` 在 name 列之后插入 model 列（不用 font-code、可 sort、空 "—"）；`column-visibility` ColumnKey + COLUMN_LABELS + ALL_KEYS 三处加 model（DEFAULT_HIDDEN 不变，默认显示）；`asset-create-form` / `asset-edit-form` 各加 defaultValues + reset + submit payload（隐含必要，否则 RHF input 不受控）；`build-asset-schema` zod baseShape 加 model nullable optional；3 个前端单测文件覆盖 model 列渲染 / column-visibility 默认 / zod schema 接受
- **Phase 6** 收尾：`services/export.py` `_FIXED_COLUMN_NAMES` 加 "型号"（11 列，紧邻 "名称" 之后）+ `_build_rows` 注入 `a.model or ""` + 4 处既有测试 column 索引 / autofilter 范围 `A1:K{n}` / header startswith 更新；`examples/types/gpu.json` 删冗余 model custom_field；SKILL.md asset register flag 段补 `[--model <txt>]`；`release-notes-v2.0.md` 顶部状态从"等 PR-2"改"等 PR-3" + 概览表加 PR-3 行 + Breaking changes 加 PR-3 4 子段 + 验证 checklist 加 PR-3 6 项 + 路线图摘要更新；`test_v2_state_machine.py` downgrade `-1` → `-2` 适配 v3 head（v3 加 head 后 `-1` 跑 v3.downgrade 而非 v2.downgrade，DID NOT RAISE）；/simplify pass 清理 8 处任务标记型注释（`# 新` / `# v2.0 PR-3`），无逻辑改动

搭车闭环（plan 没列但 implementer 自检发现的 hidden requirements，已修）：
- v1 遗留 SortByField + `_SORT_COLUMN_MAP` 不含 sn 顺修 —— service / WHITELIST / repo map 三处对齐
- v2 migration downgrade test 适配 v3 head（command.downgrade -2）—— 顺修
- CLI `--sort` help text 漏列字段补全 —— 顺修
- `examples/types/gpu.json` 冗余 model custom_field —— 闭环（与新顶层字段统一）
- router `create_asset` 加 `model=body.model` 显式透传 —— 必要 hidden requirement
- form `asset-create-form` / `asset-edit-form` defaultValues + reset + submit payload —— 必要 hidden requirement（RHF 不受控）

未解决 followup（PR-3 范围外）：
- ~~`asset-hub serve start` 不识别外部端口占用~~ —— ✅ **v2.x PR-C 已修**（2026-05-13）：根因是 `proc.is_port_in_use` 仅探 IPv4 127.0.0.1，但 Vite 8.x dev 默认监听 IPv6 ::1。修复用 (a)+(a') 组合——双栈 bind 探测 + `vite.config.ts strictPort: true` 兜底。原 bug 描述保留备忘：5173 被外部进程占用时 Vite 偷偷 fallback 5174 但 PID 文件/status 撒谎，PR-1 visual smoke 首次撞、PR-3 烟测第二次撞
- 已存在 GPU AssetType（按 v1 example 创建过）custom_fields 仍含 model —— 用户手动迁移（release-notes-v2.0.md §升级注意 已写明）
- 未来重构 update CLI 为分立 flag（含 `--name` / `--model` / `--sn` 等，与 register 对称）—— v2.x / M4 followup（plan 显式不在 PR-3 scope）
- ~~PR-3 待维护者本地视觉烟测确认~~ —— 已合并；烟测过程暴露 serve port bug 第二次复现（见上一条），未发现 PR-3 自身视觉问题

---

## v2.x polish · CI 后端+前端覆盖 PR-A · ✅ **已合并（2026-05-13）**

合并 commit：`cb16d17`（squash merge）
PR：https://github.com/chy5301/asset-hub/pull/6
分支：`feat/v2.x-ci-coverage`
spec / plan：`docs/superpowers/specs/2026-05-13-v2.x-ci-coverage-design.md` + `docs/superpowers/plans/2026-05-13-v2.x-ci-coverage.md`

落地内容：

- 新建 `.github/workflows/ci.yml`，2 个并行 job：`backend`（ruff check + pytest 609 测）+ `frontend`（ESLint + tsc -b + vitest 179 测）；ubuntu-latest，timeout 10 min
- fix(test) `tests/unit/test_doctor.py::test_check_{uv,pnpm}_ok` 显式 mock `_resolve` —— 原测试隐式依赖 runner 装机 `shutil.which` 命中真 path 才能走到 subprocess.run mock；backend job 只装 uv + python 不装 pnpm → `_resolve("pnpm")` 返 None → short-circuit 'not found' → fail（commit `7b9b8aa`）。test_check_uv_ok 同步显式化（防御性，runner 当前装 uv 凑巧过）

**CI 实战结果**（PR #6 push 后实测）：

| Check | 第一次（commit 1359c81）| 第二次（fix 后 7b9b8aa）| rerun |
|---|---|---|---|
| backend | fail (1 测) | **pass** 49s | — |
| frontend | pass | **pass** 56s | — |
| e2e | pass 1m52s | CANCELLED 15m17s | CANCELLED 14m48s |

未解决 followup（PR-A 范围外）：

- **e2e workflow flaky · playwright browser install 无 cache**：`.github/workflows/e2e.yml` step 9 `pnpm exec playwright install --with-deps chromium` 每次冷下载 ~250MB chromium binary，撞 CDN 慢就被自身 `timeout-minutes: 15` 卡停 cancel。第一次同分支 1m52s 全绿、第二次/第三次（rerun）连卡 14m48s/14m48s。**与 PR-A 0 相关**（PR-A 没动 e2e.yml / playwright specs / 前端代码 / backend service）。修复方向（独立 PR）：（a）加 `actions/cache@v4` 缓存 `~/.cache/ms-playwright`，key 用 playwright 版本；或（b）改用 `microsoft/playwright-github-action`；或（c）把 timeout 从 15 min 抬到 20-25 min 给冷启动留余量

---

## v2.x polish · ruff format baseline PR-B · ✅ **已合并（2026-05-13）**

合并 commit：`07fc0fc`（squash merge）
PR：https://github.com/chy5301/asset-hub/pull/7
分支：`style/v2.x-ruff-format-baseline`
spec / plan：`docs/superpowers/specs/2026-05-13-v2.x-ruff-format-baseline-design.md` + `docs/superpowers/plans/2026-05-13-v2.x-ruff-format-baseline.md`

落地内容：

- 跑 `uv run ruff format .` 对 80 个未格式化 .py 文件按现有 `pyproject.toml` ruff 配置一次性 reformat 到 baseline（+2288/-892，commit `fc27bb8`，机械 AST 重排，0 逻辑改动）
- `.github/workflows/ci.yml` `backend` job 在 `ruff check` 之后插入 `ruff format check` 步骤（commit `0fd5ed2`）；位置选定在 ruff check 之后、pytest 之前——lint 失败诊断价值高优先看，format 检查 <1s fail-fast 比 pytest 快

CI 实战：一次推送 3 check 全绿（backend 45s / frontend 1m9s / e2e 1m49s）。

不做（已 doc 到 spec）：
- pre-commit hook（YAGNI；CI --check + IDE 集成已双层）
- `.editorconfig`（与 ruff format 无 overlap）
- 锁 ruff 版本（dev group `ruff>=0.8` 范围保留；未来 format 行为变化由 CI 自动抓）
- `.git-blame-ignore-revs`（单维护者仓库 squash blame 简单跳前一版即可）

---

## v2.x polish · serve start IPv6 端口探测 PR-C · ⏳ **等 review/merge（2026-05-13）**

PR：https://github.com/chy5301/asset-hub/pull/<TBD>
分支：`fix/v2.x-serve-port-detection`
spec / plan：`docs/superpowers/specs/2026-05-13-v2.x-serve-port-detection-design.md` + `docs/superpowers/plans/2026-05-13-v2.x-serve-port-detection.md`

落地内容：

- (a) `src/asset_hub/cli/serve/proc.py::is_port_in_use` IPv4 127.0.0.1 + IPv6 ::1 双栈探测；IPv6 系统级不可用时 graceful 退化为 IPv4 单栈；删除 `host` 参数（仅两处调用均默认 host，零 caller 改动；commit `698c9ce`）
- (a') `frontend/vite.config.ts` 加 `server.strictPort: true` 兜底——Vite 端口占用时直接 exit 非零而非 fallback 撒谎；与 (a) 配合双层防御（commit `d80da2f`）
- 不做 (b) doctor 加"占用者 PID 检测"：(a) 修复后 `doctor.check_port_free` 复用 `is_port_in_use` 自动获得双栈
- 不做 (c) PID 文件加 port 字段：(a)+(a') 让 fallback 路径不存在，PID 设定 port 即真实监听 port，YAGNI

根因（spec 首次明确记录）：Vite 8.x dev 默认监听 IPv6 ::1（lifecycle.py:144-146 已有注释），原 is_port_in_use 仅探 IPv4 127.0.0.1 → 漏检 → start_service 不 fail-fast → Vite 内部检测 ::1:5173 占用偷偷 fallback 5174 → PID 文件 / status 撒谎。

TDD 完成：先加 IPv6 占用测试看 fail（旧 IPv4-only 实现 `assert False is True`）→ 改实现 → 4 个 proc 测试全 PASS → 全量 611 pytest PASS（原 609 + 新 2）。

闭环：v2.0 PR-3 段第一条 followup（serve port detection）由本 PR 终结。

---

## v2.0.1 发版规划（PR-A + PR-B + PR-C）

PR-A / PR-B 是开发者侧 infrastructure（CI / format baseline）无 runtime 影响；PR-C 是用户可见 bug fix 向下兼容。三者合并按 SemVer 严格语义 → PATCH → **v2.0.1**。

PR-C merge 后维护者按 v2.0.0 release-notes 流程发版：changelog 聚焦 PR-C 这一 fix，PR-A/PR-B 在 "Developer Experience" 段一行简略提及（不影响用户语义）。
