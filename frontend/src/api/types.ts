/**
 * API 客户端层公共类型 + 工具.
 *
 * 此文件是 spec §H4 决议产物：
 * - OpenapiFetchResult<T>：统一 openapi-fetch 返回形状
 * - unwrap()：从 lib/error.ts 工具迁移到此，签名简化
 *
 * 与业务 alias 层 (features/assets/types.ts, spec §D1) 关注点分离：
 * - 此文件 = openapi-fetch 通用包装（与具体 feature 无关）
 * - features/assets/types.ts = 业务 DTO alias
 */
import type { components } from "./generated/schema";

import { toHttpError } from "@/lib/error";

/** openapi-fetch 调用的统一返回形状 (data | error + response). */
export type OpenapiFetchResult<T> = {
  data?: T;
  error?: unknown;
  response: Response;
};

/** 拆 OpenapiFetchResult，成功返 data；失败抛 HttpErrorShape (toHttpError 统一映射). */
export function unwrap<T>(result: OpenapiFetchResult<T>): T {
  if (result.error || !result.data) {
    throw toHttpError(result);
  }
  return result.data;
}

/** 同 unwrap，但 204/无 body 端点用. */
export function unwrapVoid(
  result: { error?: unknown; response: Response }
): void {
  if (result.error) {
    throw toHttpError(result);
  }
}

/** 业务 alias 层之外、API 客户端通用的 schema 类型重导出. */
export type ApiSchema = components["schemas"];
