import type { ApiErrorBody } from '@/types/api';

export class ApiError extends Error {
  readonly status: number;
  readonly body: ApiErrorBody;

  constructor(status: number, body: ApiErrorBody, message: string) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

/** Produit un message humain à partir d'une réponse API en erreur. */
export async function parseApiError(res: Response): Promise<ApiError> {
  let body: ApiErrorBody = {};
  try {
    body = (await res.json()) as ApiErrorBody;
  } catch {
    // Corps non JSON — on laisse body vide
  }
  let message: string;
  if (body.errors && body.errors.length) {
    message = body.errors
      .map((e) => {
        const loc = (e.loc ?? []).filter((x) => x !== 'body').join('.');
        return loc ? `${loc}: ${e.msg}` : e.msg;
      })
      .join(' · ');
  } else if (body.message) {
    message = body.message;
  } else if (typeof body.detail === 'string') {
    message = body.detail;
  } else if (body.error) {
    message = body.error;
  } else {
    message = `HTTP ${res.status}`;
  }
  return new ApiError(res.status, body, message);
}
