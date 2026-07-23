import type { APIRoute } from "astro";
import { env } from "cloudflare:workers";

export const GET: APIRoute = async () => {
  try {
    await env.DB.prepare("SELECT 1").first();
    return Response.json({ status: "ok" });
  } catch {
    return Response.json({ status: "error" }, { status: 503 });
  }
};
