interface Env {
  DB: D1Database;
  SECRET_KEY: string;
  LOGIN_USERNAME?: string;
  LOGIN_PASSWORD_HASH?: string;
  HTTPS_ONLY?: string;
}
