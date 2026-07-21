/**
 * Sesja administratora: podpisany cookie (HMAC-SHA256) z czasem wygaśnięcia.
 *
 * Ochrona CSRF: SameSite=Lax (przeglądarka nie wyśle cookie przy cross-site POST)
 * plus wbudowane `security.checkOrigin` Astro, włączone w astro.config.mjs.
 */

const SESSION_COOKIE = "session";
const SESSION_TTL_SECONDS = 60 * 60 * 12;

function base64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

async function hmac(secret: string, payload: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(payload));
  return base64Url(new Uint8Array(signature));
}

/** Porównanie odporne na atak czasowy. */
function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export function passwordMatches(actual: string, expected: string): boolean {
  return Boolean(expected) && safeEqual(actual, expected);
}

export async function createSession(secret: string): Promise<string> {
  const exp = Math.floor(Date.now() / 1000) + SESSION_TTL_SECONDS;
  return `${exp}.${await hmac(secret, String(exp))}`;
}

export async function verifySession(
  value: string | undefined,
  secret: string | undefined,
): Promise<boolean> {
  if (!value || !secret) return false;
  const [expRaw, signature] = value.split(".");
  if (!expRaw || !signature) return false;
  if (!safeEqual(signature, await hmac(secret, expRaw))) return false;
  const exp = Number(expRaw);
  return Number.isFinite(exp) && exp > Math.floor(Date.now() / 1000);
}

export function readSessionCookie(request: Request): string | undefined {
  const cookie = request.headers.get("Cookie") || "";
  const found = cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${SESSION_COOKIE}=`));
  return found?.slice(SESSION_COOKIE.length + 1);
}

export function setSessionCookie(headers: Headers, value: string, httpsOnly: boolean): void {
  const secure = httpsOnly ? "; Secure" : "";
  headers.append(
    "Set-Cookie",
    `${SESSION_COOKIE}=${value}; Path=/; Max-Age=${SESSION_TTL_SECONDS}; HttpOnly; SameSite=Lax${secure}`,
  );
}

export function clearSessionCookie(headers: Headers, httpsOnly: boolean): void {
  const secure = httpsOnly ? "; Secure" : "";
  headers.append(
    "Set-Cookie",
    `${SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax${secure}`,
  );
}

export function isHttpsOnly(value: string | undefined): boolean {
  return (
    String(value ?? "true")
      .trim()
      .toLowerCase() !== "false"
  );
}

/** Chroni przed open redirect w parametrze ?next=. */
export function safeNext(value: string | null | undefined): string {
  if (!value) return "/";
  if (!value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return "/";
  return value;
}
