import type { SessionData } from './types';

const SESSION_COOKIE = 'session';
const SESSION_TTL_SECONDS = 60 * 60 * 12;

function base64Url(bytes: Uint8Array): string {
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function base64UrlEncodeText(text: string): string {
  return base64Url(new TextEncoder().encode(text));
}

function base64UrlDecodeText(value: string): string {
  const padded = value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (value.length % 4)) % 4);
  const binary = atob(padded);
  return new TextDecoder().decode(Uint8Array.from(binary, (c) => c.charCodeAt(0)));
}

async function hmac(secret: string, payload: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(payload));
  return base64Url(new Uint8Array(sig));
}

function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export function randomToken(bytes = 32): string {
  const buf = new Uint8Array(bytes);
  crypto.getRandomValues(buf);
  return base64Url(buf);
}

export async function createSessionCookie(secret: string): Promise<{ value: string; session: SessionData }> {
  const session: SessionData = {
    csrf: randomToken(32),
    exp: Math.floor(Date.now() / 1000) + SESSION_TTL_SECONDS,
  };
  const payload = base64UrlEncodeText(JSON.stringify(session));
  const sig = await hmac(secret, payload);
  return { value: `${payload}.${sig}`, session };
}

export async function verifySessionCookie(value: string | undefined, secret: string): Promise<SessionData | null> {
  if (!value) return null;
  const [payload, sig] = value.split('.');
  if (!payload || !sig) return null;
  const expected = await hmac(secret, payload);
  if (!safeEqual(sig, expected)) return null;
  try {
    const session = JSON.parse(base64UrlDecodeText(payload)) as SessionData;
    if (!session.csrf || !session.exp) return null;
    if (session.exp < Math.floor(Date.now() / 1000)) return null;
    return session;
  } catch {
    return null;
  }
}

export function setSession(headers: Headers, value: string, httpsOnly = true): void {
  const secure = httpsOnly ? '; Secure' : '';
  headers.append(
    'Set-Cookie',
    `${SESSION_COOKIE}=${value}; Path=/; Max-Age=${SESSION_TTL_SECONDS}; HttpOnly; SameSite=Lax${secure}`,
  );
}

export function clearSession(headers: Headers, httpsOnly = true): void {
  const secure = httpsOnly ? '; Secure' : '';
  headers.append('Set-Cookie', `${SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax${secure}`);
}

export function getSessionCookie(request: Request): string | undefined {
  const cookie = request.headers.get('Cookie') || '';
  const found = cookie.split(';').map((part) => part.trim()).find((part) => part.startsWith(`${SESSION_COOKIE}=`));
  return found?.slice(SESSION_COOKIE.length + 1);
}

export function verifyCsrf(session: SessionData | null | undefined, form: FormData, request: Request): boolean {
  if (!session?.csrf) return false;
  const sent = String(form.get('csrf_token') || request.headers.get('X-CSRFToken') || '');
  return safeEqual(sent, session.csrf);
}

export async function requireCsrf(
  session: SessionData | null | undefined,
  request: Request,
  html = false,
): Promise<Response | null> {
  const form = await request.formData().catch(() => new FormData());
  if (verifyCsrf(session, form, request)) return null;
  const body = html
    ? '<div class="alert alert--error">Nieprawidłowy token CSRF — odśwież stronę.</div>'
    : 'Nieprawidłowy token CSRF — odśwież stronę.';
  return new Response(body, { status: 403 });
}

export function isHttpsOnly(envValue: string | undefined): boolean {
  return String(envValue ?? 'true').trim().toLowerCase() !== 'false';
}

export function safeNext(url: string | null | undefined): string {
  if (!url) return '/';
  if (!url.startsWith('/') || url.startsWith('//') || url.startsWith('/\\')) return '/';
  return url;
}

export function csvSafe(value: unknown): string {
  const s = value == null ? '' : String(value);
  return ['=', '+', '-', '@', '\t', '\r'].includes(s[0] || '') ? `'${s}` : s;
}

export const PERMISSIONS_POLICY = [
  'accelerometer=()',
  'ambient-light-sensor=()',
  'autoplay=()',
  'battery=()',
  'camera=()',
  'display-capture=()',
  'document-domain=()',
  'encrypted-media=()',
  'fullscreen=(self)',
  'geolocation=()',
  'gyroscope=()',
  'magnetometer=()',
  'microphone=()',
  'midi=()',
  'payment=()',
  'picture-in-picture=()',
  'publickey-credentials-get=()',
  'usb=()',
  'xr-spatial-tracking=()',
].join(', ');
