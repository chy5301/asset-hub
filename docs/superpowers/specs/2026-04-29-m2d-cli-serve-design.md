# M2d · CLI 接管 web 服务生命周期 设计文档

- **日期**：2026-04-29
- **里程碑**：M2d（独立子里程碑，承接 M2c-3，先于 M2c-4 / M3）
- **状态**：初稿，待实施
- **作者**：conghaoyangbobby@gmail.com（与 Claude 协同 brainstorm）
- **承接**：[`2026-04-15-asset-hub-design.md`](./2026-04-15-asset-hub-design.md) §14.9 / §14.2 / §14.10 + [`../followup-allocation.md`](../followup-allocation.md) M2d 范围拆分

## 0. 导读

本文档是 **M2d 独立子里程碑** 的 spec。M2d 是 §14.9 草案描述的 "CLI 接管 web 服务生命周期"——把 dev/prod 期的服务起停、健康检查、日志收集统一收到 `asset-hub serve` 子命令下；同时打包 4 项 M2c-3 烟测 / simplify 二轮 follow-up 作为附录交付。

| 子里程碑 | 范围 | spec |
| --- | --- | --- |
| M2c-3 · 表单 + 附件上传 + 状态切换 + 后端字段补齐 | RHF/Zod + acquired_at + asset_code 反向纠偏 | [✓ 已交付](./2026-04-26-m2c3-form-attachments-actions-design.md) |
| **M2d · CLI 接管 web 服务生命周期**（本文） | `asset-hub serve start/stop/status/restart/logs` + 4 项 backend gaps | 本文 |
| M2c-4 · 类型管理 UI | AssetType CRUD + 结构化 custom_fields builder | 未写 |

**里程碑顺序**：M2d → M2c-4 → M3 → M4。M2d 与 M2c-4 顺序在 M2c-3 brainstorm 阶段已拍：先 M2d（daily dev 体验改善每天兑现）。

**Timebox**：约一周。serve 主线估半天 brainstorm + 一两天实现 + 一天烟测；4 项 backend gaps 各 0.5–1 天独立 PR。

## 1. 目标与非目标

### 1.1 目标

1. **统一服务生命周期入口**：dev / prod 模式下起停服务都走 `asset-hub serve` 子命令；现有 `scripts/dev.sh` 删除
2. **解决 Windows 上 Ctrl+C 杀不干净的痛点**：psutil 进程树清理（uvicorn `--reload` watcher/worker 分离 + pnpm → node 链路）
3. **后台运行 + 状态可查**：start 立即返回 + status / stop / logs 在任何终端都可用
4. **健康检查端点上线**：`GET /api/healthz`，供 start 探测、status HTTP 探测、未来 doctor 子命令复用
5. **配置走 pydantic-settings**：端口 / host 通过环境变量 / `.env` / CLI 参数三层覆盖
6. **打包 4 项 backend gaps**：B2（归还记录地点 + 接收人）、B3（AssetType 删除）、I1+I2（后端 validation 补全 + FieldType Enum）

### 1.2 非目标

- ❌ **不做 doctor 诊断子命令**（M3 候选；登记 follow-up）
- ❌ **不做 SKILL.md 完善**（M3 主线项）
- ❌ **不做反代 / HTTPS / 域名管理**（FastAPI StaticFiles 单端口对外已搞定）
- ❌ **不做内网穿透 / 远程访问**
- ❌ **不做多代日志轮转**（v1 单用户场景，1 代足够；登记 follow-up）
- ❌ **不做 multi-worker 协调**（v1 prod 默认单 worker；plan 阶段评估是否加 `--workers` flag）
- ❌ **不做 People 实体化（§14.4）**（与 B2 的"接收人"字段相关，但本身是独立 M5 大里程碑）
- ❌ **不做 §14.6 状态切换 audit 化**（M3+ 候选；smoketest B1 由 §14.6 同周期吸收）

### 1.3 主 spec 钩子状态

- §14.9 CLI 接管 web 服务生命周期 → 本文实施
- §14.2 归还时可改 location / holder → 本文 §A.2（B2）实施
- §14.10 acquired_at → 已在 M2c-3 落地
- §14.5 状态切换 web 入口 → 已在 M2c-3 落地
- §14.6 audit 化 / smoketest B1 → M3+ 联合处理（不在本文）
- §14.3 IDLE 资产显式 location 维护 → 残值待 M3（B2 落地后 §14.3 缩小为"独立修改位置 action"）

## 2. 系统位置与组件分解

### 2.1 文件树（M2d 新增）

```
src/asset_hub/
├── api/
│   └── routers/
│       └── health.py          # 新增：极简 liveness 端点
├── cli/
│   ├── main.py                 # 改：注册 serve 子命令
│   └── serve/                  # 新增子包
│       ├── __init__.py
│       ├── cmd.py              # Typer 子命令注册
│       ├── lifecycle.py        # start/stop/restart/status/logs 主流程协调
│       ├── pid.py              # PID 文件读写 + state 判定
│       ├── proc.py             # Popen detach + psutil 进程树管理 + 端口检查
│       ├── probe.py            # 渐进退避健康轮询 + status HTTP 探测
│       ├── logs.py             # tail (一次性 + follow) + 启动次数轮转
│       └── output.py           # 表格 / JSON 信封渲染
└── config.py                   # 改：扩 backend_port / frontend_port / backend_host

data/                            # 运行期产物（.gitignore）
├── pids/
│   ├── backend.pid
│   └── frontend.pid (dev only)
└── logs/
    ├── backend.log              # 当前会话
    ├── backend.log.1            # 上一会话归档
    ├── frontend.log (dev only)
    └── frontend.log.1 (dev only)

scripts/
└── dev.sh                       # 删除：被 serve 取代
```

### 2.2 组件职责

| 组件 | 职责 | 主要依赖 |
|---|---|---|
| `serve/cmd.py` | Typer 子命令注册；解析 args 调 lifecycle | typer |
| `serve/lifecycle.py` | 5 个动作的协调主流程；调度 pid / proc / probe / logs；exit code 决策 | pid + proc + probe + logs |
| `serve/pid.py` | `read_pid_state(service)`；写 / 解析 PID 文件；stale 自动清理；mode 元数据读写 | psutil |
| `serve/proc.py` | Popen 跨平台 detach；进程树 SIGTERM → SIGKILL；端口占用检查；构建 cmdline 校验关键词 | psutil + subprocess |
| `serve/probe.py` | start 渐进退避轮询 `/api/healthz`；status 单次 HTTP 探测 | urllib.request |
| `serve/logs.py` | tail N 行（一次性）+ follow 模式（自实现 tail -f）；启动次数日志轮转 | stdlib |
| `serve/output.py` | 表格渲染 + JSON 信封；stderr 文案锚点 | rich（已有） |
| `api/routers/health.py` | `GET /api/healthz` → 200 + `{"status": "ok"}` | fastapi |
| `config.py::Settings` | 扩 `backend_port` / `frontend_port` / `backend_host` 字段；加 `env_file=".env"` | pydantic-settings |

### 2.3 单元边界设计原则

- **lifecycle 是协调者，不做底层操作**：所有 IO（PID 读写、进程启动、HTTP 探测、文件读取）都委托给 pid / proc / probe / logs；这让 lifecycle 的测试只需 mock 这 4 个模块
- **pid 与 proc 严格分离**：pid 只管 "PID 文件状态机"（none / running / stale）；proc 只管 "OS 进程操作"。它们的合作由 lifecycle 协调
- **output 集中所有面向用户/Agent 的渲染**：避免 lifecycle 里散落 print；plain text + json 两种渲染共用 lifecycle 输出的同一组数据结构（`StartResult` / `StatusReport` / `StopResult` 等 dataclass）
- **跨平台分支只在 proc.py 内部**：其他模块不直接 import `sys.platform`

### 2.4 进程拓扑

**dev 模式**：
```
                    ┌── uvicorn (PID=A, --reload)
                    │      ├─ watcher subprocess
                    │      └─ worker subprocess
asset-hub serve     │
   start --mode dev ────► detached → exit 0
                    │
                    └── pnpm dev (PID=B)
                           └─ node (Vite) subprocess
                                  └─ esbuild workers
```

**prod 模式**：
```
asset-hub serve start
   --mode prod  ──► [pnpm build]（如需）──► uvicorn (PID=A) ──► detached → exit 0
                                                 └─ FastAPI（含 StaticFiles 托管 dist）
```

CLI 进程在 detach 后立即退出；运行期没有"主控进程"，状态全在磁盘（`data/pids/*.pid` + `data/logs/*.log`）。

## 3. CLI 契约

### 3.1 全局规约

1. `--help` 由 Typer 自动生成；docstring 写中文短描述
2. `--json` 信封遵循全局 `cli/envelope.py` 形态；`error.code` 命名空间为 `serve.*`
3. **stderr 文案首词**为可识别状态词（`already running` / `port` / `cannot infer` / `frontend build failed` 等），grep / Agent parse 友好
4. 参数错误（拼错 mode / 非法 port）由 Typer 自动 exit 2，CLI 不手写
5. **stdout vs stderr 分工**：成功输出 → stdout；失败 / 警告 / stale 提示 → stderr（与现有 CLI 一致）
6. `--json` 模式下抑制图标（✓/!/✗/-），保持纯结构化 JSON

### 3.2 `asset-hub serve start`

```
asset-hub serve start [OPTIONS]

Options:
  --mode [dev|prod]                     启动模式，默认 prod
  --skip-build                           prod 模式下跳过自动 build（dist 缺失则报错）
  --port INTEGER                         覆盖后端端口（默认从 Settings 读，初值 8000）
  --frontend-port INTEGER                覆盖前端端口（仅 dev；默认 5173）
  --host TEXT                            覆盖后端 host（默认按 mode：dev=127.0.0.1，prod=0.0.0.0）
  --json                                 输出 JSON 信封
  --help                                 显示帮助
```

人类输出示例（成功，prod 模式）：
```
✓ Backend started     pid=12345  http://127.0.0.1:8000  mode=prod
  data/logs/backend.log
```

人类输出示例（成功，dev 模式）：
```
✓ Backend started     pid=12345  http://127.0.0.1:8000  mode=dev
✓ Frontend started    pid=12346  http://127.0.0.1:5173
  Logs: data/logs/{backend,frontend}.log
```

`--json` 输出（成功）：
```json
{
  "success": true,
  "data": {
    "mode": "prod",
    "backend": {"pid": 12345, "port": 8000, "host": "127.0.0.1", "log": "data/logs/backend.log"},
    "frontend": null
  },
  "metadata": {"took_ms": 4231, "build_ran": true},
  "error": null
}
```

`--json` 输出（失败示例）：
```json
{
  "success": false,
  "data": null,
  "metadata": {"took_ms": 12},
  "error": {"code": "serve.port_occupied", "message": "port 8000 is in use by external process (pid=98765)"}
}
```

`error.code` 取值（plan 阶段定全集）：
- `serve.already_running`
- `serve.port_occupied`
- `serve.build_failed`
- `serve.dist_missing`
- `serve.health_probe_timeout`
- `serve.frontend_failed_to_start`
- `serve.data_unwritable`

### 3.3 `asset-hub serve stop`

```
asset-hub serve stop [OPTIONS]

Options:
  --json
  --help
```

无业务参数（stop 永远停"当前在跑的全部"）。

人类输出（正常）：
```
✓ Backend stopped     pid=12345
✓ Frontend stopped    pid=12346  (mode=dev)
```

人类输出（未运行）：
```
- Not running
```

人类输出（stale 自动清理）：
```
! Stale PID files cleaned (backend pid=12345 not alive)
- Not running
```

人类输出（SIGKILL 兜底）：
```
! Backend stopped via SIGKILL  pid=12345  (SIGTERM timeout 5s)
```

### 3.4 `asset-hub serve status`

```
asset-hub serve status [OPTIONS]

Options:
  --json
  --no-probe              跳过 HTTP 健康探测（仅查进程活性）
  --help
```

人类输出（运行中）：
```
SERVICE   STATUS    PID    PORT  MODE  UPTIME    HEALTHY
backend   running   12345  8000  prod  2h 13m    ✓
frontend  -         -      -     -     -         -
```

人类输出（dev 模式 + 后端健康但前端 hung）：
```
SERVICE   STATUS    PID    PORT  MODE  UPTIME    HEALTHY
backend   running   12345  8000  dev   18m       ✓
frontend  running   12346  5173  dev   18m       ✗ (port not responding)
```

`--no-probe` 借鉴自 slim doctor 思路：不发 HTTP 用纯进程查询，避免 status 因网络/防火墙慢。默认仍发探测。

### 3.5 `asset-hub serve restart`

```
asset-hub serve restart [OPTIONS]

Options:
  --mode [dev|prod]      显式指定模式（默认沿用 PID 文件里的 mode）
  --json
  --help
  # 透传 start 选项：
  --skip-build / --port / --frontend-port / --host
```

人类输出：
```
✓ Backend stopped     pid=12345  (was mode=prod)
✓ Backend started     pid=12347  (mode=prod)
```

未运行 → 直接 start：
```
- Not running, starting fresh
✓ Backend started     pid=12347  (mode=prod)
```

无法推断 mode：
```
✗ Cannot infer mode from PID files; specify --mode dev|prod
```
exit 1。

### 3.6 `asset-hub serve logs`

```
asset-hub serve logs [OPTIONS]

Options:
  --service [backend|frontend|all]   日志源，默认 backend
  --lines INTEGER                    一次性 tail 行数，默认 200
  --follow                           持续 tail（Ctrl+C 终止）
  --json                             仅一次性模式有意义；--follow 时忽略
  --help
```

人类输出（all，prefix 区分）：
```
[backend]  INFO:     127.0.0.1:54321 - "GET /api/assets HTTP/1.1" 200 OK
[frontend] VITE v6.0.0  ready in 234 ms
```

人类输出（文件不存在）：
```
- No logs available for frontend (not running in dev mode?)
```
exit 0（read-only 操作不当 error）。

`--follow` + `--json`：抑制 `--json`（流式输出，信封语义不成立），打印 warning 到 stderr 后走人类输出。

### 3.7 退出码矩阵

仅使用全局规约的 0 / 1 / 2 三个码（3 资源不存在 / 10 dry-run 在 serve 上下文用不到，不引入新码）。

| 命令 | 场景 | exit |
|---|---|:-:|
| start | 启动成功 + 健康探测通过 | **0** |
| start | 已运行 / 端口占用 / build 失败 / dist 缺失 / 健康探测超时 / data 不可写 | **1** |
| start | 参数非法（Typer 自动） | **2** |
| stop | 干净停止 + PID 清理 | **0** |
| stop | 服务未运行（PID 不存在或全 stale） | **0** |
| stop | SIGTERM 后存活，SIGKILL 兜底成功 | **0** |
| stop | SIGKILL 后仍存活 | **1** |
| stop | PID 复用（cmdline 不匹配） | **0**（清 PID 不杀） |
| status | 任何状态（running / stopped / unhealthy） | **0** |
| restart | 全流程成功 / 服务未运行后 fresh start | **0** |
| restart | stop 失败 / start 失败 / 无法推断 mode | **1** |
| logs | 文件存在且读取成功 / 文件不存在 / Ctrl+C 终止 | **0** |
| logs | 参数非法 | **2** |

**关键不变量**：
1. 幂等命令（stop / status / logs）对"无服务运行"返回 0
2. 状态变更命令（start / restart）对"动作失败"返回 1
3. `--json` 模式 `success: true` ↔ exit 0；`success: false` ↔ exit 1

## 4. 配置层

### 4.1 现状

`src/asset_hub/config.py::Settings` 当前仅有 `data_dir` 字段；通过 `pydantic-settings` 的 `BaseSettings` + `env_prefix="ASSET_HUB_"` 自动从环境变量读取。Settings 当前实际消费者只有 `alembic/env.py`。

### 4.2 M2d 扩字段

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ASSET_HUB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Path("data")

    # M2d 新增
    backend_port: int = 8000
    frontend_port: int = 5173
    backend_host: str | None = None  # None = 按 mode 自动选

    @property
    def db_url(self) -> str: ...
    @property
    def attachments_dir(self) -> Path: ...

    # M2d 新增
    @property
    def pids_dir(self) -> Path:
        return self.data_dir / "pids"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    def resolve_backend_host(self, mode: Literal["dev", "prod"]) -> str:
        if self.backend_host is not None:
            return self.backend_host
        return "127.0.0.1" if mode == "dev" else "0.0.0.0"
```

字段命名规则：环境变量 = `ASSET_HUB_` + 字段名大写。

`env_file=".env"` 是新增项（之前 Settings 没读 `.env`）；`extra="ignore"` 容错（.env 中无关字段不会报错）。

### 4.3 优先级链

```
高 ────────────────────────────────────────────────► 低
CLI 参数 (--port, --frontend-port, --host)
    ↓ 未传
环境变量 (ASSET_HUB_BACKEND_PORT 等)
    ↓ 未设
.env 文件
    ↓ 缺失
代码默认值 (8000 / 5173 / mode 派生)
```

实现：CLI 实例化 `Settings()` 时 pydantic-settings 自动按 env > .env > default 解析；CLI 参数（`--port` 等）由 lifecycle 在 `Settings()` 之上覆盖。每次子命令调用都新建 `Settings()` 实例，无缓存、无 monkey-patch。

### 4.4 `.env.example` 模板

仓库根加 `.env.example`（M2d 同 PR 提交，`.env` 本身 git ignore）：

```
# .env.example — 复制为 .env 后按需修改
# 所有字段都可省略，省略则使用代码默认值

# ASSET_HUB_DATA_DIR=/var/asset-hub
# ASSET_HUB_BACKEND_PORT=8000
# ASSET_HUB_FRONTEND_PORT=5173
# ASSET_HUB_BACKEND_HOST=
```

### 4.5 dev / prod 配置机制不区分

两个模式统一走 "环境变量 + `.env` + CLI 参数"。pydantic-settings 是项目级机制，为 dev 跳过这层会破坏一致性。

## 5. 状态层

### 5.1 PID 文件格式

```
12345
mode=prod
started_at=2026-04-29T10:23:14Z
```

- 第 1 行（必填）：进程 PID
- 第 2 行（推荐）：`mode=dev|prod` 元数据
- 第 3 行（可选）：ISO 8601 UTC 启动时间，供 status 显示 uptime
- 解析容错：第 2 / 3 行缺失时 fallback（mode 推断走 "是否存在 frontend.pid"）

不用 JSON / TOML：3 行键值对纯文本，零依赖、人眼可读、`cat backend.pid` 直接给答案。

### 5.2 `read_pid_state` 状态机

```python
@dataclass
class PidState:
    service: Literal["backend", "frontend"]
    file_exists: bool
    pid: int | None
    mode: Literal["dev", "prod"] | None
    started_at: datetime | None
    process_alive: bool        # psutil.pid_exists & status != zombie
    cmdline_match: bool         # cmdline 含预期关键词
    status: Literal["none", "running", "stale"]
```

**状态派生**：
- `file_exists=False` → none
- `file_exists=True & process_alive=True & cmdline_match=True` → running
- 其他（PID 不在 / zombie / cmdline 不匹配 / 文件损坏） → stale

**cmdline 匹配关键词**（`serve/proc.py` 常量）：
- backend: cmdline 同时含 `uvicorn` + `asset_hub.api.app`
- frontend: cmdline 同时含 `pnpm` + `dev`（plan 阶段实测各平台 cmdline 形态再确定 token）

匹配设计原则：**两个 token 同时命中**，避免误判系统中其他 uvicorn 进程。

### 5.3 状态自动清理矩阵

| 命令 | 遇到 stale | 处理 |
|---|---|---|
| start | 自动清理 PID 文件，进入正常 start 流程 | 不打扰用户 |
| stop | 自动清理 PID 文件 + 输出 "stale PID files cleaned" + exit 0 | 幂等 |
| status | 显示 "not running (stale PID detected)"，**不**清理 | 仅诊断不动状态 |
| restart | 视同未运行，跳过 stop 直接 start | 与 stop 一致 |

→ status 故意保留 stale 不清理，让用户能反复看到诊断信息。

### 5.4 PID 复用防御

任何"按 PID 操作"都需要 cmdline 校验：
- `psutil.pid_exists()` 不够——PID 可能被复用到其他进程
- `Process.cmdline()` 必须命中预期 token，否则视为 stale（不杀，仅清 PID 文件）

### 5.5 日志文件

**位置**：
- `data/logs/backend.log`（当前会话）
- `data/logs/backend.log.1`（上一会话归档；语义在 spec/SKILL.md 文档化）
- frontend 同理（仅 dev 模式）

**轮转策略（启动次数轮转，1 代）**：

```
serve start 流程（写 PID 文件之前）:
  1. 若 backend.log 存在:
       移除 backend.log.1（如存在）
       重命名 backend.log → backend.log.1
  2. 创建空 backend.log
  3. 用 open('data/logs/backend.log', 'a') 作为 Popen stdout
```

**重定向方式**：
```python
log_file = open(settings.logs_dir / "backend.log", "a")
backend = subprocess.Popen(
    ["uv", "run", "uvicorn", ...],
    stdout=log_file,
    stderr=subprocess.STDOUT,  # 合并到 stdout
    cwd=...,
    start_new_session=True,           # Unix
    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,  # Windows
    close_fds=True,
)
```

uvicorn / pnpm 的原生日志格式原样落盘，CLI 这层不包 logging.Handler。

**为什么不做尺寸 / 时间轮转**：控制权在子进程，CLI 只能在 Popen 启动时刻轮转；启动次数轮转能解决 95% 的"上次崩溃日志覆盖"问题；扩多代登记 follow-up（触发条件：实际使用中 1 代被冲掉过有用的崩溃日志）。

### 5.6 tail 实现

**一次性模式**：SEEK_END + 估算回退 + splitlines。

**follow 模式**：seek 到末尾循环 `readline + sleep(0.1)`，遇 EOF 不退出；Ctrl+C → KeyboardInterrupt → exit 0。**不**做 nginx-style "detect rotation 跳新文件"——用户在 follow 时若另开终端 restart，会停在旧文件 EOF 直到 Ctrl+C 重进。

### 5.7 目录懒创建 + 写权限预检

CLI 在写 PID / 日志文件之前才 `mkdir(parents=True, exist_ok=True)`，不强制 init 命令。data 目录不可写时 start 前置预检失败 → exit 1, error="serve.data_unwritable"。

### 5.8 不变量

1. **PID 文件不存在 = 服务未运行**（OS 重启后状态自然为 not running）
2. **PID 文件 = 唯一权威**：任何命令决策不依赖内存状态，每次新建 `Settings()` + `read_pid_state()` 读磁盘
3. **stale 自动恢复**：start / stop / restart 三个状态变更命令遇 stale 自动清理
4. **log 文件保留**：stale 清理只删 PID 文件，log 文件保留供查看上次崩溃
5. **PID 复用防御**：cmdline 校验缺一不可

## 6. 关键流程

### 6.1 `serve start` 完整流程

```
INPUT: mode (default prod), --skip-build, --port, --frontend-port, --host

Phase 0 · 前置检查
  1. 加载 Settings (env + .env + 默认值)
  2. 解析最终参数 (CLI > Settings > 默认)
  3. data_dir / pids_dir / logs_dir 写权限预检
     └ 失败 → exit 1, error="serve.data_unwritable"
  4. read_pid_state("backend") + read_pid_state("frontend")
     ├─ 任一 status=running → exit 1, error="serve.already_running"
     ├─ 任一 stale → 清理 PID 文件，进入下一步
  5. 端口占用预检 (psutil.net_connections)
     └ 占用 → exit 1, error="serve.port_occupied"

Phase 1 · 构建（仅 prod 模式）
  6. mode == "prod":
     ├─ frontend/dist/index.html 存在 → 跳过 build
     ├─ 不存在 + --skip-build → exit 1, error="serve.dist_missing"
     ├─ 不存在 + 默认 → 调 pnpm build (stdout 透传)
        ├─ build 失败 → exit 1, error="serve.build_failed"
        └─ build 成功 → 进入下一步

Phase 2 · 日志轮转
  7. logs_dir/backend.log 存在 → 移除 .log.1（如有）→ rename .log → .log.1
  8. dev 模式同样处理 frontend.log

Phase 3 · 启动子进程
  9. Popen backend (uvicorn, stdout/stderr → backend.log, detached)
 10. 写 backend.pid (pid + mode + started_at)
 11. dev 模式:
     ├─ Popen frontend (pnpm dev, stdout/stderr → frontend.log, detached)
     └─ 写 frontend.pid

Phase 4 · 健康探测
 12. 渐进退避循环 GET /api/healthz
     SLEEP_INTERVALS = [0.2, 0.5, 1.0, 1.0, 2.0, 2.0, 3.0]  # 累计 ~10s
     ├─ 任一次返回 200 → 进入 Phase 5
     └─ 全部失败 → 进入 Phase 4-rollback

  Phase 4-rollback:
     a. SIGTERM backend 进程树
     b. dev 模式: SIGTERM frontend 进程树
     c. 5s 后存活 → SIGKILL
     d. 删 backend.pid + frontend.pid (如有)
     e. exit 1, error="serve.health_probe_timeout"

 13. dev 模式额外探测 frontend (GET http://127.0.0.1:{frontend_port}/, 200/304/302)
     └ 失败 → 同 4-rollback, error="serve.frontend_failed_to_start"

Phase 5 · 输出
 14. 渲染 StartResult
 15. exit 0
```

**关键不变量**：
- Phase 4 失败必须回滚 Phase 3 已起的子进程；不允许"半启动"残留
- Phase 1 失败不写 PID 文件、不轮转日志
- Phase 3 写 PID 文件后，Phase 4 失败必须回滚 PID 文件

### 6.2 `serve stop` 流程

```
1. read_pid_state("backend"), read_pid_state("frontend")
2. 全 status=none → 输出 "not running" + exit 0
3. 任一 status=stale → 清理对应 PID 文件 + 输出 "stale PID files cleaned"
4. 对每个 status=running 的 service:
   a. proc = psutil.Process(pid)
   b. children = proc.children(recursive=True)
   c. 整树 SIGTERM (proc + children)
   d. wait 5s
   e. 仍存活 → 整树 SIGKILL
   f. 仍存活 → exit 1, error="serve.kill_failed", PID 文件保留
   g. 全 dead → 删 PID 文件
5. 输出 StopResult + exit 0
```

幂等保证：连续两次 stop 第二次输出 "not running" + exit 0。

### 6.3 `serve restart` 流程

```
1. read_pid_state("backend") → infer current_mode:
   a. PID 文件第二行 mode=xxx 优先
   b. fallback: frontend.pid 存在 → dev, 否则 → prod
   c. PID 文件不存在 → current_mode = None

2. target_mode 决策:
   ├─ --mode 显式传入 → target_mode = 显式值
   ├─ current_mode 推断成功 → target_mode = current_mode
   └─ 全推断失败 → exit 1, error="serve.mode_required"

3. 调 stop 流程 (允许 not running)
4. 调 start 流程 (--mode target_mode + 透传其他 flags)
5. exit code 跟随 start 流程
```

### 6.4 健康探测

**端点**：`GET /api/healthz` → 200 + `{"status": "ok"}`

**实现位置**：`src/asset_hub/api/routers/health.py`

```python
from fastapi import APIRouter
router = APIRouter(prefix="/api", tags=["health"])

@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

**探测算法**（`serve/probe.py`）：

```python
SLEEP_INTERVALS = [0.2, 0.5, 1.0, 1.0, 2.0, 2.0, 3.0]  # 累计 ≈ 9.7s
PROBE_TIMEOUT_PER_CALL = 1.0

def probe_until_ready(url: str) -> ProbeResult:
    for interval in SLEEP_INTERVALS:
        time.sleep(interval)
        try:
            with urllib.request.urlopen(url, timeout=PROBE_TIMEOUT_PER_CALL) as r:
                if r.status == 200:
                    return ProbeResult.ok()
        except (URLError, ConnectionRefusedError, socket.timeout):
            continue
    return ProbeResult.timeout()
```

**status 命令的探测**：单次 GET，2s 超时；200 → healthy，其他 → unhealthy。不重试。

**前端探测（dev 模式）**：GET `http://127.0.0.1:{frontend_port}/` 接受 200/304/302（Vite dev server 行为）。具体退避区间 plan 阶段实测后定。

**stdlib `urllib.request`，不引入 httpx**：M2d 已新增 psutil 一个依赖，再加 httpx 不必要。

### 6.5 跨平台 detach 形态

唯一 platform 分支处：`serve/proc.py::start_detached(cmd, stdout_fd) -> int`，其他模块不感知。

**Unix**：
```python
subprocess.Popen(cmd, ..., start_new_session=True)
```

**Windows**：
```python
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
subprocess.Popen(cmd, ..., creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP, close_fds=True)
```

### 6.6 跨平台 kill_tree（psutil 双平台一致）

```python
def kill_tree(pid: int, timeout: float = 5.0) -> KillMethod:
    proc = psutil.Process(pid)
    children = proc.children(recursive=True)
    targets = [proc] + children
    for p in targets:
        try: p.terminate()
        except psutil.NoSuchProcess: pass
    gone, alive = psutil.wait_procs(targets, timeout=timeout)
    if not alive:
        return KillMethod.SIGTERM
    for p in alive:
        try: p.kill()
        except psutil.NoSuchProcess: pass
    gone2, alive2 = psutil.wait_procs(alive, timeout=2.0)
    if alive2:
        raise KillFailedError(alive2)
    return KillMethod.SIGKILL
```

psutil 把 `terminate()` / `kill()` 在 Windows 上映射到 TerminateProcess soft / force，CLI 无需写 platform 分支。

### 6.7 边界场景汇总

| 场景 | 检测点 | 处理 |
|---|---|---|
| OS 重启后跑 start | Phase 0 stale | 自动清理 PID，正常 start |
| 用户手工 kill backend，PID 残留 | Phase 0 stale | 同上 |
| start 期间 Ctrl+C | CLI 进程被中断 | 已起子进程独立运行；下次 start 视为 stale 自愈 |
| backend 启动后 5s 内 hung | Phase 4 探测超时 | 回滚（kill + 删 PID）→ exit 1 |
| dev 模式后端起来但 5173 被占 | Phase 0 端口预检 | exit 1，frontend.pid 未写 |
| logs --follow 跑着时 restart | follow 在旧 fd 继续读 | 旧 fd 读到 EOF 不退出；用户 Ctrl+C 重进 |
| psutil 拒绝访问其他用户进程 | kill_tree 抛 AccessDenied | 当前用户启动的进程有权限；理论不出现 |

## 7. 测试策略

### 7.1 测试分层

```
tests/
├── unit/
│   ├── test_pid_state.py        # read_pid_state 状态矩阵
│   ├── test_pid_io.py            # PID 文件解析容错
│   ├── test_proc_kill_tree.py    # kill_tree (mock psutil)
│   ├── test_proc_detach.py       # start_detached 跨平台 flag
│   ├── test_health_probe.py      # 渐进退避 + urllib mock
│   ├── test_logs_tail.py          # 一次性 tail
│   ├── test_logs_follow.py        # follow 循环
│   ├── test_settings_serve.py    # 优先级链
│   └── test_serve_output.py      # 表格 + JSON 信封
├── cli/
│   ├── test_serve_start.py       # CliRunner + Popen mock (假后端进程)
│   ├── test_serve_stop.py
│   ├── test_serve_status.py
│   ├── test_serve_restart.py
│   └── test_serve_logs.py
└── api/
    └── test_health.py            # /api/healthz 端点
```

### 7.2 关键决策：不真起 uvicorn

CLI 集成测试不打通"真起 uvicorn"端到端。改用 `subprocess.Popen` 起 `python -c "import time; time.sleep(99)"` 假进程作 backend 替身。理由：
- CI 起 8000 端口冲突 / 残留进程
- 健康端点轮询带来 flaky
- 跨 OS runner 行为差异放大

### 7.3 Mock 边界

| 模块 | mock 对象 | 不 mock 的部分 |
|---|---|---|
| pid_state | psutil.Process / pid_exists | 真实文件 IO（tmp_path） |
| proc | psutil.Process / subprocess.Popen | — |
| probe | urllib.request.urlopen + time.sleep | — |
| logs | 文件 IO 用真文件（tmp_path） | — |
| start/stop CLI | psutil + subprocess（用假进程替身） | PID 文件 IO |

原则：**文件 IO 用真文件**（写得出来、看得见）；**进程 / 网络 IO 全 mock**。

### 7.4 跨平台单测

用 `sys.platform` 分支 + `pytest.mark.skipif` 各自覆盖 Windows-specific / Unix-specific 路径。CI 当前只跑 Linux runner（项目当前形态），但单测 mock 双平台路径，保证 Windows 上手工烟测时代码真能跑。

### 7.5 烟测 checklist

```markdown
## M2d 烟测 checklist

### 共通
- [ ] uv sync 安装无报错（含新增 psutil）
- [ ] uv run pytest 全绿
- [ ] uv run ruff check . 无报错
- [ ] pnpm --dir frontend lint / test 全绿
- [ ] pnpm --dir frontend gen:api 拉新 schema 含 /api/healthz

### Windows + dev 模式（必跑）
- [ ] asset-hub serve start 默认 prod
- [ ] asset-hub serve start --mode dev 起后端 + 前端
- [ ] 浏览器 :5173 看到前端，调 /api/assets 走代理通
- [ ] asset-hub serve status 表格输出含 backend + frontend 两行
- [ ] asset-hub serve logs --follow 看到 access log
- [ ] Ctrl+C 终止 logs --follow → exit 0
- [ ] taskkill /PID xxx /F 后 status 显示 stale
- [ ] asset-hub serve stop 干净杀进程树（任务管理器无残留 uvicorn / node / pnpm）
- [ ] 关闭 cmd 终端后 status 仍能查到（detach 验证）
- [ ] asset-hub serve restart 切换模式

### Windows + prod 模式（必跑）
- [ ] frontend/dist 不存在时 start 自动 build
- [ ] frontend/dist 存在时 start 跳过 build
- [ ] --skip-build + dist 不存在 → exit 1
- [ ] :8000 单端口对外访问前端 + API

### Linux 烟测（待补，跨平台覆盖延后）
- [ ] 当前阶段 Linux 路径仅靠单测覆盖（test_proc_detach 用 mock 验证 start_new_session）
- [ ] 真机烟测延后至 Linux 部署环境就绪后单独执行；M2d release 不阻塞
- [ ] 已知风险登记：psutil + start_new_session detach 行为虽业界稳定，但未在本项目真机验证
```

### 7.6 测试覆盖率目标

不设具体百分比；**关键路径必须有测**：
- read_pid_state 全 5 种状态分支
- start 9 种终止路径每条至少 1 case
- stop 5 种路径每条至少 1 case
- 退避循环超时与首次成功两端
- mode 推断 4 种路径

非关键路径（output 渲染微调、help 文案）允许无测。

## 8. M2d 完成判据

```
M2d 视为完成需要满足:
✓ asset-hub serve 5 个子命令全部实现 + 单测全绿 + Windows 双模式烟测通过
✓ /api/healthz 端点上线 + frontend gen:api 拉到 healthz
✓ I1+I2 PR merge: 后端 validation 支持 url/multi-enum/min-max + FieldType Enum
✓ B3 PR merge: DELETE /api/types/{id} + asset-hub type delete CLI
✓ B2 PR merge: 归还记录归还地点 + 接收人 + ReturnDialog 加字段 + service 行为变更
✓ scripts/dev.sh 删除（被 serve 取代）
✓ CLAUDE.md 更新 dev 启动说明（dev.sh → serve）
✓ Linux 烟测延后登记到 spec 已知 gap

不视为 M2d 范围:
- serve doctor 子命令（M3 候选）
- M3 看板 / 导出 / SKILL.md 完善
- M2c-4 类型管理 UI
```

## 附录 A · M2d 期间并行交付

本附录登记 M2d 期间并行交付的 4 项 backend gaps + 1 项 follow-up，每项给"验收标准 + 决策延后清单 + PR 边界"，不展开方案。

### A.1 `serve doctor` follow-up（不入 M2d 范围）

**触发场景**：用户/Agent 反复因为环境问题（stale dist / alembic drift / 端口被占）调试时。

**检查项候选**（plan 阶段定全集）：
- DB 文件存在 + 可写 + alembic head 与 schema 一致
- frontend/dist 是否新于 src 最近修改（stale build 检测）
- :8000 / :5173 端口空闲
- data/pids 与 data/logs 目录可写
- psutil / 关键依赖已安装

**落地阶段**：M3（与 SKILL.md 完善 + 部署文档同周期）。

**为何不入 M2d**：M2d timebox 1 周已含 serve 主线 + 4 项 backend gaps；doctor 与 M3 SKILL.md 完善天然合并。设计灵感来自 [nilbuild/slim](https://github.com/nilbuild/slim) 的 `slim doctor` 子命令。

### A.2 B2 · 归还时记录归还地点与接收人（PR 顺序：第 4，最后做）

**来源**：`followups-m2c3-smoketest.md` §B2（文字描述失真，按 spec §14.2 真实意图实施）+ `specs/2026-04-15-asset-hub-design.md` §14.2

**用户故事**：仓库/存放点不止一个，接收的管理员也不止一个；归还时必须能明确记录"实物归还到哪 + 谁接收的"。当前 ReturnDialog 只能填备注，归还后资产 holder/location 都被无脑清空，丢失"实际去向"信息。

**数据模型（DB migration）**：
- `CheckoutRecord` 增加：
  - `return_location: str | None` — 归还时记录的物理位置
  - `return_receiver: str | None` — 归还时接收的管理员
- 资产归还后状态变化：
  - `Asset.holder` 清空（IDLE 资产无 holder，不变）
  - `Asset.location` ← `return_location`（**不再硬清空**——纠正 v1 临时简化）
  - 若 return_location 留空 → location 也清空（向后兼容）

**API / DTO**：
- `CheckoutReturn` DTO 加 `return_location?: str` + `return_receiver?: str`
- `CheckoutRecordRead` DTO 同步加这两字段（详情页时间线展示）

**Service**：`CheckoutService.return_(asset_id, note, return_location=None, return_receiver=None)` 单事务内：关闭 CheckoutRecord（写两字段）+ 更新 Asset.location。

**前端**：ReturnDialog 加两字段（自由文本）；详情页流转记录的归还卡片展示这两字段（如有）。

**CLI**：`asset-hub asset return <id> --location "仓库A-第3排" --receiver "张三" --note "..."`

**验收标准**：
- DB migration 跑通（alembic upgrade head）
- service unit 4 路径测试（不传 / 仅 location / 仅 receiver / 双带）
- API integration 字段写入正确
- CLI integration 参数透传
- 前端 Vitest（useReturn hook + ReturnDialog）
- Asset.location 在 return_location 提供时跟随，不再硬清空

**决策延后到 plan**：
- 归还地点 / 接收人是否做 autocomplete（从历史值提取）→ 推荐 v1 不做，自由文本足够
- 流转记录卡片的视觉布局（同行 vs 分行）
- 是否引入"标准 location / receiver 列表"做下拉 → 推荐 v1 不做（YAGNI；接近 §14.4 People 实体化轻量前哨）

**关于已有归还记录的 backfill**：migration 加两个 nullable 列；历史 CheckoutRecord 这两字段为 NULL；前端 UI 容错显示"-"。不做 backfill。

**关于"接收人"字段**：v1 仍是 `str` 自由文本；§14.4 People 实体化做后，`return_receiver` 跟随升级到 `person_id`，与 holder 同步迁移。

### A.3 B3 · AssetType DELETE 端点（PR 顺序：第 3）

**来源**：`followups-m2c3-smoketest.md` §B3

**用户故事**：误建的 AssetType 能通过 CLI / API 删除；引用资产时严格拒绝。

**验收标准**：
- `DELETE /api/types/{type_id}`：无引用资产 → 200 + 删除；有引用 → 409 Conflict + 错误信息含引用数量
- CLI `asset-hub type delete <id>` 支持 `--dry-run` + 二次确认（默认 `--yes` flag 跳过）
- service `AssetTypeService.delete(type_id)` 抛 `ConflictError`（含引用 asset 数量）；router 走既有异常映射
- 前端不做 GUI 删除入口（M2c-4 类型管理 UI 时再加）

**决策延后到 plan**：
- 错误信息文案（"该类型仍有 5 个资产引用，请先删除/迁移"具体表述）
- CLI dry-run 输出列哪些字段（类型 name + 引用资产示例 N 条 vs 仅数量）

**测试要求**：service unit（无引用 / 有引用两路径）+ API integration（HTTP 状态码）+ CLI integration。

### A.4 I1 + I2 · 后端 validation 补全 + FieldType Enum（PR 顺序：第 1+2，合并）

**来源**：`simplify-followups.md` §4 I1 + I2

**触发动因**：
- I1：前端 m2c-3 已支持 `url` / `multi-enum` 字段类型，后端 `validation.py` 未实现 → 用户可触发的运行时错误
- I2：`validation.py` 7 层平铺 `if t == "..."` 临界，新增 url/multi-enum 进一步加分支

**合并 PR 验收标准**：
- 引入 `FieldType(str, Enum)`：`STRING / TEXT / URL / NUMBER / INT / FLOAT / ENUM / MULTI_ENUM / BOOL / DATE`
- `validation.py` 改表驱动 dispatch
- 新增校验规则：
  - `url`：`urllib.parse.urlparse(value).scheme in {"http","https"} and netloc`
  - `multi-enum`：`isinstance(value, list)` + 每元素 `in options`
  - `int / float` 的 `min / max`：值在区间内
- 前端 `field-def-to-zod.ts` 已存在的同名校验作为对照——后端校验文案需与前端一致或更具体
- `pnpm --dir frontend gen:api` 重新生成 schema.d.ts，确保 FieldType Enum 在 OpenAPI 输出中

**决策延后到 plan**：
- FieldType Enum 是否影响 generated schema.d.ts 字段名（gen:api 后 audit）
- 前端 generated 类型若需同步改名，影响哪些前端文件
- url 校验是否限协议 → 推荐仅 http/https

**测试要求**：service unit 全 dispatch 分支 + 边界（空 list / 超 max / 非法 url 各 case）。

### A.5 PR 顺序与并行性

四项独立 PR，按 `followup-allocation.md` 拍板顺序：

```
M2d 主线 (asset-hub serve)            ← feature/m2d-serve
   │ 与下面 4 个 PR 互不冲突，可并行
   │
M2d 期间并行 PR:
   1. I1 + I2 合并 (后端 validation)   ← feature/m2d-validation
   2. B3 (AssetType DELETE)              ← feature/m2d-type-delete
   3. B2 (归还记录地点 + 接收人)         ← feature/m2d-return-fields
```

**PR 之间无 import / schema 依赖**：
- I1+I2 改 `validation.py`，不动其他 service
- B3 改 `AssetTypeService` + `types.py` router + CLI
- B2 改 `CheckoutService` + `checkouts.py` router + ReturnDialog + CLI

**唯一交集**：四个 PR 都要跑 `pnpm gen:api`（schema 改了），merge 顺序按上面定，每个 merge 后 main 上 trigger 一次 gen:api。

## 附录 B · 已知 Gap 与 Follow-up

| 项 | 性质 | 落地阶段 |
|---|---|---|
| Linux 烟测 | M2d release 时未真机验证；单测 mock 覆盖 | Linux 环境就绪后补一轮 |
| 多代日志轮转 | 当前 1 代；超过被冲掉过崩溃日志时启动 | 触发条件出现后小 PR |
| `serve doctor` 诊断子命令 | 灵感来自 nilbuild/slim | M3（与 SKILL.md 完善 + 部署文档同周期） |
| `serve build` 独立子命令 | 当前 build 藏在 start 里；CI / Docker layer 缓存场景出现时再剥 | v2 候选 |
| `--workers N` flag（prod 多 worker） | v1 默认单 worker | M3+ 业务驱动 |
| §14.3 IDLE 资产显式 location 维护（独立"修改位置" action） | B2 落地后残值 | M3 表单里程碑顺手做 |
| §14.4 People 实体化（含 return_receiver 升级 person_id） | 独立 M5 大里程碑 | §14.1 之后 |
| §14.6 状态切换 audit 化（吸收 smoketest B1） | M3+ 候选 | 与 §14.1 派出类型扩展同周期 |

---

**spec 完。** 下一步 → writing-plans skill 生成实施计划。
