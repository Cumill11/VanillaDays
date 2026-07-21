import type { APIRoute } from "astro";
import { env } from "cloudflare:workers";
import { clearSessionCookie, isHttpsOnly } from "@/lib/auth";

export const POST: APIRoute = async () => {
  const headers = new Headers({ Location: "/login" });
  clearSessionCookie(headers, isHttpsOnly(env.HTTPS_ONLY));
  return new Response(null, { status: 303, headers });
};
