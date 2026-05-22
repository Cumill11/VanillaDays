# VanillaDays

Prosta aplikacja webowa do śledzenia urlopów, dni Home Office i nadgodzin —
zbudowana we Flasku, z bazą MySQL/MariaDB. Działa też jako PWA (instalacja na
telefonie, tryb offline).

---

## 🇵🇱 Polski

### Funkcje

- **Pulpit** — bilans urlopu, Home Office, urlopu okolicznościowego oraz nadgodzin,
  wykresy miesięczne i ostrzeżenia (np. kończący się limit).
- **Kalendarz** — widok miesięczny z polskimi świętami i wpisami urlopowymi.
- **Historia** — lista wszystkich wpisów z filtrowaniem po typie i miesiącu,
  eksport do CSV.
- **Typy wpisów** — urlop wypoczynkowy, Home Office, urlop okolicznościowy,
  bezpłatny, L4, urlop za święto.
- **Nadgodziny** — rejestr godzin wypracowanych i odebranych.
- **Ustawienia** — limity urlopu, Home Office oraz dni przeniesione z poprzedniego roku.
- **Bezpieczeństwo** — logowanie (bcrypt), ochrona CSRF, limit prób logowania,
  nagłówki bezpieczeństwa (CSP, X-Frame-Options itd.).
- **PWA** — działa offline, instalowalna jako aplikacja.

### Wymagania

- Python 3.14 (lub Docker)
- Baza MySQL / MariaDB

### Konfiguracja

1. Skopiuj plik przykładowy i uzupełnij wartości:

   ```bash
   cp .env.example .env
   ```

2. Wygeneruj klucz sesji:

   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

3. Wygeneruj hash hasła logowania:

   ```bash
   python3 -c "import bcrypt; print(bcrypt.hashpw(b'TWOJE_HASLO', bcrypt.gensalt(12)).decode())"
   ```

   Wstaw hash do `LOGIN_PASSWORD_HASH` **w apostrofach** — inaczej docker compose
   zinterpretuje znak `$` i uszkodzi hash.

### Uruchomienie

**Docker Compose** (zalecane):

```bash
docker compose up -d
```

Aplikacja będzie dostępna pod `http://localhost:8003`.

**Lokalnie:**

```bash
pip install -r requirements.txt
python VanillaDays/app.py
```

Aplikacja będzie dostępna pod `http://localhost:8000`.

Tabele w bazie tworzą się automatycznie przy starcie.

### Zmienne środowiskowe

| Zmienna               | Opis                                                          |
|-----------------------|---------------------------------------------------------------|
| `DB_HOST`             | Adres serwera bazy danych                                     |
| `DB_USER`             | Użytkownik bazy danych                                        |
| `DB_PASSWORD`         | Hasło do bazy danych                                          |
| `DB_NAME`             | Nazwa bazy danych                                             |
| `SECRET_KEY`          | Klucz sesji Flask                                             |
| `LOGIN_USERNAME`      | Nazwa użytkownika do logowania                                |
| `LOGIN_PASSWORD_HASH` | Hash hasła (bcrypt), w apostrofach                            |
| `HTTPS_ONLY`          | `true` jeśli aplikacja działa za HTTPS                        |
| `TRUSTED_PROXY`       | `true` jeśli aplikacja stoi za reverse proxy                  |
| `FLASK_DEBUG`         | Tryb debugowania (tylko `python app.py`)                      |
| `FLASK_HOST`          | Adres nasłuchiwania (tylko `python app.py`)                   |
| `FLASK_PORT`          | Port nasłuchiwania (tylko `python app.py`)                    |

---

## 🇬🇧 English

VanillaDays is a simple web app for tracking vacation days, Home Office days and
overtime — built with Flask and a MySQL/MariaDB database. It also works as a PWA
(installable on mobile, offline support).

### Features

- **Dashboard** — balance of vacation, Home Office, special leave and overtime,
  monthly charts and warnings (e.g. limit running low).
- **Calendar** — monthly view with Polish public holidays and leave entries.
- **History** — list of all entries with filtering by type and month, CSV export.
- **Entry types** — vacation, Home Office, special leave, unpaid leave, sick
  leave (L4), holiday-in-lieu.
- **Overtime** — log of hours earned and taken.
- **Settings** — vacation and Home Office limits, days carried over from the
  previous year.
- **Security** — login (bcrypt), CSRF protection, login rate limiting, security
  headers (CSP, X-Frame-Options, etc.).
- **PWA** — works offline, installable as an app.

### Requirements

- Python 3.14 (or Docker)
- MySQL / MariaDB database

### Configuration

1. Copy the example file and fill in the values:

   ```bash
   cp .env.example .env
   ```

2. Generate the session key:

   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

3. Generate the login password hash:

   ```bash
   python3 -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt(12)).decode())"
   ```

   Put the hash into `LOGIN_PASSWORD_HASH` **inside single quotes** — otherwise
   docker compose interpolates the `$` character and corrupts the hash.

### Running

**Docker Compose** (recommended):

```bash
docker compose up -d
```

The app will be available at `http://localhost:8003`.

**Locally:**

```bash
pip install -r requirements.txt
python VanillaDays/app.py
```

The app will be available at `http://localhost:8000`.

Database tables are created automatically on startup.

### Environment variables

| Variable              | Description                                                   |
|-----------------------|---------------------------------------------------------------|
| `DB_HOST`             | Database server host                                          |
| `DB_USER`             | Database user                                                 |
| `DB_PASSWORD`         | Database password                                             |
| `DB_NAME`             | Database name                                                 |
| `SECRET_KEY`          | Flask session key                                             |
| `LOGIN_USERNAME`      | Login username                                                |
| `LOGIN_PASSWORD_HASH` | Password hash (bcrypt), inside single quotes                  |
| `HTTPS_ONLY`          | `true` if the app runs behind HTTPS                           |
| `TRUSTED_PROXY`       | `true` if the app runs behind a reverse proxy                 |
| `FLASK_DEBUG`         | Debug mode (only for `python app.py`)                         |
| `FLASK_HOST`          | Listen address (only for `python app.py`)                     |
| `FLASK_PORT`          | Listen port (only for `python app.py`)                        |
