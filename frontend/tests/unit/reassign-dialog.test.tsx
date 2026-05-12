import { describe, it, expect } from "vitest";
import { reassignSchema } from "@/features/assets/detail/reassign-dialog";

describe("reassignSchema v2.0", () => {
  it("必须改 holder 或 location 至少一项（current 都为空，提交空 = no-op）", () => {
    const schema = reassignSchema(null, null);
    const result = schema.safeParse({ to_holder: "", to_location: "", note: "" });
    expect(result.success).toBe(false);
  });

  it("仅改 holder 通过", () => {
    const schema = reassignSchema(null, "原位置");
    const result = schema.safeParse({ to_holder: "李四", to_location: "原位置", note: "" });
    expect(result.success).toBe(true);
  });

  it("仅改 location 通过", () => {
    const schema = reassignSchema("张三", null);
    const result = schema.safeParse({ to_holder: "张三", to_location: "仓库", note: "" });
    expect(result.success).toBe(true);
  });

  it("同改 holder + location 通过", () => {
    const schema = reassignSchema("张三", "原位置");
    const result = schema.safeParse({ to_holder: "李四", to_location: "新位置", note: "" });
    expect(result.success).toBe(true);
  });

  it("传值与 current 同 → no-op → 拒绝", () => {
    const schema = reassignSchema("张三", "L1");
    const result = schema.safeParse({ to_holder: "张三", to_location: "L1", note: "" });
    expect(result.success).toBe(false);
  });
});
