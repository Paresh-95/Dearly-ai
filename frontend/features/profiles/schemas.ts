import { z } from "zod";
import { optionalDate, optionalText } from "@/lib/form-utils";

const csvList = z
  .string()
  .optional()
  .transform((v) =>
    (v ?? "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
  );

export const profileSchema = z
  .object({
    name: z.string().trim().min(1, "Please enter a name").max(200),
    relationship: z.string().trim().min(1, "Please enter a relationship").max(100),
    preferred_name: optionalText(200),
    languages: csvList,
    biography: optionalText(20_000),
    personality: optionalText(20_000),
    favourite_expressions: csvList,
    hobbies: csvList,
    birth_date: optionalDate,
    death_date: optionalDate,
  })
  .refine((v) => !v.birth_date || !v.death_date || v.death_date >= v.birth_date, {
    path: ["death_date"],
    message: "This date cannot be before the birth date",
  });

export type ProfileFormValues = z.input<typeof profileSchema>;
export type ProfileFormOutput = z.output<typeof profileSchema>;
