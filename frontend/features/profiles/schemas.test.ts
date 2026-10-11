import { describe, expect, it } from "vitest";
import { profileSchema } from "./schemas";

const base = { name: "Asha Patil", relationship: "mother" };

describe("profileSchema", () => {
  it("accepts only the two required fields", () => {
    const r = profileSchema.safeParse(base);
    expect(r.success).toBe(true);
    if (r.success) expect(r.data.languages).toEqual([]);
  });

  it("requires a name and relationship", () => {
    expect(profileSchema.safeParse({ ...base, name: "" }).success).toBe(false);
    expect(profileSchema.safeParse({ ...base, relationship: "" }).success).toBe(false);
  });

  it("splits a comma-separated language list and trims whitespace", () => {
    const r = profileSchema.safeParse({ ...base, languages: "Marathi,  English ," });
    expect(r.success && r.data.languages).toEqual(["Marathi", "English"]);
  });

  it("rejects a death date before the birth date", () => {
    const r = profileSchema.safeParse({
      ...base,
      birth_date: "2000-01-01",
      death_date: "1990-01-01",
    });
    expect(r.success).toBe(false);
  });

  it("treats an empty date input as not provided", () => {
    const r = profileSchema.safeParse({ ...base, birth_date: "", death_date: "" });
    expect(r.success).toBe(true);
    if (r.success) {
      expect(r.data.birth_date).toBeUndefined();
      expect(r.data.death_date).toBeUndefined();
    }
  });
});
