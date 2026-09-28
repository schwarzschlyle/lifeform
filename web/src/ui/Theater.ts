import type { Ticker } from "pixi.js";
import { PopulationChart } from "../charts/PopulationChart";
import { ApiClient } from "../data/ApiClient";
import { ReplayStore } from "../data/ReplayStore";
import type { BundleIndex, Frame, WorldMeta } from "../data/types";
import { PlaybackClock } from "../playback/PlaybackClock";
import { WorldView } from "../render/WorldView";
import { element } from "./dom";
import { Inspector } from "./Inspector";
import { Legend } from "./Legend";
import { Timeline } from "./Timeline";
import { TopBar } from "./TopBar";

const MAX_EFFECT_TICK_GAP = 3;
const LIVE_REFRESH_MS = 15000;

export class Theater {
  readonly root = element("div", "theater");
  private readonly stage = element("div", "stage");
  private store: ReplayStore;
  private clock!: PlaybackClock;
  private view!: WorldView;
  private topBar!: TopBar;
  private timeline!: Timeline;
  private legend!: Legend;
  private inspector!: Inspector;
  private chart!: PopulationChart;
  private selected: number | null = null;
  private highlight: number | null = null;
  private shownTick = -1;
  private liveTimer = 0;

  constructor(api: ApiClient, runId: string, worldSlug: string, private readonly startTick = 0,
              private readonly startSelection: number | null = null) {
    this.store = new ReplayStore(api, runId, worldSlug);
  }

  async load(): Promise<void> {
    const loading = element("div", "loading", "Loading world…");
    this.root.append(loading);
    await this.store.load();
    loading.remove();
    this.clock = new PlaybackClock(this.store.lastTick);
    this.clock.seek(this.startTick);
    this.view = new WorldView(this.store);
    this.topBar = new TopBar(this.store);
    this.timeline = new Timeline(this.store, this.clock);
    this.legend = new Legend(this.store);
    this.inspector = new Inspector(this.store);
    this.chart = new PopulationChart(this.store);
    this.root.append(this.stage, this.topBar.root, this.legend.root, this.inspector.root, this.chart.root,
                     this.timeline.root);
    await this.view.mount(this.stage);
    this.wire();
    this.chart.draw();
    this.timeline.drawMarkers();
    if (this.startSelection !== null) {
      this.select(this.startSelection);
    }
    this.view.app.ticker.add((ticker) => this.frame(ticker));
    if (this.store.meta.status === "running") {
      this.liveTimer = window.setInterval(() => void this.refreshLive(), LIVE_REFRESH_MS);
    }
  }

  destroy(): void {
    window.clearInterval(this.liveTimer);
    this.view?.app.destroy(true, { children: true });
  }

  private wire(): void {
    this.view.onPick = (organismId) => this.select(organismId);
    this.inspector.onClose = () => this.select(null);
    this.inspector.onFollow = (organismId) => {
      this.view.follow = organismId;
      this.view.focusOn(organismId);
    };
    this.legend.onHighlight = (species) => {
      this.highlight = species;
    };
    this.chart.onSeek = (tick) => this.clock.seek(tick);
    window.addEventListener("keydown", (event) => this.key(event));
    window.addEventListener("resize", () => {
      this.chart.draw();
      this.timeline.drawMarkers();
    });
  }

  private select(organismId: number | null): void {
    this.selected = organismId;
    if (organismId === null) {
      this.view.follow = null;
    }
    this.inspector.select(organismId);
  }

  private key(event: KeyboardEvent): void {
    if (event.target instanceof HTMLInputElement) {
      return;
    }
    const day = this.store.meta.calendar.ticks_per_day;
    const actions: Record<string, () => void> = {
      " ": () => this.clock.toggle(),
      ArrowRight: () => this.clock.step(event.shiftKey ? day : 1),
      ArrowLeft: () => this.clock.step(event.shiftKey ? -day : -1),
      "]": () => this.clock.faster(),
      "[": () => this.clock.slower(),
      f: () => {
        if (this.selected !== null) {
          this.view.follow = this.selected;
        }
      },
      Escape: () => this.select(null),
    };
    const action = actions[event.key];
    if (action) {
      event.preventDefault();
      action();
    }
  }

  private frame(ticker: Ticker): void {
    const seconds = ticker.deltaMS / 1000;
    this.clock.advance(seconds);
    const tick = this.clock.tick;
    const current = this.store.frameAt(tick);
    if (current === null) {
      return;
    }
    const next = tick < this.store.lastTick ? (this.store.frameAt(tick + 1) ?? current) : current;
    const fraction = next === current ? 0 : this.clock.fraction;
    if (tick !== this.shownTick) {
      this.onTick(current, tick);
    }
    this.view.render(current, next, fraction, this.selected, this.highlight, seconds);
  }

  private onTick(frame: Frame, tick: number): void {
    const gap = tick - this.shownTick;
    if (gap > 0 && gap <= MAX_EFFECT_TICK_GAP) {
      this.view.spawnEffects(frame, this.store.eventsBetween(this.shownTick, tick));
    } else {
      this.view.clearEffects();
    }
    this.shownTick = tick;
    this.topBar.update(frame);
    this.legend.update(frame);
    this.timeline.update(tick);
    this.chart.moveCursor(tick);
    this.inspector.update(frame, this.clock.playing);
  }

  private async refreshLive(): Promise<void> {
    const api = new ApiClient();
    const base = `runs/${this.store.runId}/worlds/${this.store.worldSlug}`;
    this.store.index = await api.json<BundleIndex>(`${base}/files/index.json`);
    this.store.meta = await api.json<WorldMeta>(base);
    await this.store.refreshHistory();
    this.clock.setMaxTick(this.store.lastTick);
    this.chart.draw();
    this.timeline.drawMarkers();
    if (this.store.meta.status !== "running") {
      window.clearInterval(this.liveTimer);
    }
  }
}
