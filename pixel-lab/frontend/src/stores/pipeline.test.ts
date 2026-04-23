import { describe, it, expect, beforeEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { usePipelineStore } from './pipeline';

describe('usePipelineStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('ajoute et retire des étapes', () => {
    const s = usePipelineStore();
    expect(s.isEmpty).toBe(true);
    s.addStep('sharpen', 'unsharp_mask', { radius: 1.2 });
    s.addStep('denoise', 'median', {});
    expect(s.steps).toHaveLength(2);
    s.removeStep(0);
    expect(s.steps).toHaveLength(1);
    expect(s.steps[0]?.algo).toBe('denoise');
  });

  it('met à jour un paramètre sans toucher aux autres', () => {
    const s = usePipelineStore();
    s.addStep('sharpen', 'unsharp_mask', { radius: 1.2, percent: 150 });
    s.updateParam(0, 'radius', 2.0);
    expect(s.steps[0]?.params.radius).toBe(2.0);
    expect(s.steps[0]?.params.percent).toBe(150);
  });

  it('change de méthode et réinitialise les params', () => {
    const s = usePipelineStore();
    s.addStep('sharpen', 'unsharp_mask', { radius: 1.2 });
    s.setMethod(0, 'denoise', 'median');
    expect(s.steps[0]?.algo).toBe('denoise');
    expect(s.steps[0]?.method).toBe('median');
    expect(s.steps[0]?.params).toEqual({});
  });

  it('reset vide toutes les étapes', () => {
    const s = usePipelineStore();
    s.addStep('sharpen', 'unsharp_mask', {});
    s.addStep('scale2x', 'scale2x', {});
    s.reset();
    expect(s.isEmpty).toBe(true);
  });

  it('undo/redo restaure un état antérieur', () => {
    const s = usePipelineStore();
    expect(s.canUndo).toBe(false);
    s.addStep('sharpen', 'unsharp_mask', {});
    s.addStep('denoise', 'median', {});
    expect(s.canUndo).toBe(true);
    s.undo();
    expect(s.steps).toHaveLength(1);
    expect(s.steps[0]?.algo).toBe('sharpen');
    expect(s.canRedo).toBe(true);
    s.redo();
    expect(s.steps).toHaveLength(2);
  });

  it('coalesce les updateParam consécutifs sur la même clé', () => {
    const s = usePipelineStore();
    s.addStep('sharpen', 'unsharp_mask', { radius: 1 });
    const before = s.steps[0]?.params.radius;
    s.updateParam(0, 'radius', 2);
    s.updateParam(0, 'radius', 3);
    s.updateParam(0, 'radius', 4);
    s.undo();
    expect(s.steps[0]?.params.radius).toBe(before);
  });
});
