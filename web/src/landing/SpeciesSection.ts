import type { ArchetypeFacts } from "../data/catalog";
import { element } from "../ui/dom";
import type { LandingSection } from "./LandingSection";
import { SpeciesCard } from "./SpeciesCard";
import { sectionFrame } from "./widgets";

export class SpeciesSection implements LandingSection {
  readonly id = "species";
  readonly navLabel = "Species";

  constructor(private readonly archetypes: ArchetypeFacts[]) {}

  render(): HTMLElement {
    const section = sectionFrame({
      id: this.id,
      kicker: "The founders",
      title: `${this.archetypes.length} founding species`,
      lead: "Each world is seeded from these archetypes. The figures below describe a typical founder, derived from "
        + "the same allometry and genetics the simulation uses. Real founders vary around them, some worlds adjust a "
        + "few genes, and once breeding starts every trait is free to evolve. New species split off and get their "
        + "own names.",
    });
    const grid = element("div", "species-grid");
    grid.append(...this.sortedBySize().map((archetype) => new SpeciesCard(archetype).render()));
    section.append(grid);
    return section;
  }

  private sortedBySize(): ArchetypeFacts[] {
    return [...this.archetypes].sort((a, b) => a.stats.adult_mass_kg - b.stats.adult_mass_kg);
  }
}
