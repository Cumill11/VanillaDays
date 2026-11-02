/// <reference path="../.astro/types.d.ts" />
/// <reference types="astro/client" />

declare namespace Cloudflare {
  interface Env {
    DB: D1Database;
  }
}
