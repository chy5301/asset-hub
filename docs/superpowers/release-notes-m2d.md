# M2d 部署手工干预清单

## 概览

M2d 交付内容：

- **主线 §14.9**：`asset-hub serve start/stop/status/restart/logs` 五个子命令（后台 detach + psutil 进程树清理 + PID/log 文件状态 + `/api/healthz` 端点）
- **附录 4 项 backend gaps**（独立 PR 已合并）：
  - I1+I2：后端 validation 补 url/multi-enum/int+float min/max + FieldType StrEnum
  - B3：AssetType DELETE 端点（严格拒绝有引用）+ CLI `type delete --dry-run/--yes`
  - B2：归还时记录归还地点 + 接收人（修正 smoketest 原文表述失真，按 spec §14.2 真实意图实施）

## 升级前

1. **备份数据库**：

   ```bash
   cp data/asset_hub.db data/asset_hub.db.<日期>.bak
   ```

2. **如有自定义 dev 启动脚本**（CI / Docker / IDE 任务），改为 `uv run asset-hub serve start --mode dev`。`scripts/dev.sh` 已删除。

## 升级

```bash
git pull
uv sync                         # 拉 psutil 等新依赖
uv run alembic upgrade head     # 跑 B2 的 return_location/receiver migration
```

## 升级后验证

### 1. 自动化测试

```bash
uv run pytest                   # 285 backend tests，期望全绿
uv run ruff check .             # 期望 clean
pnpm --dir frontend test --run  # 38 frontend tests，期望全绿
pnpm --dir frontend lint        # 期望 0 errors（仅 1 个 pre-existing react-hooks 警告）
```

### 2. CLI 表面验证

```bash
uv run asset-hub serve --help               # 期望列出 start/stop/status/restart/logs
uv run asset-hub serve start --help         # 期望列出 --mode/--skip-build/--port/--frontend-port/--host/--json
uv run asset-hub serve status --json        # 服务未跑时返回 {"running": false, ...}
```

### 3. Windows 烟测 checklist（必跑）

> 当前阶段 Linux 路径仅靠单测 mock 覆盖；Linux 真机烟测延后到 Linux 部署环境就绪后单独执行（M2d release 不阻塞此项）。

#### Windows + dev 模式

- [ ] `uv run asset-hub serve start --mode dev` 起后端 + 前端，`data/pids/{backend,frontend}.pid` 两文件存在
- [ ] 浏览器访问 `http://127.0.0.1:5173` 看到前端，调 `/api/assets` 走 Vite 代理通
- [ ] `uv run asset-hub serve status` 表格输出含 backend + frontend 两行，healthy ✓
- [ ] `uv run asset-hub serve logs --follow` 看到 access log；Ctrl+C 终止 → exit 0
- [ ] `taskkill /PID xxx /F` 模拟崩溃后，`uv run asset-hub serve status` 显示 stale
- [ ] `uv run asset-hub serve stop` 干净杀进程树（任务管理器无残留 uvicorn / node / pnpm）
- [ ] 关闭 cmd 终端后，新开终端 `uv run asset-hub serve status` 仍能查到（detach 验证）
- [ ] `uv run asset-hub serve restart --mode prod` 切换模式

#### Windows + prod 模式

- [ ] 删 `frontend/dist` 后 `uv run asset-hub serve start --mode prod` 自动 build → 启动成功
- [ ] `frontend/dist` 已存在时 start 跳过 build
- [ ] 删 `frontend/dist` + `--skip-build` → exit 1 + `serve.dist_missing` error
- [ ] prod 模式下 `:8000` 单端口对外访问前端 + `/api/healthz` 返回 200

### 4. Backend gaps 验证

- [ ] `uv run asset-hub type delete <id> --dry-run --json` 输出 `{would_delete, reference_count}`，DB 不变
- [ ] `uv run asset-hub type delete <id> --yes --json` 无引用时 exit 0；有引用时 exit 1 + `serve` 风格错误
- [ ] 详情页归还 dialog 含"归还地点"+"接收人"两可选字段；填写后流转记录卡片展示

## 已知 Gap

| 项 | 性质 | 处理 |
|---|---|---|
| Linux 真机烟测 | M2d release 时未真机验证；单测 mock 覆盖代码层 | Linux 环境就绪后补一轮 |
| 多代日志轮转 | 当前 1 代（log + log.1）；超过被冲掉过有用崩溃日志时启动 | 触发条件出现后小 PR |
| `serve doctor` 子命令 | 灵感来自 nilbuild/slim | M3 候选（与 SKILL.md 完善 + 部署文档同周期） |
| `serve build` 独立子命令 | 当前 build 藏在 start 里 | v2 候选（CI / Docker layer 缓存场景出现时） |
| `--workers N` flag | v1 默认单 worker | M3+ 业务驱动 |

## 回滚（如需）

```bash
git revert <m2d-merge-commit>
uv run alembic downgrade -1     # 回退 B2 的 return_location/receiver migration
cp data/asset_hub.db.<日期>.bak data/asset_hub.db
```

## 补充：alembic post_write_hooks ruff_format 不工作

如 M2c-3 release notes 已记录的——`alembic.ini` 中的 `[post_write_hooks] ruff_format` 不工作（ruff 没注册 console_scripts entrypoint）。新生成 migration 文件后**手工跑 `uv run ruff format <文件>`**。M2d 期间 Task 9 也踩过这个，留作 follow-up。
