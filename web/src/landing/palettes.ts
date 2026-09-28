export const PALETTE_GRADIENTS: Record<string, string> = {
  "serengeti-pulse": "linear-gradient(135deg, #c9a24b, #6f8f3a 55%, #3b2a4a)",
  "galapagos-scatter": "linear-gradient(135deg, #1f6f8b, #2a9d8f 50%, #e9c46a)",
  "boreal-long-night": "linear-gradient(135deg, #0b3a4a, #3d6b6b 50%, #e0f0ff)",
  "oasis-of-salt": "linear-gradient(135deg, #e6b17e, #f4e1c1 50%, #1d1b3a)",
  "emerald-canopy": "linear-gradient(135deg, #0f3d2e, #1f7a4c 55%, #c0399a)",
  "delta-of-tides": "linear-gradient(135deg, #6b5b3a, #7a9a6b 50%, #a8c5d8)",
  "ashfall-caldera": "linear-gradient(135deg, #1b1414, #7a2e12 50%, #f0a030)",
  "spine-of-the-world": "linear-gradient(135deg, #3b4a5a, #7ea06b 50%, #dfe9f5)",
  "twilight-ring": "linear-gradient(135deg, #5a0f1f, #c05a2e 45%, #2a3a7a)",
  "red-queen-pit": "linear-gradient(135deg, #b8c9a3, #e8efe0 60%, #6b8a5a)",
  "pale-plague-meadow": "linear-gradient(135deg, #a9c28a, #e6e3cf 55%, #8fa300)",
  "the-sundering": "linear-gradient(135deg, #5a8a4a, #2f6fb0 50%, #a6c58a)",
  "glacial-advance": "linear-gradient(135deg, #6a8a6a, #b8d0e0 60%, #ffffff)",
  "lightless-hollows": "linear-gradient(135deg, #0a0a12, #1a2a3a 60%, #33c3b0)",
};

const FALLBACK_GRADIENT = "linear-gradient(135deg, #223, #445)";

export function paletteGradient(palette: string): string {
  return PALETTE_GRADIENTS[palette] ?? FALLBACK_GRADIENT;
}
