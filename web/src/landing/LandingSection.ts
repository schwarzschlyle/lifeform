export interface LandingSection {
  readonly id: string;
  readonly navLabel: string;
  render(): HTMLElement;
}
