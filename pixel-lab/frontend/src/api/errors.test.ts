import { describe, expect, it } from 'vitest';
import { parseApiError } from './errors';

function jsonResponse(body: unknown, status = 422): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('parseApiError', () => {
  it('formate les erreurs Pydantic avec loc + msg', async () => {
    const err = await parseApiError(
      jsonResponse({
        errors: [
          { loc: ['body', 'images'], msg: "fichier introuvable 'x.png'", type: 'value_error' },
          { loc: ['body', 'pipeline', 0, 'algo'], msg: 'Input should be sharpen', type: 'literal_error' },
        ],
      }),
    );
    expect(err.status).toBe(422);
    expect(err.message).toContain('images');
    expect(err.message).toContain("fichier introuvable 'x.png'");
    expect(err.message).toContain('pipeline.0.algo');
  });

  it("remonte le champ `error` legacy quand pas d'errors Pydantic", async () => {
    const err = await parseApiError(jsonResponse({ error: 'not_found' }, 404));
    expect(err.status).toBe(404);
    expect(err.message).toBe('not_found');
  });

  it('fallback HTTP N quand le corps est vide', async () => {
    const res = new Response('', { status: 500 });
    const err = await parseApiError(res);
    expect(err.message).toBe('HTTP 500');
  });

  it('lit le champ `detail` de FastAPI HTTPException', async () => {
    const err = await parseApiError(jsonResponse({ detail: 'Un job est déjà actif' }, 409));
    expect(err.message).toBe('Un job est déjà actif');
  });
});
