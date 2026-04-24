import fs from "node:fs/promises";
import path from "node:path";
import openapiTS, { astToString } from "openapi-typescript";

const OPENAPI_URL = process.env.OPENAPI_URL ?? "http://localhost:8000/openapi.json";
const OUT = path.resolve("src/api/generated/schema.d.ts");

async function main() {
  console.log(`[gen-openapi] fetching ${OPENAPI_URL}`);
  const ast = await openapiTS(new URL(OPENAPI_URL));
  const body = astToString(ast);
  await fs.mkdir(path.dirname(OUT), { recursive: true });
  await fs.writeFile(OUT, body, "utf8");
  console.log(`[gen-openapi] wrote ${OUT} (${body.length} bytes)`);
}

main().catch((err) => {
  console.error("[gen-openapi] failed:", err);
  process.exit(1);
});
