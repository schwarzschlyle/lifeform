import "./landing.css";
import type { ApiClient } from "../data/ApiClient";
import type { ProjectCatalog } from "../data/catalog";
import type { RunManifest } from "../data/types";
import { element } from "../ui/dom";
import { BehaviorSection } from "./BehaviorSection";
import { EcologySection } from "./EcologySection";
import { GenomeSection } from "./GenomeSection";
import { HeroSection } from "./HeroSection";
import { JevSection } from "./JevSection";
import { LandingNav } from "./LandingNav";
import type { LandingSection } from "./LandingSection";
import { ReplaysSection } from "./ReplaysSection";
import { RoleSection } from "./RoleSection";
import { RunGuideSection } from "./RunGuideSection";
import { SampleCallSection } from "./SampleCallSection";
import { SpeciesSection } from "./SpeciesSection";
import { TickSection } from "./TickSection";
import { WorldModelSection } from "./WorldModelSection";
import { WorldsSection } from "./WorldsSection";

interface RunListing {
  runs: RunManifest[];
  failure: string | null;
}

export class Landing {
  readonly root = element("div", "landing");
  private nav: LandingNav | null = null;

  constructor(private readonly api: ApiClient) {}

  async load(): Promise<void> {
    const [catalog, listing] = await Promise.all([this.api.json<ProjectCatalog>("catalog"), this.listRuns()]);
    const sections = this.sections(catalog, listing);
    this.nav = new LandingNav(sections);
    const content = element("main", "landing-content");
    content.append(...sections.map((section) => section.render()));
    this.root.append(this.nav.root, content, element("footer", "landing-footer",
      "Lifeform · code computes, Jev chooses · animal decisions by TypeSafe AI's Jev"));
    this.nav.watch();
  }

  show(sectionId: string, smooth: boolean): void {
    LandingNav.reveal(sectionId, smooth);
  }

  destroy(): void {
    this.nav?.destroy();
  }

  private sections(catalog: ProjectCatalog, listing: RunListing): LandingSection[] {
    return [
      new HeroSection(catalog, LandingNav.navigate),
      new ReplaysSection(listing.runs, listing.failure),
      new JevSection(catalog.jev),
      new RoleSection(catalog.panel),
      new SampleCallSection(this.api, listing.runs),
      new TickSection(catalog.calendar, catalog.phases),
      new SpeciesSection(catalog.archetypes),
      new GenomeSection(catalog.modules, catalog.genes, catalog.instincts),
      new BehaviorSection(catalog.verbs, catalog.calls),
      new EcologySection(catalog.death_causes),
      new WorldModelSection(catalog.terrain, catalog.food_layers),
      new WorldsSection(catalog.worlds, catalog.archetypes),
      new RunGuideSection(catalog.jev, catalog.brains),
    ];
  }

  private async listRuns(): Promise<RunListing> {
    try {
      return { runs: await this.api.json<RunManifest[]>("runs"), failure: null };
    } catch (error) {
      return { runs: [], failure: String(error) };
    }
  }
}
