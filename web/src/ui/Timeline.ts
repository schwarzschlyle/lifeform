import type { ReplayStore } from "../data/ReplayStore";
import type { PlaybackClock } from "../playback/PlaybackClock";
import { element } from "./dom";

const MARKER_COLORS: Record<string, string> = {
  birth: "#ffe08a",
  death: "#d9d4cc",
  speciation: "#9ef0ff",
  extinction: "#ff6b6b",
  fire_start: "#ff8c1a",
  eruption: "#ff5a1a",
  rift_open: "#4da3ff",
  outbreak: "#c6f000",
  drought_start: "#e0b060",
};
const MAJOR_EVENTS = new Set(["speciation", "extinction", "fire_start", "eruption", "rift_open", "outbreak",
                              "drought_start"]);
const MARKER_HEIGHT = 18;

export class Timeline {
  readonly root = element("footer", "timeline glass");
  private readonly playButton = element("button", "play", "▶");
  private readonly slider = element("input", "scrubber");
  private readonly label = element("div", "tick-label");
  private readonly speedLabel = element("button", "speed", "2×");
  private readonly markers = element("canvas", "markers");

  constructor(private readonly store: ReplayStore, private readonly clock: PlaybackClock) {
    this.slider.type = "range";
    this.slider.min = "0";
    this.slider.max = String(store.lastTick);
    this.slider.step = "1";
    const back = element("button", "step", "⏮");
    const forward = element("button", "step", "⏭");
    const slower = element("button", "step", "−");
    const faster = element("button", "step", "+");
    back.title = "Back one day";
    forward.title = "Forward one day";
    const track = element("div", "track");
    track.append(this.markers, this.slider);
    this.root.append(this.playButton, back, forward, slower, this.speedLabel, faster, track, this.label);
    const day = store.meta.calendar.ticks_per_day;
    this.playButton.addEventListener("click", () => clock.toggle());
    back.addEventListener("click", () => clock.step(-day));
    forward.addEventListener("click", () => clock.step(day));
    slower.addEventListener("click", () => clock.slower());
    faster.addEventListener("click", () => clock.faster());
    this.slider.addEventListener("input", () => clock.seek(Number(this.slider.value)));
    clock.onChange(() => this.refreshControls());
    this.refreshControls();
  }

  drawMarkers(): void {
    const width = this.markers.clientWidth || 600;
    this.markers.width = width;
    this.markers.height = MARKER_HEIGHT;
    const context = this.markers.getContext("2d")!;
    context.clearRect(0, 0, width, MARKER_HEIGHT);
    const span = Math.max(1, this.store.lastTick);
    for (const event of this.store.events) {
      const color = MARKER_COLORS[event.kind];
      if (!color) {
        continue;
      }
      const major = MAJOR_EVENTS.has(event.kind);
      context.fillStyle = color;
      context.globalAlpha = major ? 0.95 : 0.25;
      const x = (event.tick / span) * width;
      context.fillRect(x, major ? 0 : MARKER_HEIGHT / 2, major ? 2 : 1, major ? MARKER_HEIGHT : MARKER_HEIGHT / 2);
    }
  }

  update(tick: number): void {
    this.slider.value = String(tick);
    const day = this.store.meta.calendar.ticks_per_day;
    this.label.textContent = `tick ${tick} / ${this.store.lastTick} · day ${Math.floor(tick / day) + 1}`;
  }

  private refreshControls(): void {
    this.playButton.textContent = this.clock.playing ? "❚❚" : "▶";
    this.speedLabel.textContent = `${this.clock.speed}× ticks/s`;
  }
}
