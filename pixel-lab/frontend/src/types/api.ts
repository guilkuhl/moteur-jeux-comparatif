/** Contrats API — alignés sur les schémas Pydantic de `server_fastapi/schemas/`. */

export type Algo = 'sharpen' | 'scale2x' | 'denoise' | 'pixelsnap';

export interface AlgoParamMeta {
  name: string;
  type: 'int' | 'float' | 'bool';
  default: number | boolean;
  min?: number;
  max?: number;
}

export interface AlgoMethod {
  params: AlgoParamMeta[];
}

export type AlgosCatalog = Record<Algo, { methods: Record<string, AlgoMethod> }>;

export interface PipelineStep {
  algo: Algo;
  method: string;
  params: Record<string, number | boolean>;
}

export interface ConvertRequest {
  images: string[];
  pipeline: PipelineStep[];
}

export interface PreviewRequest {
  image: string;
  pipeline: PipelineStep[];
  downscale: number | null;
}

export interface PreviewResult {
  blob: Blob;
  width: number;
  height: number;
  elapsedMs: number;
  cacheHitDepth: number;
}

export interface InputFile {
  name: string;
  processed: boolean;
}

export interface PydanticErrorItem {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ApiErrorBody {
  errors?: PydanticErrorItem[];
  error?: string;
  message?: string;
  detail?: string | Record<string, unknown>;
}

export interface JobCreatedResponse {
  job_id: string;
}
