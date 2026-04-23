/** Événements SSE — union discriminée sur `type`. */

export interface StepStartEvent {
  type: 'step_start';
  image: string;
  step: number;
  algo: string;
  method: string;
}

export interface StepDoneEvent {
  type: 'step_done';
  image: string;
  step: number;
  output: string | null;
}

export interface StepErrorEvent {
  type: 'step_error';
  image: string;
  step: number;
  stderr: string;
}

export interface WarningEvent {
  type: 'warning';
  message: string;
}

export interface ImageDoneEvent {
  type: 'image_done';
  image: string;
}

export interface DoneEvent {
  type: 'done';
}

export type SSEEvent =
  | StepStartEvent
  | StepDoneEvent
  | StepErrorEvent
  | WarningEvent
  | ImageDoneEvent
  | DoneEvent;

export const isStepDone = (e: SSEEvent): e is StepDoneEvent => e.type === 'step_done';
export const isStepError = (e: SSEEvent): e is StepErrorEvent => e.type === 'step_error';
export const isDone = (e: SSEEvent): e is DoneEvent => e.type === 'done';
