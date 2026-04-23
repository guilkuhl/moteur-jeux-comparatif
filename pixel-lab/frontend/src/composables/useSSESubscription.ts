/** Wrapper `EventSource` avec cleanup automatique au démontage. */
import { onUnmounted, ref, watch, type Ref } from 'vue';
import type { SSEEvent } from '@/types/sse';

export function useSSESubscription(jobId: Ref<string | null>, onEvent: (e: SSEEvent) => void) {
  const streamError = ref<string | null>(null);
  let es: EventSource | null = null;

  const close = () => {
    if (es) {
      es.close();
      es = null;
    }
  };

  watch(
    jobId,
    (id) => {
      close();
      streamError.value = null;
      if (!id) return;
      es = new EventSource(`/api/jobs/${id}/stream`);
      es.onmessage = (ev) => {
        try {
          onEvent(JSON.parse(ev.data) as SSEEvent);
        } catch (e) {
          console.error('SSE parse error', e);
        }
      };
      es.onerror = () => {
        streamError.value = 'Connexion SSE perdue';
      };
    },
    { immediate: true },
  );

  onUnmounted(close);

  return { streamError, close };
}
