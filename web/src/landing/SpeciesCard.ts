import type { ArchetypeFacts, GeneValue, SpeciesStats } from "../data/catalog";
import { element } from "../ui/dom";
import { DIET_COLORS, DIET_LABELS } from "./prose";
import { chip, colorChip, dataTable, definitionList, disclosure, formatNumber, hueColor, humanize, meter } from "./widgets";

const PERCENT = 100;
const NATURAL_UNIT = "0–1";

type StatGroup = [string, [string, string][]];

export class SpeciesCard {
  private readonly color: string;

  constructor(private readonly archetype: ArchetypeFacts) {
    this.color = hueColor(archetype.hue);
  }

  render(): HTMLElement {
    const archetype = this.archetype;
    const root = element("article", "species-card panel");
    root.style.setProperty("--species", this.color);
    root.append(this.header(), element("p", "species-summary", archetype.summary), this.dietBar(),
                this.temperament(), this.instincts(), this.statGroups(), this.worlds(), this.geneTable());
    return root;
  }

  private header(): HTMLElement {
    const archetype = this.archetype;
    const header = element("div", "species-header");
    const sigil = element("span", "species-sigil");
    const titles = element("div");
    const blood = archetype.stats.warm_blooded ? "warm-blooded" : "cold-blooded";
    titles.append(element("h3", "species-name", archetype.name),
                  element("div", "muted", `${formatNumber(archetype.stats.adult_mass_kg)} kg · ${archetype.rhythm} · ${blood}`));
    header.append(sigil, titles);
    return header;
  }

  private dietBar(): HTMLElement {
    const block = element("div", "diet");
    const bar = element("div", "diet-bar");
    const legend = element("div", "diet-legend");
    for (const [key, share] of Object.entries(this.archetype.diet)) {
      const segment = element("span", "diet-segment", "", { title: `${DIET_LABELS[key]}: ${Math.round(share * PERCENT)}%` });
      segment.style.width = `${share * PERCENT}%`;
      segment.style.background = DIET_COLORS[key];
      bar.append(segment);
      const entry = element("span", "diet-entry", `${DIET_LABELS[key]} ${Math.round(share * PERCENT)}%`);
      entry.style.setProperty("--dot", DIET_COLORS[key]);
      legend.append(entry);
    }
    block.append(element("div", "mini-label", "Diet"), bar, legend);
    return block;
  }

  private temperament(): HTMLElement {
    const block = element("div", "chip-row");
    const words = this.archetype.temperament;
    block.append(...(words.length > 0 ? words.map((word) => chip(word)) : [chip("even-tempered", "outline")]));
    return block;
  }

  private instincts(): HTMLElement {
    const block = element("div", "instincts");
    block.append(element("div", "mini-label", "Instincts (shown to Jev as words)"));
    for (const instinct of this.archetype.instincts) {
      const row = element("div", "instinct");
      row.append(element("span", "instinct-wording", instinct.wording), meter(instinct.strength, this.color));
      block.append(row);
    }
    return block;
  }

  private statGroups(): HTMLElement {
    const grid = element("div", "stat-groups");
    for (const [title, entries] of this.groups(this.archetype.stats)) {
      const group = element("div", "stat-group");
      group.append(element("div", "mini-label", title), definitionList(entries, "facts compact"));
      grid.append(group);
    }
    return grid;
  }

  private groups(stats: SpeciesStats): StatGroup[] {
    const bodyHeat: [string, string] = stats.comfortable_down_to_c === null
      ? ["Body heat", "follows the air"]
      : ["Burns heat below", `${formatNumber(stats.comfortable_down_to_c, 0)} °C`];
    return [
      ["Life history", [
        ["Adult mass", `${formatNumber(stats.adult_mass_kg)} kg`],
        ["Life span", `about ${formatNumber(stats.lifespan_days, 0)} days`],
        ["Matures at", `${formatNumber(stats.maturity_days)} days`],
        ["Gestation", `${formatNumber(stats.gestation_days)} days`],
        ["Weaned at", `${formatNumber(stats.weaning_days)} days`],
        ["Litter", `${stats.litter_size}`],
      ]],
      ["Body", [
        ["Top speed", `${stats.top_speed_patches_per_tick} patches a tick`],
        ["Attack", formatNumber(stats.attack_power)],
        ["Defense", formatNumber(stats.defense)],
        ["Basal energy", `${formatNumber(stats.basal_energy_per_tick, 0)} EU a tick`],
        ["Can fast for", `about ${formatNumber(stats.fasting_days)} days`],
        ["Stomach · bite", `${formatNumber(stats.stomach_kg, 2)} kg · ${formatNumber(stats.bite_kg, 2)} kg`],
      ]],
      ["Senses and climate", [
        ["Sight by day", `${formatNumber(stats.vision_day_patches)} patches`],
        ["Sight at night", `${formatNumber(stats.vision_night_patches)} patches`],
        ["Hears above", `${formatNumber(stats.hearing_threshold_db, 0)} dB`],
        ["Thermal optimum", `${formatNumber(stats.thermal_optimum_c, 0)} °C (width ${formatNumber(stats.thermal_breadth_c, 0)} °C)`],
        bodyHeat,
      ]],
      ["Decision style", [
        ["Decisiveness β", formatNumber(stats.decisiveness_beta, 2)],
        ["Caution", formatNumber(stats.caution, 2)],
      ]],
    ];
  }

  private worlds(): HTMLElement {
    const block = element("div", "species-worlds");
    block.append(element("div", "mini-label", `Founds populations on ${this.archetype.worlds.length} worlds`));
    const row = element("div", "chip-row");
    row.append(...this.archetype.worlds.map((appearance) => {
      const name = appearance.local_name ? ` as ${appearance.local_name}` : "";
      const tweaks = Object.keys(appearance.overrides).length > 0 ? " · adapted" : "";
      return colorChip(`${appearance.world} ×${appearance.count}${name}${tweaks}`, this.color);
    }));
    block.append(row);
    return block;
  }

  private geneTable(): HTMLElement {
    const modules = new Map<string, GeneValue[]>();
    for (const gene of this.archetype.genes) {
      modules.set(gene.module, [...(modules.get(gene.module) ?? []), gene]);
    }
    const rows = [...modules.entries()].flatMap(([module, genes]) => genes.map((gene, index) => [
      index === 0 ? humanize(module) : "",
      humanize(gene.name),
      meter(gene.fraction, this.color),
      this.geneValue(gene),
    ]));
    return disclosure(`All ${this.archetype.genes.length} trait genes`,
                      dataTable(["Module", "Gene", "Position in range", "Value"], rows, "gene-table"));
  }

  private geneValue(gene: GeneValue): string {
    return gene.unit === NATURAL_UNIT ? formatNumber(gene.value, 2) : `${formatNumber(gene.value, 2)} ${gene.unit}`;
  }
}
