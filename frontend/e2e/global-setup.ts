import { execSync } from "node:child_process";
import fs from "node:fs";

/**
 * 定义一个 AssetType 并把其 id 落盘到 e2e/.state/<stateFile>。
 * type_id 落盘是因为 worker 进程通过文件读取（process.env 修改不跨 worker）；
 * playwright globalSetup 默认 cwd = frontend/，与 register-asset.ts 用同一相对路径。
 */
function seedType(fixture: string, prefix: string, stateFile: string): void {
  // --prefix 是 CLI 必填，fixtures/*.json 不含此字段
  const out = execSync(
    `uv run asset-hub type define --from frontend/e2e/fixtures/${fixture} --prefix ${prefix} --json`,
    { env: process.env, cwd: ".." },
  ).toString();
  const parsed = JSON.parse(out);
  if (!parsed.success) {
    throw new Error(`seed type ${fixture} failed: ${JSON.stringify(parsed.error)}`);
  }
  fs.writeFileSync(`e2e/.state/${stateFile}`, parsed.data.id, "utf8");
  console.log(`[e2e setup] seeded ${fixture} type id=${parsed.data.id} → ${stateFile}`);
}

export default async function globalSetup() {
  const dataDir = process.env.ASSET_HUB_DATA_DIR;
  if (!dataDir) {
    throw new Error(
      "ASSET_HUB_DATA_DIR must be set for e2e (typically a tmp dir). " +
        "Example: ASSET_HUB_DATA_DIR=/tmp/asset-hub-e2e pnpm --dir frontend e2e",
    );
  }

  console.log(`[e2e setup] using ASSET_HUB_DATA_DIR=${dataDir}`);

  // 0. 确保 data dir 存在 (CI 的 runner.temp 子目录不会自动创建; 本地用户也可能给不存在的 path)
  fs.mkdirSync(dataDir, { recursive: true });

  // 1. 确保 frontend dist 已 build（uvicorn 不像 serve start 那样自动 build）
  console.log("[e2e setup] building frontend dist...");
  execSync("pnpm --dir frontend build", {
    stdio: "inherit",
    env: process.env,
    cwd: "..",
  });

  // 2. alembic upgrade（alembic.ini 在 repo root，cwd 退到上级）
  execSync("uv run alembic upgrade head", {
    stdio: "inherit",
    env: process.env,
    cwd: "..",
  });

  // 3. seed types（laptop = 默认；workstation 含选项数>4 的 enum form_factor → 走 Select
  // 渲染，用于 issue #39 回归：编辑页选项>4 的 enum 字段须回显已存值）
  fs.mkdirSync("e2e/.state", { recursive: true });
  seedType("laptop.json", "NB", "type-id.txt");
  seedType("workstation.json", "WS", "ws-type-id.txt");
}
