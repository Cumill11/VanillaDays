import type { APIRoute } from "astro";
import { env } from "cloudflare:workers";
import { safeNext } from "@/lib/auth";

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export const POST: APIRoute = async ({ request, redirect }) => {
  const form = await request.formData();
  const back = safeNext(String(form.get("next") || "/"));
  const date = String(form.get("date") || "").trim();
  const type = String(form.get("type") || "earned").trim();
  const hours = Number(String(form.get("hours") || "").trim());
  const notes = String(form.get("notes") || "").trim() || null;

  if (!DATE_RE.test(date)) return new Response("Brak daty", { status: 400 });
  if (type !== "earned" && type !== "taken")
    return new Response("Nieprawidłowy typ", { status: 400 });
  if (!Number.isFinite(hours) || hours <= 0) {
    return new Response("Liczba godzin musi być większa od 0", { status: 400 });
  }

  await env.DB.prepare("INSERT INTO overtime_log (date, hours, type, notes) VALUES (?, ?, ?, ?)")
    .bind(date, hours, type, notes)
    .run();
  return redirect(back, 303);
};
