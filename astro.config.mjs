import { defineConfig } from "astro/config";
import cloudflare from "@astrojs/cloudflare";

export default defineConfig({
  output: "server",
  adapter: cloudflare({
    imageService: "passthrough",
  }),
  security: {
    // Blokuje cross-site POST z formularzy — nasza ochrona CSRF (razem z SameSite=Lax).
    checkOrigin: true,
  },
  server: {
    host: "127.0.0.1",
    port: 4321,
  },
  devToolbar: {
    enabled: false,
  },
  vite: {
    build: {
      // Bez tego Vite wkleja pliki poniżej 4 kB jako data: URI, a CSP
      // (`script-src 'self'`) blokuje takie skrypty.
      assetsInlineLimit: 0,
    },
  },
});
