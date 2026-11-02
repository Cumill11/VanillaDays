import { defineConfig } from "astro/config";
import cloudflare from "@astrojs/cloudflare";

export default defineConfig({
  output: "server",
  adapter: cloudflare({
    imageService: "passthrough",
  }),
  // Bez tego adapter Cloudflare sam włącza sesje w KV (binding SESSION).
  session: false,
  vite: {
    // Obejście withastro/astro#17893 / #17788:
    // adapter Cloudflare nie dopisuje tych modułów do SSR optimizeDeps, więc przy
    // zimnym cache `.vite` Vite odkrywa je w trakcie żądania i `astro dev` pada.
    // Tylko dev — build produkcyjny ignoruje optimizeDeps.
    ssr: {
      optimizeDeps: {
        include: [
          "astro/app/manifest",
          "astro/assets/services/noop",
          "astro/logger/json",
          "astro/logger/console",
        ],
      },
    },
  },
});
