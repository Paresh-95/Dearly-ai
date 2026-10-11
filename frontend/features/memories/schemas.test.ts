import { describe, expect, it } from "vitest";
import { memoryFormSchema } from "./schemas";

const base = { title: "Sunday breakfast", description: "Mum made poha.", people: [] };

describe("memoryFormSchema", () => {
  it("accepts the minimal valid shape", () => {
    const r = memoryFormSchema.safeParse(base);
    expect(r.success).toBe(true);
  });

  it("requires a title and description", () => {
    expect(memoryFormSchema.safeParse({ ...base, title: "" }).success).toBe(false);
    expect(memoryFormSchema.safeParse({ ...base, description: "" }).success).toBe(false);
  });

  it("treats an empty optional date as not provided, not a parse error", () => {
    const r = memoryFormSchema.safeParse({ ...base, date_start: "" });
    expect(r.success).toBe(true);
    if (r.success) expect(r.data.date_start).toBeUndefined();
  });

  it("keeps a real date value", () => {
    const r = memoryFormSchema.safeParse({ ...base, date_start: "1995-04-02" });
    expect(r.success && r.data.date_start).toBe("1995-04-02");
  });

  it("requires a name for each person added", () => {
    const r = memoryFormSchema.safeParse({ ...base, people: [{ name: "" }] });
    expect(r.success).toBe(false);
  });

  it("allows a person with no relationship given", () => {
    const r = memoryFormSchema.safeParse({ ...base, people: [{ name: "Grandma" }] });
    expect(r.success).toBe(true);
  });
});
