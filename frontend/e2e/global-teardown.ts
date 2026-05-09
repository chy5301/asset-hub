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

  // .state 路径与 global-setup 一致 — playwright globalSetup/Teardown 同 cwd (frontend/)
  if (process.env.CI) {
    try {
      rmSync("e2e/.state", { recursive: true, force: true });
    } catch (e) {
      console.warn(`[e2e teardown] failed to rm e2e/.state: ${e}`);
    }
  }
}
