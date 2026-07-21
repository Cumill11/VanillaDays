import { defineMiddleware } from "astro:middleware";
import { env } from "cloudflare:workers";
import { readSessionCookie, verifySession } from "@/lib/auth";

/** Ścieżki dostępne bez zalogowania. Cała reszta aplikacji jest chroniona. */
const PUBLIC_PATHS = new Set(["/login", "/health"]);

const SECURITY_HEADERS: Record<string, string> = {
  "Content-Security-Policy": [
    "default-src 'self'",
    "img-src 'self' data:",
    "style-src 'self' 'unsafe-inline'",
    "script-src 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; "),
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
};

/**
 * Cała aplikacja jest prywatna, więc żadna strona nie może trafić do cache —
 * łącznie z ekranem logowania. Bez tego przeglądarka stosuje własną heurystykę
 * i po wdrożeniu potrafi podać stary HTML, wskazujący na nieistniejące
 * już pliki /_astro/*.
 *
 * Pliki statyczne to omija: Workers Assets serwuje je bez uruchamiania Workera.
 */
function withSecurityHeaders(response: Response): Response {
  const headers = new Headers(response.headers);
  for (const [name, value] of Object.entries(SECURITY_HEADERS)) headers.set(name, value);
  headers.set("Cache-Control", "no-store");
  headers.set("X-Robots-Tag", "noindex, nofollow");
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

function isPublic(pathname: string): boolean {
  return PUBLIC_PATHS.has(pathname) || pathname.startsWith("/static/");
}

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = context.url;
  context.locals.authenticated = await verifySession(
    readSessionCookie(context.request),
    env.SECRET_KEY,
  );

  if (!isPublic(pathname) && !context.locals.authenticated) {
    const target = `/login?next=${encodeURIComponent(pathname)}`;
    return withSecurityHeaders(context.redirect(target, 303));
  }

  return withSecurityHeaders(await next());
});
