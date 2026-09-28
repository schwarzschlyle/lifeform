import { Application, Container, RenderTexture, Sprite, Texture } from "pixi.js";
import type { ReplayStore } from "../data/ReplayStore";
import type { Frame } from "../data/types";
import { AtmosphereOverlay } from "./AtmosphereOverlay";
import { CELL, CreatureLayer, wrapDelta } from "./CreatureLayer";
import { EffectsLayer } from "./EffectsLayer";
import { TerrainPainter } from "./TerrainPainter";

const MIN_ZOOM = 0.35;
const MAX_ZOOM = 8;
const ZOOM_STEP = 1.12;
const FOLLOW_SMOOTHING = 0.15;
const PICK_RADIUS_PIXELS = 14;
const DRAG_THRESHOLD_PIXELS = 4;
const BACKGROUND = 0x0b0f14;
const GLYPH_SCREEN_SIZE = 1.8;
const MAX_GLYPH_SCALE = 3.5;
const FIT_MARGIN = 0.98;

export class WorldView {
  readonly app = new Application();
  private readonly world = new Container();
  private readonly scene = new Container();
  private creatures!: CreatureLayer;
  private effects!: EffectsLayer;
  private atmosphere!: AtmosphereOverlay;
  private painter!: TerrainPainter;
  private terrainTexture!: Texture;
  private overlayTexture!: RenderTexture;
  private centerX = 0;
  private centerY = 0;
  private zoom = 1;
  private dragging: { x: number; y: number; moved: boolean } | null = null;
  private paintedKeyframe = -1;
  follow: number | null = null;
  onPick: (organismId: number | null) => void = () => undefined;

  constructor(private readonly store: ReplayStore) {}

  async mount(host: HTMLElement): Promise<void> {
    await this.app.init({ resizeTo: host, background: BACKGROUND, antialias: true, autoDensity: true,
                          resolution: window.devicePixelRatio || 1 });
    host.appendChild(this.app.canvas);
    const { width, height } = this.store.staticData;
    this.painter = new TerrainPainter(this.store.meta, this.store.staticData);
    this.painter.paint(this.store.keyframeAt(0));
    this.terrainTexture = Texture.from(this.painter.canvas);
    this.terrainTexture.source.scaleMode = "linear";
    this.overlayTexture = RenderTexture.create({ width: width * CELL, height: height * CELL });
    this.creatures = new CreatureLayer(this.store, width, height);
    this.effects = new EffectsLayer(this.store.meta.call_names ?? []);
    this.scene.addChild(this.creatures.root, this.effects.root);
    this.buildTiles(width, height);
    this.atmosphere = new AtmosphereOverlay(this.store.meta.calendar.ticks_per_day, this.store.meta.tidally_locked);
    this.app.stage.addChild(this.world, this.atmosphere.root);
    this.centerX = (width * CELL) / 2;
    this.centerY = (height * CELL) / 2;
    this.zoom = Math.max(this.app.screen.width / (width * CELL), this.app.screen.height / (height * CELL)) * FIT_MARGIN;
    this.bindInput();
  }

  render(previous: Frame, next: Frame, fraction: number, selected: number | null, highlight: number | null,
         seconds: number): void {
    this.repaintTerrain(next.tick);
    const glyphScale = Math.min(MAX_GLYPH_SCALE, Math.max(1, GLYPH_SCREEN_SIZE / this.zoom));
    this.creatures.update(previous, next, fraction, selected, highlight, glyphScale);
    this.effects.update(seconds);
    this.app.renderer.render({ container: this.scene, target: this.overlayTexture, clear: true });
    this.followSelection();
    this.applyCamera();
    this.atmosphere.resize(this.app.screen.width, this.app.screen.height);
    this.atmosphere.update(fraction < 0.5 ? previous.clock : next.clock, seconds);
  }

  spawnEffects(frame: Frame, events: Parameters<EffectsLayer["spawnForTick"]>[1]): void {
    this.effects.spawnForTick(frame, events, this.creatures.positions);
  }

  clearEffects(): void {
    this.effects.clear();
  }

  focusOn(organismId: number): void {
    const point = this.creatures.positions.get(organismId);
    if (point) {
      this.centerX = point.x;
      this.centerY = point.y;
      this.zoom = Math.max(this.zoom, 2.5);
    }
  }

  private buildTiles(width: number, height: number): void {
    const spanX = width * CELL;
    const spanY = height * CELL;
    for (let row = -1; row <= 1; row += 1) {
      for (let column = -1; column <= 1; column += 1) {
        const terrain = new Sprite(this.terrainTexture);
        terrain.scale.set(CELL / this.painter.upscale);
        terrain.position.set(column * spanX, row * spanY);
        const overlay = new Sprite(this.overlayTexture);
        overlay.position.set(column * spanX, row * spanY);
        this.world.addChild(terrain, overlay);
      }
    }
  }

  private repaintTerrain(tick: number): void {
    const keyframe = this.store.keyframeAt(tick);
    if (keyframe === null || keyframe.tick === this.paintedKeyframe) {
      return;
    }
    this.paintedKeyframe = keyframe.tick;
    this.painter.paint(keyframe);
    this.terrainTexture.source.update();
  }

  private followSelection(): void {
    if (this.follow === null) {
      return;
    }
    const point = this.creatures.positions.get(this.follow);
    if (!point) {
      return;
    }
    const spanX = this.store.staticData.width * CELL;
    const spanY = this.store.staticData.height * CELL;
    this.centerX += wrapDelta(point.x - this.centerX, spanX) * FOLLOW_SMOOTHING;
    this.centerY += wrapDelta(point.y - this.centerY, spanY) * FOLLOW_SMOOTHING;
  }

  private applyCamera(): void {
    const spanX = this.store.staticData.width * CELL;
    const spanY = this.store.staticData.height * CELL;
    this.centerX = ((this.centerX % spanX) + spanX) % spanX;
    this.centerY = ((this.centerY % spanY) + spanY) % spanY;
    this.world.scale.set(this.zoom);
    this.world.position.set(this.app.screen.width / 2 - this.centerX * this.zoom,
                            this.app.screen.height / 2 - this.centerY * this.zoom);
  }

  private bindInput(): void {
    const canvas = this.app.canvas;
    canvas.addEventListener("pointerdown", (event) => {
      this.dragging = { x: event.clientX, y: event.clientY, moved: false };
    });
    window.addEventListener("pointermove", (event) => this.drag(event));
    window.addEventListener("pointerup", (event) => this.release(event));
    canvas.addEventListener("wheel", (event) => this.wheel(event), { passive: false });
  }

  private drag(event: PointerEvent): void {
    if (this.dragging === null) {
      return;
    }
    const dx = event.clientX - this.dragging.x;
    const dy = event.clientY - this.dragging.y;
    if (Math.hypot(dx, dy) > DRAG_THRESHOLD_PIXELS) {
      this.dragging.moved = true;
      this.follow = null;
    }
    if (this.dragging.moved) {
      this.centerX -= dx / this.zoom;
      this.centerY -= dy / this.zoom;
      this.dragging.x = event.clientX;
      this.dragging.y = event.clientY;
    }
  }

  private release(event: PointerEvent): void {
    if (this.dragging !== null && !this.dragging.moved) {
      this.pick(event);
    }
    this.dragging = null;
  }

  private pick(event: PointerEvent): void {
    const bounds = this.app.canvas.getBoundingClientRect();
    const worldX = (event.clientX - bounds.left - this.app.screen.width / 2) / this.zoom + this.centerX;
    const worldY = (event.clientY - bounds.top - this.app.screen.height / 2) / this.zoom + this.centerY;
    const spanX = this.store.staticData.width * CELL;
    const spanY = this.store.staticData.height * CELL;
    const picked = this.creatures.nearest(((worldX % spanX) + spanX) % spanX, ((worldY % spanY) + spanY) % spanY,
                                          PICK_RADIUS_PIXELS / this.zoom + CELL);
    this.onPick(picked);
  }

  private wheel(event: WheelEvent): void {
    event.preventDefault();
    const bounds = this.app.canvas.getBoundingClientRect();
    const screenX = event.clientX - bounds.left - this.app.screen.width / 2;
    const screenY = event.clientY - bounds.top - this.app.screen.height / 2;
    const before = { x: screenX / this.zoom + this.centerX, y: screenY / this.zoom + this.centerY };
    const factor = event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP;
    this.zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, this.zoom * factor));
    this.centerX = before.x - screenX / this.zoom;
    this.centerY = before.y - screenY / this.zoom;
  }
}
