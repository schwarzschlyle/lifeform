import type { NamedNote } from "../data/catalog";
import { element } from "../ui/dom";
import type { LandingSection } from "./LandingSection";
import { ECOLOGY_MODELS } from "./prose";
import { card, humanize, sectionFrame, subheading } from "./widgets";

export class EcologySection implements LandingSection {
  readonly id = "ecology";
  readonly navLabel = "Life & death";

  constructor(private readonly deathCauses: NamedNote[]) {}

  render(): HTMLElement {
    const section = sectionFrame({
      id: this.id,
      kicker: "The mathematics of bodies",
      title: "Survive, eat, breed, die",
      lead: "Bodies follow established models from physiology and ecology. Energy is the common currency: food adds "
        + "it, living and moving spend it, fat stores it, and running out of it kills.",
    });
    const models = element("div", "tile-grid three");
    for (const model of ECOLOGY_MODELS) {
      const tile = card("model");
      tile.append(element("h4", "", model.title), element("p", "", model.text));
      models.append(tile);
    }
    section.append(models, subheading(`${this.deathCauses.length} ways to die`), this.deaths());
    return section;
  }

  private deaths(): HTMLElement {
    const grid = element("div", "death-grid");
    for (const cause of this.deathCauses) {
      const tile = element("div", "death");
      tile.append(element("span", "death-name", humanize(cause.name)), element("span", "death-note", cause.note));
      grid.append(tile);
    }
    return grid;
  }
}
