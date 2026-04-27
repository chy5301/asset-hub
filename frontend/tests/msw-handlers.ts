import { http, HttpResponse } from 'msw';

/**
 * 默认空 handlers——hook 测试用 server.use(...) 覆盖具体端点。
 */
export const handlers = [
  // 占位：默认捕获，让单测显式 stub
  http.all('*', () =>
    HttpResponse.json({ detail: 'unhandled (override in test)' }, { status: 501 }),
  ),
];
