import type { ReplayStore } from "../data/ReplayStore";
import { BrainIdentity } from "../data/BrainIdentity";
import type { Frame } from "../data/types";
import { WEATHER_ICONS, WEATHER_NAMES } from "../render/theme";
import { element } from "./dom";

export class TopBar {
  readonly root = element("header", "topbar glass");
  private readonly clockText = element("div", "clock");
  private readonly statsText = element("div", "stats");

  constructor(store: ReplayStore) {
    const title = element("div", "title-block");
    const back = element("a", "back", "← worlds", { href: "#/" });
    title.append(back, element("h1", "world-title", store.meta.title),
                 element("div", "world-subtitle", `${store.meta.biome} · ${store.meta.question}`));
    const brain = new BrainIdentity(store.run);
    const badge = element("span", `badge ${brain.tone}`, brain.badgeText, { title: brain.servedModel });
    this.root.append(title, this.clockText, this.statsText, badge);
  }

  update(frame: Frame): void {
    const clock = frame.clock;
    const weather = `${WEATHER_ICONS[clock.weather] ?? ""} ${WEATHER_NAMES[clock.weather] ?? ""}`;
    this.clockText.textContent = `Day ${clock.day + 1} · ${clock.phase} · ${clock.season_word} · ${weather} · `
      + `${clock.temperature.toFixed(0)}°C`;
    this.statsText.textContent = `tick ${frame.tick} · ${frame.organisms.id.length} animals`;
  }
}
