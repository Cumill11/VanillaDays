# VanillaDays

Prosta aplikacja do ewidencji urlopów, Home Office i nadgodzin. Napisana w Astro
(SSR), działa na Cloudflare Workers, dane trzyma w bazie D1.

## Funkcje

- Pulpit z bilansem urlopu, Home Office i nadgodzin
- Kalendarz miesięczny z polskimi świętami
- Historia wpisów z filtrami i eksportem do CSV
- Typy wpisów: urlop, Home Office, okolicznościowy, bezpłatny, L4, za święto
- Ustawienia limitów rocznych

## Uruchomienie lokalne

Wymagany Node.js 22.12+ i konto Cloudflare.

```bash
npm install
npm run db:migrate:local
npm run dev
```

Aplikacja działa pod `http://localhost:4321`.

## Wdrożenie

Migracje i deploy:

```bash
npm run db:migrate:remote
npm run deploy
```

Podczas git push następuje automatyczne wdrożenie na Cloudflare.

## Komendy

| Komenda                     | Działanie                       |
| --------------------------- | ------------------------------- |
| `npm run dev`               | Serwer deweloperski             |
| `npm run build`             | Build produkcyjny               |
| `npm run deploy`            | Build i wdrożenie na Cloudflare |
| `npm run db:migrate:local`  | Migracje bazy lokalnej          |
| `npm run db:migrate:remote` | Migracje bazy produkcyjnej      |
