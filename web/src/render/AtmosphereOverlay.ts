import { Container, Graphics } from "pixi.js";
import type { Clock } from "../data/types";
import { dayGrading } from "./theme";

const RAIN_DROPS = 160;
const SNOW_FLAKES = 120;
const RAIN_LENGTH = 14;
const RAIN_SPEED = 900;
const SNOW_SPEED = 60;
const FOG_ALPHA = 0.18;
const CLOUD_ALPHA = 0.08;
const WEATHER_CLOUDY = 1;
const WEATHER_FOG = 2;
const WEATHER_RAIN = 3;
const WEATHER_STORM = 4;
const FREEZING_C = 0;

interface Particle {
  x: number;
  y: number;
}

export class AtmosphereOverlay {
  readonly root = new Container();
  private readonly grading = new Graphics();
  private readonly weather = new Graphics();
  private readonly particles: Particle[] = [];
  private width = 1;
  private height = 1;

  constructor(private readonly ticksPerDay: number, private readonly tidallyLocked: boolean) {
    this.root.addChild(this.weather, this.grading);
    for (let index = 0; index < Math.max(RAIN_DROPS, SNOW_FLAKES); index += 1) {
      this.particles.push({ x: Math.random(), y: Math.random() });
    }
  }

  resize(width: number, height: number): void {
    this.width = width;
    this.height = height;
  }

  update(clock: Clock, seconds: number): void {
    const grading = dayGrading(clock.sun, clock.tick_of_day, this.ticksPerDay, this.tidallyLocked);
    this.grading.clear();
    if (grading.alpha > 0) {
      this.grading.rect(0, 0, this.width, this.height).fill({ color: grading.color, alpha: grading.alpha });
    }
    this.drawWeather(clock, seconds);
  }

  private drawWeather(clock: Clock, seconds: number): void {
    const g = this.weather;
    g.clear();
    if (clock.weather === WEATHER_CLOUDY) {
      g.rect(0, 0, this.width, this.height).fill({ color: 0x9aa4b1, alpha: CLOUD_ALPHA });
    }
    if (clock.weather === WEATHER_FOG) {
      g.rect(0, 0, this.width, this.height).fill({ color: 0xe8eef4, alpha: FOG_ALPHA });
    }
    if (clock.weather !== WEATHER_RAIN && clock.weather !== WEATHER_STORM) {
      return;
    }
    const snowing = clock.temperature < FREEZING_C;
    const count = snowing ? SNOW_FLAKES : RAIN_DROPS * (clock.weather === WEATHER_STORM ? 1 : 0.6);
    const [windX] = clock.wind;
    for (let index = 0; index < count; index += 1) {
      const particle = this.particles[index];
      const fall = (snowing ? SNOW_SPEED : RAIN_SPEED) * seconds / this.height;
      particle.y = (particle.y + fall) % 1;
      particle.x = (particle.x + windX * seconds * 0.05 + 1) % 1;
      const x = particle.x * this.width;
      const y = particle.y * this.height;
      if (snowing) {
        g.circle(x, y, 1.6).fill({ color: 0xffffff, alpha: 0.8 });
      } else {
        g.moveTo(x, y).lineTo(x + windX * 6, y + RAIN_LENGTH).stroke({ width: 1, color: 0xcfe3ff, alpha: 0.45 });
      }
    }
  }
}
