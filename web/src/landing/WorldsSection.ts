import type { ArchetypeFacts, FounderGroup, WorldFacts } from "../data/catalog";
import { element } from "../ui/dom";
import type { LandingSection } from "./LandingSection";
import { paletteGradient } from "./palettes";
import { bulletList, chip, colorChip, hueColor, humanize, sectionFrame } from "./widgets";

const PERCENT = 100;

export class WorldsSection implements LandingSection {
  readonly id = "worlds";
  readonly navLabel = "Worlds";
  private readonly archetypes: Map<string, ArchetypeFacts>;

  constructor(
    private readonly worlds: WorldFacts[],
    archetypes: ArchetypeFacts[],
  ) {
    this.archetypes = new Map(archetypes.map((archetype) => [archetype.slug, archetype]));
  }

  render(): HTMLElement {
    const core = this.worlds.filter((world) => !world.stretch).length;
    const section = sectionFrame({
      id: this.id,
      kicker: "Settings",
      title: `${this.worlds.length} worlds`,
      lead: `${core} core worlds and ${this.worlds.length - core} stretch worlds. Each one poses an ecological `
        + "question and is built to test it: its own terrain, climate, disturbances and founding species.",
    });
    const grid = element("div", "world-grid");
    grid.append(...this.coreFirst().map((world) => this.worldCard(world)));
    section.append(grid);
    return section;
  }

  private coreFirst(): WorldFacts[] {
    return [...this.worlds.filter((world) => !world.stretch), ...this.worlds.filter((world) => world.stretch)];
  }

  private worldCard(world: WorldFacts): HTMLElement {
    const panel = element("article", "world-card panel");
    const banner = element("div", "world-banner");
    banner.style.background = paletteGradient(world.palette);
    banner.append(element("div", "card-title", world.title), element("div", "card-biome", world.biome));
    if (world.stretch) {
      banner.append(chip("stretch", "warn"));
    }
    const body = element("div", "world-body");
    body.append(element("p", "", world.description), element("p", "world-question", world.question),
                element("div", "muted", this.climateLine(world)), this.founders(world.founders));
    if (world.disturbances.length > 0) {
      body.append(bulletList(world.disturbances, "bullets compact"));
    }
    panel.append(banner, body);
    return panel;
  }

  private climateLine(world: WorldFacts): string {
    const climate = world.climate;
    const parts = [
      `${world.grid[0]}×${world.grid[1]} patches`,
      `${world.default_ticks.toLocaleString()} ticks`,
      `${climate.equator_temperature_c} °C at its warmest latitude`,
      `seasons ±${climate.seasonal_amplitude_c} °C`,
      `${humanize(climate.weather)} weather`,
    ];
    if (world.water_fraction > 0) {
      parts.push(`${Math.round(world.water_fraction * PERCENT)}% open water`);
    }
    parts.push(...world.features.map(humanize));
    if (climate.tidally_locked) {
      parts.push("tidally locked");
    }
    if (climate.moving_rain_belt) {
      parts.push("a moving rain belt");
    }
    return parts.join(" · ");
  }

  private founders(groups: FounderGroup[]): HTMLElement {
    const row = element("div", "chip-row");
    for (const group of groups) {
      const archetype = this.archetypes.get(group.archetype);
      const name = group.name ?? archetype?.name ?? humanize(group.archetype);
      const color = archetype ? hueColor(archetype.hue) : "var(--muted)";
      row.append(colorChip(`${name} ×${group.count}`, color));
    }
    return row;
  }
}
