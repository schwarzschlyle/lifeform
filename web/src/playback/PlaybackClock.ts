export const SPEEDS = [0.25, 0.5, 1, 2, 4, 8, 16, 32];
const DEFAULT_SPEED_INDEX = 3;

type Listener = () => void;

export class PlaybackClock {
  time = 0;
  playing = false;
  private speedIndex = DEFAULT_SPEED_INDEX;
  private listeners: Listener[] = [];

  constructor(private maxTick: number) {}

  get speed(): number {
    return SPEEDS[this.speedIndex];
  }

  get tick(): number {
    return Math.floor(this.time);
  }

  get fraction(): number {
    return this.time - Math.floor(this.time);
  }

  setMaxTick(maxTick: number): void {
    this.maxTick = maxTick;
  }

  onChange(listener: Listener): void {
    this.listeners.push(listener);
  }

  advance(seconds: number): void {
    if (!this.playing) {
      return;
    }
    this.time = Math.min(this.maxTick, this.time + seconds * this.speed);
    if (this.time >= this.maxTick) {
      this.playing = false;
      this.notify();
    }
  }

  toggle(): void {
    if (!this.playing && this.time >= this.maxTick) {
      this.time = 0;
    }
    this.playing = !this.playing;
    this.notify();
  }

  seek(tick: number): void {
    this.time = Math.max(0, Math.min(this.maxTick, tick));
    this.notify();
  }

  step(ticks: number): void {
    this.playing = false;
    this.seek(Math.round(this.time) + ticks);
  }

  faster(): void {
    this.speedIndex = Math.min(SPEEDS.length - 1, this.speedIndex + 1);
    this.notify();
  }

  slower(): void {
    this.speedIndex = Math.max(0, this.speedIndex - 1);
    this.notify();
  }

  private notify(): void {
    for (const listener of this.listeners) {
      listener();
    }
  }
}
