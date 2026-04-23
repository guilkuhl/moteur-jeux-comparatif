/// <reference lib="webworker" />

export interface DiffRequest {
  seq: number;
  width: number;
  height: number;
  srcBuf: ArrayBuffer;
  prevBuf: ArrayBuffer;
}

export interface DiffResponse {
  seq: number;
  width: number;
  height: number;
  diffBuf: ArrayBuffer;
}

self.addEventListener('message', (ev: MessageEvent<DiffRequest>) => {
  const { seq, width, height, srcBuf, prevBuf } = ev.data;
  const a = new Uint8ClampedArray(srcBuf);
  const b = new Uint8ClampedArray(prevBuf);
  const out = new Uint8ClampedArray(width * height * 4);
  const len = out.length;
  for (let i = 0; i < len; i += 4) {
    const dr = Math.abs((a[i] ?? 0) - (b[i] ?? 0));
    const dg = Math.abs((a[i + 1] ?? 0) - (b[i + 1] ?? 0));
    const db = Math.abs((a[i + 2] ?? 0) - (b[i + 2] ?? 0));
    const m = dr > dg ? (dr > db ? dr : db) : (dg > db ? dg : db);
    out[i] = m;
    out[i + 1] = 0;
    out[i + 2] = 0;
    out[i + 3] = 255;
  }
  const resp: DiffResponse = { seq, width, height, diffBuf: out.buffer };
  (self as unknown as Worker).postMessage(resp, [out.buffer]);
});
