import { z } from "zod";

export const consentSchema = z.object({
  acknowledged: z.literal(true, {
    error: "Please confirm you understand how memories are processed before continuing",
  }),
});

export type ConsentValues = z.infer<typeof consentSchema>;
