import { env } from 'cloudflare:workers';
import type { APIRoute } from 'astro';
import { getOrCreateConfig } from '../../../lib/db';
import { verifyCsrf } from '../../../lib/security';

function boundedNumber(value: FormDataEntryValue | null, fallback: number, min: number, max: number): number {
  const parsed = Number(value || fallback);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(min, Math.min(max, parsed));
}

export const POST: APIRoute = async ({ params, request, locals }) => {
  const form = await request.formData();
  if (!verifyCsrf(locals.session, form, request)) return new Response('<div class="alert alert--error">Nieprawidłowy token CSRF — odśwież stronę.</div>', { status: 403 });

  const year = Number.parseInt(params.year || '', 10);
  if (!Number.isFinite(year) || year < 2020 || year > new Date().getFullYear() + 2) {
    return new Response('<div class="alert alert--error">Nieprawidłowy rok.</div>', { status: 400 });
  }

  await getOrCreateConfig(env.DB, year);
  await env.DB.prepare(`
    UPDATE year_config
    SET vacation_limit = ?, ho_limit = ?, vacation_carried_over = ?
    WHERE year = ?
  `).bind(
    boundedNumber(form.get('vacation_limit'), 26, 0, 100),
    Math.round(boundedNumber(form.get('ho_limit'), 24, 0, 260)),
    boundedNumber(form.get('vacation_carried_over'), 0, 0, 50),
    year,
  ).run();
  return new Response('<div class="alert alert--success">Zapisano!</div>', { status: 200 });
};
