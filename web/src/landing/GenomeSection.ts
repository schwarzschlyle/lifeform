import type { GeneModuleFacts, GeneReference, InstinctFacts } from "../data/catalog";
import { element } from "../ui/dom";
import type { LandingSection } from "./LandingSection";
import { card, chip, dataTable, disclosure, formatNumber, humanize, paragraphs, sectionFrame, subheading } from "./widgets";

const NATURAL_UNIT = "0–1";

export class GenomeSection implements LandingSection {
  readonly id = "genome";
  readonly navLabel = "Genome";

  constructor(
    private readonly modules: GeneModuleFacts[],
    private readonly genes: GeneReference[],
    private readonly instincts: InstinctFacts[],
  ) {}

  render(): HTMLElement {
    const section = sectionFrame({
      id: this.id,
      kicker: "Heredity",
      title: `A diploid genome of ${this.genes.length} loci`,
      lead: "Every animal carries two copies of every locus, one from each parent. A gene's value is the average of "
        + "its two copies plus a little developmental noise, mapped onto a natural range. Each parent passes on one "
        + "recombined copy of every locus, with occasional mutation, so traits drift and are selected over generations.",
    });
    section.append(this.moduleGrid(), subheading(`${this.instincts.length} heritable instincts`),
                   paragraphs(["An instinct is a gene that, above one half, adds a phrase to what Jev reads about the "
                     + "animal. Its strength sets the adverb: \"somewhat\" or \"strongly\". Jev weighs these phrases "
                     + "along with everything else in the state."], "prose narrow"),
                   this.instinctList(),
                   subheading("Speciation"),
                   paragraphs(["Every 24 ticks the population is clustered by genetic distance. A cluster that has "
                     + "drifted far enough from its parent species is recognized as a new species, gets a generated "
                     + "name, and appears in the theater's legend. A species with no living members goes extinct."],
                              "prose narrow"),
                   disclosure(`Reference: all ${this.genes.length} loci`, this.referenceTable()));
    return section;
  }

  private moduleGrid(): HTMLElement {
    const grid = element("div", "tile-grid four");
    for (const module of this.modules) {
      const tile = card("module");
      const header = element("div", "module-header");
      header.append(element("h4", "", humanize(module.name)), chip(`${module.count} loci`, "outline"));
      tile.append(header, element("p", "", module.note));
      grid.append(tile);
    }
    return grid;
  }

  private instinctList(): HTMLElement {
    const list = element("div", "chip-row instinct-cloud");
    list.append(...this.instincts.map((instinct) => chip(instinct.wording)));
    return list;
  }

  private referenceTable(): HTMLElement {
    const rows = this.genes.map((gene) => [
      String(gene.index),
      humanize(gene.name.replace("instinct:", "")),
      humanize(gene.module),
      this.range(gene),
      gene.note,
    ]);
    return dataTable(["#", "Locus", "Module", "Range", "What it does"], rows, "reference-table");
  }

  private range(gene: GeneReference): string {
    if (gene.unit === NATURAL_UNIT) {
      return NATURAL_UNIT;
    }
    const scale = gene.scale === "log" ? " (log)" : "";
    return `${formatNumber(gene.low, 3)}–${formatNumber(gene.high, 3)} ${gene.unit}${scale}`;
  }
}
