import { onMounted, onUnmounted, ref } from 'vue';

export interface UseImageDropOptions {
  onFiles: (files: File[]) => void | Promise<void>;
}

/**
 * Global drag & drop + paste handler for image files. Drops anywhere in the window
 * and clipboard pastes (Ctrl+V) surface image files to the caller. Ignores drops
 * targeting a form input so the browser's default file chooser still works.
 */
export function useImageDrop({ onFiles }: UseImageDropOptions) {
  const isDragging = ref(false);
  let dragCounter = 0;

  function pickImages(list: FileList | DataTransferItemList | null): File[] {
    if (!list) return [];
    const out: File[] = [];
    for (const item of Array.from(list as ArrayLike<File | DataTransferItem>)) {
      if (item instanceof File) {
        if (item.type.startsWith('image/')) out.push(item);
      } else if ('kind' in item && item.kind === 'file') {
        const f = item.getAsFile();
        if (f && f.type.startsWith('image/')) out.push(f);
      }
    }
    return out;
  }

  function onDragEnter(e: DragEvent) {
    if (!e.dataTransfer?.types.includes('Files')) return;
    e.preventDefault();
    dragCounter += 1;
    isDragging.value = true;
  }

  function onDragOver(e: DragEvent) {
    if (!e.dataTransfer?.types.includes('Files')) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }

  function onDragLeave() {
    dragCounter = Math.max(0, dragCounter - 1);
    if (dragCounter === 0) isDragging.value = false;
  }

  async function onDrop(e: DragEvent) {
    dragCounter = 0;
    isDragging.value = false;
    if (!e.dataTransfer?.types.includes('Files')) return;
    e.preventDefault();
    const files = pickImages(e.dataTransfer.files);
    if (files.length) await onFiles(files);
  }

  async function onPaste(e: ClipboardEvent) {
    const files = pickImages(e.clipboardData?.items ?? null);
    if (!files.length) return;
    e.preventDefault();
    await onFiles(files);
  }

  onMounted(() => {
    window.addEventListener('dragenter', onDragEnter);
    window.addEventListener('dragover', onDragOver);
    window.addEventListener('dragleave', onDragLeave);
    window.addEventListener('drop', onDrop);
    window.addEventListener('paste', onPaste);
  });

  onUnmounted(() => {
    window.removeEventListener('dragenter', onDragEnter);
    window.removeEventListener('dragover', onDragOver);
    window.removeEventListener('dragleave', onDragLeave);
    window.removeEventListener('drop', onDrop);
    window.removeEventListener('paste', onPaste);
  });

  return { isDragging };
}
