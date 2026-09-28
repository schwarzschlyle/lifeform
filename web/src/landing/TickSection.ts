import type { CalendarFacts, NamedNote } from "../data/catalog";
import { element } from "../ui/dom";
import type { LandingSection } from "./LandingSection";
import { humanize, sectionFrame, statTile } from "./widgets";

const JEV_PHASES = new Set(["deliberation", "intent"]);

export class TickSection implements LandingSection {
  readonly id = "tick";
  readonly navLabel = "A tick";

  constructor(
    private readonly calendar: CalendarFacts,
    private readonly phases: NamedNote[],
  ) {}

  render(): HTMLElement {
    const calendar = this.calendar;
    const section = sectionFrame({
      id: this.id,
      kicker: "Discrete time",
      title: "Anatomy of a tick",
      lead: `Time moves in ticks of ${calendar.hours_per_tick} simulated hours. The world waits until every animal `
        + "has its decision, then resolves them all at once, so no animal gets to act on information from the "
        + "same tick.",
    });
    const tiles = element("div", "stat-row");
    tiles.append(statTile(`${calendar.hours_per_tick} h`, "per tick"), statTile(String(calendar.ticks_per_day), "ticks a day"),
                 statTile(String(calendar.days_per_season), "days a season"),
                 statTile(calendar.ticks_per_year.toLocaleString(), "ticks a year"));
    section.append(tiles, this.phaseList(),
                   element("p", "footnote", "Seasons are compressed so that animals live through several years and "
                     + "many generations in a run. Growth and building costs are scaled to match."));
    return section;
  }

  private phaseList(): HTMLElement {
    const list = element("ol", "phase-list");
    this.phases.forEach((phase, index) => {
      const item = element("li", JEV_PHASES.has(phase.name) ? "phase jev" : "phase");
      item.append(element("span", "phase-number", String(index + 1)), element("span", "phase-name", humanize(phase.name)),
                  element("span", "phase-note", phase.note));
      list.append(item);
    });
    return list;
  }
}
