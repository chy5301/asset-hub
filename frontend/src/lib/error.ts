export interface HttpErrorShape {
  status: number;
  detail?: string;
}

export function isHttpError(err: unknown): err is HttpErrorShape {
  return (
    typeof err === "object" &&
    err !== null &&
    typeof (err as { status?: unknown }).status === "number"
  );
}

const STATUS_MESSAGES: Record<number, string> = {
  404: "资产不存在或已被删除",
  409: "请求冲突",
  422: "数据校验失败",
};

export function toFriendlyMessage(err: unknown): string {
  if (isHttpError(err)) {
    if (err.status === 409 && err.detail) return err.detail;
    if (err.status === 422 && err.detail) return `数据校验失败：${err.detail}`;
    if (err.status >= 500) return "服务端错误，请稍后重试";
    return STATUS_MESSAGES[err.status] ?? `请求失败（HTTP ${err.status}）`;
  }
  if (err instanceof Error && err.message.includes("fetch")) {
    return "网络请求失败，请检查后端是否运行";
  }
  return "未知错误";
}

/** Wrap openapi-fetch 的 { data, error, response } 响应，失败时抛 HttpErrorShape。 */
export function unwrap<T>(result: {
  data?: T;
  error?: unknown;
  response: Response;
}): T {
  if (result.error || !result.data) {
    const detail =
      typeof result.error === "object" && result.error !== null
        ? (result.error as { detail?: string }).detail
        : undefined;
    const err: HttpErrorShape = { status: result.response.status, detail };
    throw err;
  }
  return result.data;
}
