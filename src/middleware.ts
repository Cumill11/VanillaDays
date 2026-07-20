import { defineMiddleware } from 'astro:middleware';
import { env } from 'cloudflare:workers';
import { PERMISSIONS_POLICY, getSessionCookie, verifySessionCookie } from './lib/security';

const UNPROTECTED = new Set(['/login', '/health']);

function applyResponseHeaders(response: Response, requestId: string): Response {
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('Permissions-Policy', PERMISSIONS_POLICY);
  response.headers.set('X-Request-ID', requestId);
  return response;
}

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = new URL(context.request.url);
  const requestId = crypto.randomUUID();

  context.locals.session = await verifySessionCookie(getSessionCookie(context.request), env.SECRET_KEY);

  if (!pathname.startsWith('/static/') && !UNPROTECTED.has(pathname) && !context.locals.session) {
    const response = context.redirect(`/login?next=${encodeURIComponent(pathname)}`, 303);
    applyResponseHeaders(response, requestId);
    return response;
  }

  const response = await next();
  applyResponseHeaders(response, requestId);
  return response;
});
