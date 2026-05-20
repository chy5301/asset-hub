# CL-3 · e2e workflow playwright browser cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 `.github/workflows/e2e.yml` 加 `actions/cache@v4` 步骤缓存 `~/.cache/ms-playwright`，避免 chromium binary（~250MB）每次冷下导致 15min timeout cancel。

**Architecture:** 在 `pnpm install --frozen-lockfile` 之后、`pnpm exec playwright install` 之前插入 cache step。cache key 用 `${{ runner.os }}-playwright-${{ hashFiles('frontend/pnpm-lock.yaml') }}` —— pnpm-lock 变即失效，确保 playwright 升级时拿到新 binary。

**Tech Stack:** GitHub Actions `actions/cache@v4`，playwright 默认缓存路径 `~/.cache/ms-playwright`。

**Spec 来源**：`docs/superpowers/specs/2026-05-17-m4-batch-plan-design.md` CL-3 段。

**预期开销**：单 PR / 单 task / commit `ci: 加 playwright browser cache 防冷下 timeout`。SemVer PATCH。

---

## Phase 1：加 cache step

### Task 1：插入 `actions/cache@v4` step

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\.github\workflows\e2e.yml`（共 50 行；插入位置：第 32 行 "Install frontend deps" step 与第 33 行 "Install playwright browsers" step 之间）

**当前 e2e.yml 结构**（行 30-35）：

```yaml
      - run: uv sync
      - name: Install frontend deps
        run: pnpm install --frozen-lockfile
        working-directory: frontend
      - name: Install playwright browsers
        run: pnpm exec playwright install --with-deps chromium
        working-directory: frontend
```

- [ ] **Step 1：在 "Install playwright browsers" 之前插入 cache step**

修改 `.github/workflows/e2e.yml`，在第 32 行之后（"Install frontend deps" 结束）、第 33 行之前（"Install playwright browsers" 开始）插入：

```yaml
      - name: Cache playwright browsers
        uses: actions/cache@v4
        id: playwright-cache
        with:
          path: ~/.cache/ms-playwright
          key: ${{ runner.os }}-playwright-${{ hashFiles('frontend/pnpm-lock.yaml') }}
```

修改后 `e2e.yml` 第 30-39 行应为：

```yaml
      - run: uv sync
      - name: Install frontend deps
        run: pnpm install --frozen-lockfile
        working-directory: frontend
      - name: Cache playwright browsers
        uses: actions/cache@v4
        id: playwright-cache
        with:
          path: ~/.cache/ms-playwright
          key: ${{ runner.os }}-playwright-${{ hashFiles('frontend/pnpm-lock.yaml') }}
      - name: Install playwright browsers
        run: pnpm exec playwright install --with-deps chromium
        working-directory: frontend
```

**说明**：

- `actions/cache@v4` 自动在 cache hit 时跳过下载（playwright install 内部检测到 browser 已存在则秒过；cache miss 时正常冷下并在 job 结束自动 upload cache）
- `id: playwright-cache` 留着便于未来如需在 `if: steps.playwright-cache.outputs.cache-hit != 'true'` 条件分支使用（本 plan 不用）
- cache key 第一段 `${{ runner.os }}` 防跨 OS 撞 cache；第二段 `hashFiles('frontend/pnpm-lock.yaml')` 让 playwright 升级（lockfile 改）自动 invalidate

- [ ] **Step 2：本地静态校验 yaml 合法性**

跑：

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/e2e.yml'))"
```

期望：无 traceback，stdout 空。

- [ ] **Step 3：提交**

```bash
git add .github/workflows/e2e.yml
git commit -m "ci: 加 playwright browser cache 防 e2e workflow 冷下 timeout

之前每次跑 e2e 都冷下 ~250MB chromium binary，第 2/3 次（rerun）连卡 14m48s 撞 15min timeout cancel。
加 actions/cache@v4 缓存 ~/.cache/ms-playwright，cache key 用 pnpm-lock hash 确保 playwright 升级自动失效。
cache hit 时 playwright install 秒过，cache miss 时正常下载并 upload。"
```

---

## Phase 2：CI 实战验证

### Task 2：开 PR 验证 cache 行为

**Files:** （无代码改动，仅 PR 行为观测）

- [ ] **Step 1：推分支并开 PR**

```bash
git push -u origin <branch-name>
gh pr create --title "ci: 加 playwright browser cache" --body "$(cat <<'EOF'
## Summary
- 加 actions/cache@v4 step 缓存 ~/.cache/ms-playwright
- key 用 runner.os + pnpm-lock.yaml hash，playwright 升级自动失效

## Test plan
- [ ] 第一次 push：cache miss，正常冷下 chromium，job 完成（5-10 min）
- [ ] 第二次 rerun：cache hit，playwright install 秒过，job 完成（1-2 min）
- [ ] 检查 e2e job 总耗时从 14m+ 降到 < 5 min
EOF
)"
```

- [ ] **Step 2：观察首次 CI 跑结果**

`gh pr checks <pr-number>`：

- 期望 backend / frontend / e2e 三个 check 全绿
- e2e job 第一次跑应正常冷下 chromium（约 5-10 min）

- [ ] **Step 3：手动 rerun e2e 验证 cache hit**

```bash
gh run rerun <run-id> --failed   # 或在 PR 页 UI "Re-run failed jobs"
# 实际是 rerun 全 e2e job 看 cache hit 行为，可用 "Re-run all jobs"
```

期望：

- e2e job 第二次跑应 cache hit，"Cache playwright browsers" step log 显示 `Cache restored from key:`
- "Install playwright browsers" step 应秒过（无 ~250MB 下载）
- 总耗时降到 1-3 min

- [ ] **Step 4：merge**

如三个 check 全绿且 cache hit 验证通过，merge PR：

```bash
gh pr merge --squash --delete-branch
```

---

## Self-Review Checklist

- [x] Spec coverage：CL-3 段全部 4 行需求（cache step / 缓存路径 / key 用 pnpm-lock hash / 不抬 timeout）都在 Task 1 中
- [x] 不在 scope：未引入 `microsoft/playwright-github-action`（spec 明示不做）
- [x] timeout 保持 15 min 未抬（spec §123 "若后续仍反复 timeout 再单独抬到 20"，本 plan 不动）
- [x] 无 placeholder：cache step yaml 完整、commit msg 完整

## 风险

- cache key 用 `pnpm-lock.yaml` 整体 hash 而非单独锁 `@playwright/test` 版本：极少数情况 lockfile 改但 playwright 未升时会浪费一次 cache invalidate。可接受（playwright 版本就是通过 pnpm-lock 锁的，invalidate 不会产生错误结果）。
