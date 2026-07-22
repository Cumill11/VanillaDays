import type { APIRoute } from "astro";
import { env } from "cloudflare:workers";

/**
 * Sonda dla monitoringu zewnętrznego (Uptime-Kuma).
 *
 * Wykonuje jedno tanie zapytanie, żeby zielony status potwierdzał całą ścieżkę
 * Worker → D1, a nie samo to, że Worker wstał. Odpowiedź jest wyłączona
 * z cache — podana z krawędzi opisywałaby stan sprzed godziny.
 */
export const GET: APIRoute = async () => {
  const headers = { "Cache-Control": "no-store" };
  try {
    await env.DB.prepare("SELECT 1").first();
    return Response.json({ status: "ok" }, { headers });
  } catch {
    return Response.json({ status: "error" }, { status: 503, headers });
  }
};
