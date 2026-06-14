# 桌面便携版 PR2 — undo 的 API + GUI 化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把已有但仅 CLI 暴露的"撤销上一次流转"（`TransitionService.undo_last_transition`）通过 HTTP API + 前端时间线撤销按钮暴露出来，让纯 GUI 桌面版不丢这个能力（兑现 issue24 §3 Q2 预留的"未来 GUI 化"）。

**Architecture:** 后端在 `transitions` router 加 `POST /api/assets/{id}/transitions/undo`，直接复用既有 service（返回 `TransitionRead` DTO；域异常由 `api/app.py` 集中映射 404/409）。前端加 `useUndoLastTransitionMutation` hook + `UndoLastTransitionAlert` 确认弹窗，挂到流转记录时间线表头（仅当存在流转记录时显示）。

**Tech Stack:** FastAPI / pytest TestClient（`tests/api/conftest.py` fixtures）；React + TanStack Query + msw（`tests/hooks` 范式）；shadcn `AlertDialog`。

**设计依据:** spec §4（GUI 能力核对）、§7.5；issue24 设计 `docs/superpowers/specs/2026-05-20-issue24-asset-undo-design.md`。

**前置:** 与 PR1 无强依赖（可并行），但建议 PR1 先合。**分支:** `feat/desktop-release`。

---

### Task 1: 后端 undo 端点

**Files:**
- Modify: `src/asset_hub/api/routers/transitions.py`（在 `list_transitions` 后追加）
- Test: `tests/api/test_transition_undo_api.py`

- [ ] **Step 1: 写失败测试**

`tests/api/test_transition_undo_api.py`（复用 `tests/api/conftest.py` 的 `client` / `idle_asset` fixtures）：

```python
import uuid


def test_undo_reverts_last_transition(client, idle_asset):
    """checkout 后 undo → asset 回 IDLE，holder 清空，流转记录清零。"""
    aid = idle_asset["id"]
    # 先 checkout（IDLE → IN_USE）
    r = client.post(
        f"/api/assets/{aid}/transitions",
        json={"kind": "CHECKOUT_INTERNAL", "to_holder": "张三"},
    )
    assert r.status_code == 201

    # undo
    r = client.post(f"/api/assets/{aid}/transitions/undo")
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "CHECKOUT_INTERNAL"  # 返回被撤销的那条

    # asset 回到 IDLE / holder 清空
    a = client.get(f"/api/assets/{aid}").json()
    assert a["status"] == "IDLE"
    assert a["holder"] is None

    # 流转记录清零
    lst = client.get(f"/api/assets/{aid}/transitions").json()
    assert lst == []


def test_undo_no_transition_returns_409(client, idle_asset):
    """无流转记录的 asset undo → StateError → 409。"""
    aid = idle_asset["id"]
    r = client.post(f"/api/assets/{aid}/transitions/undo")
    assert r.status_code == 409
    assert r.json()["code"] == "state_conflict"


def test_undo_nonexistent_asset_returns_404(client):
    r = client.post(f"/api/assets/{uuid.uuid4()}/transitions/undo")
    assert r.status_code == 404
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/api/test_transition_undo_api.py -v`
Expected: FAIL（undo 路由不存在 → 404/405 不符）。

- [ ] **Step 3: 加端点**

在 `src/asset_hub/api/routers/transitions.py` 末尾追加：

```python
@router.post("/{asset_id}/transitions/undo", response_model=TransitionRead)
def undo_last_transition(
    asset_id: uuid.UUID,
    svc: Annotated[TransitionService, Depends(_get_svc)],
):
    """撤销该资产最后一条流转记录（物理删除，元操作不进状态机）。
    域异常（NotFoundError/StateError）由 api/app.py 集中映射 404/409。"""
    return svc.undo_last_transition(asset_id)
```

> 路由挂在 `assets` 前缀下（transitions router include 时 prefix=`/api/assets`），最终路径 `POST /api/assets/{id}/transitions/undo`。注意它必须在 `POST /{asset_id}/transitions`（create）之后定义不影响——路径不冲突（`/undo` 是更具体的子路径）。

- [ ] **Step 4: 跑测试确认通过 + 回归**

Run: `uv run pytest tests/api/test_transition_undo_api.py tests/api/test_transitions.py -v`
Expected: 新测试 3 PASS；原 transitions 测试不受影响。

- [ ] **Step 5: 提交**

```bash
git add src/asset_hub/api/routers/transitions.py tests/api/test_transition_undo_api.py
git commit -m "feat(api): 新增 POST /api/assets/{id}/transitions/undo 端点"
```

---

### Task 2: 同步 openapi 类型产物

**Files:**
- Modify: `frontend/src/api/generated/schema.d.ts`（自动生成，勿手改）

- [ ] **Step 1: 起后端**

Run（后台）: `uv run uvicorn asset_hub.api.app:app --port 8000 &`
等待 ~2s 直到 `http://127.0.0.1:8000/api/healthz` 可访问（`curl -s http://127.0.0.1:8000/api/healthz`）。

- [ ] **Step 2: 生成类型**

Run: `pnpm --dir frontend gen:api`
Expected: `frontend/src/api/generated/schema.d.ts` 更新，diff 中出现 `/api/assets/{asset_id}/transitions/undo` path。

- [ ] **Step 3: 停后端**

Run: 结束 Step 1 的 uvicorn 进程（`kill %1` 或对应 PID）。

- [ ] **Step 4: 确认类型可编译**

Run: `pnpm --dir frontend exec tsc -b`
Expected: 无类型错误（CLAUDE.md：最终类型校验用 `tsc -b`，见 [[feedback_tsc_verification]]）。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/api/generated/schema.d.ts
git commit -m "chore(frontend): gen:api 同步 undo 端点类型"
```

---

### Task 3: 前端 `useUndoLastTransitionMutation` hook

**Files:**
- Modify: `frontend/src/api/hooks/transitions.ts`（追加）
- Test: `frontend/tests/hooks/use-undo-transition.test.tsx`

- [ ] **Step 1: 写失败测试**

`frontend/tests/hooks/use-undo-transition.test.tsx`（沿用 `use-types-mutations.test.tsx` 的 `__mswServer` + wrapper 范式）：

```tsx
import { describe, expect, it } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { useUndoLastTransitionMutation } from '@/api/hooks/transitions';

type MswServer = ReturnType<typeof setupServer>;
const server = (globalThis as unknown as { __mswServer: MswServer }).__mswServer;

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe('useUndoLastTransitionMutation', () => {
  it('POST undo + 返回被撤销的 transition', async () => {
    server.use(
      http.post('http://localhost:3000/api/assets/abc/transitions/undo', () =>
        HttpResponse.json({
          id: 't1',
          asset_id: 'abc',
          kind: 'CHECKOUT_INTERNAL',
          from_status: 'IDLE',
          to_status: 'IN_USE',
          created_at: '2026-05-01T00:00:00Z',
        }),
      ),
    );
    const { result } = renderHook(() => useUndoLastTransitionMutation('abc'), { wrapper });
    const data = await result.current.mutateAsync();
    expect(data.kind).toBe('CHECKOUT_INTERNAL');
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pnpm --dir frontend exec vitest run tests/hooks/use-undo-transition.test.tsx`
Expected: FAIL（`useUndoLastTransitionMutation` 未导出）。

- [ ] **Step 3: 加 hook**

在 `frontend/src/api/hooks/transitions.ts` 末尾追加（紧贴 `useRecordTransitionMutation` 的 invalidate 范式）：

```ts
export function useUndoLastTransitionMutation(assetId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<TransitionRead> => {
      const res = await http.POST("/api/assets/{asset_id}/transitions/undo", {
        params: { path: { asset_id: assetId } },
      });
      return unwrap(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets.detail(assetId) });
      qc.invalidateQueries({ queryKey: qk.assets.transitions(assetId) });
      qc.invalidateQueries({ queryKey: qk.assets.all });
    },
  });
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pnpm --dir frontend exec vitest run tests/hooks/use-undo-transition.test.tsx`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/api/hooks/transitions.ts frontend/tests/hooks/use-undo-transition.test.tsx
git commit -m "feat(frontend): 新增 useUndoLastTransitionMutation hook"
```

---

### Task 4: 撤销确认弹窗 + 接入时间线表头

**Files:**
- Create: `frontend/src/features/assets/detail/undo-last-transition-alert.tsx`
- Modify: `frontend/src/features/assets/detail/transition-timeline.tsx:104-106`

- [ ] **Step 1: 写组件（确认弹窗 + 触发按钮）**

`frontend/src/features/assets/detail/undo-last-transition-alert.tsx`（参照 `delete-asset-alert.tsx` 的 AlertDialog 范式）：

```tsx
import { useState } from "react";
import { Undo2 } from "lucide-react";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { useUndoLastTransitionMutation } from "@/api/hooks/transitions";
import { toFriendlyMessage } from "@/lib/error";

export function UndoLastTransitionAlert({ assetId }: { assetId: string }) {
  const [open, setOpen] = useState(false);
  const mutation = useUndoLastTransitionMutation(assetId);

  async function confirm() {
    try {
      await mutation.mutateAsync();
      toast.success("已撤销上一次流转");
      setOpen(false);
    } catch (err) {
      toast.error(toFriendlyMessage(err));
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1.5">
          <Undo2 className="size-3.5" aria-hidden />
          撤销上一次
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>撤销上一次流转？</AlertDialogTitle>
          <AlertDialogDescription className="space-y-2">
            <span className="block">
              将<strong>物理删除</strong>最近一条流转记录，并把资产状态/保管人/位置回退到该记录发生前。
            </span>
            <span className="block text-destructive font-medium">
              此操作不可恢复（无法 redo）。
            </span>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={mutation.isPending}>取消</AlertDialogCancel>
          <AlertDialogAction
            onClick={confirm}
            disabled={mutation.isPending}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {mutation.isPending ? "撤销中…" : "确认撤销"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

- [ ] **Step 2: 接入时间线表头**

改 `transition-timeline.tsx`。先加 import：

```tsx
import { UndoLastTransitionAlert } from "./undo-last-transition-alert";
```

把表头那行（当前 `<h2 className="mb-3 text-lg font-medium">流转记录</h2>`）替换为：

```tsx
<div className="mb-3 flex items-center justify-between">
  <h2 className="text-lg font-medium">流转记录</h2>
  {(query.data ?? []).length > 0 && (
    <UndoLastTransitionAlert assetId={assetId} />
  )}
</div>
```

（其余 timeline 主体不变。）

- [ ] **Step 3: 类型校验 + lint**

Run: `pnpm --dir frontend exec tsc -b && pnpm --dir frontend lint`
Expected: 无错误。

- [ ] **Step 4: 浏览器烟测（playwright MCP，按 CLAUDE.md 优先浅色模式 [[ui-test-light-mode-first]]）**

起 `uv run asset-hub serve start --mode dev`，浏览器：进入一个有流转记录的资产详情 → 流转记录区出现"撤销上一次"按钮 → 点击 → 确认弹窗 → 确认 → toast "已撤销上一次流转" + 时间线少一条、资产状态回退。无流转记录的资产详情：按钮不显示。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/features/assets/detail/undo-last-transition-alert.tsx frontend/src/features/assets/detail/transition-timeline.tsx
git commit -m "feat(frontend): 流转记录加撤销上一次入口 + 确认弹窗"
```

---

### Task 5: PR2 收尾 — 双端 gate + 文档同步

**Files:**
- Modify: `references/transitions.md`（undo 段补 API/GUI 暴露说明）

- [ ] **Step 1: 后端 gate**

Run: `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`
Expected: 全绿。

- [ ] **Step 2: 前端 gate**

Run: `pnpm --dir frontend lint && pnpm --dir frontend exec tsc -b && pnpm --dir frontend test`
Expected: 全绿。

- [ ] **Step 3: 同步 references/transitions.md**

在 `references/transitions.md` 的 undo（元操作）段补一句：

```markdown
> undo 现也经 HTTP 暴露：`POST /api/assets/{id}/transitions/undo`（返回被撤销的 TransitionRead；asset 不存在→404，无流转记录→409 state_conflict）。Web GUI 在「流转记录」区提供「撤销上一次」按钮（带不可恢复确认）。
```

- [ ] **Step 4: 提交**

```bash
git add references/transitions.md
git commit -m "docs(transitions): undo 段补 API/GUI 暴露说明"
```

---

## Self-Review（PR2）

- **Spec 覆盖**：§4 undo 缺口 → Task 1（API）+ Task 3/4（GUI）；§7.5 → Task 1-4；文档 → Task 5。
- **类型一致性**：后端 `undo_last_transition`（service 既有）/ 端点同名；前端 `useUndoLastTransitionMutation(assetId)` → `UndoLastTransitionAlert({assetId})` 命名贯穿。openapi path `/api/assets/{asset_id}/transitions/undo` 与 hook 调用一致。
- **无占位符**：测试/实现/命令均为真实代码。
- **依赖既有**：复用 `TransitionService.undo_last_transition`（issue24 已实现）、`AlertDialog`、`toFriendlyMessage`、`unwrap`、`qk`，无新造基础设施。
