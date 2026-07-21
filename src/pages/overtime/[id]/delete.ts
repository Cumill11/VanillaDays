import type { APIRoute } from "astro";
import { env } from "cloudflare:workers";
import { safeNext } from "@/lib/auth";

export const POST: APIRoute = async ({ params, request, redirect }) => {
  const form = await request.formData();
  const back = safeNext(String(form.get("next") || "/"));
  const id = Number.parseInt(params.id || "", 10);
  if (!Number.isFinite(id)) return new Response("Nieprawidłowy wpis", { status: 400 });
  await env.DB.prepare("DELETE FROM overtime_log WHERE id = ?").bind(id).run();
  return redirect(back, 303);
};
