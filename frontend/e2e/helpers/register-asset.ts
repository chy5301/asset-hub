import { execFileSync } from "node:child_process";
import fs from "node:fs";

export interface RegisteredAsset {
  id: string;
  name: string;
  status: string;
}

/**
 * 通过 CLI 直接登记一台资产，返回 id。
 * 比走 UI 表单稳定（UI 表单后续会变，CLI 契约稳定）。
 *
 * type_id 从 global-setup 落盘的 e2e/.state/type-id.txt 读取，
 * 避免 process.env 跨 worker 不可靠的问题。
 */
export function registerAsset(opts: {
  name: string;
  sn: string;
  custom?: Record<string, unknown>;
}): RegisteredAsset {
  const typeId = fs.readFileSync("e2e/.state/type-id.txt", "utf8").trim();
  if (!typeId) throw new Error("type-id.txt 为空（global-setup 未跑？）");

  const customJson = JSON.stringify(opts.custom ?? { brand: "Lenovo", ram_gb: 16 });
  // execFileSync argv 数组直传子进程，不走 shell — 避免 name/sn 含元字符时注入或解析错
  const out = execFileSync(
    "uv",
    [
      "run",
      "asset-hub",
      "asset",
      "register",
      "--name", opts.name,
      "--type-id", typeId,
      "--sn", opts.sn,
      "--custom", customJson,
      "--json",
    ],
    { env: process.env, cwd: "..", encoding: "utf8" },
  );
  const parsed = JSON.parse(out);
  if (!parsed.success) throw new Error(`register failed: ${JSON.stringify(parsed.error)}`);
  return parsed.data as RegisteredAsset;
}
