import { env } from 'cloudflare:workers';
import type { APIRoute } from 'astro';
import { verifyCsrf } from '../../lib/security';

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export const POST: APIRoute = async ({ request, locals }) => {
  const form = await request.formData();
  if (!verifyCsrf(locals.session, form, request)) return new Response('Nieprawidłowy token CSRF — odśwież stronę.', { status: 403 });
  const date = String(form.get('date') || '').trim();
  const hoursStr = String(form.get('hours') || '').trim();
  const type = String(form.get('type') || 'earned').trim();
  const notes = String(form.get('notes') || '').trim() || null;
  if (!DATE_RE.test(date) || !hoursStr) return new Response('Brak danych', { status: 400 });
  if (type !== 'earned' && type !== 'taken') return new Response('Nieprawidłowy typ', { status: 400 });
  const hours = Number(hoursStr);
  if (!Number.isFinite(hours)) return new Response('Nieprawidłowa liczba godzin', { status: 400 });
  if (hours <= 0) return new Response('Liczba godzin musi być większa od 0', { status: 400 });
  await env.DB.prepare('INSERT INTO overtime_log (date, hours, type, notes) VALUES (?, ?, ?, ?)')
    .bind(date, hours, type, notes)
    .run();
  return new Response(null, { status: 200 });
};
