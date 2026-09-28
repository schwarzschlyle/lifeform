import * as d3 from "d3";
import type { ReplayStore } from "../data/ReplayStore";
import { speciesColor } from "../render/theme";
import { colorHex, element } from "../ui/dom";

const HEIGHT = 150;
const MARGIN = { top: 10, right: 12, bottom: 20, left: 34 };

interface Row {
  tick: number;
  [species: string]: number;
}

export class PopulationChart {
  readonly root = element("section", "chart glass");
  private readonly svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;
  private cursor!: d3.Selection<SVGLineElement, unknown, null, undefined>;
  private x!: d3.ScaleLinear<number, number>;
  onSeek: (tick: number) => void = () => undefined;

  constructor(private readonly store: ReplayStore) {
    this.root.append(element("h2", "", "Population by species"));
    this.svg = d3.select(this.root).append("svg").attr("height", HEIGHT);
  }

  draw(): void {
    const width = Math.max(320, this.root.clientWidth - 24);
    this.svg.attr("width", width).selectAll("*").remove();
    const keys = [...this.store.species.keys()].map(String);
    const rows: Row[] = this.store.stats.map((stat) => {
      const row: Row = { tick: stat.tick };
      for (const key of keys) {
        row[key] = stat.population[key] ?? 0;
      }
      return row;
    });
    if (rows.length === 0) {
      return;
    }
    const stacked = d3.stack<Row>().keys(keys)(rows);
    this.x = d3.scaleLinear().domain([0, this.store.lastTick || 1]).range([MARGIN.left, width - MARGIN.right]);
    const maxTotal = d3.max(stacked, (layer) => d3.max(layer, (point) => point[1])) ?? 1;
    const y = d3.scaleLinear().domain([0, maxTotal]).nice().range([HEIGHT - MARGIN.bottom, MARGIN.top]);
    const area = d3.area<d3.SeriesPoint<Row>>()
      .x((point) => this.x(point.data.tick))
      .y0((point) => y(point[0]))
      .y1((point) => y(point[1]))
      .curve(d3.curveBasis);
    this.svg.append("g").selectAll("path").data(stacked).join("path")
      .attr("d", area)
      .attr("fill", (layer) => colorHex(speciesColor(this.store.speciesHue(Number(layer.key)))))
      .attr("fill-opacity", 0.85)
      .append("title").text((layer) => this.store.speciesName(Number(layer.key)));
    this.svg.append("g").attr("transform", `translate(0,${HEIGHT - MARGIN.bottom})`)
      .call(d3.axisBottom(this.x).ticks(6).tickSizeOuter(0)).attr("class", "axis");
    this.svg.append("g").attr("transform", `translate(${MARGIN.left},0)`)
      .call(d3.axisLeft(y).ticks(4).tickSizeOuter(0)).attr("class", "axis");
    this.cursor = this.svg.append("line").attr("class", "cursor")
      .attr("y1", MARGIN.top).attr("y2", HEIGHT - MARGIN.bottom);
    this.svg.on("click", (event: MouseEvent) => this.onSeek(Math.round(this.x.invert(d3.pointer(event)[0]))));
  }

  moveCursor(tick: number): void {
    if (this.cursor && this.x) {
      const x = this.x(tick);
      this.cursor.attr("x1", x).attr("x2", x);
    }
  }
}
