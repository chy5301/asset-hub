#!/usr/bin/env bash
# 同步 asset-hub 的 label 体系到 GitHub 远程仓库
#
# 用法:
#   scripts/sync-labels.sh              # 默认仓库 chy5301/asset-hub
#   REPO=owner/name scripts/sync-labels.sh
#
# 要求:gh CLI 已登录且对目标仓库有写权限
#
# 幂等:gh label create --force 在标签已存在时更新颜色/描述

set -euo pipefail

REPO="${REPO:-chy5301/asset-hub}"

create() {
  local name="$1" color="$2" desc="$3"
  gh label create "$name" --color "$color" --description "$desc" --repo "$REPO" --force >/dev/null
  echo "  ok  $name"
}

del() {
  local name="$1"
  if gh label delete "$name" --repo "$REPO" --yes >/dev/null 2>&1; then
    echo "  del $name"
  fi
}

echo "==> 创建/更新 type: 系列"
create "type: bug"          "d73a4a" "Bug 报告"
create "type: feature"      "a2eeef" "新功能请求"
create "type: enhancement"  "84b6eb" "现有功能改进"
create "type: docs"         "0075ca" "文档相关"
create "type: refactor"     "bfdadc" "重构(无行为变化)"

echo "==> 创建/更新 status: 系列"
create "status: confirmed"  "0e8a16" "已确认"
create "status: needs-info" "fbca04" "需要更多信息"
create "status: duplicate"  "cfd3d7" "重复"
create "status: wontfix"    "eeeeee" "不会修复"

echo "==> 创建/更新 area: 系列(对应三层分离架构与子系统)"
create "area: cli"          "5319e7" "Typer CLI 与 --json 信封"
create "area: api"          "5319e7" "FastAPI 路由与 schemas"
create "area: frontend"     "5319e7" "React / TanStack Router 前端"
create "area: serve"        "5319e7" "serve 子命令(进程编排)"
create "area: db-migration" "5319e7" "Alembic 迁移与 ORM 模型"
create "area: storage"      "5319e7" "StorageAdapter 与附件 I/O"

echo "==> 保留社区类标签"
create "good first issue"   "7057ff" "适合新手的入门任务"
create "help wanted"        "008672" "欢迎社区贡献"

echo "==> 删除被前缀化标签替代的默认 label"
del "bug"
del "enhancement"
del "documentation"
del "duplicate"
del "invalid"
del "question"
del "wontfix"

echo "==> 完成"
