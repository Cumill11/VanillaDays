# VanillaDays

Prosta aplikacja do ewidencji urlopów, Home Office i nadgodzin. Napisana w Astro
(SSR), działa na Cloudflare Workers, dane trzyma w bazie D1.

## Funkcje

- Pulpit z bilansem urlopu, Home Office i nadgodzin
- Kalendarz miesięczny z polskimi świętami
- Historia wpisów z filtrami i eksportem do CSV
- Typy wpisów: urlop, Home Office, okolicznościowy, bezpłatny, L4, za święto
- Ustawienia limitów rocznych
- Logowanie — aplikacja jest w całości prywatna

## Uruchomienie lokalne

Wymagany Node.js 20+ i konto Cloudflare.

```bash
npm install
cp .dev.vars.example .dev.vars   # uzupełnij ADMIN_USERNAME i ADMIN_PASSWORD
npm run db:migrate:local
npm run dev
```

Aplikacja działa pod `http://localhost:4321`.

## Wdrożenie

Sekrety na produkcji ustawia się raz przez wranglera:

```bash
npx wrangler secret put ADMIN_USERNAME
npx wrangler secret put ADMIN_PASSWORD
```

Potem migracje i deploy:

```bash
npm run db:migrate:remote
npm run deploy
```
Podczas git push następuje automatyczne wdrożenie na Cloudflare
## Komendy

| Komenda                     | Działanie                       |
| --------------------------- | ------------------------------- |
| `npm run dev`               | Serwer deweloperski             |
| `npm run build`             | Build produkcyjny               |
| `npm run deploy`            | Build i wdrożenie na Cloudflare |
| `npm run db:migrate:local`  | Migracje bazy lokalnej          |
| `npm run db:migrate:remote` | Migracje bazy produkcyjnej      |

## Jak działa logowanie

Jest jedno konto — dane logowania siedzą w sekretach Cloudflare, nie w bazie.
Po zalogowaniu Astro tworzy sesję (wbudowane `Astro.session`) przechowywaną
w Cloudflare KV i ważną 12 godzin. Middleware sprawdza sesję przy każdym
żądaniu i bez niej przekierowuje na `/login`. Wylogowanie kasuje sesję po
stronie serwera.
