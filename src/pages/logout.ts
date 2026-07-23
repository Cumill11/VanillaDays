import type { APIRoute } from "astro";

export const POST: APIRoute = ({ session, redirect }) => {
  session?.destroy();
  return redirect("/login", 303);
};
