import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().trim().email("Please enter a valid email address"),
  password: z.string().min(1, "Please enter your password"),
});

export const registerSchema = z
  .object({
    displayName: z.string().trim().max(200).optional(),
    email: z.string().trim().email("Please enter a valid email address"),
    password: z.string().min(10, "Use at least 10 characters"),
    confirm: z.string(),
    acknowledged: z.literal(true, {
      error: "Please confirm you understand this is not the real person",
    }),
  })
  .refine((v) => v.password === v.confirm, {
    path: ["confirm"],
    message: "Passwords do not match",
  });

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
