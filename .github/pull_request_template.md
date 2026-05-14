## 摘要

<!-- 简述本 PR 的目的与改动范围 -->

## 改动类型

<!-- 在下面对应项前打 x,至少选一个;对应 type: 标签 -->

- [ ] bug —— Bug 修复
- [ ] feature —— 新功能
- [ ] enhancement —— 现有功能改进
- [ ] refactor —— 重构(无行为变化)
- [ ] docs —— 仅文档

## 涉及模块

<!-- 在下面对应项前打 x,可多选;对应 area: 标签 -->

- [ ] cli
- [ ] api
- [ ] frontend
- [ ] serve
- [ ] db-migration
- [ ] storage

## 关联 Issue

<!-- 用 closes #N / refs #N 关联,无关联可留空 -->

## 验证清单

- [ ] `uv run ruff check . && uv run ruff format --check .`
- [ ] `uv run pytest`
- [ ] `pnpm --dir frontend lint && pnpm --dir frontend exec tsc -b`
- [ ] `pnpm --dir frontend test`
- [ ] 改了 API schema → 跑过 `pnpm --dir frontend gen:api`
- [ ] 改了状态机 / 数据库迁移 → 加了 `tests/migration/` 测试

## 补充说明

<!-- 设计取舍、Breaking change、跟进事项等(可选) -->
