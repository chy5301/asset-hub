import { describe, it, expect } from "vitest";
import { STATUS_META } from "@/features/assets/status-labels";

describe("STATUS_META v2.0", () => {
  it("6 态全两字（含 BROKEN）", () => {
    expect(STATUS_META.IDLE.label).toBe("闲置");
    expect(STATUS_META.IN_USE.label).toBe("在用");
    expect(STATUS_META.MAINTENANCE.label).toBe("送修");
    expect(STATUS_META.BROKEN.label).toBe("故障");
    expect(STATUS_META.RETIRED.label).toBe("退役");
    expect(STATUS_META.DISPOSED.label).toBe("注销");
  });

  it("BROKEN 用 alert-triangle icon", () => {
    expect(STATUS_META.BROKEN.bgVar).toBe("--status-broken");
    expect(STATUS_META.BROKEN.fgVar).toBe("--status-broken-fg");
  });
});
