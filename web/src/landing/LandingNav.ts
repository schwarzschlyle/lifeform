import { element } from "../ui/dom";
import type { LandingSection } from "./LandingSection";

const ACTIVE_LINE = 0.35;
const BOTTOM_SLACK_PX = 2;
const TOP = "top";

export class LandingNav {
  readonly root = element("nav", "landing-nav");
  private readonly links = new Map<string, HTMLElement>();
  private readonly onScroll = (): void => this.highlight(this.currentSection());

  constructor(sections: LandingSection[]) {
    const brand = element("button", "nav-brand", "Lifeform");
    brand.addEventListener("click", () => LandingNav.navigate(TOP));
    const list = element("div", "nav-links");
    for (const section of sections) {
      const link = element("button", "nav-link", section.navLabel);
      link.addEventListener("click", () => LandingNav.navigate(section.id));
      this.links.set(section.id, link);
      list.append(link);
    }
    this.root.append(brand, list);
  }

  static navigate(id: string): void {
    window.location.hash = id === TOP ? "#/" : `#/${id}`;
  }

  static reveal(id: string, smooth: boolean): void {
    const behavior: ScrollBehavior = smooth ? "smooth" : "instant";
    if (id === "" || id === TOP) {
      window.scrollTo({ top: 0, behavior });
      return;
    }
    document.getElementById(id)?.scrollIntoView({ behavior, block: "start" });
  }

  watch(): void {
    window.addEventListener("scroll", this.onScroll, { passive: true });
    this.onScroll();
  }

  destroy(): void {
    window.removeEventListener("scroll", this.onScroll);
  }

  private currentSection(): string {
    const ids = [...this.links.keys()];
    if (LandingNav.atBottom()) {
      return ids[ids.length - 1] ?? TOP;
    }
    const line = window.innerHeight * ACTIVE_LINE;
    let current = TOP;
    for (const id of ids) {
      const target = document.getElementById(id);
      if (target !== null && target.getBoundingClientRect().top <= line) {
        current = id;
      }
    }
    return current;
  }

  private static atBottom(): boolean {
    return window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - BOTTOM_SLACK_PX;
  }

  private highlight(id: string): void {
    for (const [key, link] of this.links) {
      link.classList.toggle("active", key === id);
    }
  }
}
