import { describe, expect, it } from "vitest";

import { dashboardSearchSchema } from "@/features/dashboard/search-schema";

describe("dashboardSearchSchema", () => {
  it("defaults are false when fields omitted", () => {
    const result = dashboardSearchSchema.parse({});
    expect(result.include_retired).toBe(false);
    expect(result.include_disposed).toBe(false);
  });

  it("accepts boolean true/false", () => {
    expect(dashboardSearchSchema.parse({ include_retired: true })).toMatchObject({
      include_retired: true,
      include_disposed: false,
    });
    expect(dashboardSearchSchema.parse({ include_disposed: true })).toMatchObject({
      include_retired: false,
      include_disposed: true,
    });
  });

  it("rejects non-boolean values", () => {
    expect(() => dashboardSearchSchema.parse({ include_retired: "yes" })).toThrow();
  });
});
