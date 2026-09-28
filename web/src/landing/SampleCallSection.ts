import type { ApiClient } from "../data/ApiClient";
import { BrainIdentity } from "../data/BrainIdentity";
import type { DecisionSample } from "../data/catalog";
import type { ChoiceAnswer, DecisionRecord, RunManifest, ScoreAnswer } from "../data/types";
import { clear, element } from "../ui/dom";
import type { LandingSection } from "./LandingSection";
import { brainChip, card, chip, formatNumber, humanize, meter, sectionFrame } from "./widgets";

const SHOWN_OPTIONS = 8;
const PERCENT = 100;

class StateView {
  render(value: unknown): HTMLElement {
    if (Array.isArray(value)) {
      const list = element("ul", "state-list");
      list.append(...value.map((item) => this.listItem(item)));
      return list;
    }
    if (value !== null && typeof value === "object") {
      const list = element("dl", "state-object");
      for (const [key, entry] of Object.entries(value as Record<string, unknown>)) {
        const description = element("dd");
        description.append(this.render(entry));
        list.append(element("dt", "", humanize(key)), description);
      }
      return list;
    }
    return element("span", "state-text", String(value));
  }

  private listItem(item: unknown): HTMLElement {
    const node = element("li");
    node.append(this.render(item));
    return node;
  }
}

export class SampleCallSection implements LandingSection {
  readonly id = "sample";
  readonly navLabel = "A real call";
  private readonly body = element("div", "sample-body");

  constructor(
    private readonly api: ApiClient,
    private readonly runs: RunManifest[],
  ) {}

  render(): HTMLElement {
    const section = sectionFrame({
      id: this.id,
      kicker: "One animal, one moment",
      title: "What a call looks like",
      lead: "This is one decision taken from a recorded run: the words the animal sent, the menu it chose from, and "
        + "the answers that came back. The theater's Mind Inspector shows the same for any animal at any tick.",
    });
    this.body.append(element("p", "muted", "Loading a recorded decision…"));
    section.append(this.body);
    void this.load();
    return section;
  }

  private async load(): Promise<void> {
    const run = this.runs.find((candidate) => candidate.worlds.length > 0);
    if (run === undefined) {
      this.showMessage("Record a run to see a real call here.");
      return;
    }
    const world = run.worlds.find((candidate) => candidate.slug === "serengeti-pulse") ?? run.worlds[0];
    try {
      const sample = await this.api.json<DecisionSample>(
        `runs/${encodeURIComponent(run.run_id)}/worlds/${world.slug}/decision-sample`);
      clear(this.body);
      this.body.append(this.provenance(run, world.title, world.slug, sample), this.columns(sample.decision));
    } catch {
      this.showMessage("This run did not record decision states. Record with --decision-detail full to see one.");
    }
  }

  private showMessage(text: string): void {
    clear(this.body);
    this.body.append(element("p", "notice", text));
  }

  private provenance(run: RunManifest, title: string, slug: string, sample: DecisionSample): HTMLElement {
    const line = element("div", "sample-provenance");
    const link = element("a", "text-link", "Open this animal in the theater →", {
      href: `#/run/${encodeURIComponent(run.run_id)}/${slug}@${sample.tick}:${sample.decision.id}`,
    });
    const identity = new BrainIdentity(run);
    const brain = brainChip(identity.answeredBy, identity.tone);
    line.append(element("span", "", `${title}, tick ${sample.tick}, animal #${sample.decision.id}`), brain, link);
    return line;
  }

  private columns(decision: DecisionRecord): HTMLElement {
    const columns = element("div", "two-columns sample-columns");
    const statePanel = card("state-panel");
    statePanel.append(element("h4", "", "The state it sent (words only)"), new StateView().render(decision.state ?? {}));
    const answerPanel = card("answer-panel");
    answerPanel.append(element("h4", "", `Action: ${decision.menu.length} options on the menu`),
                       this.actionBars(decision), this.outcome(decision),
                       element("h4", "", "Other answers from the same call"), this.otherAnswers(decision));
    columns.append(statePanel, answerPanel);
    return columns;
  }

  private actionBars(decision: DecisionRecord): HTMLElement {
    const descriptions = new Map(decision.menu);
    const ranked = Object.entries(decision.answers.action.probabilities).sort((a, b) => b[1] - a[1]);
    const list = element("ol", "probability-list");
    for (const [key, probability] of ranked.slice(0, SHOWN_OPTIONS)) {
      const marks = `${key === decision.sampled ? "▶ " : ""}${key === decision.argmax ? "★ " : ""}`;
      const item = element("li", key === decision.sampled ? "chosen" : "");
      item.append(element("span", "option-text", `${marks}${descriptions.get(key) ?? key}`), meter(probability),
                  element("span", "option-probability", `${formatNumber(probability * PERCENT)}%`));
      list.append(item);
    }
    const hidden = ranked.length - SHOWN_OPTIONS;
    if (hidden > 0) {
      list.append(element("li", "muted more", `… and ${hidden} more options`));
    }
    return list;
  }

  private outcome(decision: DecisionRecord): HTMLElement {
    const confidence = decision.answers.action.confidence ?? 0;
    const line = element("div", "sample-outcome");
    line.append(chip(`confidence ${formatNumber(confidence, 2)}`, "outline"), chip(decision.band, "outline"),
                chip(`effort ${decision.effort} of 3`, "outline"));
    if (decision.urgent) {
      line.append(chip("urgent", "warn"));
    }
    line.append(element("span", "muted", "▶ sampled · ★ Jev's top choice"));
    return line;
  }

  private otherAnswers(decision: DecisionRecord): HTMLElement {
    const grid = element("div", "answer-grid");
    grid.append(this.score("Effort", decision.answers.effort), this.score("Threat", decision.answers.threat),
                this.choice("Call", decision.answers.call), this.choice("Focus", decision.answers.focus));
    return grid;
  }

  private score(title: string, answer: ScoreAnswer): HTMLElement {
    const block = element("div", "answer");
    block.append(element("div", "answer-title", `${title}: expected level ${formatNumber(answer.score, 2)}`));
    const bars = element("div", "level-bars");
    for (const [level, probability] of Object.entries(answer.probabilities)) {
      const bar = element("span", "level-bar", "", { title: `level ${level}: ${formatNumber(probability * PERCENT)}%` });
      bar.style.height = `${Math.max(2, probability * PERCENT)}%`;
      bars.append(bar);
    }
    block.append(bars);
    return block;
  }

  private choice(title: string, answer: ChoiceAnswer): HTMLElement {
    const block = element("div", "answer");
    const top = answer.probabilities[answer.choice] ?? 0;
    block.append(element("div", "answer-title", title),
                 element("div", "answer-value", `${humanize(answer.choice)} (${formatNumber(top * PERCENT)}%)`));
    return block;
  }
}
