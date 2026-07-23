import { defineMiddleware } from "astro:middleware";

const PUBLIC_PATHS = new Set(["/login", "/health"]);

export const onRequest = defineMiddleware(async (context, next) => {
  context.locals.authenticated = (await context.session?.get("user")) === "admin";

  if (!context.locals.authenticated && !PUBLIC_PATHS.has(context.url.pathname)) {
    return context.redirect("/login", 303);
  }

  const response = await next();
  response.headers.set("Cache-Control", "no-store");
  return response;
});
