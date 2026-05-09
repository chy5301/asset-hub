import { execSync } from "node:child_process";
import fs from "node:fs";

export default async function globalSetup() {
  const dataDir = process.env.ASSET_HUB_DATA_DIR;
  if (!dataDir) {
    throw new Error(
      "ASSET_HUB_DATA_DIR must be set for e2e (typically a tmp dir). " +
        "Example: ASSET_HUB_DATA_DIR=/tmp/asset-hub-e2e pnpm --dir frontend e2e",
    );
  }

  console.log(`[e2e setup] using ASSET_HUB_DATA_DIR=${dataDir}`);

  // 0. 确保 frontend dist 已 build（uvicorn 不像 serve start 那样自动 build）
  console.log("[e2e setup] building frontend dist...");
  execSync("pnpm --dir frontend build", {
    stdio: "inherit",
    env: process.env,
    cwd: "..",
  });

  // 1. alembic upgrade（alembic.ini 在 repo root，cwd 退到上级）
  execSync("uv run alembic upgrade head", {
    stdio: "inherit",
    env: process.env,
    cwd: "..",
  });

  // 2. seed laptop type
  const result = execSync(
    "uv run asset-hub type define --from frontend/e2e/fixtures/laptop.json --json",
    { env: process.env, cwd: ".." },
  ).toString();

  const parsed = JSON.parse(result);
  if (!parsed.success) {
    throw new Error(`seed type failed: ${JSON.stringify(parsed.error)}`);
  }

  const typeId: string = parsed.data.id;
  console.log(`[e2e setup] seeded laptop type id=${typeId}`);

  // 3. 把 type_id 落盘到文件，worker 进程通过文件读取（process.env 修改不跨 worker）
  fs.mkdirSync("frontend/e2e/.state", { recursive: true });
  fs.writeFileSync("frontend/e2e/.state/type-id.txt", typeId, "utf8");
  console.log("[e2e setup] wrote type-id to frontend/e2e/.state/type-id.txt");
}
