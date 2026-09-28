export type Rgb = [number, number, number];

export const TERRAIN_COLORS: Record<number, Rgb> = {
  0: [22, 62, 112],
  1: [58, 124, 170],
  2: [226, 208, 158],
  3: [150, 184, 92],
  4: [196, 176, 96],
  5: [62, 118, 72],
  6: [30, 92, 58],
  7: [104, 136, 92],
  8: [228, 192, 124],
  9: [196, 204, 196],
  10: [138, 132, 126],
  11: [62, 48, 48],
  12: [44, 38, 52],
};

export const LUSH: Rgb = [70, 150, 60];
export const DRY: Rgb = [196, 168, 110];
export const WATER_DEEP: Rgb = [16, 52, 104];
export const WATER_SHALLOW: Rgb = [70, 140, 186];
export const SNOW: Rgb = [238, 244, 250];
export const FIRE: Rgb = [255, 128, 32];
export const TOXIN: Rgb = [140, 70, 170];
export const CANOPY: Rgb = [24, 70, 40];

export const CALL_COLORS: Record<string, number> = {
  alarm_call: 0xff5a4f,
  food_call: 0x8fd694,
  mating_call: 0xf28bd1,
  contact_call: 0x9ad0ff,
  distress_call: 0xffd166,
  warning_growl: 0xff8c42,
  territorial_call: 0xc7a3ff,
};

export const BAND_NAMES = ["decisive", "hesitant", "dithering"];

export interface Grading {
  color: number;
  alpha: number;
}

export function speciesColor(hue: number, lightness = 0.6, saturation = 0.62): number {
  const [r, g, b] = hslToRgb(hue, saturation, lightness);
  return (r << 16) | (g << 8) | b;
}

export function hslToRgb(hue: number, saturation: number, lightness: number): Rgb {
  const chroma = (1 - Math.abs(2 * lightness - 1)) * saturation;
  const sector = ((hue % 1) + 1) % 1 * 6;
  const x = chroma * (1 - Math.abs((sector % 2) - 1));
  const m = lightness - chroma / 2;
  const table: Rgb[] = [
    [chroma, x, 0],
    [x, chroma, 0],
    [0, chroma, x],
    [0, x, chroma],
    [x, 0, chroma],
    [chroma, 0, x],
  ];
  const [r, g, b] = table[Math.floor(sector) % 6];
  return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)];
}

export function mix(a: Rgb, b: Rgb, t: number): Rgb {
  const clamped = Math.max(0, Math.min(1, t));
  return [a[0] + (b[0] - a[0]) * clamped, a[1] + (b[1] - a[1]) * clamped, a[2] + (b[2] - a[2]) * clamped];
}

export function dayGrading(sun: number, tickOfDay: number, ticksPerDay: number, tidallyLocked: boolean): Grading {
  if (tidallyLocked) {
    return { color: 0x6a3a5a, alpha: 0.18 };
  }
  const hour = (tickOfDay / ticksPerDay) * 24;
  if (sun >= 0.45) {
    return { color: 0xffffff, alpha: 0 };
  }
  if (sun > 0.05) {
    const warmth = hour < 12 ? 0xffc38a : 0xff9a6b;
    return { color: warmth, alpha: 0.35 * (1 - sun / 0.45) };
  }
  return { color: 0x1f2a5c, alpha: 0.62 };
}

export const WEATHER_NAMES = ["clear", "cloudy", "fog", "rain", "storm"];
export const WEATHER_ICONS = ["☀", "☁", "🌫", "🌧", "⛈"];
