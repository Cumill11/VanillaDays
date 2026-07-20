import { env } from 'cloudflare:workers';
import type { APIRoute } from 'astro';
import { clearSession, isHttpsOnly, requireCsrf } from '../lib/security';

export const POST: APIRoute = async ({ request, locals }) => {
  const csrfError = await requireCsrf(locals.session, request);
  if (csrfError) return csrfError;
  const headers = new Headers({ Location: '/login' });
  clearSession(headers, isHttpsOnly(env.HTTPS_ONLY));
  return new Response(null, { status: 303, headers });
};
