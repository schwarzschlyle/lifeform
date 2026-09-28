import type { FieldKeyframe, StaticData, WorldMeta } from "../data/types";
import {
  CANOPY,
  DRY,
  FIRE,
  LUSH,
  type Rgb,
  SNOW,
  TERRAIN_COLORS,
  TOXIN,
  WATER_DEEP,
  WATER_SHALLOW,
  mix,
} from "./theme";

const BYTE = 255;
const WATER_SCALE_M = 3;
const SNOW_SCALE_CM = 150;
const RELIEF = 6;
const SHADE_BASE = 0.82;
const SHADE_GAIN = 0.35;
const LIGHT: [number, number, number] = [-0.55, -0.55, 0.63];
const GRASSY_TERRAIN = new Set([3, 4, 7, 9]);
const WATER_TERRAIN = new Set([0, 1]);
const POOL_DEPTH_M = 0.05;
const DEEP_FLOOD_M = 1;
const SNOW_FULL_CM = 30;
const LUSH_WEIGHT = 0.45;
const DRY_WEIGHT = 0.35;
const CANOPY_WEIGHT = 0.35;
const TOXIN_WEIGHT = 0.5;
const DAY_SIDE: Rgb = [255, 190, 150];
const NIGHT_SIDE: Rgb = [70, 90, 150];
const UPSCALE = 4;
const SOFTEN = "blur(2.2px)";

export class TerrainPainter {
  readonly canvas: HTMLCanvasElement;
  readonly upscale = UPSCALE;
  private readonly cells: HTMLCanvasElement;
  private readonly context: CanvasRenderingContext2D;
  private readonly upscaled: CanvasRenderingContext2D;
  private readonly image: ImageData;
  private readonly shade: Float32Array;

  constructor(
    private readonly meta: WorldMeta,
    private readonly staticData: StaticData,
  ) {
    this.cells = document.createElement("canvas");
    this.cells.width = staticData.width;
    this.cells.height = staticData.height;
    this.context = this.cells.getContext("2d")!;
    this.canvas = document.createElement("canvas");
    this.canvas.width = staticData.width * UPSCALE;
    this.canvas.height = staticData.height * UPSCALE;
    this.upscaled = this.canvas.getContext("2d")!;
    this.upscaled.imageSmoothingEnabled = true;
    this.upscaled.imageSmoothingQuality = "high";
    this.image = this.context.createImageData(staticData.width, staticData.height);
    this.shade = this.hillshade();
  }

  paint(keyframe: FieldKeyframe | null): void {
    const { width, height, terrain } = this.staticData;
    const pixels = this.image.data;
    const layers = keyframe?.layers ?? {};
    for (let cell = 0; cell < width * height; cell += 1) {
      const color = this.cellColor(cell, terrain[cell], layers);
      const shade = this.shade[cell];
      const offset = cell * 4;
      pixels[offset] = Math.min(255, color[0] * shade);
      pixels[offset + 1] = Math.min(255, color[1] * shade);
      pixels[offset + 2] = Math.min(255, color[2] * shade);
      pixels[offset + 3] = 255;
    }
    this.context.putImageData(this.image, 0, 0);
    this.softenWithWrap();
  }

  private softenWithWrap(): void {
    const { width, height } = this.canvas;
    this.upscaled.filter = SOFTEN;
    for (let row = -1; row <= 1; row += 1) {
      for (let column = -1; column <= 1; column += 1) {
        this.upscaled.drawImage(this.cells, column * width, row * height, width, height);
      }
    }
    this.upscaled.filter = "none";
  }

  private cellColor(cell: number, terrain: number, layers: Record<string, Uint8Array>): Rgb {
    let color: Rgb = TERRAIN_COLORS[terrain] ?? [128, 128, 128];
    const vegetation = this.vegetation(cell, layers);
    if (GRASSY_TERRAIN.has(terrain)) {
      color = mix(mix(color, LUSH, LUSH_WEIGHT * vegetation), DRY, DRY_WEIGHT * (1 - vegetation));
    }
    const canopy = (layers.canopy?.[cell] ?? 0) / BYTE;
    color = mix(color, CANOPY, CANOPY_WEIGHT * canopy);
    color = this.water(color, cell, terrain, layers);
    const snow = ((layers.snow?.[cell] ?? 0) / BYTE) * SNOW_SCALE_CM;
    color = mix(color, SNOW, snow / SNOW_FULL_CM);
    color = mix(color, TOXIN, TOXIN_WEIGHT * ((layers.toxin?.[cell] ?? 0) / BYTE));
    color = mix(color, FIRE, (layers.fire?.[cell] ?? 0) / BYTE);
    if (this.meta.tidally_locked) {
      const exposure = this.staticData.substellar[cell] / BYTE;
      color = mix(color, exposure > 0.5 ? DAY_SIDE : NIGHT_SIDE, Math.abs(exposure - 0.5) * 0.9);
    }
    return color;
  }

  private vegetation(cell: number, layers: Record<string, Uint8Array>): number {
    const grass = layers.grass?.[cell] ?? 0;
    const browse = layers.browse?.[cell] ?? 0;
    const fruit = layers.fruit?.[cell] ?? 0;
    return Math.min(1, (grass + browse * 0.6 + fruit * 0.4) / BYTE);
  }

  private water(color: Rgb, cell: number, terrain: number, layers: Record<string, Uint8Array>): Rgb {
    if (WATER_TERRAIN.has(terrain)) {
      return color;
    }
    const depth = ((layers.water?.[cell] ?? 0) / BYTE) * WATER_SCALE_M;
    if (depth < POOL_DEPTH_M) {
      return color;
    }
    const shallow = mix(color, WATER_SHALLOW, Math.min(1, depth / 0.6));
    return depth > DEEP_FLOOD_M ? mix(shallow, WATER_DEEP, (depth - DEEP_FLOOD_M) / 2) : shallow;
  }

  private hillshade(): Float32Array {
    const { width, height, elevation } = this.staticData;
    const shade = new Float32Array(width * height);
    const relief = RELIEF * Math.min(1, this.staticData.elevation_max_m / 1000 + 0.3);
    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        const east = elevation[y * width + ((x + 1) % width)];
        const west = elevation[y * width + ((x - 1 + width) % width)];
        const south = elevation[((y + 1) % height) * width + x];
        const north = elevation[((y - 1 + height) % height) * width + x];
        const dx = ((east - west) / BYTE) * relief;
        const dy = ((south - north) / BYTE) * relief;
        const length = Math.hypot(dx, dy, 1);
        const lit = (-dx * LIGHT[0] - dy * LIGHT[1] + LIGHT[2]) / length;
        shade[y * width + x] = SHADE_BASE + SHADE_GAIN * lit;
      }
    }
    return shade;
  }
}
