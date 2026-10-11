import { describe, expect, it } from "vitest";
import { loginSchema, registerSchema } from "./schemas";

const valid = {
  email: "a@example.com",
  password: "long-enough-pass",
  confirm: "long-enough-pass",
  acknowledged: true as const,
};

describe("registerSchema", () => {
  it("accepts valid input", () => {
    expect(registerSchema.safeParse(valid).success).toBe(true);
  });
  it("rejects short passwords", () => {
    expect(registerSchema.safeParse({ ...valid, password: "short", confirm: "short" }).success).toBe(false);
  });
  it("rejects mismatched confirmation on the confirm field", () => {
    const r = registerSchema.safeParse({ ...valid, confirm: "different-pass" });
    expect(r.success).toBe(false);
    if (!r.success) expect(r.error.issues[0].path).toEqual(["confirm"]);
  });
  it("requires the not-the-real-person acknowledgement", () => {
    expect(registerSchema.safeParse({ ...valid, acknowledged: false }).success).toBe(false);
  });
});

describe("loginSchema", () => {
  it("rejects bad emails", () => {
    expect(loginSchema.safeParse({ email: "nope", password: "x" }).success).toBe(false);
  });
});
