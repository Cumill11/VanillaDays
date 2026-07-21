# VanillaDays

Ewidencja urlopów, Home Office, nieobecności i nadgodzin. Astro SSR na Cloudflare
Workers, dane w D1.

> Instalacja, sekrety, wdrożenie i hasła są opisane raz dla wszystkich trzech
> projektów w [`../README.md`](../README.md). Tutaj tylko to, co swoiste dla tej aplikacji.

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
