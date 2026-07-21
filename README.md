# VanillaDays

Ewidencja urlopów, Home Office, nieobecności i nadgodzin. Astro SSR na Cloudflare
Workers, dane w D1.

## Wymagania

- Node.js 20+
- Konto Cloudflare z dostępem do Workers i D1
- Zalogowany Wrangler: `npx wrangler login`

## Uruchomienie lokalne

```bash
npm install
cp .dev.vars.example .dev.vars
```

Uzupełnij `.dev.vars`. Klucz podpisujący sesję wygeneruj przez `openssl rand -hex 32`:

```
SECRET_KEY=<wynik openssl rand -hex 32>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<dowolne hasło do lokalnych testów>
HTTPS_ONLY=false
```

> `HTTPS_ONLY=false` jest lokalnie konieczne. Przy `true` cookie sesji dostaje flagę
> `Secure` i przeglądarka nie odeśle go po zwykłym HTTP — zalogujesz się i od razu
> wrócisz na ekran logowania.

`.dev.vars` jest w `.gitignore` i nigdy nie trafia do repozytorium. W repozytorium
jest tylko `.dev.vars.example` z pustymi wartościami.

Baza lokalna i start:

```bash
npm run db:migrate:local
npm run dev
```

Aplikacja stoi pod `http://127.0.0.1:4321`, wejście przez `/login`.

**Serwer odłącza się do tła** — komenda kończy się od razu, ale proces działa dalej
i nie zamknie go `Ctrl+C`:

```bash
npx astro dev status    # czy działa, na jakim porcie
npx astro dev logs      # log serwera
npx astro dev stop      # zatrzymanie
```

## Sekrety

| Nazwa            | Rola                                                           |
| ---------------- | -------------------------------------------------------------- |
| `SECRET_KEY`     | Klucz podpisujący cookie sesji. **Nie jest** hasłem logowania. |
| `ADMIN_USERNAME` | Nazwa użytkownika. **Wymagana.**                               |
| `ADMIN_PASSWORD` | Hasło. **Wymagane.**                                           |

Nie ma bazy użytkowników — jest jedno konto, którego dane leżą w sekretach Cloudflare.
Po zalogowaniu serwer odsyła podpisane HMAC-SHA256 ciasteczko ważne **12 godzin**;
zawiera tylko datę wygaśnięcia i podpis. Hasło porównywane jest metodą stałoczasową.
Bcrypta nie ma — hasło i tak leży w Cloudflare Secrets, obok `SECRET_KEY`, więc
hashowanie nic by tu nie dodało.

`SECRET_KEY` ma być **inny w każdej aplikacji**. Token sesji zawiera wyłącznie datę
i podpis, bez nazwy aplikacji — przy wspólnym kluczu ciasteczko z jednej aplikacji
otworzyłoby pozostałe.

`HTTPS_ONLY` nie jest sekretem — siedzi w `wrangler.jsonc` jako `vars` i na produkcji
ma być `"true"`.

## Wdrożenie

Sekrety **nie są brane z `.dev.vars`** — ten plik działa wyłącznie lokalnie. Na produkcji
ustawia się je raz, osobno:

```bash
npx wrangler secret put SECRET_KEY        # openssl rand -hex 32
npx wrangler secret put ADMIN_USERNAME
npx wrangler secret put ADMIN_PASSWORD
npx wrangler secret list                  # podgląd nazw, bez wartości
```

Migracje bazy produkcyjnej:

```bash
npm run db:migrate:remote
npx wrangler d1 migrations list vanilladays --remote   # co jeszcze czeka
```

Wdrożenie:

```bash
npm run deploy
```

`deploy` sam buduje projekt (`astro build && wrangler deploy`) — bez tego dałoby się
wysłać nieaktualny `dist`, a przy nazwach plików z hashem kończy się to stroną bez CSS-u.

Podgląd bez publikowania: `npx wrangler deploy --dry-run`.

## Zmiana hasła

```bash
npx wrangler secret put ADMIN_PASSWORD
```

Działa od razu, ale **istniejące sesje pozostają ważne** do końca swoich 12 godzin,
bo podpisuje je `SECRET_KEY`, nie hasło. Żeby natychmiast unieważnić wszystkie sesje,
zmień `SECRET_KEY`.

Nie ma procedury odzyskiwania hasła i nie jest potrzebna — po prostu ustaw nowe.
Dostęp do panelu Cloudflare jest tu jedynym „resetem hasła”.

## Częste problemy

| Objaw                                                                        | Przyczyna                                                                                                                       |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| „Logowanie nie jest skonfigurowane”                                          | Brakuje `ADMIN_USERNAME` albo `ADMIN_PASSWORD`. Oba są wymagane.                                                                |
| Logujesz się i wracasz na ekran logowania                                    | Lokalnie `HTTPS_ONLY=true`. Zmień na `false` w `.dev.vars`.                                                                     |
| Formularz zwraca 403                                                         | Ochrona CSRF odrzuciła żądanie z obcego źródła. Przy normalnym korzystaniu z przeglądarki nie występuje.                        |
| Każda strona zwraca 500, w treści „does not exist … optimize deps directory” | Rozjechany cache Vite po zmianie zależności albo `.dev.vars`. `npx astro dev stop`, `rm -rf node_modules/.vite`, `npm run dev`. |

## Komendy

| Komenda                     | Działanie                                |
| --------------------------- | ---------------------------------------- |
| `npm run dev`               | Serwer deweloperski                      |
| `npm run build`             | `astro check` (typy) + build produkcyjny |
| `npm run preview`           | Podgląd zbudowanej wersji                |
| `npm run format`            | Prettier                                 |
| `npm run deploy`            | Build i wdrożenie na Cloudflare          |
| `npm run db:migrate:local`  | Migracje bazy lokalnej                   |
| `npm run db:migrate:remote` | Migracje bazy produkcyjnej               |
| `npm run cf-typegen`        | Regeneracja typów bindingów              |

## Czym się różni od pozostałych dwóch

**Cała aplikacja jest prywatna.** Bez zalogowania nie zobaczysz nic poza `/login`
i `/health`. Nie ma części publicznej ani osobnego panelu — po zalogowaniu masz
dostęp do wszystkiego.

Z tego wynikają dwie rzeczy:

- **Nic nie jest cache'owane.** Każda odpowiedź dostaje `no-store` i `X-Robots-Tag: noindex`.
  Portfolio i Stories trzymają strony publiczne w cache krawędziowym; tutaj byłoby to
  wyciekiem danych.
- **Nie ma R2.** Aplikacja nie przyjmuje plików, więc jedynym magazynem jest D1.

## Funkcje

- Pulpit: bilans urlopu, Home Office, urlopu okolicznościowego i nadgodzin
- Wykres roczny — czysty CSS, bez biblioteki
- Kalendarz miesięczny z polskimi świętami
- Historia wpisów z filtrami, wydrukiem i eksportem CSV
- Typy wpisów: urlop, Home Office, okolicznościowy, bezpłatny, L4, za święto
- Nadgodziny zarobione i odebrane
- Ustawienia limitów rocznych

## Trasy

| Ścieżka                                  | Rola                           |
| ---------------------------------------- | ------------------------------ |
| `/login`, `/health`                      | jedyne publiczne               |
| `/`                                      | pulpit                         |
| `/calendar`, `/history`, `/settings`     | pozostałe widoki               |
| `/entries/save`, `/entries/:id/delete`   | zapis i usuwanie wpisów (POST) |
| `/overtime/save`, `/overtime/:id/delete` | nadgodziny (POST)              |
| `/export/csv`                            | eksport historii               |

Zapis idzie POST-em na trasę, która odsyła przekierowanie 303. Eksport CSV
poprzedza wartości zaczynające się od `=`, `+`, `-` lub `@` apostrofem, żeby arkusz
nie potraktował ich jak formuły.

## Zasoby w Cloudflare

| Rodzaj | Nazwa                    |
| ------ | ------------------------ |
| Worker | `vanilladays`            |
| Domena | urlopy.kamilkowalczyk.pl |
| D1     | `vanilladays`            |

Binding `SESSION` (KV) dokłada automatycznie adapter Cloudflare. Aplikacja go nie
używa — logowanie opiera się na podpisanym ciasteczku, nie na magazynie sesji.

## Migracje

| Plik                           | Co robi                                                           |
| ------------------------------ | ----------------------------------------------------------------- |
| `0001_initial.sql`             | schemat                                                           |
| `0002_remove_users.sql`        | usuwa tabelę użytkowników po przejściu na jedno konto w sekretach |
| `0003_drop_login_attempts.sql` | usuwa tabelę po wyłączonym limicie prób logowania                 |

## Logi

`observability` jest włączone w `wrangler.jsonc`. Podgląd na żywo:

```bash
npx wrangler tail
```
