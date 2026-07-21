/// <reference path="../.astro/types.d.ts" />
/// <reference types="astro/client" />

declare namespace Cloudflare {
  interface Env {
    DB: D1Database;
    SECRET_KEY: string;
    ADMIN_USERNAME?: string;
    ADMIN_PASSWORD?: string;
    HTTPS_ONLY?: string;
  }
}

interface Env extends Cloudflare.Env {}

declare namespace App {
  interface Locals {
    authenticated: boolean;
  }
}
