# 放弃 M5 + 宣布 v2 功能完整 — 决策文档

> 日期：2026-05-25
> 类型：路线图决策（ADR 风格）
> 状态：已采纳

## 背景

v1.0 → v2.3.0 已发布，main 干净，无 open issue / PR。路线图（`release-notes-v2.0.md` §路线图位置）上 **M5 · People 实体化（主设计文档 §14.4）是唯一剩余的规划里程碑**——v2.x 清场期、M4 视觉打磨均已随 v2.1.0 / v2.2.0 落地。

2026-05-25 review 时重新评估 M5 的必要性，结论是放弃，并就此为整条 v1/v2 演进路线收口。

## 决策

### 1. 放弃 M5 People 实体化

**理由（YAGNI）**：本工具定位明确为「单一人类用户 + 其 AI Agent」（见 `CLAUDE.md` §项目定位），不做多用户。在这个定位下 `holder` 用字符串足够，建 `People` 实体 / FK / typeahead 选人属于过度设计。

**经验依据**：§14.4 当初要解决的痛点——`holder` 字符串记不下「重名 / 改名 / 联系方式 / 单位部门」——在真实使用中**零发生**。holder 始终只是一个名字，没有按人聚合、没有重名歧义、没有要记联系方式或部门的场景。为尚未出现的问题预建实体不符合本项目一贯的「触发条件未到不做」原则。

### 2. 宣布 v2 功能完整，进入维护态

放弃 M5 后，主设计文档 §14「演进方向 / 候选扩展」里 **M5 是最后一个未做项**，其余均已落地或明确收口：

| 候选 | 去向 |
|---|---|
| §14.1 派出类型扩展（internal / external） | ✅ v2.0 状态机（`CHECKOUT_INTERNAL` / `CHECKOUT_EXTERNAL`） |
| §14.2 归还时改 location / holder | ✅ M2d |
| §14.3 IDLE 资产显式 location | ✅ M3a（RELOCATE transition） |
| §14.5 状态切换 web 入口 | ✅ M2c-3 |
| §14.6 状态转换 audit 化 | ✅ M3a（StateTransitionRecord） |
| §14.7 状态枚举完善（6 态） | ✅ v2.0 |
| §14.8 timeline 视觉重构 | ✅ M3d（时间渐隐项决议作废） |
| **§14.4 People 实体化** | **❌ 本决策放弃** |

因此 **v2 宣布功能完整**：不再规划主动的大特性里程碑，项目进入**按需迭代 / 维护态**——后续只接真实触发的 bug fix 和小特性，整条 v1/v2 演进路线就此画句号。

### 3. 重新评估触发条件

放弃 ≠ 永不做。M5 仅在以下**具体**条件之一真实出现时才重新评估：

- 同名 `holder` 无法区分（重名歧义实际咬人）
- 工具被迫扩展到多用户 / 多人协作场景
- 按人聚合统计（部门 / 联系方式维度）成为真实诉求

触发前不投入。届时应重新走 brainstorming，而非直接复用本文废弃的旧设计。

## 维护态待办快照（2026-05-25 冻结）

进入维护态时，把 backlog 的**仍开放**项冻结如下。**已完成项不在此重列**——它们归档在各 `release-notes-*` 与 `simplify-followups.md` 的历史里，按里程碑可查。本快照只承载「还没做、且仍可能做」的项。

### 正式关闭（won't-do）

- **formal 5-iter description eval**：用 skill-creator `run_loop.py` 跑 5 轮 SKILL.md description 触发优化。自 v2.0 PR-2 起一直以「作者无 `run_loop` 兴趣」carry，M4 spec §明确不做 已列。此刻**正式终结**，不再作为待办挂着。

### 仍开放 · trigger-gated（休眠，等触发器响）

| 项 | 触发条件 |
|---|---|
| 后端 3 minor：`find_open_checkout_id` 合并为单次查询 / migration UPDATE 全表扫描加索引 / `useTransitionsQuery` 无分页 | 单资产 transition 量级显著上升，或下次大改该路径时 |
| 前端 form 类型链路 cast §J/§M/§N/§O（`build-asset-schema` 顶层 Resolver cast / `useWatch` 重复订阅 / `field-${key}` id 模板重复 / MultiEnumField label a11y） | RHF / zod 升级，或下次重构 form 字段层时同 PR 清 |
| §T `IllegalTransitionError` detail 结构化 payload | i18n 启动 / 前端 dialog 形态稳定后 |
| §S 列表 Toggle pressed 视觉态偏弱 / §W types vs assets 详情·列表面板风格不统一 | 下次碰 list filter / 该区域 UX 时顺手 |
| typer 私有 API 依赖（`typer.main.get_command` + `typer.testing._get_command`） | 已 pin `typer<0.30` 作哨兵；typer 升级触发时换更稳健的 Click 注入方案 |
| spec §13 选型观察：SQLModel → SQLAlchemy 2.x + 独立 Pydantic / Tremor 的 Radix·shadcn 原生替代 | 上游维护节奏 / 版本变化触发时重评 |

### 便宜小缺口（随时可清，非阻塞）

- `uv.lock` 版本号收尾（2.0.2 → 2.3.0，已 staged 未提交）。
- `cli/deps.py:254` 的 `--help-json` `examples` 字段当前硬编码 `[]`，计划从命令 docstring 末 `Examples:` 段提取（agent-native 小缺口，独立小 PR 即可）。

### 已完成项归档指针

不在本快照内的历史 follow-up（已闭环 / 已决定不做的旧项）见：`docs/superpowers/simplify-followups.md`（§1-§9 按里程碑）、`docs/superpowers/followup-allocation.md`、各 `release-notes-*.md` 的「未解决 followup」段。这些文档保持原样作为历史档案，不重写。

## 影响 / 引用更新

本决策顺带更新以下文档引用，使路线图状态一致：

- `release-notes-v2.0.md` §路线图位置：M5 行「⏳ 规划中」→「❌ 已放弃」，并补 v2 功能完整声明 + 指向本文。
- 主设计文档 `2026-04-15-asset-hub-design.md` §14.4：顶部标注「已决定不做（YAGNI），见本决策」。

## 不做（YAGNI 边界）

- **不**重写 `simplify-followups.md` 等历史档案去"清理"已完成项——它们是按里程碑的历史记录，重写是 churn 且可能丢上下文。
- **不**为宣布功能完整而提前清 trigger-gated / 便宜小缺口项——那与本决策放弃 M5 所依据的 YAGNI 自相矛盾。
- **不**保留一个独立 living backlog 文档——维护态低频改动，本文的时点快照 + 历史指针已足够。
