import type { APIRoute } from "astro";
import { env } from "cloudflare:workers";
import type { LeaveType } from "@/lib/types";

const TYPES = new Set<LeaveType>([
  "vacation",
  "home_office",
  "okolicznosciowy",
  "bezplatny",
  "l4",
  "za_swieto",
]);
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const MAX_NOTES = 500;

export const POST: APIRoute = async ({ request }) => {
  const form = await request.formData();
  const entryId = String(form.get("id") || "").trim();
  const date = String(form.get("date") || "").trim();
  const type = String(form.get("type") || "").trim() as LeaveType;
  const okolReason = String(form.get("okol_reason") || "").trim();
  const l4Number = String(form.get("l4_number") || "").trim();
  const zaSwietoDay = String(form.get("za_swieto_day") || "").trim();
  let notes = String(form.get("notes") || "").trim();

  if (!DATE_RE.test(date) || !TYPES.has(type))
    return new Response("Brak daty lub typu", { status: 400 });

  if (type === "okolicznosciowy" && okolReason) notes = okolReason + (notes ? ` | ${notes}` : "");
  if (type === "l4" && l4Number) notes = `ZUS: ${l4Number}` + (notes ? ` | ${notes}` : "");
  if (type === "za_swieto" && zaSwietoDay)
    notes = `Za: ${zaSwietoDay}` + (notes ? ` | ${notes}` : "");

  // Limit po sklejeniu — pola pomocnicze też trafiają do notatki.
  if (notes.length > MAX_NOTES) return new Response("Notatka jest za długa", { status: 400 });
  const noteValue = notes || null;

  try {
    if (entryId) {
      const id = Number.parseInt(entryId, 10);
      if (!Number.isFinite(id)) return new Response("Nieprawidłowy wpis", { status: 400 });
      await env.DB.prepare("UPDATE leave_entries SET date = ?, type = ?, notes = ? WHERE id = ?")
        .bind(date, type, noteValue, id)
        .run();
    } else {
      await env.DB.prepare("INSERT INTO leave_entries (date, type, notes) VALUES (?, ?, ?)")
        .bind(date, type, noteValue)
        .run();
    }
  } catch {
    return new Response("Wpis dla tej daty już istnieje", { status: 409 });
  }

  return new Response(null, { status: 204 });
};
