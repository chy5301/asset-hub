import { execSync } from "node:child_process";
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
  // 读文件（worker cwd = frontend/）
  const typeId = fs.readFileSync("e2e/.state/type-id.txt", "utf8").trim();
  if (!typeId) throw new Error("type-id.txt 为空（global-setup 未跑？）");

  const customJson = JSON.stringify(opts.custom ?? { brand: "Lenovo", ram_gb: 16 });
  const cmd = [
    "uv run asset-hub asset register",
    `--name ${JSON.stringify(opts.name)}`,
    `--type-id ${typeId}`,
    `--sn ${JSON.stringify(opts.sn)}`,
    `--custom ${JSON.stringify(customJson)}`,
    "--json",
  ].join(" ");

  // cwd ".." 回到 repo root 跑 CLI（asset-hub CLI 从 repo root 解析数据目录）
  const out = execSync(cmd, { env: process.env, cwd: ".." }).toString();
  const parsed = JSON.parse(out);
  if (!parsed.success) throw new Error(`register failed: ${JSON.stringify(parsed.error)}`);
  return parsed.data as RegisteredAsset;
}
