import { describe, expect, it } from "vitest";

import { buildExportUrl } from "@/features/assets/list/export-button";
import type { AssetsSearch } from "@/features/assets/list/search-schema";

const baseSearch: AssetsSearch = {
  sort: "asset_code",
  page: 1,
  pageSize: 50,
};

describe("buildExportUrl", () => {
  it("minimal search → only format param", () => {
    expect(buildExportUrl(baseSearch, "csv")).toBe("/api/export?format=csv");
    expect(buildExportUrl(baseSearch, "xlsx")).toBe("/api/export?format=xlsx");
  });

  it("includes type / status / holder / q when present", () => {
    const url = buildExportUrl(
      {
        ...baseSearch,
        type: "uuid-1",
        status: "IDLE",
        holder: "张三",
        q: "笔记本",
      },
      "csv",
    );
    const params = new URLSearchParams(url.split("?")[1]);
    expect(params.get("format")).toBe("csv");
    expect(params.get("type_id")).toBe("uuid-1");
    expect(params.get("status")).toBe("IDLE");
    expect(params.get("holder")).toBe("张三");
    expect(params.get("q")).toBe("笔记本");
  });

  it("translates show_retired → include_retired", () => {
    const url = buildExportUrl(
      { ...baseSearch, show_retired: true },
      "csv",
    );
    expect(url).toContain("include_retired=true");
    expect(url).not.toContain("show_retired");
  });

  it("translates show_disposed → include_disposed", () => {
    const url = buildExportUrl(
      { ...baseSearch, show_disposed: true },
      "csv",
    );
    expect(url).toContain("include_disposed=true");
    expect(url).not.toContain("show_disposed");
  });

  it("show_retired false → no param emitted", () => {
    const url = buildExportUrl(
      { ...baseSearch, show_retired: false },
      "csv",
    );
    expect(url).not.toContain("include_retired");
  });

  it("excludes sort / page / pageSize (export 整 filter 集, 不分页)", () => {
    const url = buildExportUrl(
      { ...baseSearch, sort: "name", page: 3, pageSize: 100 },
      "csv",
    );
    const params = new URLSearchParams(url.split("?")[1]);
    expect(params.has("sort")).toBe(false);
    expect(params.has("page")).toBe(false);
    expect(params.has("pageSize")).toBe(false);
  });
});
