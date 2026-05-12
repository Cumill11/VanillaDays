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
cd app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Ustaw zmienne środowiskowe (lub utwórz .env w katalogu app/)
export SECRET_KEY=...
export LOGIN_USERNAME=...
export LOGIN_PASSWORD_HASH=...
export DB_HOST=...

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
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
script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net;
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src 'self' https://fonts.gstatic.com;
img-src 'self' https://cdn.kamilkowalczyk.pl data:;
connect-src 'self';
frame-ancestors 'none';
base-uri 'self';
form-action 'self';
```

> `unsafe-inline` dla skryptów jest wymagane przez Alpine.js (`x-data`, `@click`) i inline handlery HTMX. Pozostałe dyrektywy (`form-action`, `frame-ancestors`, `base-uri`) pozostają restrykcyjne.

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
├── docker-compose.yml
└── app/
    ├── main.py              # Logika aplikacji i routing
    ├── requirements.txt
    ├── Dockerfile
    ├── static/
    │   ├── css/style.css    # Material Design 3 dark theme
    │   ├── fonts/           # Czcionka Gotham
    │   ├── js/app.js        # Alpine.js + HTMX + Chart.js helpers
    │   └── logo.svg
    └── templates/
        ├── base.html        # Layout z sidebarem, topbarem i modalem
        ├── dashboard.html
        ├── calendar.html
        ├── history.html
        ├── settings.html
        └── login.html
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
