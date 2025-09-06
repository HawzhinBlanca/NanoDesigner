import { z } from "zod";

export const paletteSchema = z.array(
  z
    .string()
    .regex(/^#([0-9a-fA-F]{6})$/, "Must be hex color like #112233")
).max(12);

export const fontsSchema = z.array(z.string().min(1)).max(6);

export const voiceSchema = z.object({
  tone: z.string().min(2),
  dos: z.array(z.string().min(1)).default([]),
  donts: z.array(z.string().min(1)).default([]),
});

export const canonSchema = z.object({
  palette_hex: paletteSchema,
  fonts: fontsSchema,
  voice: voiceSchema,
});

export type Canon = z.infer<typeof canonSchema>;

