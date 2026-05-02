import createClient from "openapi-fetch";
import type { paths } from "./generated/schema";

// 浏览器使用页面 origin，Node/测试环境回退到 localhost
const baseUrl =
  typeof window !== "undefined" ? window.location.origin : "http://localhost:3000";

// 通过 wrapper 延迟解析 globalThis.fetch，确保 MSW 等测试拦截器在 listen() 后生效
export const http = createClient<paths>({
  baseUrl,
  fetch: (...args) => globalThis.fetch(...args),
});
