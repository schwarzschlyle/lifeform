import { Container, Graphics } from "pixi.js";
import type { EventRecord, Frame } from "../data/types";
import { CELL, type ScreenPoint } from "./CreatureLayer";
import { CALL_COLORS } from "./theme";

const RING_SECONDS = 1.4;
const FLASH_SECONDS = 0.5;
const BURST_SECONDS = 1.2;
const CALL_RING_CELLS = 7;
const BIRTH_COLOR = 0xffe08a;
const DEATH_COLOR = 0xd9d4cc;
const PREDATION_COLOR = 0xe0463c;
const STRIKE_COLOR = 0xff5a4f;
const MISS_COLOR = 0xffffff;
const FIRE_COLOR = 0xff8c1a;
const BURST_PARTICLES = 8;
const MAX_EFFECTS = 400;

interface Effect {
  kind: "ring" | "flash" | "burst" | "cross";
  x: number;
  y: number;
  toX?: number;
  toY?: number;
  color: number;
  radius: number;
  age: number;
  life: number;
}

export class EffectsLayer {
  readonly root = new Container();
  private readonly canvas = new Graphics();
  private effects: Effect[] = [];

  constructor(private readonly callNames: string[]) {
    this.root.addChild(this.canvas);
  }

  spawnForTick(frame: Frame, events: EventRecord[], positions: Map<number, ScreenPoint>): void {
    this.spawnCalls(frame, positions);
    for (const event of events) {
      this.spawnEvent(event, positions);
    }
    if (this.effects.length > MAX_EFFECTS) {
      this.effects = this.effects.slice(-MAX_EFFECTS);
    }
  }

  clear(): void {
    this.effects = [];
    this.canvas.clear();
  }

  update(seconds: number): void {
    this.canvas.clear();
    const survivors: Effect[] = [];
    for (const effect of this.effects) {
      effect.age += seconds;
      if (effect.age < effect.life) {
        this.draw(effect);
        survivors.push(effect);
      }
    }
    this.effects = survivors;
  }

  private spawnCalls(frame: Frame, positions: Map<number, ScreenPoint>): void {
    const columns = frame.organisms;
    for (let index = 0; index < columns.id.length; index += 1) {
      const name = this.callNames[columns.call[index]];
      const color = name ? CALL_COLORS[name] : undefined;
      const point = positions.get(columns.id[index]);
      if (color !== undefined && point) {
        this.push({ kind: "ring", x: point.x, y: point.y, color, radius: CALL_RING_CELLS * CELL, age: 0,
                    life: RING_SECONDS });
      }
    }
  }

  private spawnEvent(event: EventRecord, positions: Map<number, ScreenPoint>): void {
    const at = event.position ? { x: (event.position[0] + 0.5) * CELL, y: (event.position[1] + 0.5) * CELL } : null;
    switch (event.kind) {
      case "birth":
        if (at) this.push({ kind: "burst", ...at, color: BIRTH_COLOR, radius: 2.5 * CELL, age: 0, life: BURST_SECONDS });
        break;
      case "death": {
        const predation = event.payload.cause === "predation";
        if (at) this.push({ kind: "cross", ...at, color: predation ? PREDATION_COLOR : DEATH_COLOR, radius: 1.5 * CELL,
                            age: 0, life: BURST_SECONDS * 1.5 });
        break;
      }
      case "strike": {
        const attacker = positions.get(event.actors[0]);
        const defender = positions.get(event.actors[1]);
        if (attacker && defender) {
          this.push({ kind: "flash", x: attacker.x, y: attacker.y, toX: defender.x, toY: defender.y,
                      color: event.payload.hit ? STRIKE_COLOR : MISS_COLOR, radius: 1, age: 0, life: FLASH_SECONDS });
        }
        break;
      }
      case "fire_start":
      case "eruption":
        if (at) this.push({ kind: "ring", ...at, color: FIRE_COLOR, radius: 12 * CELL, age: 0, life: RING_SECONDS * 2 });
        break;
      default:
        break;
    }
  }

  private push(effect: Effect): void {
    this.effects.push(effect);
  }

  private draw(effect: Effect): void {
    const progress = effect.age / effect.life;
    const fade = 1 - progress;
    const g = this.canvas;
    if (effect.kind === "ring") {
      g.circle(effect.x, effect.y, effect.radius * (0.2 + 0.8 * progress))
        .stroke({ width: 1.2, color: effect.color, alpha: 0.75 * fade });
    } else if (effect.kind === "flash" && effect.toX !== undefined && effect.toY !== undefined) {
      g.moveTo(effect.x, effect.y).lineTo(effect.toX, effect.toY).stroke({ width: 2, color: effect.color, alpha: fade });
      g.circle(effect.toX, effect.toY, CELL * (0.6 + progress)).fill({ color: effect.color, alpha: 0.35 * fade });
    } else if (effect.kind === "burst") {
      for (let particle = 0; particle < BURST_PARTICLES; particle += 1) {
        const angle = (particle / BURST_PARTICLES) * Math.PI * 2;
        const distance = effect.radius * progress;
        g.circle(effect.x + Math.cos(angle) * distance, effect.y + Math.sin(angle) * distance, 1.2)
          .fill({ color: effect.color, alpha: fade });
      }
    } else if (effect.kind === "cross") {
      const size = effect.radius;
      g.moveTo(effect.x - size, effect.y - size).lineTo(effect.x + size, effect.y + size)
        .moveTo(effect.x + size, effect.y - size).lineTo(effect.x - size, effect.y + size)
        .stroke({ width: 1.4, color: effect.color, alpha: 0.9 * fade });
    }
  }
}

