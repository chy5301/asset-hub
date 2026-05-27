import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { TypeCustomFieldsDisplay } from "@/features/types/detail/type-custom-fields-display";
import type { TypeRead } from "@/features/assets/types";

type Field = TypeRead["custom_fields"][number];

const fields = [
  { key: "cpu", label: "处理器", type: "string", required: true } as Field,
  {
    key: "tier",
    label: "档位",
    type: "enum",
    required: false,
    options: ["低", "高"],
  } as Field,
];

describe("TypeCustomFieldsDisplay", () => {
  it("列出每个字段的 label / key / 类型，必填标记，enum 选项", () => {
    render(<TypeCustomFieldsDisplay fields={fields} />);
    expect(screen.getByText("处理器")).toBeInTheDocument();
    expect(screen.getByText("cpu")).toBeInTheDocument();
    expect(screen.getByText("档位")).toBeInTheDocument();
    expect(screen.getByText(/低.*高|低、高/)).toBeInTheDocument();
    expect(screen.getByText("必填")).toBeInTheDocument();
  });

  it("空字段列表显示占位", () => {
    render(<TypeCustomFieldsDisplay fields={[]} />);
    expect(screen.getByText("无自定义字段")).toBeInTheDocument();
  });
});
