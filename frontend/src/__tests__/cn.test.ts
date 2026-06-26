import { describe, expect, it } from "vitest";

import { cn } from "@/lib/utils";

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("handles conditional class names", () => {
    expect(cn("base", false && "hidden", "extra")).toBe("base extra");
    expect(cn("base", true && "shown")).toBe("base shown");
  });

  it("resolves tailwind conflicts by keeping the latter", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("accepts arrays and objects", () => {
    expect(cn(["a", "b"], { c: true, d: false })).toBe("a b c");
  });
});
