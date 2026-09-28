import type { PanelFacts, PanelQuestion } from "../data/catalog";
import { element } from "../ui/dom";
import type { LandingSection } from "./LandingSection";
import { CODE_DUTIES, DESIGN_RULES, JEV_DUTIES, PIPELINE_STEPS } from "./prose";
import { bulletList, card, chip, sectionFrame, subheading } from "./widgets";

const JEV_STEP = "Jev";

export class RoleSection implements LandingSection {
  readonly id = "role";
  readonly navLabel = "Jev's role";

  constructor(private readonly panel: PanelFacts) {}

  render(): HTMLElement {
    const section = sectionFrame({
      id: this.id,
      kicker: "Code computes, Jev chooses",
      title: "Jev's role in Lifeform",
      lead: "Jev is the only thing that decides. Every living animal, from a newborn to the dying, gets exactly one "
        + "Jev call per tick. Code never picks an action on an animal's behalf.",
    });
    section.append(this.split(), subheading("From a moment of experience to an action"), this.pipeline(),
                   subheading("The five questions in every call"), this.questions(),
                   subheading("How the answers become behavior"), this.interpretation(),
                   subheading("Design rules"), this.rules());
    return section;
  }

  private split(): HTMLElement {
    const split = element("div", "duty-split");
    const code = card("duty code");
    code.append(element("h4", "", "Code computes"), bulletList(CODE_DUTIES));
    const jev = card("duty jev");
    jev.append(element("h4", "", "Jev chooses"), bulletList(JEV_DUTIES));
    split.append(code, jev);
    return split;
  }

  private pipeline(): HTMLElement {
    const flow = element("ol", "flow");
    for (const step of PIPELINE_STEPS) {
      const item = element("li", step.title === JEV_STEP ? "flow-step jev" : "flow-step");
      item.append(element("div", "flow-title", step.title), element("div", "flow-text", step.text));
      flow.append(item);
    }
    return flow;
  }

  private questions(): HTMLElement {
    const grid = element("div", "question-grid");
    grid.append(...this.panel.questions.map((question) => this.question(question)));
    return grid;
  }

  private question(question: PanelQuestion): HTMLElement {
    const tile = card("question");
    const header = element("div", "question-header");
    header.append(element("span", "question-key", question.key), chip(question.type, "outline"));
    const answers = question.type === "Score"
      ? element("ol", "question-answers", "", { start: "0" })
      : element("ul", "question-answers choices");
    answers.append(...question.answers.map((answer) => element("li", "", answer)));
    tile.append(header, element("blockquote", "question-text", question.instructions), answers);
    return tile;
  }

  private interpretation(): HTMLElement {
    const rules = this.panel.interpretation;
    const cautionLow = rules.dithering_below;
    const cautionHigh = rules.hesitant_below;
    const span = rules.caution_span;
    const grid = element("div", "tile-grid two");
    const entries: [string, string][] = [
      ["Sampling, not obeying",
       `The action is drawn from Jev's probabilities raised to the power β, the animal's heritable decisiveness (from `
       + `${rules.min_decisiveness} to ${rules.max_decisiveness}). A β of 1 follows Jev's distribution as it is; a `
       + "high β nearly always takes Jev's top choice. The same sampling picks the call."],
      ["Hesitation",
       `Jev's confidence sorts each action into a band. Below ${cautionLow}–${(cautionLow + span).toFixed(2)} the `
       + `animal dithers and below ${cautionHigh}–${(cautionHigh + span).toFixed(2)} it hesitates (the thresholds rise `
       + "with its caution gene). Hesitant and dithering animals act with one level less effort."],
      ["Urgency",
       `When Jev rates the danger as "${rules.urgent_threat_level.split(":")[0]}" or worse, the animal acts at full `
       + "chosen effort however unsure it is."],
      ["Fear",
       `Jev's danger rating feeds the animal's fear, which moves ${Math.round(rules.fear_integration_rate * 100)}% of `
       + "the way toward it each tick. Fear is fed back to Jev as a feeling on the next tick."],
      ["Attention",
       "The animal learns more from whatever it focuses on: harm or a meal involving that species changes its "
       + `associations more strongly. Each state holds at most `
       + `${rules.attention.entities} nearby things, ${rules.attention.smells} smells, ${rules.attention.sounds} `
       + `sounds and ${rules.attention.memories} memories, ranked by salience.`],
      ["Legal menus only",
       `Jev chooses from up to ${this.panel.max_menu_options} options that are all possible right now, each described `
       + "with its consequence. Code then carries out the choice: which patch to step into, whether the strike lands."],
    ];
    for (const [title, text] of entries) {
      const tile = card("interpretation");
      tile.append(element("h4", "", title), element("p", "", text));
      grid.append(tile);
    }
    return grid;
  }

  private rules(): HTMLElement {
    const grid = element("div", "rule-grid");
    for (const rule of DESIGN_RULES) {
      const tile = element("div", "rule");
      tile.append(element("span", "rule-code", rule.code), element("span", "rule-title", rule.rule),
                  element("span", "rule-detail", rule.detail));
      grid.append(tile);
    }
    return grid;
  }
}
