import { z } from "zod";

/** An empty HTML input emits "", not undefined. Treat "" the same as "not provided" so
 * optional dates/text don't get sent to the API as an unparseable empty string. */
export const optionalText = (max: number) =>
  z
    .string()
    .max(max)
    .optional()
    .transform((v) => (v ? v : undefined));

export const optionalDate = z
  .string()
  .optional()
  .transform((v) => (v ? v : undefined));
