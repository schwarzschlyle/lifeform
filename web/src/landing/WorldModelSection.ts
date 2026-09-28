import type { FoodLayerFacts, TerrainFacts } from "../data/catalog";
import { TERRAIN_COLORS } from "../render/theme";
import { element } from "../ui/dom";
import type { LandingSection } from "./LandingSection";
import { WORLD_MECHANICS } from "./prose";
import { card, chip, dataTable, formatNumber, humanize, meter, sectionFrame, subheading } from "./widgets";

const PERCENT = 100;

export class WorldModelSection implements LandingSection {
  readonly id = "world";
  readonly navLabel = "The world";

  constructor(
    private readonly terrain: TerrainFacts[],
    private readonly foodLayers: FoodLayerFacts[],
  ) {}

  render(): HTMLElement {
    const section = sectionFrame({
      id: this.id,
      kicker: "Everything code computes",
      title: "How a world works",
      lead: "The environment is simulated in code, patch by patch, every tick. Animals never see these numbers; "
        + "they sense their effects and describe them to Jev in words.",
    });
    section.append(this.mechanics(), subheading(`${this.terrain.length} kinds of terrain`), this.terrainGrid(),
                   subheading(`${this.foodLayers.length} food layers`), this.foodTable());
    return section;
  }

  private mechanics(): HTMLElement {
    const grid = element("div", "tile-grid three");
    for (const mechanic of WORLD_MECHANICS) {
      const tile = card();
      tile.append(element("h4", "", mechanic.title), element("p", "", mechanic.text));
      grid.append(tile);
    }
    return grid;
  }

  private terrainGrid(): HTMLElement {
    const grid = element("div", "terrain-grid");
    grid.append(...this.terrain.map((terrain) => this.terrainTile(terrain)));
    return grid;
  }

  private terrainTile(terrain: TerrainFacts): HTMLElement {
    const tile = card("terrain");
    const swatch = element("div", "terrain-swatch");
    const [red, green, blue] = TERRAIN_COLORS[terrain.id] ?? [80, 80, 80];
    swatch.style.background = `rgb(${red}, ${green}, ${blue})`;
    const cost = terrain.move_cost === null ? "swimmers only" : `${formatNumber(terrain.move_cost)}× effort to cross`;
    const properties = element("div", "terrain-properties");
    properties.append(this.property("cover", terrain.cover), this.property("blocks sight", terrain.sight_opacity));
    const food = element("div", "chip-row");
    const layers = Object.entries(terrain.food);
    food.append(...(layers.length > 0
      ? layers.map(([layer, amount]) => chip(`${humanize(layer)} ${formatNumber(amount)} kg`))
      : [chip("no food", "outline")]));
    const temperature = terrain.temperature_offset_c !== 0
      ? ` · ${terrain.temperature_offset_c > 0 ? "+" : ""}${terrain.temperature_offset_c} °C` : "";
    tile.append(swatch, element("h4", "", terrain.description), element("div", "muted", `${cost}${temperature}`),
                properties, food);
    return tile;
  }

  private property(label: string, value: number): HTMLElement {
    const row = element("div", "property");
    row.append(element("span", "property-label", label), meter(value, "var(--accent-2)"));
    return row;
  }

  private foodTable(): HTMLElement {
    const rows = this.foodLayers.map((layer) => [
      humanize(layer.key),
      humanize(layer.diet_class),
      `${formatNumber(layer.energy_density_eu_per_kg, 0)} EU/kg`,
      `${formatNumber(layer.growth_rate_per_tick * PERCENT, 2)}% a tick`,
      `${layer.thermal_optimum_c} ± ${layer.thermal_breadth_c} °C`,
      layer.needs_light ? "yes" : "no",
      `${formatNumber(layer.max_assimilation * PERCENT, 0)}%`,
      `${formatNumber(layer.water_fraction * PERCENT, 0)}%`,
    ]);
    return dataTable(["Layer", "Diet class", "Energy", "Regrowth", "Grows best at", "Needs light", "Digestible",
                      "Water"], rows);
  }
}
