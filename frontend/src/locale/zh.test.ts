import { describe, expect, it } from "vitest";
import { formatDayHeader } from "./format";
import { categoryLabel, recipeTypeLabel, slotLabel } from "./zh";

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

describe("formatDayHeader", () => {
  it("formats ISO date with Chinese weekday", () => {
    const d = new Date("2026-05-18T12:00:00");
    expect(formatDayHeader(d)).toBe("2026-05-18 · 周一");
  });
});
