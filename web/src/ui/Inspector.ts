import type { ReplayStore } from "../data/ReplayStore";
import type { DecisionRecord, Frame } from "../data/types";
import { BAND_NAMES, speciesColor } from "../render/theme";
import { clear, colorHex, element, titleCase } from "./dom";

const BYTE = 255;
const TOP_OPTIONS = 14;
const FETCH_INTERVAL_MS = 1200;
const VITALS: [keyof Frame["organisms"], string][] = [
  ["energy", "energy"],
  ["hydration", "water"],
  ["health", "health"],
  ["fear", "fear"],
  ["sleep", "sleep pressure"],
];
const STATE_SECTIONS = ["feelings", "conditions", "around_you", "smells", "sounds", "memories", "recent"];

export class Inspector {
  readonly root = element("aside", "inspector glass hidden");
  private readonly header = element("div", "inspector-header");
  private readonly vitals = element("div", "vitals");
  private readonly now = element("div", "now");
  private readonly choice = element("div", "choice");
  private readonly mind = element("div", "mind");
  private readonly traits = element("div", "traits");
  private selected: number | null = null;
  private decisionKey = "";
  private lastFetch = 0;
  onFollow: (organismId: number) => void = () => undefined;
  onClose: () => void = () => undefined;

  constructor(private readonly store: ReplayStore) {
    const close = element("button", "close", "×");
    close.addEventListener("click", () => this.onClose());
    this.root.append(close, this.header, this.vitals, this.now,
                     element("h3", "", "What it chose"), this.choice,
                     element("h3", "", "What it sensed and felt"), this.mind,
                     element("h3", "", "Heritable traits"), this.traits);
  }

  select(organismId: number | null): void {
    this.selected = organismId;
    this.decisionKey = "";
    this.root.classList.toggle("hidden", organismId === null);
    if (organismId !== null) {
      this.renderHeader(organismId);
      this.renderTraits(organismId);
    }
  }

  update(frame: Frame, playing: boolean): void {
    if (this.selected === null) {
      return;
    }
    const index = frame.organisms.id.indexOf(this.selected);
    if (index < 0) {
      this.renderGone(frame.tick);
      return;
    }
    this.renderVitals(frame, index);
    this.renderNow(frame, index);
    const now = performance.now();
    const key = `${this.selected}@${frame.tick}`;
    if (key !== this.decisionKey && (!playing || now - this.lastFetch > FETCH_INTERVAL_MS)) {
      this.decisionKey = key;
      this.lastFetch = now;
      void this.loadDecision(frame.tick, this.selected, key);
    }
  }

  private renderHeader(organismId: number): void {
    const summary = this.store.organisms.get(organismId);
    clear(this.header);
    if (!summary) {
      this.header.append(element("h2", "", `Animal #${organismId}`));
      return;
    }
    const swatch = element("span", "swatch large");
    swatch.style.background = colorHex(speciesColor(this.store.speciesHue(summary.species)));
    const name = element("h2", "", summary.name);
    name.prepend(swatch);
    const follow = element("button", "follow", "follow");
    follow.addEventListener("click", () => this.onFollow(organismId));
    const parents = summary.mother ? `child of ${this.nameOf(summary.mother)} and ${this.nameOf(summary.father)}`
      : `founder (${summary.archetype ?? "unknown"})`;
    this.header.append(name, follow,
                       element("div", "subtitle", `${summary.species_name} · ${summary.sex} · generation ${summary.generation}`),
                       element("div", "subtitle", `${parents} · ${summary.offspring} offspring`));
  }

  private nameOf(organismId: number | null): string {
    if (organismId === null) {
      return "unknown";
    }
    return this.store.organisms.get(organismId)?.name ?? `#${organismId}`;
  }

  private renderVitals(frame: Frame, index: number): void {
    clear(this.vitals);
    for (const [column, label] of VITALS) {
      const value = (frame.organisms[column][index] as number) / BYTE;
      const row = element("div", "vital");
      const bar = element("div", "bar");
      const fill = element("div", `fill ${column}`);
      fill.style.width = `${Math.round(value * 100)}%`;
      bar.append(fill);
      row.append(element("span", "label", label), bar);
      this.vitals.append(row);
    }
    const ageDays = frame.organisms.age[index] / this.store.meta.calendar.ticks_per_day;
    const mass = frame.organisms.mass[index] / 1000;
    this.vitals.append(element("div", "subtitle", `age ${ageDays.toFixed(1)} days · ${mass.toFixed(2)} kg`));
  }

  private renderNow(frame: Frame, index: number): void {
    const columns = frame.organisms;
    const verb = this.store.meta.verbs[columns.verb[index]] ?? "stalled";
    const call = this.store.meta.call_names?.[columns.call[index]] ?? "silent";
    const band = BAND_NAMES[columns.band[index]] ?? "";
    const confidence = Math.round((columns.confidence[index] / BYTE) * 100);
    clear(this.now);
    this.now.append(element("div", "now-verb", titleCase(verb)),
                    element("div", "subtitle", `${band} · confidence ${confidence}% · effort ${columns.effort[index]}`
                      + (call !== "silent" ? ` · ${titleCase(call)}` : "")));
  }

  private async loadDecision(tick: number, organismId: number, key: string): Promise<void> {
    const decision = await this.store.decision(tick, organismId);
    if (key !== this.decisionKey) {
      return;
    }
    this.renderChoice(decision);
    this.renderMind(decision);
  }

  private renderChoice(decision: DecisionRecord | null): void {
    clear(this.choice);
    if (decision === null) {
      this.choice.append(element("div", "muted", "No decision recorded for this tick."));
      return;
    }
    const probabilities = decision.answers.action.probabilities;
    const descriptions = new Map(decision.menu);
    const ranked = Object.entries(probabilities).sort((a, b) => b[1] - a[1]).slice(0, TOP_OPTIONS);
    for (const [key, probability] of ranked) {
      const row = element("div", `option${key === decision.sampled ? " sampled" : ""}`);
      const bar = element("div", "bar");
      const fill = element("div", "fill");
      fill.style.width = `${Math.max(1, Math.round(probability * 100))}%`;
      bar.append(fill);
      const marker = key === decision.sampled ? "▶ " : key === decision.argmax ? "★ " : "";
      row.title = descriptions.get(key) ?? key;
      row.append(element("span", "option-key", `${marker}${key}`), bar,
                 element("span", "option-p", `${(probability * 100).toFixed(1)}%`));
      this.choice.append(row);
    }
    const threat = decision.answers.threat.score.toFixed(2);
    const effort = decision.answers.effort.score.toFixed(2);
    this.choice.append(element("div", "subtitle",
      `confidence ${(decision.answers.action.confidence ?? 0).toFixed(2)} · ${decision.band}`
      + ` · threat ${threat}/4 · effort ${effort}/3 · call ${decision.call} · focus ${decision.focus ?? "none"}`),
      element("div", "muted", `${decision.model} · ${decision.tokens} tokens · ${decision.latency_ms} ms`
        + (decision.outcome ? ` · outcome: ${decision.outcome}` : "")));
  }

  private renderMind(decision: DecisionRecord | null): void {
    clear(this.mind);
    const state = decision?.state;
    if (!state) {
      this.mind.append(element("div", "muted", "State text not recorded (decision detail was not 'full')."));
      return;
    }
    const you = state.you as Record<string, unknown> | undefined;
    if (you) {
      this.mind.append(element("p", "you", String(you.kind ?? "")));
      if (you.temperament) {
        this.mind.append(element("p", "muted", `temperament: ${String(you.temperament)}`));
      }
    }
    for (const section of STATE_SECTIONS) {
      const value = state[section];
      if (value === undefined) {
        continue;
      }
      const block = element("div", "state-block");
      block.append(element("div", "state-title", titleCase(section)));
      block.append(this.renderValue(value));
      this.mind.append(block);
    }
    const raw = element("details", "raw");
    raw.append(element("summary", "", "raw state sent to Jev"), element("pre", "", JSON.stringify(state, null, 1)));
    this.mind.append(raw);
  }

  private renderValue(value: unknown): HTMLElement {
    if (Array.isArray(value)) {
      const list = element("ul", "state-list");
      for (const item of value) {
        list.append(element("li", "", typeof item === "string" ? item : this.describe(item)));
      }
      return list;
    }
    if (value && typeof value === "object") {
      const list = element("ul", "state-list");
      for (const [key, inner] of Object.entries(value)) {
        list.append(element("li", "", `${titleCase(key)}: ${String(inner)}`));
      }
      return list;
    }
    return element("span", "", String(value));
  }

  private describe(item: unknown): string {
    if (item && typeof item === "object") {
      const record = item as Record<string, string>;
      const parts = [record.id, record.what, record.where, record.doing, record.facts, record.you_remember];
      return parts.filter(Boolean).join(" · ");
    }
    return String(item);
  }

  private renderTraits(organismId: number): void {
    const summary = this.store.organisms.get(organismId);
    clear(this.traits);
    if (!summary) {
      return;
    }
    const diet = summary.diet.map((value) => Math.round(value * 100));
    this.traits.append(element("div", "subtitle",
      `adult mass ${summary.adult_mass_kg.toFixed(1)} kg · diet fiber ${diet[0]}% / soft ${diet[1]}% / animal ${diet[2]}%`));
    const grid = element("div", "trait-grid");
    for (const [name, value] of Object.entries(summary.traits)) {
      grid.append(element("span", "trait-name", titleCase(name)), element("span", "trait-value", value.toFixed(2)));
    }
    this.traits.append(grid);
    if (summary.instincts.length) {
      this.traits.append(element("div", "subtitle", `instincts: ${summary.instincts.map(titleCase).join(", ")}`));
    }
  }

  private renderGone(tick: number): void {
    const summary = this.selected !== null ? this.store.organisms.get(this.selected) : undefined;
    clear(this.now);
    const cause = summary?.death_cause ? `died of ${summary.death_cause} at tick ${summary.death_tick}` : "not alive now";
    this.now.append(element("div", "now-verb", summary?.birth_tick !== undefined && summary.birth_tick > tick
      ? "not born yet" : cause));
  }
}
