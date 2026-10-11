import { describe, expect, it } from "vitest";
import { consentSchema } from "./schemas";

describe("consentSchema", () => {
  it("requires the checkbox to be checked", () => {
    expect(consentSchema.safeParse({ acknowledged: false }).success).toBe(false);
    expect(consentSchema.safeParse({}).success).toBe(false);
  });

  it("accepts the acknowledgement", () => {
    expect(consentSchema.safeParse({ acknowledged: true }).success).toBe(true);
  });
});
