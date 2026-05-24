import { describe, expect, it } from "vitest";
import { formatDayHeader } from "./format";
import { categoryLabel, recipeTypeLabel, slotLabel, zh } from "./zh";

describe("recipeTypeLabel", () => {
  it("maps known types", () => {
    expect(recipeTypeLabel("soup")).toBe("汤");
    expect(recipeTypeLabel("meat")).toBe("荤菜");
  });

  it("falls back to raw value", () => {
    expect(recipeTypeLabel("unknown")).toBe("unknown");
  });
});

describe("slotLabel", () => {
  it("maps lunch and dinner", () => {
    expect(slotLabel("lunch")).toBe("午餐");
    expect(slotLabel("dinner")).toBe("晚餐");
  });
});

describe("categoryLabel", () => {
  it("maps produce and pantry", () => {
    expect(categoryLabel("produce")).toBe("蔬果");
    expect(categoryLabel("pantry")).toBe("干货调料");
  });
});

describe("v2 zh keys", () => {
  it("includes cooked and journal strings", () => {
    expect(zh.cooked.markDone).toBe("标记已做");
    expect(zh.journal.title).toBe("饮食记录");
    expect(zh.recipeForm.cover).toBe("食谱封面");
  });
});

describe("formatDayHeader", () => {
  it("formats ISO date with Chinese weekday", () => {
    const d = new Date("2026-05-18T12:00:00");
    expect(formatDayHeader(d)).toBe("2026-05-18 · 周一");
  });
});
