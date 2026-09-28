import { decode } from "@msgpack/msgpack";

export class ApiClient {
  constructor(private readonly base: string = "/api") {}

  async json<T>(path: string): Promise<T> {
    const response = await fetch(`${this.base}/${path}`);
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText} for ${path}`);
    }
    return (await response.json()) as T;
  }

  async packed<T>(path: string): Promise<T> {
    const response = await fetch(`${this.base}/${path}`);
    if (!response.ok || response.body === null) {
      throw new Error(`${response.status} ${response.statusText} for ${path}`);
    }
    const inflated = response.body.pipeThrough(new DecompressionStream("gzip"));
    const buffer = await new Response(inflated).arrayBuffer();
    return decode(new Uint8Array(buffer)) as T;
  }
}
