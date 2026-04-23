import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { usePreviewStore } from './preview';
import type { PreviewResult } from '@/types/api';

vi.mock('@/api/client', () => {
  return {
    api: {
      postPreview: vi.fn(),
    },
  };
});

import { api } from '@/api/client';

function fakeBlob(): Blob {
  return new Blob([new Uint8Array([1, 2, 3])], { type: 'image/png' });
}

function makeResult(id: number): PreviewResult {
  return {
    blob: fakeBlob(),
    width: id,
    height: id,
    elapsedMs: 1,
    cacheHitDepth: 0,
  };
}

/**
 * Retourne une promesse contrôlable : la factory résout manuellement via
 * `resolver(value)` — permet de séquencer des requêtes concurrentes.
 */
function deferred<T>() {
  let resolver: (v: T) => void = () => {};
  let rejecter: (e: unknown) => void = () => {};
  const promise = new Promise<T>((res, rej) => {
    resolver = res;
    rejecter = rej;
  });
  return { promise, resolve: resolver, reject: rejecter };
}

beforeEach(() => {
  setActivePinia(createPinia());
  // URL mocks (jsdom/happy-dom ne les fournissent pas toujours)
  if (!globalThis.URL.createObjectURL) {
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:mock');
  }
  if (!globalThis.URL.revokeObjectURL) {
    globalThis.URL.revokeObjectURL = vi.fn();
  }
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('usePreviewStore — latest-wins', () => {
  it('ignore la résolution tardive d\'une requête obsolète', async () => {
    const store = usePreviewStore();
    store.setLiveMode(true);

    const slow = deferred<PreviewResult>();
    const fast = deferred<PreviewResult>();
    (api.postPreview as ReturnType<typeof vi.fn>)
      .mockImplementationOnce(() => slow.promise)
      .mockImplementationOnce(() => fast.promise);

    // Lance A puis B quasi-immédiatement
    const pA = store.fire('img.png', [
      { algo: 'sharpen', method: 'unsharp_mask', params: { radius: 1 } },
    ]);
    const pB = store.fire('img.png', [
      { algo: 'sharpen', method: 'unsharp_mask', params: { radius: 2 } },
    ]);

    // B résout en premier
    fast.resolve(makeResult(20));
    await pB;

    expect(store.status).toBe('ready');
    expect(store.lastMeta?.width).toBe(20);

    // A résout après, avec une valeur différente — DOIT être ignorée
    slow.resolve(makeResult(10));
    await pA;

    expect(store.status).toBe('ready');
    expect(store.lastMeta?.width).toBe(20);
  });

  it('ignore l\'erreur tardive d\'une requête obsolète', async () => {
    const store = usePreviewStore();
    store.setLiveMode(true);

    const failA = deferred<PreviewResult>();
    const okB = deferred<PreviewResult>();
    (api.postPreview as ReturnType<typeof vi.fn>)
      .mockImplementationOnce(() => failA.promise)
      .mockImplementationOnce(() => okB.promise);

    const pA = store.fire('img.png', [
      { algo: 'sharpen', method: 'unsharp_mask', params: { radius: 1 } },
    ]);
    const pB = store.fire('img.png', [
      { algo: 'sharpen', method: 'unsharp_mask', params: { radius: 2 } },
    ]);

    // B réussit d'abord → status ready
    okB.resolve(makeResult(30));
    await pB;
    expect(store.status).toBe('ready');

    // A échoue plus tard → DOIT être ignoré (status reste ready)
    failA.reject(new Error('timeout'));
    await pA;

    expect(store.status).toBe('ready');
    expect(store.errorMsg).toBeNull();
  });

  it('publie le résultat quand la requête n\'a pas de successeur', async () => {
    const store = usePreviewStore();
    store.setLiveMode(true);

    (api.postPreview as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      makeResult(42),
    );

    await store.fire('img.png', [
      { algo: 'sharpen', method: 'unsharp_mask', params: {} },
    ]);

    expect(store.status).toBe('ready');
    expect(store.lastMeta?.width).toBe(42);
  });
});
