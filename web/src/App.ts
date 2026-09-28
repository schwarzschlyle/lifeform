import { ApiClient } from "./data/ApiClient";
import { Landing } from "./landing/Landing";
import { clear, element } from "./ui/dom";
import { Theater } from "./ui/Theater";

const THEATER_ROUTE = /^#\/run\/([^/]+)\/([^/@]+)(?:@(\d+)(?::(\d+))?)?$/;
const LANDING_ROUTE = /^#?\/?([a-z-]*)$/;

export class App {
  private readonly api = new ApiClient();
  private theater: Theater | null = null;
  private landing: Landing | null = null;

  constructor(private readonly host: HTMLElement) {}

  start(): void {
    window.addEventListener("hashchange", () => void this.route());
    void this.route();
  }

  private async route(): Promise<void> {
    const section = LANDING_ROUTE.exec(window.location.hash)?.[1];
    if (this.landing !== null && section !== undefined) {
      this.landing.show(section, true);
      return;
    }
    this.theater?.destroy();
    this.theater = null;
    this.landing?.destroy();
    this.landing = null;
    clear(this.host);
    const match = THEATER_ROUTE.exec(window.location.hash);
    try {
      if (match) {
        const startTick = match[3] ? Number(match[3]) : 0;
        const selected = match[4] ? Number(match[4]) : null;
        this.theater = new Theater(this.api, decodeURIComponent(match[1]), match[2], startTick, selected);
        this.host.append(this.theater.root);
        await this.theater.load();
      } else {
        this.landing = new Landing(this.api);
        this.host.append(this.landing.root);
        await this.landing.load();
        this.landing.show(section ?? "", false);
      }
    } catch (error) {
      this.host.append(element("div", "error", `Something went wrong: ${String(error)}`));
    }
  }
}
