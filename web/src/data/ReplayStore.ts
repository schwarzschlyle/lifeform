import { ApiClient } from "./ApiClient";
import type {
  BundleIndex,
  ChunkRange,
  DecisionRecord,
  EventRecord,
  FieldKeyframe,
  Frame,
  OrganismSummary,
  RunManifest,
  SpeciesEntry,
  StaticData,
  StatsRow,
  WorldMeta,
} from "./types";

const PREFETCH_CHUNKS = 2;
const MAX_CACHED_CHUNKS = 12;
const HUE_OFFSET = 0.03;
const DESCENDANT_HUE_STEP = 0.045;

class ChunkCache<T> {
  private readonly loaded = new Map<number, T[]>();
  private readonly pending = new Map<number, Promise<T[]>>();

  constructor(private readonly loader: (range: ChunkRange) => Promise<T[]>) {}

  request(range: ChunkRange): void {
    const start = range[0];
    if (this.loaded.has(start) || this.pending.has(start)) {
      return;
    }
    const promise = this.loader(range).then((items) => {
      this.loaded.set(start, items);
      this.pending.delete(start);
      this.evict(start);
      return items;
    });
    this.pending.set(start, promise);
  }

  async ensure(range: ChunkRange): Promise<T[]> {
    this.request(range);
    return this.loaded.get(range[0]) ?? (await this.pending.get(range[0])!);
  }

  items(range: ChunkRange): T[] | undefined {
    return this.loaded.get(range[0]);
  }

  private evict(keep: number): void {
    while (this.loaded.size > MAX_CACHED_CHUNKS) {
      const farthest = [...this.loaded.keys()].sort((a, b) => Math.abs(b - keep) - Math.abs(a - keep))[0];
      this.loaded.delete(farthest);
    }
  }
}

export class ReplayStore {
  meta!: WorldMeta;
  index!: BundleIndex;
  staticData!: StaticData;
  events: EventRecord[] = [];
  stats: StatsRow[] = [];
  organisms = new Map<number, OrganismSummary>();
  species = new Map<number, SpeciesEntry>();
  run!: RunManifest;
  private frames!: ChunkCache<Frame>;
  private fields!: ChunkCache<FieldKeyframe>;
  private lastFrame: Frame | null = null;
  private displayHues = new Map<number, number>();

  constructor(
    private readonly api: ApiClient,
    readonly runId: string,
    readonly worldSlug: string,
  ) {}

  private path(file: string): string {
    return `runs/${this.runId}/worlds/${this.worldSlug}/files/${file}`;
  }

  async load(): Promise<void> {
    const [run, meta, index, staticData] = await Promise.all([
      this.api.json<RunManifest>(`runs/${this.runId}`),
      this.api.json<WorldMeta>(`runs/${this.runId}/worlds/${this.worldSlug}`),
      this.api.json<BundleIndex>(this.path("index.json")),
      this.api.packed<StaticData>(this.path("static.msgpack.gz")),
    ]);
    this.run = run;
    this.meta = meta;
    this.index = index;
    this.staticData = staticData;
    this.frames = new ChunkCache<Frame>((range) => this.api.packed<Frame[]>(this.path(range[2])));
    this.fields = new ChunkCache<FieldKeyframe>((range) => this.api.packed<FieldKeyframe[]>(this.path(range[2])));
    await this.refreshHistory();
    if (this.index.frames.length > 0) {
      await this.frames.ensure(this.index.frames[0]);
    }
    if (this.index.fields.length > 0) {
      await this.fields.ensure(this.index.fields[0]);
    }
  }

  async refreshHistory(): Promise<void> {
    const [events, stats, organisms, species] = await Promise.all([
      this.api.packed<EventRecord[]>(this.path("events.msgpack.gz")).catch(() => []),
      this.api.packed<StatsRow[]>(this.path("stats.msgpack.gz")).catch(() => []),
      this.api.packed<OrganismSummary[]>(this.path("organisms.msgpack.gz")).catch(() => []),
      this.api.json<SpeciesEntry[]>(this.path("species.json")).catch(() => []),
    ]);
    this.events = events;
    this.stats = stats;
    this.organisms = new Map(organisms.map((organism) => [organism.id, organism]));
    this.species = new Map(species.map((entry) => [entry.id, entry]));
    this.assignDisplayHues();
  }

  private assignDisplayHues(): void {
    const all = [...this.species.values()].sort((a, b) => a.id - b.id);
    const founders = all.filter((entry) => entry.parent === null).sort((a, b) => a.hue - b.hue);
    this.displayHues = new Map(
      founders.map((entry, index) => [entry.id, (index / Math.max(1, founders.length) + HUE_OFFSET) % 1]),
    );
    const descendants = new Map<number, number>();
    for (const entry of all) {
      if (entry.parent === null) {
        continue;
      }
      const siblings = (descendants.get(entry.parent) ?? 0) + 1;
      descendants.set(entry.parent, siblings);
      const parentHue = this.displayHues.get(entry.parent) ?? entry.hue;
      this.displayHues.set(entry.id, (parentHue + DESCENDANT_HUE_STEP * siblings) % 1);
    }
  }

  get lastTick(): number {
    const frames = this.index.frames;
    return frames.length > 0 ? frames[frames.length - 1][1] : 0;
  }

  frameAt(tick: number): Frame | null {
    const range = this.rangeFor(this.index.frames, tick);
    if (range === null) {
      return this.lastFrame;
    }
    this.prefetch(this.index.frames, range, this.frames);
    const frame = this.frames.items(range)?.find((candidate) => candidate.tick === tick) ?? null;
    if (frame !== null) {
      this.lastFrame = frame;
    }
    return frame ?? this.lastFrame;
  }

  keyframeAt(tick: number): FieldKeyframe | null {
    const ranges = this.index.fields;
    let chosen: ChunkRange | null = null;
    for (const range of ranges) {
      if (range[0] <= tick) {
        chosen = range;
      }
    }
    if (chosen === null) {
      return null;
    }
    this.prefetch(ranges, chosen, this.fields);
    const keyframes = this.fields.items(chosen);
    if (!keyframes) {
      return null;
    }
    let best: FieldKeyframe | null = null;
    for (const keyframe of keyframes) {
      if (keyframe.tick <= tick) {
        best = keyframe;
      }
    }
    return best;
  }

  async decision(tick: number, organism: number): Promise<DecisionRecord | null> {
    try {
      return await this.api.json<DecisionRecord>(
        `runs/${this.runId}/worlds/${this.worldSlug}/decision?tick=${tick}&organism=${organism}`,
      );
    } catch {
      return null;
    }
  }

  eventsBetween(fromTick: number, toTick: number): EventRecord[] {
    return this.events.filter((event) => event.tick > fromTick && event.tick <= toTick);
  }

  speciesHue(speciesId: number): number {
    return this.displayHues.get(speciesId) ?? this.species.get(speciesId)?.hue ?? 0.5;
  }

  speciesName(speciesId: number): string {
    return this.species.get(speciesId)?.name ?? `species ${speciesId}`;
  }

  private rangeFor(ranges: ChunkRange[], tick: number): ChunkRange | null {
    for (const range of ranges) {
      if (range[0] <= tick && tick <= range[1]) {
        return range;
      }
    }
    return null;
  }

  private prefetch<T>(ranges: ChunkRange[], current: ChunkRange, cache: ChunkCache<T>): void {
    const position = ranges.indexOf(current);
    for (let offset = 0; offset <= PREFETCH_CHUNKS; offset += 1) {
      const range = ranges[position + offset];
      if (range) {
        cache.request(range);
      }
    }
  }
}
