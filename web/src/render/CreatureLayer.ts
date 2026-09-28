import { Container, Graphics } from "pixi.js";
import type { ReplayStore } from "../data/ReplayStore";
import type { Frame } from "../data/types";
import { speciesColor } from "./theme";

export const CELL = 8;
const BASE_RADIUS = 1.1;
const MASS_RADIUS = 1.35;
const MIN_RADIUS = 1.4;
const MAX_RADIUS = 8;
const ASLEEP_FLAG = 1;
const HIDDEN_FLAG = 1 << 1;
const DIMMED_ALPHA = 0.25;
const HIDDEN_ALPHA = 0.45;
const ASLEEP_ALPHA = 0.6;
const CARNIVORE_DIET = 0.5;
const HEADING_STEP_DEGREES = 45;

export interface ScreenPoint {
  x: number;
  y: number;
}

class CreatureGlyph {
  readonly root = new Container();
  private readonly body = new Graphics();
  private readonly ring = new Graphics();
  private radius = 0;
  private signature = "";
  private selected = false;

  constructor() {
    this.root.addChild(this.ring, this.body);
  }

  redraw(radius: number, color: number, carnivore: boolean, male: boolean): void {
    const signature = `${radius.toFixed(1)}|${color}|${carnivore}|${male}`;
    if (signature === this.signature) {
      return;
    }
    this.signature = signature;
    this.radius = radius;
    const outline = 0x111418;
    this.body.clear();
    this.body.ellipse(0, 0, radius * 1.25, radius * 0.85).fill({ color }).stroke({ width: 0.6, color: outline, alpha: 0.8 });
    this.body.circle(radius * 1.15, 0, radius * 0.42).fill({ color: carnivore ? 0xd9534f : 0xf3e9d2 });
    if (male) {
      this.body.circle(-radius * 0.35, 0, radius * 0.22).fill({ color: outline, alpha: 0.35 });
    }
  }

  select(selected: boolean): void {
    if (selected === this.selected) {
      return;
    }
    this.selected = selected;
    this.ring.clear();
    if (selected) {
      this.ring.circle(0, 0, this.radius * 2.2).stroke({ width: 1.2, color: 0xffffff, alpha: 0.9 });
    }
  }
}

export class CreatureLayer {
  readonly root = new Container();
  readonly positions = new Map<number, ScreenPoint>();
  private readonly glyphs = new Map<number, CreatureGlyph>();

  constructor(
    private readonly store: ReplayStore,
    private readonly width: number,
    private readonly height: number,
  ) {}

  update(previous: Frame, next: Frame, fraction: number, selected: number | null, highlight: number | null,
         glyphScale: number): void {
    const indexOfPrevious = new Map<number, number>();
    previous.organisms.id.forEach((id, index) => indexOfPrevious.set(id, index));
    const alive = new Set<number>();
    const eased = fraction * fraction * (3 - 2 * fraction);
    const columns = next.organisms;
    for (let index = 0; index < columns.id.length; index += 1) {
      const id = columns.id[index];
      alive.add(id);
      const glyph = this.glyph(id);
      const point = this.interpolate(previous, next, indexOfPrevious.get(id), index, eased);
      this.positions.set(id, point);
      glyph.root.position.set(point.x, point.y);
      glyph.root.scale.set(glyphScale);
      glyph.root.rotation = ((columns.heading[index] * HEADING_STEP_DEGREES - 90) * Math.PI) / 180;
      this.style(glyph, next, index, selected, highlight);
    }
    for (const [id, glyph] of this.glyphs) {
      if (!alive.has(id)) {
        glyph.root.destroy({ children: true });
        this.glyphs.delete(id);
        this.positions.delete(id);
      }
    }
  }

  nearest(worldX: number, worldY: number, maxDistance: number): number | null {
    let best: number | null = null;
    let bestDistance = maxDistance;
    const spanX = this.width * CELL;
    const spanY = this.height * CELL;
    for (const [id, point] of this.positions) {
      const dx = wrapDelta(point.x - worldX, spanX);
      const dy = wrapDelta(point.y - worldY, spanY);
      const distance = Math.hypot(dx, dy);
      if (distance < bestDistance) {
        best = id;
        bestDistance = distance;
      }
    }
    return best;
  }

  private glyph(id: number): CreatureGlyph {
    let glyph = this.glyphs.get(id);
    if (!glyph) {
      glyph = new CreatureGlyph();
      this.glyphs.set(id, glyph);
      this.root.addChild(glyph.root);
    }
    return glyph;
  }

  private style(glyph: CreatureGlyph, frame: Frame, index: number, selected: number | null,
                highlight: number | null): void {
    const columns = frame.organisms;
    const id = columns.id[index];
    const species = columns.species[index];
    const massKg = columns.mass[index] / 1000;
    const summary = this.store.organisms.get(id);
    const carnivore = (summary?.diet?.[2] ?? 0) >= CARNIVORE_DIET;
    const radius = Math.max(MIN_RADIUS, Math.min(MAX_RADIUS, BASE_RADIUS + MASS_RADIUS * Math.cbrt(massKg)));
    glyph.redraw(radius, speciesColor(this.store.speciesHue(species)), carnivore, columns.sex[index] === 1);
    glyph.select(id === selected);
    const flags = columns.flags[index];
    let alpha = 1;
    if (flags & HIDDEN_FLAG) {
      alpha = HIDDEN_ALPHA;
    } else if (flags & ASLEEP_FLAG) {
      alpha = ASLEEP_ALPHA;
    }
    if (highlight !== null && species !== highlight) {
      alpha = Math.min(alpha, DIMMED_ALPHA);
    }
    glyph.root.alpha = alpha;
  }

  private interpolate(previous: Frame, next: Frame, previousIndex: number | undefined, index: number,
                      fraction: number): ScreenPoint {
    const endX = next.organisms.x[index];
    const endY = next.organisms.y[index];
    if (previousIndex === undefined) {
      return this.toWorld(endX, endY);
    }
    const startX = previous.organisms.x[previousIndex];
    const startY = previous.organisms.y[previousIndex];
    const path = next.paths[String(next.organisms.id[index])] ?? [];
    const waypoints: [number, number][] = [[startX, startY]];
    for (let step = 0; step + 1 < path.length; step += 2) {
      waypoints.push([path[step], path[step + 1]]);
    }
    if (waypoints.length === 1) {
      waypoints.push([endX, endY]);
    }
    const unwrapped = this.unwrap(waypoints);
    const segments = unwrapped.length - 1;
    const position = fraction * segments;
    const segment = Math.min(segments - 1, Math.floor(position));
    const local = position - segment;
    const [ax, ay] = unwrapped[segment];
    const [bx, by] = unwrapped[segment + 1];
    return this.toWorld(ax + (bx - ax) * local, ay + (by - ay) * local);
  }

  private unwrap(waypoints: [number, number][]): [number, number][] {
    const result: [number, number][] = [waypoints[0]];
    for (let index = 1; index < waypoints.length; index += 1) {
      const [px, py] = result[index - 1];
      const [x, y] = waypoints[index];
      result.push([px + wrapDelta(x - px, this.width), py + wrapDelta(y - py, this.height)]);
    }
    return result;
  }

  private toWorld(x: number, y: number): ScreenPoint {
    const spanX = this.width * CELL;
    const spanY = this.height * CELL;
    return {
      x: (((x + 0.5) * CELL) % spanX + spanX) % spanX,
      y: (((y + 0.5) * CELL) % spanY + spanY) % spanY,
    };
  }
}

export function wrapDelta(delta: number, span: number): number {
  return ((((delta + span / 2) % span) + span) % span) - span / 2;
}
