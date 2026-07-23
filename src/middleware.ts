import { defineMiddleware } from "astro:middleware";

export const onRequest = defineMiddleware(async (context, next) => {
  context.locals.authenticated = (await context.session?.get("user")) === "admin";

  if (!context.locals.authenticated && context.url.pathname !== "/login") {
    return context.redirect("/login", 303);
  }

  const response = await next();
  response.headers.set("Cache-Control", "no-store");
  return response;
});
