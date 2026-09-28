import type { ReplayStore } from "../data/ReplayStore";
import type { Frame } from "../data/types";
import { speciesColor } from "../render/theme";
import { clear, colorHex, element } from "./dom";

export class Legend {
  readonly root = element("aside", "legend glass");
  private readonly list = element("ul", "species-list");
  highlight: number | null = null;
  onHighlight: (species: number | null) => void = () => undefined;

  constructor(private readonly store: ReplayStore) {
    this.root.append(element("h2", "", "Species"), this.list);
  }

  update(frame: Frame): void {
    const counts = new Map<number, number>();
    for (const species of frame.organisms.species) {
      counts.set(species, (counts.get(species) ?? 0) + 1);
    }
    clear(this.list);
    const ordered = [...this.store.species.values()].sort((a, b) => (counts.get(b.id) ?? 0) - (counts.get(a.id) ?? 0));
    for (const species of ordered) {
      const count = counts.get(species.id) ?? 0;
      const item = element("li", `species${this.highlight === species.id ? " active" : ""}${count ? "" : " gone"}`);
      const swatch = element("span", "swatch");
      swatch.style.background = colorHex(speciesColor(this.store.speciesHue(species.id)));
      const extinct = species.extinct_tick !== null && species.extinct_tick <= frame.tick ? " · extinct" : "";
      item.append(swatch, element("span", "name", species.name), element("span", "count", `${count}${extinct}`));
      item.addEventListener("click", () => this.toggle(species.id));
      this.list.append(item);
    }
  }

  private toggle(species: number): void {
    this.highlight = this.highlight === species ? null : species;
    this.onHighlight(this.highlight);
  }
}
