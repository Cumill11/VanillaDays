import { env } from 'cloudflare:workers';
import type { APIRoute } from 'astro';
import { requireCsrf } from '../../../lib/security';

export const POST: APIRoute = async ({ params, request, locals }) => {
  const csrfError = await requireCsrf(locals.session, request);
  if (csrfError) return csrfError;
  const id = Number.parseInt(params.id || '', 10);
  if (!Number.isFinite(id)) return new Response('Nieprawidłowy wpis', { status: 400 });
  await env.DB.prepare('DELETE FROM overtime_log WHERE id = ?').bind(id).run();
  return new Response(null, { status: 204, headers: { 'HX-Refresh': 'true' } });
};
