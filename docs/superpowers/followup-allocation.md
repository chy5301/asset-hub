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

## v2.0 PR-2 · Agent-native 收口 ⏳

合并 commit：<等 PR-2 merge 后回填>
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
