# 部署指南

asset-hub v1.0 部署文档。首选 Windows 11 单机；Linux 真机烟测推 v1.1，macOS 仅用于开发。

## 环境要求

| 工具 | 版本 |
|---|---|
| Python | 3.12+ |
| Node.js | 20+ |
| uv | 0.4+ |
| pnpm | 9+ |
| OS | Windows 11（首选）/ Linux（v1.1 真机验证）/ macOS（开发用）|

## 安装步骤

```bash
git clone <repo-url>
cd asset-hub
uv sync                                     # 安装 Python 依赖
pnpm --dir frontend install                 # 安装前端依赖
cp .env.example .env                        # 配置（见下节）
uv run alembic upgrade head                 # 建数据库
uv run asset-hub serve doctor               # 验证环境（7 项检查全绿再继续）
uv run asset-hub serve start --mode prod    # 启动（单端口 :8000）
```

## 配置项（.env）

仅 4 个可配 env var，所有路径都派生自 `ASSET_HUB_DATA_DIR`：

| env var | 默认值 | 说明 |
|---|---|---|
| `ASSET_HUB_DATA_DIR` | `data` | 数据根目录；db / 附件 / pid / 日志全派生此处 |
| `ASSET_HUB_BACKEND_PORT` | `8000` | FastAPI 端口 |
| `ASSET_HUB_FRONTEND_PORT` | `5173` | Vite dev 端口（仅 dev 模式生效） |
| `ASSET_HUB_BACKEND_HOST` | _未设_ | 显式指定后端绑定地址；未设时 dev=127.0.0.1 / prod=0.0.0.0 |

**派生路径（不可单独配置，只能改 `ASSET_HUB_DATA_DIR`）：**

- 数据库：`<data_dir>/asset_hub.db`
- 附件：`<data_dir>/attachments/<yyyy>/<mm>/<sha256>.<ext>`
- pid 文件：`<data_dir>/pids/{backend,frontend}.pid`
- 日志：`<data_dir>/logs/{backend,frontend}.log`（`.1` 为上一会话）

> 注意：`ASSET_HUB_DATABASE_URL`、`ASSET_HUB_LOGS_DIR`、`ASSET_HUB_PIDS_DIR`、`ASSET_HUB_MODE` **不存在**——在 Settings 中均为派生属性，不接受 env var 覆盖。

## 数据维护

| 资源 | 路径 |
|---|---|
| 数据库 | `data/asset_hub.db`（SQLite 单文件） |
| 附件 | `data/attachments/<yyyy>/<mm>/<sha256>.<ext>` |
| 日志 | `data/logs/{backend,frontend}.log`（+ `.1` 上一会话） |
| pid | `data/pids/{backend,frontend}.pid` |

**备份建议**：每日一次 + 每次升级前务必备份。

```bash
# 停服后备份（先停，避免 WAL 文件不一致）
uv run asset-hub serve stop
cp data/asset_hub.db data/asset_hub.db.$(date +%Y%m%d).bak
tar czf attachments-$(date +%Y%m%d).tgz data/attachments/

# 还原
uv run asset-hub serve stop
cp data/asset_hub.db.<日期>.bak data/asset_hub.db
tar xzf attachments-<日期>.tgz
uv run asset-hub serve start --mode prod
```

## 升级

```bash
git pull
uv sync                                         # 同步 Python 依赖
pnpm --dir frontend install                     # 同步前端依赖
uv run alembic upgrade head                     # 运行新迁移
uv run asset-hub serve doctor                   # 验证升级后状态
uv run asset-hub serve restart --mode prod      # 重启服务
```

## 故障排查

### `serve start` 失败

先跑 doctor 定位：

```bash
uv run asset-hub serve doctor --json | jq '.data | {ok, issue_count, failing: [.checks[] | select(.ok==false)]}'
```

常见 fail code 及修复：

| fail code | 原因 | 修复 |
|---|---|---|
| `serve.uv_missing` | uv 未安装或版本过低 | 见 https://docs.astral.sh/uv/getting-started/installation/ |
| `serve.pnpm_missing` | pnpm 未安装 | `npm install -g pnpm@9` |
| `serve.python_version_low` | Python < 3.12 | 升级 Python |
| `serve.data_unwritable` | data dir 无写权限 | `mkdir -p data`；检查文件系统权限 |
| `serve.alembic_outdated` | 迁移未跑 | `uv run alembic upgrade head` |
| `serve.dist_missing` | 前端未构建 | `pnpm --dir frontend build` |
| `serve.port_occupied` | 端口被占 | `uv run asset-hub serve stop` 或加 `--port 8001` 覆盖 |

### pid 残留（进程僵尸）

`serve status` 显示 stale → 之前进程异常退出，pid 文件未清理。

```bash
uv run asset-hub serve stop   # 会清理 stale pid
uv run asset-hub serve start --mode prod
```

### 数据库 lock

报 `sqlite3.OperationalError: database is locked`，通常为 WAL 文件残留：

```bash
uv run asset-hub serve stop
rm -f data/asset_hub.db-shm data/asset_hub.db-wal
uv run asset-hub serve start --mode prod
```

### 查看日志

```bash
# 实时跟踪后端日志
uv run asset-hub serve logs --service backend --follow

# 查看最近 200 行
uv run asset-hub serve logs --service backend --lines 200

# 日志文件直接路径
# data/logs/backend.log（当前）/ data/logs/backend.log.1（上一会话）
# data/logs/frontend.log
```

## Windows 单机部署补充

### 安装 PowerShell 7+

```powershell
winget install --id Microsoft.PowerShell --source winget
```

### 配置数据目录（系统环境变量，可选）

```powershell
# 注意：setx 写入后需重新打开终端才生效
setx ASSET_HUB_DATA_DIR "C:\path\to\asset-hub-data"

# 或写入 .env 文件（推荐，不影响系统全局）
# ASSET_HUB_DATA_DIR=C:/path/to/asset-hub-data
```

### 开放防火墙端口

```powershell
# prod 模式只需 :8000
New-NetFirewallRule -DisplayName "asset-hub" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow

# dev 模式额外开 :5173
New-NetFirewallRule -DisplayName "asset-hub-dev" -Direction Inbound -Protocol TCP -LocalPort 5173 -Action Allow
```

### 强制杀进程（异常场景）

```powershell
# 方式一：通过 PID
taskkill /PID <pid> /F
# 方式二：PowerShell
Stop-Process -Id <pid> -Force
# 清理残留 pid 文件
Remove-Item data\pids\*.pid
```

### 注意事项

- **不要把 `data/` 目录放在云盘**（OneDrive / iCloud 等）：SQLite WAL 与云同步冲突会损坏数据库。
- Windows 路径分隔符在 `.env` 中建议用正斜杠（`/`）或双反斜杠（`\\`），避免转义问题。
- PowerShell 7（`pwsh`）与 Windows 内置终端（`cmd`）均可运行，但推荐使用 PowerShell 7。
