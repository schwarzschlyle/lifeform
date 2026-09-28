import type { RunManifest } from "./types";

export type BrainTone = "jev" | "compatible" | "offline";

const HEURISTIC_BRAIN = "heuristic";

export class BrainIdentity {
  readonly tone: BrainTone;
  readonly title: string;

  constructor(private readonly run: RunManifest) {
    this.title = run.brain_title ?? (run.is_jev ? "Jev" : run.brain);
    this.tone = run.is_jev ? "jev" : run.brain === HEURISTIC_BRAIN ? "offline" : "compatible";
  }

  get badgeText(): string {
    if (this.tone === "offline") {
      return "heuristic stand-in · not Jev";
    }
    return `${this.title} · ${this.run.model}`;
  }

  get answeredBy(): string {
    if (this.tone === "jev") {
      return `answered by Jev (${this.run.model})`;
    }
    if (this.tone === "compatible") {
      return `answered by ${this.title} (${this.run.model}), a Jev-compatible model, not Jev itself`;
    }
    return "answered by the offline heuristic stand-in, not Jev: same shape, not Jev's judgment";
  }

  get servedModel(): string {
    return this.run.served_model ?? "";
  }
}
