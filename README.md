# VanillaDays — FastAPI

Aplikacja do śledzenia urlopów i nieobecności napisana w FastAPI + Jinja2 + HTMX + Alpine.js.

## Funkcje

- **Pulpit** — bilans urlopu, nadgodzin i HO z wykresem miesięcznym
- **Kalendarz** — widok miesięczny, dodawanie/usuwanie wpisów kliknięciem
- **Historia** — tabela z filtrowaniem po typie i miesiącu, eksport CSV, drukowanie
- **Ustawienia** — limity urlopu i HO per rok, przeniesione dni z poprzedniego roku
- Obsługa 6 typów nieobecności: urlop, HO, okolicznościowy, bezpłatny, L4, za święto
- Polskie święta wyliczane dynamicznie (włącznie z ruchomymi)
- Rate limiting na logowanie (5 prób → blokada 15 min)
- Ciemny motyw Material Design 3

## Stack

| Warstwa | Technologia |
|---------|-------------|
| Backend | FastAPI + Uvicorn |
| Szablony | Jinja2 (server-side rendering) |
| Interaktywność | HTMX + Alpine.js |
| Wykresy | Chart.js |
| Baza danych | MySQL (pymysql) |
| Sesje | Starlette SessionMiddleware (itsdangerous) |
| Hasła | bcrypt |

## Wymagania

- Docker + Docker Compose
- Baza danych MySQL / MariaDB (zewnętrzna lub w osobnym kontenerze)

## Szybki start

```bash
# 1. Skopiuj plik środowiskowy i uzupełnij zmienne
cp .env.example .env

# 2. Uruchom
docker-compose up -d

# 3. Aplikacja dostępna pod
http://localhost:8000
```

Tabele w bazie danych (`year_config`, `leave_entries`, `overtime_log`) tworzone są automatycznie przy starcie.

## Zmienne środowiskowe

| Zmienna | Opis | Przykład |
|---------|------|---------|
| `DB_HOST` | Adres serwera MySQL | `db.example.com` |
| `DB_USER` | Użytkownik bazy danych | `urlopy` |
| `DB_PASSWORD` | Hasło do bazy danych | |
| `DB_NAME` | Nazwa bazy danych | `urlopy` |
| `SECRET_KEY` | Klucz podpisujący sesję (min. 32 losowe bajty) | |
| `LOGIN_USERNAME` | Nazwa użytkownika do logowania | `admin` |
| `LOGIN_PASSWORD_HASH` | Hash hasła (bcrypt) | |
| `COOKIE_SECURE` | `1` = ciasteczko tylko przez HTTPS | `1` |
| `TRUSTED_PROXY` | `1` = czytaj IP z `X-Forwarded-For` | `1` |

### Generowanie wartości

```bash
# SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"

# LOGIN_PASSWORD_HASH
python3 -c "import bcrypt; print(bcrypt.hashpw(b'TWOJE_HASLO', bcrypt.gensalt(12)).decode())"
```

## Uruchomienie lokalne (bez Docker)

```bash
# Utwórz venv w katalogu projektu
python3 -m venv venv
source venv/bin/activate

# Zainstaluj zależności
pip install -r app/requirements.txt

# Uzupełnij .env (skopiuj z .env.example)
cp .env.example .env

# Uruchom (musi być z katalogu app/ ze względu na relatywne ścieżki)
cd app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Testy

```bash
# Zainstaluj zależności testowe (raz)
pip install -r requirements-test.txt

# Uruchom testy (nie wymaga połączenia z bazą danych)
python -m pytest
```

## Bezpieczeństwo

### Co jest zabezpieczone

| Zagrożenie | Zastosowane zabezpieczenie |
|-----------|---------------------------|
| SQL injection | Parametryzowane zapytania pymysql |
| XSS | Jinja2 autoescape (`autoescape=True`) na wszystkich szablonach |
| CSRF | `SameSite=Lax` na ciasteczku sesji + `form-action 'self'` w CSP |
| Clickjacking | `frame-ancestors 'none'` w CSP + `X-Frame-Options: DENY` |
| MIME sniffing | `X-Content-Type-Options: nosniff` |
| Open redirect | Walidacja `next=` — tylko ścieżki względne bez `//` i `/\` |
| Brute force | Rate limiting: 5 prób → blokada 15 min per IP |
| Przejęcie sesji | `HttpOnly=True`, `SameSite=Lax`, opcjonalnie `Secure=True` |
| Wyciek referera | `Referrer-Policy: strict-origin-when-cross-origin` |

### Content Security Policy

```
default-src 'self';
script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.jsdelivr.net;
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src 'self' https://fonts.gstatic.com;
img-src 'self' https://cdn.kamilkowalczyk.pl data:;
connect-src 'self' https://cdn.jsdelivr.net;
frame-ancestors 'none';
base-uri 'self';
form-action 'self';
```

> `unsafe-inline` i `unsafe-eval` są wymagane przez Alpine.js (ewaluacja wyrażeń `x-data`, `@click` itp.). XSS jest blokowany po stronie serwera przez Jinja2 autoescape. `cdn.jsdelivr.net` w `connect-src` jest potrzebne dla source map Chart.js pobieranych przez devtools.

### Hasła

Hasła przechowywane są wyłącznie jako hash bcrypt w zmiennej środowiskowej — nigdy w bazie danych. Aplikacja obsługuje jednego użytkownika.

### Zalecana konfiguracja produkcyjna

- Ustaw `COOKIE_SECURE=1` i uruchom aplikację za odwrotnym proxy (nginx/Traefik) z TLS
- Ustaw `TRUSTED_PROXY=1` jeśli proxy ustawia `X-Forwarded-For`
- Użyj silnego, losowego `SECRET_KEY` (min. 256 bitów)
- Ogranicz dostęp do bazy danych tylko do hosta aplikacji

## Struktura projektu

```
fastapi-urlopy/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pytest.ini
├── requirements-test.txt
├── app/
│   ├── main.py              # Logika aplikacji i routing
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── static/
│   │   ├── css/style.css    # Material Design 3 dark theme
│   │   ├── fonts/           # Czcionka Gotham
│   │   ├── js/app.js        # Alpine.js + HTMX + Chart.js helpers
│   │   └── logo.svg
│   └── templates/
│       ├── base.html        # Layout z sidebarem, topbarem i modalem
│       ├── dashboard.html
│       ├── calendar.html
│       ├── history.html
│       ├── settings.html
│       └── login.html
└── tests/
    ├── conftest.py          # Fixtures i mockowanie bazy danych
    ├── test_auth.py         # Logowanie, rate limiting, wylogowanie
    ├── test_pages.py        # Renderowanie stron, guard autoryzacji
    ├── test_crud.py         # Wpisy, konfiguracja, nadgodziny, CSV
    ├── test_business_logic.py  # Czyste funkcje (fmt_days, easter, itp.)
    └── test_security.py     # Nagłówki bezpieczeństwa, CSP
```

## Endpointy API

| Metoda | Ścieżka | Opis |
|--------|---------|------|
| `GET` | `/` | Pulpit |
| `GET` | `/calendar` | Kalendarz (`?year=&month=`) |
| `GET` | `/history` | Historia (`?year=&type=&month=`) |
| `GET` | `/settings` | Ustawienia |
| `GET` | `/export/csv` | Eksport CSV (`?year=&type=`) |
| `GET` | `/login` | Formularz logowania |
| `POST` | `/login` | Logowanie |
| `POST` | `/logout` | Wylogowanie |
| `POST` | `/entries/save` | Dodaj / edytuj wpis |
| `POST` | `/entries/{id}/delete` | Usuń wpis |
| `POST` | `/config/{year}/save` | Zapisz konfigurację roku |
| `POST` | `/overtime/save` | Dodaj wpis nadgodzin |
| `POST` | `/overtime/{id}/delete` | Usuń wpis nadgodzin |
| `GET` | `/health` | Health check (bez autoryzacji) |

---

# VanillaDays — FastAPI (English)

A single-user leave and absence tracker built with FastAPI + Jinja2 + HTMX + Alpine.js.

## Features

- **Dashboard** — vacation balance, overtime and home-office summary with a monthly bar chart
- **Calendar** — month view, add/remove entries by clicking on a day
- **History** — filterable table (by type and month), CSV export, print view
- **Settings** — per-year vacation and HO limits, carry-over days from the previous year
- 6 absence types: vacation, home office, special leave, unpaid leave, sick leave (L4), holiday swap
- Polish public holidays calculated dynamically (including moveable feasts)
- Login rate limiting (5 attempts → 15-minute lockout per IP)
- Material Design 3 dark theme

## Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI + Uvicorn |
| Templates | Jinja2 (server-side rendering) |
| Interactivity | HTMX + Alpine.js |
| Charts | Chart.js |
| Database | MySQL (pymysql) |
| Sessions | Starlette SessionMiddleware (itsdangerous) |
| Passwords | bcrypt |

## Requirements

- Docker + Docker Compose
- MySQL / MariaDB database (external or in a separate container)

## Quick start

```bash
# 1. Copy the example env file and fill in the values
cp .env.example .env

# 2. Start
docker-compose up -d

# 3. Open
http://localhost:8000
```

Database tables (`year_config`, `leave_entries`, `overtime_log`) are created automatically on first start.

## Environment variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DB_HOST` | MySQL server address | `db.example.com` |
| `DB_USER` | Database user | `urlopy` |
| `DB_PASSWORD` | Database password | |
| `DB_NAME` | Database name | `urlopy` |
| `SECRET_KEY` | Session signing key (min. 32 random bytes) | |
| `LOGIN_USERNAME` | Login username | `admin` |
| `LOGIN_PASSWORD_HASH` | bcrypt password hash | |
| `COOKIE_SECURE` | `1` = HTTPS-only cookie | `1` |
| `TRUSTED_PROXY` | `1` = read IP from `X-Forwarded-For` | `1` |

### Generating values

```bash
# SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"

# LOGIN_PASSWORD_HASH
python3 -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt(12)).decode())"
```

## Local development (without Docker)

```bash
# Create a virtualenv at the project root
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r app/requirements.txt

# Copy and fill in .env
cp .env.example .env

# Run (must be from app/ because of relative static/templates paths)
cd app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Tests

```bash
# Install test dependencies (once)
pip install -r requirements-test.txt

# Run tests (no database connection required)
python -m pytest
```

## Security

### What is protected

| Threat | Mitigation |
|--------|------------|
| SQL injection | Parameterised queries via pymysql |
| XSS | Jinja2 autoescape (`autoescape=True`) on all templates |
| CSRF | `SameSite=Lax` session cookie + `form-action 'self'` in CSP |
| Clickjacking | `frame-ancestors 'none'` in CSP + `X-Frame-Options: DENY` |
| MIME sniffing | `X-Content-Type-Options: nosniff` |
| Open redirect | `next=` validation — relative paths only, rejects `//` and `/\` |
| Brute force | Rate limiting: 5 attempts → 15-min lockout per IP |
| Session hijacking | `HttpOnly=True`, `SameSite=Lax`, optionally `Secure=True` |
| Referrer leakage | `Referrer-Policy: strict-origin-when-cross-origin` |

### Content Security Policy

```
default-src 'self';
script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.jsdelivr.net;
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src 'self' https://fonts.gstatic.com;
img-src 'self' https://cdn.kamilkowalczyk.pl data:;
connect-src 'self' https://cdn.jsdelivr.net;
frame-ancestors 'none';
base-uri 'self';
form-action 'self';
```

> `unsafe-inline` and `unsafe-eval` are required by Alpine.js to evaluate template expressions (`x-data`, `@click`, etc.). XSS is prevented server-side by Jinja2 autoescape. `cdn.jsdelivr.net` in `connect-src` is needed for Chart.js source maps fetched by browser devtools.

### Passwords

Passwords are stored exclusively as a bcrypt hash in an environment variable — never in the database. The application supports a single user.

### Recommended production setup

- Set `COOKIE_SECURE=1` and run behind a reverse proxy (nginx / Traefik) with TLS
- Set `TRUSTED_PROXY=1` if the proxy sets `X-Forwarded-For`
- Use a strong, random `SECRET_KEY` (at least 256 bits)
- Restrict database access to the application host only

## Project structure

```
fastapi-urlopy/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pytest.ini
├── requirements-test.txt
├── app/
│   ├── main.py              # Application logic and routing
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── static/
│   │   ├── css/style.css    # Material Design 3 dark theme
│   │   ├── fonts/           # Gotham font
│   │   ├── js/app.js        # Alpine.js + HTMX + Chart.js helpers
│   │   └── logo.svg
│   └── templates/
│       ├── base.html        # Layout: sidebar, topbar, modal
│       ├── dashboard.html
│       ├── calendar.html
│       ├── history.html
│       ├── settings.html
│       └── login.html
└── tests/
    ├── conftest.py          # Fixtures and database mocking
    ├── test_auth.py         # Login, rate limiting, logout
    ├── test_pages.py        # Page rendering, auth guard
    ├── test_crud.py         # Entries, config, overtime, CSV
    ├── test_business_logic.py  # Pure functions (fmt_days, easter, etc.)
    └── test_security.py     # Security headers, CSP
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Dashboard |
| `GET` | `/calendar` | Calendar (`?year=&month=`) |
| `GET` | `/history` | History (`?year=&type=&month=`) |
| `GET` | `/settings` | Settings |
| `GET` | `/export/csv` | CSV export (`?year=&type=`) |
| `GET` | `/login` | Login form |
| `POST` | `/login` | Authenticate |
| `POST` | `/logout` | Log out |
| `POST` | `/entries/save` | Add / edit an entry |
| `POST` | `/entries/{id}/delete` | Delete an entry |
| `POST` | `/config/{year}/save` | Save year configuration |
| `POST` | `/overtime/save` | Add overtime entry |
| `POST` | `/overtime/{id}/delete` | Delete overtime entry |
| `GET` | `/health` | Health check (no auth required) |
