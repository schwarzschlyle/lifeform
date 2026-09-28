type Attributes = Record<string, string>;

export function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className = "",
  text = "",
  attributes: Attributes = {},
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text) {
    node.textContent = text;
  }
  for (const [name, value] of Object.entries(attributes)) {
    node.setAttribute(name, value);
  }
  return node;
}

export function clear(node: HTMLElement): void {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

export function colorHex(color: number): string {
  return `#${color.toString(16).padStart(6, "0")}`;
}

export function titleCase(text: string): string {
  return text.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
