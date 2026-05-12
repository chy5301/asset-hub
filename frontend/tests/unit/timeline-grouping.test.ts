import { describe, expect, it } from "vitest";
import { groupByMonth, groupByCheckout } from "@/lib/timeline-grouping";
import type { TransitionRead } from "@/features/assets/types";

function mkT(id: string, kind: TransitionRead["kind"], created_at: string, extra?: Partial<TransitionRead>): TransitionRead {
  return {
    id,
    asset_id: "a1",
    kind,
    from_status: null,
    to_status: "IDLE",
    from_holder: null,
    to_holder: null,
    from_location: null,
    to_location: null,
    note: null,
    created_at,
    due_at: null,
    closes_transition_id: null,
    ...extra,
  } as TransitionRead;
}

describe("groupByMonth", () => {
  it("跨月分组 + month desc 排序", () => {
    const ts = [
      mkT("t1", "DISPOSE", "2026-05-02T10:00:00Z"),
      mkT("t2", "RETIRE", "2026-04-15T10:00:00Z"),
      mkT("t3", "RECOVER_FROM_MAINTENANCE", "2026-04-01T10:00:00Z"),
      mkT("t4", "SEND_TO_MAINTENANCE", "2026-03-20T10:00:00Z"),
    ];
    const out = groupByMonth(ts);
    expect(out).toEqual([
      { month: "2026-05", items: [ts[0]] },
      { month: "2026-04", items: [ts[1], ts[2]] },
      { month: "2026-03", items: [ts[3]] },
    ]);
  });

  it("空数组返 []", () => {
    expect(groupByMonth([])).toEqual([]);
  });
});

describe("groupByCheckout", () => {
  it("一对 INTERNAL CHECKOUT + RETURN（中间无中性卡）", () => {
    const ts: TransitionRead[] = [
      mkT("ret", "RETURN", "2026-05-05T10:00:00Z", { closes_transition_id: "co" }),
      mkT("co", "CHECKOUT_INTERNAL", "2026-04-20T10:00:00Z"),
    ];
    const out = groupByCheckout(ts);
    expect(out).toEqual([
      { ...ts[0], group: { kind: "in-use", position: "end" } },
      { ...ts[1], group: { kind: "in-use", position: "start" } },
    ]);
  });

  it("EXTERNAL CHECKOUT + 中间夹 REASSIGN + RETURN", () => {
    const ts: TransitionRead[] = [
      mkT("ret", "RETURN", "2026-05-10T10:00:00Z", { closes_transition_id: "co" }),
      mkT("reassign", "REASSIGN", "2026-05-05T10:00:00Z"),
      mkT("co", "CHECKOUT_EXTERNAL", "2026-04-20T10:00:00Z"),
    ];
    const out = groupByCheckout(ts);
    expect(out[0].group).toEqual({ kind: "external", position: "end" });
    expect(out[1].group).toEqual({ kind: "external", position: "middle" });
    expect(out[2].group).toEqual({ kind: "external", position: "start" });
  });

  it("OPEN CHECKOUT（没有对应 RETURN，向更新方向延伸）", () => {
    const ts: TransitionRead[] = [
      mkT("reassign", "REASSIGN", "2026-05-05T10:00:00Z"),
      mkT("co", "CHECKOUT_INTERNAL", "2026-04-20T10:00:00Z"),
    ];
    const out = groupByCheckout(ts);
    expect(out[0].group).toEqual({ kind: "in-use", position: "middle" });
    expect(out[1].group).toEqual({ kind: "in-use", position: "start" });
  });

  it("v2: OPEN CHECKOUT 期间 REPORT_BROKEN → DISMISS 均为 middle（派出集不闭合）", () => {
    // IN_USE → REPORT_BROKEN → DISMISS 整段应归属同一 in-use 派出周期
    const ts: TransitionRead[] = [
      mkT("dismiss", "DISMISS", "2026-05-10T10:00:00Z"),
      mkT("broken", "REPORT_BROKEN", "2026-05-05T10:00:00Z"),
      mkT("co", "CHECKOUT_INTERNAL", "2026-04-20T10:00:00Z"),
    ];
    const out = groupByCheckout(ts);
    expect(out[0].group).toEqual({ kind: "in-use", position: "middle" });
    expect(out[1].group).toEqual({ kind: "in-use", position: "middle" });
    expect(out[2].group).toEqual({ kind: "in-use", position: "start" });
  });

  it("周期外 transition group=null", () => {
    const ts: TransitionRead[] = [
      mkT("dispose", "DISPOSE", "2026-05-10T10:00:00Z"),
      mkT("retire", "RETIRE", "2026-05-05T10:00:00Z"),
    ];
    const out = groupByCheckout(ts);
    expect(out[0].group).toBeNull();
    expect(out[1].group).toBeNull();
  });

  it("混合：派出周期 + 周期外", () => {
    const ts: TransitionRead[] = [
      mkT("retire", "RETIRE", "2026-06-01T10:00:00Z"),
      mkT("ret", "RETURN", "2026-05-10T10:00:00Z", { closes_transition_id: "co" }),
      mkT("co", "CHECKOUT_INTERNAL", "2026-04-20T10:00:00Z"),
      mkT("send", "SEND_TO_MAINTENANCE", "2026-04-10T10:00:00Z"),
    ];
    const out = groupByCheckout(ts);
    expect(out[0].group).toBeNull();
    expect(out[1].group).toEqual({ kind: "in-use", position: "end" });
    expect(out[2].group).toEqual({ kind: "in-use", position: "start" });
    expect(out[3].group).toBeNull();
  });
});
