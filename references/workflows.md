# workflows reference

> 端到端任务流（含 `--json` 输出对照样本）。SKILL.md 主体的"常见任务流"补充。命令调用形态与 SKILL.md 同源约定——改 CLI 接口必同步两处。

6 个端到端流程，每个流的命令链 + 关键 `--json` 响应字段。

---

## 流 1: 登记一台带照片的笔记本

```bash
# 步骤 1 · 定义类型（如已存在跳过）
uv run asset-hub type define --from examples/types/laptop.json --json
# 关键响应字段：data.id = <type_id>

# 步骤 2 · 登记资产
uv run asset-hub asset register \
    --name "ThinkPad X1 Carbon" \
    --type-id <type_id> \
    --sn "PF-1234" \
    --custom '{"brand":"Lenovo","os":"Windows","ram_gb":16}' \
    --json
# 关键响应字段：data.id = <asset_id>；data.status = "IDLE"；data.asset_code = "NB-001"

# 步骤 3 · 上传照片（attachment add，不是 upload）
uv run asset-hub attachment add <asset_id> --file ~/Pictures/laptop.jpg --kind photo --json
# 关键响应字段：data.id = <attachment_id>；data.sha256 = "..."；data.size = <bytes>

# 步骤 4 · 验证
uv run asset-hub asset show <asset_id> --json
# data.status = "IDLE"；data.asset_code 已分配；注意：顶层 data 无 attachments 字段，
# 需单独 uv run asset-hub attachment list <asset_id> --json 获取附件列表
```

**asset list 实际输出形态**（`data` 是直接 array，不是 `data.items`；count 在 `metadata.count`）：

```json
{
  "success": true,
  "data": [
    {
      "id": "...", "asset_code": "NB-001", "name": "ThinkPad X1 Carbon",
      "serial_number": "PF-1234", "type_id": "...", "type_name": "laptop",
      "status": "IDLE", "holder": null, "location": null,
      "notes": null, "custom_data": {"brand": "Lenovo", "os": "Windows", "ram_gb": 16},
      "acquired_at": "2025-01-01T00:00:00", "idle_days": 5,
      "created_at": "...", "updated_at": "..."
    }
  ],
  "metadata": {"count": 1},
  "error": null
}
```

> `idle_days` 仅 IDLE 状态非 null；IN_USE / MAINTENANCE / RETIRED 时为 null。

---

## 流 2: 派发 + 归还闭环

```bash
# 派发给张三（北京办公室），组内借用，期望 30 天归还
uv run asset-hub asset checkout <asset_id> \
    --to-holder "张三" \
    --kind internal \
    --to-location "北京办公室" \
    --due-at "2026-06-01T00:00:00Z" \
    --json
# data.kind = "CHECKOUT_INTERNAL"；data.from_status = "IDLE"；data.to_status = "IN_USE"
# data.id = <transition_id>（后续 RETURN 会写 closes_transition_id = <transition_id>）

# 张三归还，接收人李四，放入上海仓库
uv run asset-hub asset return <asset_id> \
    --to-holder "李四" \
    --to-location "上海仓库" \
    --note "正常归还" \
    --json
# data.kind = "RETURN"；data.from_status = "IN_USE"；data.to_status = "IDLE"
# data.closes_transition_id = <CHECKOUT_INTERNAL.id>（自动闭环）

# 查看历史记录
uv run asset-hub asset history <asset_id> --json
# data 为 transition 列表，最新在前
```

---

## 流 3: 送修 + 维修完成

```bash
# 屏幕坏了，送修（联系人王五，送至上海联想售后）
uv run asset-hub asset send-to-maintenance <asset_id> \
    --to-holder "王五（客服）" \
    --to-location "上海联想售后" \
    --json
# data.from_status = "IDLE"；data.to_status = "MAINTENANCE"

# 修好回库（放回上海仓库）
uv run asset-hub asset recover <asset_id> \
    --to-location "上海仓库" \
    --json
# data.from_status = "MAINTENANCE"；data.to_status = "IDLE"
```

> **IN_USE → MAINTENANCE 不可直跳**——service 层拒绝此 transition。原因：IN_USE 时送修意味着需先了结借用关系。操作路径：先 `asset return`（RETURN → IDLE），再 `asset send-to-maintenance`（IDLE → MAINTENANCE）。

---

## 流 4: 退役 + 重新启用 / 处置

```bash
# 暂时退役（硬盘老化，备件库）
uv run asset-hub asset retire <asset_id> --note "硬盘老化备件" --json
# data.to_status = "RETIRED"

# --- 路径 A：决定复活 ---
uv run asset-hub asset reinstate <asset_id> \
    --to-holder "李四" \
    --to-location "上海仓库" \
    --json
# data.to_status = "IDLE"

# --- 路径 B：决定彻底处置（卖给二手商）---
# 注意：IDLE 不可直接 dispose，需先 retire；RETIRED 才可 dispose
uv run asset-hub asset dispose <asset_id> --note "二手卖出" --yes --json
# --yes 跳过 CLI 交互确认 prompt；没有 --confirm 参数
# data.to_status = "DISPOSED"  ← 终态，不可回退

# 验证：DISPOSED 后不出现在默认列表
uv run asset-hub asset list --json | jq '.metadata.count'
# 减 1（默认不含 DISPOSED）

uv run asset-hub asset list --include-disposed --json | jq '.metadata.count'
# count 含 DISPOSED 项，故较默认 list 多 1（注意是 .metadata.count，不是 .data.items）
```

---

## 流 5: 按筛选导出（HTTP API）

> CLI 顶层**没有 export 命令**。导出通过 HTTP API 完成；Agent 需先 `serve start` 确保后端在线。

```bash
# 确保后端在线
uv run asset-hub serve status --json
# data.running = true → 可继续；false → 先启动

# 当前所有 IDLE 资产，导出 XLSX
curl -OJ "http://localhost:8000/api/export?format=xlsx&status=IDLE"
# -O 用响应 Content-Disposition 的 filename 落盘；-J 保留服务器建议文件名
# Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet

# 张三持有的资产，导出 CSV
curl -OJ "http://localhost:8000/api/export?format=csv&holder=%E5%BC%A0%E4%B8%89"
# Content-Type: text/csv；UTF-8 BOM + 10 列 + custom_fields 平铺

# 关键词 + 类型筛选
curl -OJ "http://localhost:8000/api/export?format=xlsx&q=ThinkPad&type_id=<laptop_type_id>"

# export 完整参数：format=csv|xlsx [&type_id=] [&status=] [&holder=] [&q=]
#                  [&include_retired=true] [&include_disposed=true]
```

**API 响应**：文件流，`Content-Disposition: attachment; filename="assets-2026-05-09.xlsx"` 等。

---

## 流 6: 服务生命周期 + 故障诊断

```bash
# 环境预检（7 项 prod / 8 项 dev）
uv run asset-hub serve doctor --json
# data.ok = true → 全过；false → data.checks 中 ok=false 的项含 .code + .fix_hint

# 启动 dev（前后端同启，后台 detach）
uv run asset-hub serve start --mode dev --json
# data.backend.pid = ...；data.backend.port = 8000
# data.frontend.pid = ...；data.frontend.port = 5173

# 启动 prod（自动 build 前端 + 单端口 :8000）
uv run asset-hub serve start --mode prod --json
# data.frontend = null（prod 由 FastAPI StaticFiles 托管）

# 查状态（含健康探测）
uv run asset-hub serve status --json
# data.running = true；data.backend.healthy = true；data.backend.uptime_sec = 120

# 快速查状态（跳过健康探测，仅读 PID 文件）
uv run asset-hub serve status --no-probe --json

# 看后端最新 100 行日志
uv run asset-hub serve logs --service backend --lines 100 --json

# 实时跟踪日志（非 JSON 模式，Ctrl+C 退出）
uv run asset-hub serve logs --service backend --follow

# 重启 prod
uv run asset-hub serve restart --mode prod --json

# 干净停掉整个进程树
uv run asset-hub serve stop --json
# data.stopped = [{"service": "backend", "pid": ..., "method": "SIGTERM"}, ...]
```

**serve doctor `--json` 输出结构**（关键字段）：

```json
{
  "success": true,
  "data": {
    "checks": [
      {"name": "uv (>= 0.4)", "ok": true, "detail": "uv 0.5.1"},
      {"name": "pnpm (>= 9)", "ok": false, "detail": "not found",
       "code": "serve.pnpm_missing", "fix_hint": "install pnpm: npm install -g pnpm@9"}
    ],
    "ok": false,
    "issue_count": 1
  },
  "metadata": {"took_ms": 1315},
  "error": null
}
```

> `code` 和 `fix_hint` **只在 `ok=false` 的检查项才出现**（`DoctorCheck.to_dict()` 控制）。

---

## 任务 5：出现故障 → 故障解除（自愈/自修）

```bash
# 资产 A 在 IN_USE 状态，holder=李四
uv run asset-hub asset report-broken <id> --note "屏幕背光偶发异常"
# → 进入 BROKEN，holder 保留为李四（keep）

# 李四发现重启就好了，自愈
uv run asset-hub asset dismiss <id> --note "重启后恢复正常"
# → 回到 IDLE，holder 仍是李四（如需清空传 --to-holder ""）
# 注：DISMISS 触发派出集 closes 通用化，原 CHECKOUT 在此闭合
```

---

## 任务 6：出现故障 → 送修 → 维修完成

```bash
uv run asset-hub asset report-broken <id>
uv run asset-hub asset send-to-maintenance <id> --to-location "维修车间"
# 维修完成后
uv run asset-hub asset recover <id> --to-location "原工位"
```

---

## 任务 7：出现故障 → 故障报废 → 注销

```bash
uv run asset-hub asset send-to-maintenance <id>
# 维修过程中判定不可修
uv run asset-hub asset declare-unrepairable <id> --yes --note "主板损坏不修"
# 故障态下直接走退役 + 注销
uv run asset-hub asset retire <id> --yes
uv run asset-hub asset dispose <id> --yes --note "由二手回收商处理"
```
