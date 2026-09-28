import type { BrainFacts, BrainRegistryFacts, JevFacts } from "../data/catalog";
import { element } from "../ui/dom";
import type { LandingSection } from "./LandingSection";
import { BRAIN_SWITCH_NOTES, RUN_STEPS } from "./prose";
import { card, chip, code, definitionList, formatNumber, paragraphs, sectionFrame, subheading } from "./widgets";

const TOKENS_PER_MILLION = 1_000_000;
const SECONDS_PER_MINUTE = 60;
const EXAMPLE_ANIMALS = 100;

export class RunGuideSection implements LandingSection {
  readonly id = "run";
  readonly navLabel = "Run it";

  constructor(
    private readonly jev: JevFacts,
    private readonly brains: BrainRegistryFacts,
  ) {}

  render(): HTMLElement {
    const jev = this.jev;
    const costPerTick = (EXAMPLE_ANIMALS * jev.tokens_per_call * jev.price_usd_per_million_input_tokens)
      / TOKENS_PER_MILLION;
    const secondsPerTick = (EXAMPLE_ANIMALS / jev.requests_per_minute) * SECONDS_PER_MINUTE;
    const section = sectionFrame({
      id: this.id,
      kicker: "Your own run",
      title: "Run a world yourself",
      lead: `A tick costs one call per living animal. ${EXAMPLE_ANIMALS} animals cost about $${costPerTick.toFixed(4)} `
        + `a tick and take about ${secondsPerTick.toFixed(0)} seconds at the rate limit. The limit on requests, not `
        + "the price, sets the pace. Every run shows its estimate and waits for your yes before it spends anything.",
    });
    const steps = element("ol", "command-steps");
    for (const step of RUN_STEPS) {
      const item = element("li", "command-step");
      item.append(element("code", "command", step.command), element("span", "command-note", step.explanation));
      steps.append(item);
    }
    section.append(steps, element("p", "footnote", "Options: --ticks, --population-scale, --max-usd, --max-calls, "
      + "--decision-detail, and --brain jev, kev or heuristic for a single command."),
                   subheading("Choose a brain: Jev or Kev"), paragraphs(BRAIN_SWITCH_NOTES, "prose narrow"),
                   this.brainCards());
    return section;
  }

  private brainCards(): HTMLElement {
    const grid = element("div", "tile-grid three");
    grid.append(...this.brains.providers.map((brain) => this.brainCard(brain)));
    return grid;
  }

  private brainCard(brain: BrainFacts): HTMLElement {
    const tile = card(`brain-card${brain.name === this.brains.active ? " active" : ""}`);
    const header = element("div", "module-header");
    header.append(element("h4", "", brain.title),
                  brain.name === this.brains.active ? chip("default", "good") : code(`--brain ${brain.name}`));
    tile.append(header, element("p", "", brain.description), definitionList([
      ["Model", brain.model],
      ["Endpoint", brain.endpoint],
      ["Price", this.price(brain)],
    ], "facts compact"));
    return tile;
  }

  private price(brain: BrainFacts): string {
    const parts: string[] = [];
    if (brain.price_usd_per_million_input_tokens > 0) {
      parts.push(`$${formatNumber(brain.price_usd_per_million_input_tokens, 3)} per million input tokens`);
    }
    if (brain.host_usd_per_hour > 0) {
      parts.push(`$${formatNumber(brain.host_usd_per_hour, 2)} an hour of hosting`);
    }
    return parts.join(" + ") || "nothing per call";
  }
}
