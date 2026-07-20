# VanillaDays

VanillaDays to aplikacja do śledzenia urlopów, Home Office, nieobecności i nadgodzin.
Aplikacja działa na Astro SSR, Cloudflare Workers i Cloudflare D1.

## Funkcje

- Pulpit z bilansem urlopu, Home Office, urlopu okolicznościowego i nadgodzin.
- Kalendarz miesięczny z polskimi świętami.
- Historia wpisów z filtrami, drukiem i eksportem CSV.
- Typy wpisów: urlop, Home Office, okolicznościowy, bezpłatny, L4, za święto.
- Nadgodziny: zarobione i odebrane.
- Ustawienia limitów rocznych.
- Własne logowanie: login i bcrypt hash w sekretach Workera, podpisana sesja HttpOnly, CSRF, rate limit prób logowania w D1.

## Lokalnie

```bash
npm install
cp .dev.vars.example .dev.vars
```

Uzupełnij `.dev.vars`:

```bash
SECRET_KEY=...
LOGIN_USERNAME=admin
LOGIN_PASSWORD_HASH=...
HTTPS_ONLY=false
```

Hash hasła możesz wygenerować np. tak:

```bash
node -e "import('bcryptjs').then(async b => console.log(await b.hash(process.argv[1], 12)))" 'twoje-haslo'
```

Uruchom migracje D1 lokalnie:

```bash
npm run db:migrate:local
```

Start aplikacji:

```bash
npm run build
npm run preview
```

## Cloudflare

Ustaw sekret sesji:

```bash
npx wrangler secret put SECRET_KEY
```

Ustaw login i hash hasła jako sekrety:

```bash
npx wrangler secret put LOGIN_USERNAME
npx wrangler secret put LOGIN_PASSWORD_HASH
```

Zastosuj migracje D1:

```bash
npm run db:migrate:remote
```

Build:

```bash
npm run build
```

Deploy:

```bash
npx wrangler deploy
```

Workers Logs są włączone natywnie przez `observability` w `wrangler.jsonc`.
Do podglądu logów na żywo:

```bash
npx wrangler tail
```

Jeśli używasz istniejącej bazy D1, wstaw jej `database_id` do `wrangler.jsonc`.
Bez `database_id` aktualny Wrangler może automatycznie provisionować zasób na koncie Cloudflare.
