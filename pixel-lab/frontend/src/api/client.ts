/** Wrappers HTTP typés autour de `fetch` — uniquement ici, jamais en profondeur. */
import type {
  AlgosCatalog,
  ConvertRequest,
  InputFile,
  JobCreatedResponse,
  PreviewRequest,
  PreviewResult,
} from '@/types/api';
import { parseApiError } from './errors';

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw await parseApiError(res);
  return (await res.json()) as T;
}

export const api = {
  async listInputs(): Promise<InputFile[]> {
    return jsonFetch<InputFile[]>('/api/inputs');
  },

  async uploadInput(file: File): Promise<{ basename: string; size: number }> {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch('/api/inputs', { method: 'POST', body: fd });
    if (!res.ok) throw await parseApiError(res);
    return (await res.json()) as { basename: string; size: number };
  },

  async deleteInput(basename: string): Promise<void> {
    const res = await fetch(`/api/inputs/${encodeURIComponent(basename)}`, { method: 'DELETE' });
    if (!res.ok) throw await parseApiError(res);
  },

  async getAlgos(): Promise<AlgosCatalog> {
    return jsonFetch<AlgosCatalog>('/api/algos');
  },

  async startConvert(req: ConvertRequest): Promise<JobCreatedResponse> {
    return jsonFetch<JobCreatedResponse>('/api/convert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
  },

  async postPreview(req: PreviewRequest, signal?: AbortSignal): Promise<PreviewResult> {
    const init: RequestInit = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    };
    if (signal) init.signal = signal;
    const res = await fetch('/api/preview', init);
    if (!res.ok) throw await parseApiError(res);
    const blob = await res.blob();
    const n = (h: string): number => parseInt(res.headers.get(h) ?? '0', 10);
    return {
      blob,
      width: n('X-Width'),
      height: n('X-Height'),
      elapsedMs: n('X-Elapsed-Ms'),
      cacheHitDepth: n('X-Cache-Hit-Depth'),
    };
  },

  async getBgmask(
    image: string,
    tolerance = 8,
    feather = 0,
  ): Promise<{ blob: Blob; color: string }> {
    const url = `/api/bgmask?image=${encodeURIComponent(image)}&tolerance=${tolerance}&feather=${feather}`;
    const res = await fetch(url);
    if (!res.ok) throw await parseApiError(res);
    const blob = await res.blob();
    return { blob, color: res.headers.get('X-Bgmask-Color') ?? 'none' };
  },
};
