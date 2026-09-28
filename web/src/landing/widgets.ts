import type { BrainTone } from "../data/BrainIdentity";
import { speciesColor } from "../render/theme";
import { colorHex, element } from "../ui/dom";

export interface SectionHeading {
  id: string;
  kicker: string;
  title: string;
  lead?: string;
}

export type Cell = string | number | HTMLElement;

const BRAIN_CHIP_TONES: Record<BrainTone, string> = { jev: "good", compatible: "info", offline: "warn" };

export function sectionFrame(heading: SectionHeading): HTMLElement {
  const section = element("section", "landing-section", "", { id: heading.id });
  section.append(element("div", "kicker", heading.kicker), element("h2", "section-title", heading.title));
  if (heading.lead) {
    section.append(element("p", "lead", heading.lead));
  }
  return section;
}

export function subheading(text: string): HTMLElement {
  return element("h3", "subheading", text);
}

export function paragraphs(texts: string[], className = "prose"): HTMLElement {
  const block = element("div", className);
  block.append(...texts.map((text) => element("p", "", text)));
  return block;
}

export function bulletList(items: string[], className = "bullets"): HTMLElement {
  const list = element("ul", className);
  list.append(...items.map((item) => element("li", "", item)));
  return list;
}

export function statTile(value: string, label: string): HTMLElement {
  const tile = element("div", "stat-tile");
  tile.append(element("div", "stat-value", value), element("div", "stat-label", label));
  return tile;
}

export function chip(text: string, tone = ""): HTMLElement {
  return element("span", `chip${tone ? ` ${tone}` : ""}`, text);
}

export function brainChip(text: string, tone: BrainTone): HTMLElement {
  return chip(text, BRAIN_CHIP_TONES[tone]);
}

export function colorChip(text: string, color: string): HTMLElement {
  const node = chip(text, "tinted");
  node.style.setProperty("--tint", color);
  return node;
}

export function code(text: string): HTMLElement {
  return element("code", "inline-code", text);
}

export function meter(fraction: number, color = "var(--accent)"): HTMLElement {
  const track = element("span", "meter");
  const fill = element("span", "meter-fill");
  fill.style.width = `${Math.round(Math.min(1, Math.max(0, fraction)) * 100)}%`;
  fill.style.background = color;
  track.append(fill);
  return track;
}

export function dataTable(headers: string[], rows: Cell[][], className = ""): HTMLElement {
  const wrapper = element("div", `table-wrap ${className}`.trim());
  const table = element("table", "data-table");
  const head = element("tr");
  head.append(...headers.map((header) => element("th", "", header)));
  table.append(element("thead"), element("tbody"));
  table.tHead!.append(head);
  for (const row of rows) {
    const line = element("tr");
    line.append(...row.map(tableCell));
    table.tBodies[0].append(line);
  }
  wrapper.append(table);
  return wrapper;
}

function tableCell(value: Cell): HTMLElement {
  const cell = element("td");
  if (value instanceof HTMLElement) {
    cell.append(value);
  } else {
    cell.textContent = String(value);
  }
  return cell;
}

export function definitionList(entries: [string, Cell][], className = "facts"): HTMLElement {
  const list = element("dl", className);
  for (const [term, value] of entries) {
    const description = element("dd");
    if (value instanceof HTMLElement) {
      description.append(value);
    } else {
      description.textContent = String(value);
    }
    list.append(element("dt", "", term), description);
  }
  return list;
}

export function disclosure(summary: string, content: HTMLElement, open = false): HTMLElement {
  const details = element("details", "disclosure");
  details.open = open;
  details.append(element("summary", "", summary), content);
  return details;
}

export function card(className = ""): HTMLElement {
  return element("article", `panel ${className}`.trim());
}

export function formatNumber(value: number, digits = 1): string {
  return value.toLocaleString("en-US", { maximumFractionDigits: digits });
}

export function humanize(key: string): string {
  return key.replace(/[_-]/g, " ");
}

export function hueColor(hue: number, lightness = 0.6): string {
  return colorHex(speciesColor(hue, lightness));
}
