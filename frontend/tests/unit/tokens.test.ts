import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const globalsCSS = readFileSync(
  resolve(__dirname, "../../src/styles/globals.css"),
  "utf-8",
);

function blockOf(selectorPattern: string): string {
  // selectorPattern 直接作为正则片段，调用方负责传正确的 pattern
  // 例如 ":root"、"\\.dark"、"@theme inline"
  const re = new RegExp(`${selectorPattern}\\s*\\{([^}]*)\\}`);
  const m = globalsCSS.match(re);
  if (!m) throw new Error(`block not found: ${selectorPattern}`);
  return m[1];
}

describe("M3d 新增 design tokens — 真验证 globals.css 内容", () => {
  describe(":root (light) 主题 token", () => {
    const root = blockOf(":root");

    it("--status-borrowed = oklch(0.78 0.13 75)", () => {
      expect(root).toMatch(/--status-borrowed:\s*oklch\(0\.78\s+0\.13\s+75\)/);
    });
    it("--status-borrowed-fg = oklch(0.42 0.13 75)", () => {
      expect(root).toMatch(
        /--status-borrowed-fg:\s*oklch\(0\.42\s+0\.13\s+75\)/,
      );
    });
    it("--warning = oklch(0.85 0.18 90)", () => {
      expect(root).toMatch(/--warning:\s*oklch\(0\.85\s+0\.18\s+90\)/);
    });
    it("--warning-fg = oklch(0.45 0.15 90)", () => {
      expect(root).toMatch(/--warning-fg:\s*oklch\(0\.45\s+0\.15\s+90\)/);
    });
  });

  describe(".dark 主题 token", () => {
    const dark = blockOf("\\.dark");

    it("--status-borrowed = oklch(0.70 0.13 75)", () => {
      expect(dark).toMatch(/--status-borrowed:\s*oklch\(0\.70\s+0\.13\s+75\)/);
    });
    it("--status-borrowed-fg = oklch(0.85 0.10 75)", () => {
      expect(dark).toMatch(
        /--status-borrowed-fg:\s*oklch\(0\.85\s+0\.10\s+75\)/,
      );
    });
    it("--warning = oklch(0.72 0.18 90)", () => {
      expect(dark).toMatch(/--warning:\s*oklch\(0\.72\s+0\.18\s+90\)/);
    });
    it("--warning-fg = oklch(0.88 0.13 90)", () => {
      expect(dark).toMatch(/--warning-fg:\s*oklch\(0\.88\s+0\.13\s+90\)/);
    });
  });

  describe("@theme inline utility 映射", () => {
    const theme = blockOf("@theme inline");

    it("--color-status-borrowed -> var(--status-borrowed)", () => {
      expect(theme).toMatch(
        /--color-status-borrowed:\s*var\(--status-borrowed\)/,
      );
    });
    it("--color-status-borrowed-fg -> var(--status-borrowed-fg)", () => {
      expect(theme).toMatch(
        /--color-status-borrowed-fg:\s*var\(--status-borrowed-fg\)/,
      );
    });
    it("--color-warning -> var(--warning)", () => {
      expect(theme).toMatch(/--color-warning:\s*var\(--warning\)/);
    });
    it("--color-warning-fg -> var(--warning-fg)", () => {
      expect(theme).toMatch(/--color-warning-fg:\s*var\(--warning-fg\)/);
    });
  });
});
