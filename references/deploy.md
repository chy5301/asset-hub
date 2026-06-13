# deploy reference

> 完整部署文档：[../docs/deployment.md](../docs/deployment.md)。
> 此文为 Agent 速查精简版——避免 progressive disclosure 时多查一个文件，关键命令直接落在此。详细的 .env 字段 / 升级手顺 / 环境要求详情留给 `../docs/deployment.md`。
>
> ⚠️ 与 `../docs/deployment.md` 同源约定（pointer 关系）——部署流程有变先改 deployment.md，再视需要同步此处速查表。

## 一句话速记

```bash
uv sync && pnpm --dir frontend install && uv run alembic upgrade head && uv run asset-hub serve doctor && uv run asset-hub serve start --mode prod
```

## serve doctor 检查项（7 项 prod / 8 项 dev）

| # | 检查项名称 | 失败 code | 修复命令 |
|---|---|---|---|
| 1 | `uv (>= 0.4)` | `serve.uv_missing` | 安装 uv：https://docs.astral.sh/uv/getting-started/installation/ |
| 2 | `pnpm (>= 9)` | `serve.pnpm_missing` | `npm install -g pnpm@9` |
| 3 | `Python (>= 3.12)` | `serve.python_version_low` | 升级 Python 到 3.12+ |
| 4 | `data dir writable` | `serve.data_unwritable` | `mkdir -p data`；检查文件系统权限 |
| 5 | `alembic head` | `serve.alembic_outdated` | `uv run alembic upgrade head` |
| 6 | `frontend/dist` | `serve.dist_missing` | `pnpm --dir frontend build` |
| 7 | `port :8000 free` | `serve.port_occupied` | `uv run asset-hub serve stop` 或 `--port 8001` 覆盖 |
| 8 | `port :5173 free`（仅 dev）| `serve.port_occupied` | 同上 |

```bash
# 运行 doctor 并自动解读（非零 issue_count 看 checks[]）
uv run asset-hub serve doctor --json | jq '.data | {ok, issue_count, failing: [.checks[] | select(.ok==false)]}'
```

## 故障排查速记

| 症状 | 关联 code | 修复 |
|---|---|---|
| `serve start` 卡住后超时 | `serve.health_probe_timeout` | 看 `data/logs/backend.log`；确认 alembic 已迁移（`uv run alembic upgrade head`） |
| PID stale / 进程僵尸 | — | `uv run asset-hub serve stop`，再重启 |
| `frontend/dist` 缺失 | `serve.dist_missing` | `pnpm --dir frontend build` |
| 端口被占 | `serve.port_occupied` | `uv run asset-hub serve stop` 或改 `--port` |
| `port_owner` 误报（外部进程）| `external_port_owner` | v2.2.1+ doctor 已自动识别 uv 父子链路；仍报时按 fix_hint 的 `lsof -i :<port>` / `Get-NetTCPConnection -LocalPort <port>` 排查真实占用进程 |
| SQLite database lock | WAL 残留 | 先 `serve stop`，再 `rm data/asset_hub.db-shm data/asset_hub.db-wal` |
| pnpm build 失败 | `serve.build_failed` | 检查 Node 版本 / `pnpm --dir frontend install` 后重试 |
| 无法杀进程 | `serve.kill_failed` | 手动 `taskkill /PID <pid> /F`（Windows）；PID 文件需手动删 `data/pids/*.pid` |

## 数据备份 / 还原

```bash
# 备份（先停服务）
uv run asset-hub serve stop
cp data/asset_hub.db data/asset_hub.db.<日期>.bak
tar czf attachments-<日期>.tgz data/attachments/

# 还原
uv run asset-hub serve stop
cp data/asset_hub.db.<日期>.bak data/asset_hub.db
tar xzf attachments-<日期>.tgz
uv run asset-hub serve start --mode prod
```

## Windows 单机部署要点

- PowerShell 7+ (`pwsh`) 推荐；内置终端均可
- 配置数据目录：`setx ASSET_HUB_DATA_DIR "C:\path\to\data"`（重新打开终端生效）
- 防火墙允许 `:8000`（prod 单端口）/ `:5173`（dev 额外端口）
- 杀进程用 `taskkill /PID <pid> /F` 或 `Stop-Process -Id <pid> -Force`
- 详见 `../docs/deployment.md`

## 桌面便携版（人类 GUI）

面向人类用户免安装发布形态：PyInstaller 打包单文件 exe + pywebview 内嵌 WebView2。

### 构建

```bash
uv sync --extra desktop --group packaging  # 安装 pywebview + pyinstaller
pnpm --dir frontend build         # 产出 frontend/dist
uv run pyinstaller packaging/asset_hub.spec   # 打包 → dist/asset-hub.exe
```

产物目录：`dist/asset-hub/`（含 exe、`_internal/`、`frontend/` 静态资源）。CI 自动归档为 `asset-hub-desktop-win64.zip`。

### 数据落点

- 默认：exe 同级 `./data`（即 `dist/asset-hub/data/`）
- 若检测到只读位置（`Program Files` 等），启动时弹框提示用户移动整个文件夹到可写目录
- 逃生口：`.env` 文件设 `ASSET_HUB_DATA_DIR=D:\my-data` 覆盖默认路径

### 升级

1. 下载新版本 zip，解压覆盖整个文件夹（`data/` 会保留）
2. 首次启动自动执行 `alembic upgrade head`，无需手动迁移

### 前置条件

- Windows 10+ 自带 WebView2 Runtime；若缺失（极少数精简系统），首次启动会提示下载安装
- 不需要 Python / Node / uv / pnpm 等开发工具链
