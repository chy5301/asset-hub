import { rmSync } from "node:fs";

export default async function globalTeardown() {
  const dataDir = process.env.ASSET_HUB_DATA_DIR;
  if (dataDir && process.env.CI) {
    try {
      rmSync(dataDir, { recursive: true, force: true });
      console.log(`[e2e teardown] cleaned ${dataDir}`);
    } catch (e) {
      console.warn(`[e2e teardown] failed to rm ${dataDir}: ${e}`);
    }
  }

  // 清理 .state 目录（仅 CI）
  if (process.env.CI) {
    try {
      rmSync("frontend/e2e/.state", { recursive: true, force: true });
    } catch {
      // 忽略
    }
  }
}
