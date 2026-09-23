import { defineMiddleware, sequence } from "astro:middleware";
import { getActionContext } from "astro:actions";

const PUBLIC_PATHS = new Set(["/login", "/health"]);

// Nagłówki dla każdej odpowiedzi workera (public/_headers działa tylko na pliki
// statyczne). DENY = strony nie da się osadzić w ramce (clickjacking).
const RESPONSE_HEADERS = {
  "Cache-Control": "no-store",
  "X-Frame-Options": "DENY",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
};

const responseHeaders = defineMiddleware(async (_context, next) => {
  const response = await next();
  for (const [name, value] of Object.entries(RESPONSE_HEADERS)) response.headers.set(name, value);
  return response;
});

const auth = defineMiddleware(async (context, next) => {
  context.locals.authenticated = (await context.session?.get("user")) === "admin";

  if (!context.locals.authenticated) {
    // Akcja uruchamia się przy POST na DOWOLNĄ ścieżkę z `?_action=nazwa`,
    // więc publiczna ścieżka nie może jej przepuścić.
    if (getActionContext(context).action) return new Response("Forbidden", { status: 403 });
    if (!PUBLIC_PATHS.has(context.url.pathname)) return context.redirect("/login", 303);
  }

  return next();
});

export const onRequest = sequence(responseHeaders, auth);
