import type { CallFacts, VerbFacts } from "../data/catalog";
import { CALL_COLORS } from "../render/theme";
import { colorHex, element } from "../ui/dom";
import type { LandingSection } from "./LandingSection";
import { FAMILY_TITLES } from "./prose";
import { card, chip, code, dataTable, formatNumber, humanize, sectionFrame, subheading } from "./widgets";

const SILENT_COLOR = 0x8d97a5;

export class BehaviorSection implements LandingSection {
  readonly id = "actions";
  readonly navLabel = "Actions";

  constructor(
    private readonly verbs: VerbFacts[],
    private readonly calls: CallFacts[],
  ) {}

  render(): HTMLElement {
    const section = sectionFrame({
      id: this.id,
      kicker: "Everything an animal can do",
      title: `${this.verbs.length} actions and ${this.calls.length - 1} calls`,
      lead: "Jev never sees this list as it stands. Each tick, code turns the actions that are possible right now into "
        + "a grounded menu: not \"go to memory\" but \"head for good food you remember, mid-distance to the "
        + "south-west (seen just now)\". Impossible actions, such as climbing for an animal that cannot climb or "
        + "where there are no trees, never appear.",
    });
    const example = element("p", "footnote");
    example.append(document.createTextNode("Menu keys look like "), code("graze_here"), document.createTextNode(", "),
                   code("flee_from_P1"), document.createTextNode(", "), code("go_to_food_grass_memory_1"),
                   document.createTextNode(" or "), code("court_P3"),
                   document.createTextNode(". PAL is the energy cost as a multiple of resting metabolism."));
    section.append(example, this.families(), subheading("Calls"), this.callTable());
    return section;
  }

  private families(): HTMLElement {
    const grouped = new Map<string, VerbFacts[]>();
    for (const verb of this.verbs) {
      grouped.set(verb.family, [...(grouped.get(verb.family) ?? []), verb]);
    }
    const grid = element("div", "family-grid");
    for (const [family, verbs] of grouped) {
      const panel = card("family");
      panel.append(element("h4", "", `${FAMILY_TITLES[family] ?? humanize(family)} · ${verbs.length}`));
      const list = element("ul", "verb-list");
      list.append(...verbs.map((verb) => this.verbItem(verb)));
      panel.append(list);
      grid.append(panel);
    }
    return grid;
  }

  private verbItem(verb: VerbFacts): HTMLElement {
    const item = element("li", "verb");
    const header = element("div", "verb-header");
    header.append(element("span", "verb-name", humanize(verb.name)), chip(`PAL ${formatNumber(verb.pal)}`, "outline"));
    if (verb.moves) {
      header.append(chip("moves", "outline"));
    }
    item.append(header, element("div", "verb-note", verb.note));
    return item;
  }

  private callTable(): HTMLElement {
    const rows = this.calls.map((call) => [
      this.callName(call),
      call.description,
      call.level_db > 0 ? `${call.level_db} dB` : "—",
      call.min_vocal_capacity > 0 ? `voice ≥ ${formatNumber(call.min_vocal_capacity, 2)}` : "anyone",
      call.adults_only ? "adults" : "all ages",
    ]);
    return dataTable(["Call", "Meaning", "Loudness", "Needs", "Who"], rows);
  }

  private callName(call: CallFacts): HTMLElement {
    const name = element("span", "call-name", humanize(call.name));
    name.style.setProperty("--dot", colorHex(CALL_COLORS[call.name] ?? SILENT_COLOR));
    return name;
  }
}
