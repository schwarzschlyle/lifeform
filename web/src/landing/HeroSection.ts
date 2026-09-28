import type { ProjectCatalog } from "../data/catalog";
import { element } from "../ui/dom";
import type { LandingSection } from "./LandingSection";
import { HERO_TAGLINE } from "./prose";
import { hueColor, statTile } from "./widgets";

const CONSTELLATION_LEFT = 58;
const CONSTELLATION_WIDTH = 38;
const CONSTELLATION_TOP = 8;
const CONSTELLATION_HEIGHT = 44;

export class HeroSection implements LandingSection {
  readonly id = "top";
  readonly navLabel = "Overview";

  constructor(
    private readonly catalog: ProjectCatalog,
    private readonly navigate: (id: string) => void,
  ) {}

  render(): HTMLElement {
    const hero = element("header", "hero", "", { id: this.id });
    hero.append(this.constellation(), this.copy(), this.stats());
    return hero;
  }

  private copy(): HTMLElement {
    const copy = element("div", "hero-copy");
    const actions = element("div", "hero-actions");
    actions.append(this.action("Watch a replay", "replays", "primary"), this.action("How Jev drives it", "jev", ""));
    copy.append(element("div", "kicker", "An artificial-life theater"), element("h1", "hero-title", "Lifeform"),
                element("p", "hero-tagline", HERO_TAGLINE), actions);
    return copy;
  }

  private action(label: string, target: string, tone: string): HTMLElement {
    const button = element("button", `hero-action ${tone}`.trim(), label);
    button.addEventListener("click", () => this.navigate(target));
    return button;
  }

  private stats(): HTMLElement {
    const catalog = this.catalog;
    const traitGenes = catalog.genes.filter((gene) => gene.module !== "instincts" && gene.module !== "neutral").length;
    const stats = element("div", "hero-stats");
    stats.append(
      statTile("1", "Jev call per animal per tick"),
      statTile(String(catalog.panel.questions.length), "questions answered in that call"),
      statTile(String(catalog.archetypes.length), "founding species"),
      statTile(String(catalog.worlds.length), "worlds"),
      statTile(String(catalog.verbs.length), `actions, plus ${catalog.calls.length - 1} calls`),
      statTile(String(catalog.genes.length), `genetic loci (${traitGenes} traits, ${catalog.instincts.length} instincts)`),
      statTile(String(catalog.death_causes.length), "ways to die"),
      statTile(`${catalog.calendar.hours_per_tick} h`, "of simulated time per tick"),
    );
    return stats;
  }

  private constellation(): HTMLElement {
    const field = element("div", "hero-constellation");
    this.catalog.archetypes.forEach((archetype, index) => {
      const dot = element("span", "hero-dot");
      const size = 10 + Math.cbrt(archetype.stats.adult_mass_kg) * 5;
      dot.style.width = `${size}px`;
      dot.style.height = `${size}px`;
      dot.style.background = hueColor(archetype.hue);
      dot.style.left = `${CONSTELLATION_LEFT + ((index * 37) % CONSTELLATION_WIDTH)}%`;
      dot.style.top = `${CONSTELLATION_TOP + ((index * 53) % CONSTELLATION_HEIGHT)}%`;
      dot.style.animationDelay = `${-index * 1.7}s`;
      dot.title = archetype.name;
      field.append(dot);
    });
    return field;
  }
}
