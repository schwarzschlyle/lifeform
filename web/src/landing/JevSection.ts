import type { JevFacts } from "../data/catalog";
import { element } from "../ui/dom";
import type { LandingSection } from "./LandingSection";
import { JEV_INTRODUCTION, JEV_WEAKNESSES, QUESTION_TYPES, VENDOR_FACTS } from "./prose";
import { card, code, definitionList, paragraphs, sectionFrame, subheading } from "./widgets";

const TOKENS_PER_MILLION = 1_000_000;

export class JevSection implements LandingSection {
  readonly id = "jev";
  readonly navLabel = "What Jev is";

  constructor(private readonly jev: JevFacts) {}

  render(): HTMLElement {
    const section = sectionFrame({
      id: this.id,
      kicker: `${this.jev.maker} · System One`,
      title: "What Jev is",
      lead: "Jev is Lifeform's default brain. An open, Jev-compatible model called Kev can take its place with one "
        + "switch; see \"Run it\" at the bottom.",
    });
    const columns = element("div", "two-columns");
    columns.append(paragraphs(JEV_INTRODUCTION), this.facts());
    section.append(columns, subheading("Three kinds of question"), this.questionTypes(),
                   subheading("What Jev is bad at, and how Lifeform works around it"), this.weaknesses());
    return section;
  }

  private facts(): HTMLElement {
    const jev = this.jev;
    const costPerCall = (jev.tokens_per_call * jev.price_usd_per_million_input_tokens) / TOKENS_PER_MILLION;
    const panel = card("facts-panel");
    panel.append(element("h4", "", "The model in this project"), definitionList([
      ["Model", code(jev.model)],
      ["Price", `$${jev.price_usd_per_million_input_tokens} per million input tokens; output is free`],
      ["Rate limit", `${jev.requests_per_minute.toLocaleString()} requests a minute, `
        + `${jev.tokens_per_second.toLocaleString()} tokens a second`],
      ["One animal's call", `about ${jev.tokens_per_call.toLocaleString()} tokens, roughly $${costPerCall.toFixed(6)}`],
      ...VENDOR_FACTS,
    ]));
    return panel;
  }

  private questionTypes(): HTMLElement {
    const grid = element("div", "tile-grid three");
    for (const type of QUESTION_TYPES) {
      const tile = card("question-type");
      tile.append(element("h4", "", type.title), element("p", "", type.text));
      grid.append(tile);
    }
    return grid;
  }

  private weaknesses(): HTMLElement {
    const list = element("div", "weakness-list");
    for (const entry of JEV_WEAKNESSES) {
      const row = element("div", "weakness");
      row.append(element("div", "weakness-problem", entry.weakness), element("div", "weakness-arrow", "→"),
                 element("div", "weakness-response", entry.response));
      list.append(row);
    }
    return list;
  }
}
