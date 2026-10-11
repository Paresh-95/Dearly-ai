import { z } from "zod";
import { optionalDate, optionalText } from "@/lib/form-utils";

export const memoryPersonSchema = z.object({
  name: z.string().trim().min(1, "Enter a name").max(200),
  relationship: optionalText(100),
});

export const memoryFormSchema = z.object({
  title: z.string().trim().min(1, "Please give the memory a short title").max(300),
  description: z.string().trim().min(1, "Please describe the memory").max(20_000),
  category: optionalText(100),
  date_text: optionalText(200),
  date_start: optionalDate,
  location: optionalText(300),
  people: z.array(memoryPersonSchema).max(50),
});

export type MemoryFormValues = z.input<typeof memoryFormSchema>;
export type MemoryFormOutput = z.output<typeof memoryFormSchema>;
