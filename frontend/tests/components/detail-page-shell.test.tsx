import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { DetailPageShell } from "@/components/layout/detail-page-shell";

describe("DetailPageShell", () => {
  it("渲染返回链接 / 标题 / actions / children 四个 slot", () => {
    render(
      <DetailPageShell
        backLink={<a href="/back">← 返回</a>}
        title="测试标题"
        actions={<button>编辑</button>}
      >
        <p>正文区</p>
      </DetailPageShell>,
    );
    expect(screen.getByRole("link", { name: "← 返回" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "测试标题" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "编辑" })).toBeInTheDocument();
    expect(screen.getByText("正文区")).toBeInTheDocument();
  });

  it("title 用 h1.text-2xl；titleAccessory 与 meta 可选渲染", () => {
    render(
      <DetailPageShell
        backLink={<span>back</span>}
        title="标题"
        titleAccessory={<span>角标</span>}
        meta={<span>元信息行</span>}
      >
        <p>x</p>
      </DetailPageShell>,
    );
    const h1 = screen.getByRole("heading", { name: "标题" });
    expect(h1.className).toContain("text-2xl");
    expect(screen.getByText("角标")).toBeInTheDocument();
    expect(screen.getByText("元信息行")).toBeInTheDocument();
  });
});
