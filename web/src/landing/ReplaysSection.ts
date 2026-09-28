import { BrainIdentity } from "../data/BrainIdentity";
import type { RunManifest, RunWorldEntry } from "../data/types";
import { element } from "../ui/dom";
import type { LandingSection } from "./LandingSection";
import { paletteGradient } from "./palettes";
import { brainChip, code, sectionFrame } from "./widgets";


export class ReplaysSection implements LandingSection {
  readonly id = "replays";
  readonly navLabel = "Replays";

  constructor(
    private readonly runs: RunManifest[],
    private readonly failure: string | null,
  ) {}

  render(): HTMLElement {
    const section = sectionFrame({
      id: this.id,
      kicker: "Recorded runs",
      title: "Replays",
      lead: "Every run is recorded tick by tick. Replays read the recording and never call Jev again. Pick a world "
        + "to watch it; click any animal to see exactly what it was shown and how Jev answered.",
    });
    if (this.failure !== null) {
      section.append(element("p", "notice", `Could not reach the replay server: ${this.failure}`));
    } else if (this.runs.length === 0) {
      const notice = element("p", "notice", "No runs yet. Start one with ");
      notice.append(code("lifeform run <world>"), document.createTextNode(" (see the guide at the bottom)."));
      section.append(notice);
    }
    section.append(...this.runs.map((run) => this.runBlock(run)));
    return section;
  }

  private runBlock(run: RunManifest): HTMLElement {
    const block = element("div", "run");
    const heading = element("div", "run-heading");
    heading.append(element("h3", "run-title", run.label || run.run_id), this.brainBadge(run));
    const totals = `${run.created} · ${run.totals.calls.toLocaleString()} calls · $${run.totals.usd.toFixed(4)}`
      + ` · ${run.status}`;
    const grid = element("div", "cards");
    grid.append(...run.worlds.map((world) => this.worldCard(run, world)));
    block.append(heading, element("div", "muted", totals), grid);
    return block;
  }

  private brainBadge(run: RunManifest): HTMLElement {
    const brain = new BrainIdentity(run);
    const badge = brainChip(brain.badgeText, brain.tone);
    badge.title = brain.servedModel;
    return badge;
  }

  private worldCard(run: RunManifest, world: RunWorldEntry): HTMLElement {
    const card = element("a", "card", "", { href: `#/run/${encodeURIComponent(run.run_id)}/${world.slug}` });
    card.style.background = paletteGradient(world.palette);
    const ticks = world.ticks !== undefined ? ` · ${world.ticks} ticks` : "";
    const alive = world.population !== undefined ? ` · ${world.population} alive` : "";
    card.append(element("div", "card-title", world.title), element("div", "card-biome", world.biome),
                element("div", "card-status", `${world.status}${ticks}${alive}`));
    return card;
  }
}
