import { defineMiddleware } from "astro:middleware";

// Nagłówki dla każdej odpowiedzi workera (public/_headers działa tylko na pliki
// statyczne). DENY = strony nie da się osadzić w ramce (clickjacking).
const RESPONSE_HEADERS = {
  "Cache-Control": "no-store",
  "X-Frame-Options": "DENY",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
};

export const onRequest = defineMiddleware(async (_context, next) => {
  const response = await next();
  for (const [name, value] of Object.entries(RESPONSE_HEADERS)) response.headers.set(name, value);
  return response;
});
