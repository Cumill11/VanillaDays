import os
import time
import threading
import calendar as cal_module
import csv
import io
import json
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import bcrypt
import pymysql
import pymysql.cursors
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

load_dotenv()

# ── App setup ───────────────────────────────────────────────────

app = FastAPI()

_secret = os.getenv('SECRET_KEY')
if not _secret:
    raise RuntimeError('SECRET_KEY is not set in environment')

# Auth middleware — runs after SessionMiddleware parses the cookie
UNPROTECTED_PATHS = {'/login', '/health', '/sw.js'}

@app.middleware('http')
async def require_auth(request: Request, call_next):
    path = request.url.path
    if path.startswith('/static') or path in UNPROTECTED_PATHS:
        return await call_next(request)
    if not request.session.get('logged_in'):
        return RedirectResponse(url=f'/login?next={request.url.path}', status_code=303)
    return await call_next(request)

# Security headers — wraps require_auth, so all responses get headers (including redirects)
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self' https://cdn.jsdelivr.net; "
    "worker-src 'self'; "
    "manifest-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)

@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = _CSP
    return response

# SessionMiddleware added last → outermost layer → runs before all HTTP middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=_secret,
    session_cookie='session',
    same_site='lax',
    https_only=os.getenv('COOKIE_SECURE', '0') == '1',
    max_age=12 * 3600,
)

app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')

# ── Rate limiter ────────────────────────────────────────────────

_rl_lock = threading.Lock()
_rl: dict[str, dict] = {}
_MAX_ATTEMPTS = 5
_LOCKOUT_SECS = 15 * 60

_TRUSTED_PROXY = os.getenv('TRUSTED_PROXY', '').strip()


def _get_ip(request: Request) -> str:
    if _TRUSTED_PROXY:
        forwarded = request.headers.get('X-Forwarded-For', '')
        if forwarded:
            return forwarded.split(',')[0].strip()
    return request.client.host if request.client else '127.0.0.1'


def _check_rate_limit(ip: str):
    with _rl_lock:
        entry = _rl.get(ip)
        if not entry:
            return True, 0
        if entry['locked_until'] and time.time() < entry['locked_until']:
            remaining = int(entry['locked_until'] - time.time())
            return False, remaining
        return True, 0


def _record_failure(ip: str):
    with _rl_lock:
        entry = _rl.setdefault(ip, {'count': 0, 'locked_until': None})
        entry['count'] += 1
        if entry['count'] >= _MAX_ATTEMPTS:
            entry['locked_until'] = time.time() + _LOCKOUT_SECS
            entry['count'] = 0


def _clear_failures(ip: str):
    with _rl_lock:
        _rl.pop(ip, None)


# ── DB ──────────────────────────────────────────────────────────

DB_CFG = dict(
    host=os.getenv('DB_HOST', ''),
    user=os.getenv('DB_USER', 'urlopy'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'urlopy'),
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True,
)

MONTH_NAMES = [
    'Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec',
    'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień',
]
MONTH_SHORT   = ['sty', 'lut', 'mar', 'kwi', 'maj', 'cze', 'lip', 'sie', 'wrz', 'paź', 'lis', 'gru']
WEEKDAY_SHORT = ['Pon', 'Wt', 'Śr', 'Czw', 'Pt', 'Sob', 'Nie']


def _db():
    return pymysql.connect(**DB_CFG)


def q_one(sql, params=()):
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    finally:
        conn.close()


def q_all(sql, params=()):
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def q_exec(sql, params=()):
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.lastrowid
    finally:
        conn.close()


def init_db():
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS year_config (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    year INT NOT NULL UNIQUE,
                    vacation_limit DECIMAL(5,2) NOT NULL DEFAULT 26,
                    ho_limit INT NOT NULL DEFAULT 24,
                    vacation_carried_over DECIMAL(5,2) NOT NULL DEFAULT 0,
                    overtime_balance DECIMAL(6,1) NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS leave_entries (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    date DATE NOT NULL,
                    type ENUM('vacation','home_office','okolicznosciowy','bezplatny','l4','za_swieto') NOT NULL,
                    notes VARCHAR(500) DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_date_type (date, type)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS overtime_log (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    date DATE NOT NULL,
                    hours DECIMAL(5,1) NOT NULL,
                    type ENUM('earned','taken') NOT NULL DEFAULT 'earned',
                    notes VARCHAR(200) DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            try:
                cur.execute("""
                    ALTER TABLE leave_entries
                    MODIFY COLUMN type ENUM('vacation','home_office','okolicznosciowy','bezplatny','l4','za_swieto') NOT NULL
                """)
            except Exception:
                pass
            try:
                cur.execute("""
                    ALTER TABLE year_config
                    ADD COLUMN overtime_balance DECIMAL(6,1) NOT NULL DEFAULT 0
                """)
            except Exception:
                pass
            try:
                cur.execute("""
                    ALTER TABLE overtime_log
                    ADD COLUMN type ENUM('earned','taken') NOT NULL DEFAULT 'earned'
                """)
                cur.execute("""
                    UPDATE overtime_log SET type='taken', hours=ABS(hours) WHERE hours < 0
                """)
            except Exception:
                pass
    finally:
        conn.close()


# ── Business logic ──────────────────────────────────────────────

def get_or_create_config(year):
    cfg = q_one('SELECT * FROM year_config WHERE year = %s', (year,))
    if cfg:
        return cfg
    q_exec("""
        INSERT INTO year_config (year, vacation_limit, ho_limit, vacation_carried_over)
        VALUES (%s, 26, 24, 0)
        ON DUPLICATE KEY UPDATE id=id
    """, (year,))
    return q_one('SELECT * FROM year_config WHERE year = %s', (year,))


OKOL_LIMIT = 2


def get_balance(year):
    cfg  = get_or_create_config(year)
    vac  = q_one("SELECT COUNT(*) AS days_used FROM leave_entries WHERE YEAR(date)=%s AND type='vacation'", (year,))
    ho   = q_one("SELECT COUNT(*) AS cnt FROM leave_entries WHERE YEAR(date)=%s AND type='home_office'", (year,))
    okol = q_one("SELECT COUNT(*) AS cnt FROM leave_entries WHERE YEAR(date)=%s AND type='okolicznosciowy'", (year,))
    bezp = q_one("SELECT COUNT(*) AS cnt FROM leave_entries WHERE YEAR(date)=%s AND type='bezplatny'", (year,))
    l4   = q_one("SELECT COUNT(*) AS cnt FROM leave_entries WHERE YEAR(date)=%s AND type='l4'", (year,))
    za   = q_one("SELECT COUNT(*) AS cnt FROM leave_entries WHERE YEAR(date)=%s AND type='za_swieto'", (year,))

    vac_used  = int(vac['days_used'])
    vac_total = round(float(cfg['vacation_limit']) + float(cfg['vacation_carried_over']), 2)
    ho_limit  = int(cfg['ho_limit'])
    ho_used   = int(ho['cnt'])
    okol_used = int(okol['cnt'])
    bezp_used = int(bezp['cnt'])
    l4_used   = int(l4['cnt'])
    za_used   = int(za['cnt'])

    return {
        'vacation': {
            'limit':        float(cfg['vacation_limit']),
            'carried_over': float(cfg['vacation_carried_over']),
            'total':        vac_total,
            'used':         vac_used,
            'remaining':    round(vac_total - vac_used, 2),
            'pct':          min(100, round(vac_used / vac_total * 100)) if vac_total else 0,
        },
        'home_office': {
            'limit':     ho_limit,
            'used':      ho_used,
            'remaining': ho_limit - ho_used,
            'pct':       min(100, round(ho_used / ho_limit * 100)) if ho_limit else 0,
        },
        'okolicznosciowy': {
            'limit':     OKOL_LIMIT,
            'used':      okol_used,
            'remaining': max(0, OKOL_LIMIT - okol_used),
            'pct':       min(100, round(okol_used / OKOL_LIMIT * 100)),
        },
        'bezplatny':  {'used': bezp_used},
        'l4':         {'used': l4_used},
        'za_swieto':  {'used': za_used},
        'overtime_balance': (lambda r: float(r['earned']) - float(r['taken']))(q_one("""
            SELECT
                COALESCE(SUM(CASE WHEN type='earned' THEN hours ELSE 0 END), 0) AS earned,
                COALESCE(SUM(CASE WHEN type='taken'  THEN hours ELSE 0 END), 0) AS taken
            FROM overtime_log WHERE YEAR(date)=%s
        """, (year,))),
    }


def get_stats(year):
    rows = q_all("""
        SELECT MONTH(date) AS month, type, COUNT(*) AS days
        FROM leave_entries WHERE YEAR(date)=%s
        GROUP BY MONTH(date), type ORDER BY month
    """, (year,))
    monthly = [{'month': i + 1, 'label': MONTH_SHORT[i], 'vacation': 0, 'home_office': 0} for i in range(12)]
    for row in rows:
        monthly[int(row['month']) - 1][row['type']] = round(float(row['days']), 2)
    return monthly


def get_calendar_days(year, month):
    first = date(year, month, 1)
    last  = date(year, month, cal_module.monthrange(year, month)[1])
    start = first - timedelta(days=first.weekday())
    end   = last  + timedelta(days=(6 - last.weekday()) % 7)
    days  = []
    cur   = start
    while cur <= end:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def easter_date(year):
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day   = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def get_polish_holidays(year):
    e = easter_date(year)
    hols = {
        date(year, 1, 1):    'Nowy Rok',
        date(year, 1, 6):    'Trzech Króli',
        e:                   'Wielkanoc',
        e + timedelta(1):    'Lany Poniedziałek',
        date(year, 5, 1):    'Święto Pracy',
        date(year, 5, 3):    'Święto Konstytucji',
        e + timedelta(49):   'Zielone Świątki',
        e + timedelta(60):   'Boże Ciało',
        date(year, 8, 15):   'Wniebowzięcie NMP',
        date(year, 11, 1):   'Wszyscy Święci',
        date(year, 11, 11):  'Niepodległość',
        date(year, 12, 25):  'Boże Narodzenie',
        date(year, 12, 26):  '2. dzień Bożego Narodzenia',
    }
    return {d.isoformat(): name for d, name in hols.items()}


def get_warnings(year, balance):
    today    = date.today()
    warns    = []
    vac_rem  = balance['vacation']['remaining']
    ho_rem   = balance['home_office']['remaining']
    okol_rem = balance['okolicznosciowy']['remaining']

    if vac_rem == 0:
        warns.append(('error', 'Urlop wyczerpany',
                      'Nie masz już dni urlopu na ten rok.'))
    elif vac_rem <= 3:
        warns.append(('warning', f'Zostało {fmt_days(vac_rem)} urlopu',
                      'Zaplanuj ostatnie dni urlopowe.'))

    if today.year == year:
        days_left = (date(year, 12, 31) - today).days
        if 0 < days_left <= 60 and vac_rem >= 3:
            warns.append(('info', f'Koniec roku za {days_left} dni',
                          f'Masz jeszcze {fmt_days(vac_rem)} urlopu do wykorzystania lub przeniesienia.'))

    if ho_rem == 0:
        warns.append(('warning', 'Limit HO wyczerpany',
                      'Nie masz już dni Home Office — HO nie przechodzi na kolejny rok.'))
    elif ho_rem <= 2:
        warns.append(('warning', f'Zostały {ho_rem} {"dzień" if ho_rem == 1 else "dni"} HO',
                      'Pamiętaj, że HO nie przechodzi na kolejny rok.'))

    if okol_rem == 0:
        warns.append(('warning', 'Limit urlopu okolicznościowego wyczerpany',
                      'Wykorzystałeś już 2 dni urlopu okolicznościowego w tym roku.'))

    return warns


def fmt_days(days, wpd=8):
    full  = int(days)
    frac  = days - full
    hours = round(frac * wpd * 2) / 2
    if hours >= wpd:
        full += 1
        hours = 0
    h_str = str(int(hours)) if hours == int(hours) else str(hours)
    if hours == 0:
        return f'{full} dni'
    elif full == 0:
        return f'{h_str}h'
    else:
        return f'{full} dni {h_str}h'


def fmt_date_pl(d):
    if not d:
        return ''
    return f"{WEEKDAY_SHORT[d.weekday()]}, {d.day} {MONTH_SHORT[d.month - 1]} {d.year}"


# ── Jinja2 globals & filters ────────────────────────────────────

def _tojson_filter(value):
    def _default(obj):
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f'Object of type {type(obj)} is not JSON serializable')
    # Markup prevents Jinja2 autoescape from double-encoding the JSON output
    return Markup(json.dumps(value, default=_default))


templates.env.globals['fmt_days']    = fmt_days
templates.env.globals['fmt_date_pl'] = fmt_date_pl
templates.env.filters['tojson']      = _tojson_filter


# ── Helpers ─────────────────────────────────────────────────────

def _parse_year(val, default=None):
    try:
        y = int(val)
        today = date.today()
        return max(2020, min(y, today.year + 2))
    except (TypeError, ValueError):
        return default if default is not None else date.today().year


def year_context(year):
    today = date.today()
    cy = today.year
    return dict(year=year, year_options=list(range(2023, cy + 2)), today=today)


def _safe_next(url: str) -> str:
    """Accept only same-origin relative paths; reject anything else."""
    if not url:
        return '/'
    # Reject protocol-relative (//evil.com) and backslash tricks (/\evil.com)
    if not url.startswith('/') or url.startswith('//') or url.startswith('/\\'):
        return '/'
    return url


# ── Routes: auth ────────────────────────────────────────────────

@app.get('/login')
async def login_get(request: Request, next: str = ''):
    if request.session.get('logged_in'):
        return RedirectResponse(url='/', status_code=303)
    return templates.TemplateResponse(request, 'login.html', {
        'error': None, 'next': _safe_next(next),
    })


@app.post('/login')
async def login_post(request: Request):
    if request.session.get('logged_in'):
        return RedirectResponse(url='/', status_code=303)

    form  = await request.form()
    ip    = _get_ip(request)
    error = None

    allowed, wait = _check_rate_limit(ip)
    if not allowed:
        mins  = wait // 60
        error = f'Za dużo nieudanych prób. Spróbuj za {mins} min.'
    else:
        username      = form.get('username', '').strip()
        password      = form.get('password', '').encode()
        stored        = os.getenv('LOGIN_PASSWORD_HASH', '').encode()
        expected_user = os.getenv('LOGIN_USERNAME', '')
        if stored and expected_user and username == expected_user and bcrypt.checkpw(password, stored):
            _clear_failures(ip)
            request.session['logged_in'] = True
            return RedirectResponse(url=_safe_next(form.get('next', '')), status_code=303)
        else:
            _record_failure(ip)
            _, wait = _check_rate_limit(ip)
            if wait:
                error = f'Za dużo nieudanych prób. Spróbuj za {wait // 60} min.'
            else:
                error = 'Nieprawidłowe hasło.'

    return templates.TemplateResponse(request, 'login.html', {
        'error': error,
        'next':  form.get('next', ''),
    })


@app.post('/logout')
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url='/login', status_code=303)


# ── Routes: pages ───────────────────────────────────────────────

@app.get('/')
async def dashboard(request: Request, year: Optional[str] = None):
    year    = _parse_year(year)
    balance = get_balance(year)
    recent  = q_all(
        "SELECT * FROM leave_entries WHERE YEAR(date)=%s ORDER BY date DESC LIMIT 10", (year,)
    )
    return templates.TemplateResponse(request, 'dashboard.html', {
        'balance':  balance,
        'stats':    get_stats(year),
        'warnings': get_warnings(year, balance),
        'recent':   recent,
        'active':   'dashboard',
        **year_context(year),
    })


@app.get('/calendar')
async def calendar_page(
    request: Request,
    year:  Optional[str] = None,
    month: Optional[int] = None,
):
    year  = _parse_year(year)
    month = month if month is not None else date.today().month

    days         = get_calendar_days(year, month)
    entries_list = q_all(
        "SELECT * FROM leave_entries WHERE date >= %s AND date <= %s ORDER BY date",
        (days[0].isoformat(), days[-1].isoformat()),
    )

    entries_by_date: dict = {}
    for e in entries_list:
        key = e['date'].isoformat() if hasattr(e['date'], 'isoformat') else str(e['date'])
        entries_by_date.setdefault(key, []).append(e)

    ot_list = q_all(
        "SELECT * FROM overtime_log WHERE date >= %s AND date <= %s ORDER BY date",
        (days[0].isoformat(), days[-1].isoformat()),
    )
    overtime_by_date: dict = {}
    for ot in ot_list:
        key = ot['date'].isoformat() if hasattr(ot['date'], 'isoformat') else str(ot['date'])
        overtime_by_date.setdefault(key, []).append(ot)

    prev_m, prev_y = (month - 1, year) if month > 1 else (12, year - 1)
    next_m, next_y = (month + 1, year) if month < 12 else (1, year + 1)

    return templates.TemplateResponse(request, 'calendar.html', {
        'month':            month,
        'month_name':       MONTH_NAMES[month - 1],
        'days':             days,
        'entries_by_date':  entries_by_date,
        'overtime_by_date': overtime_by_date,
        'holidays':         get_polish_holidays(year),
        'prev_month':       prev_m,
        'prev_year':        prev_y,
        'next_month':       next_m,
        'next_year':        next_y,
        'active':           'calendar',
        **year_context(year),
    })


@app.get('/history')
async def history(
    request: Request,
    year:  Optional[str] = None,
    type:  str = '',
    month: str = '',
):
    year    = _parse_year(year)
    type_f  = type
    month_f = month

    sql    = 'SELECT * FROM leave_entries WHERE YEAR(date)=%s'
    params = [year]
    if type_f:
        sql += ' AND type=%s'; params.append(type_f)
    if month_f:
        sql += ' AND MONTH(date)=%s'; params.append(int(month_f))
    sql += ' ORDER BY date DESC'
    entries = q_all(sql, tuple(params))

    ot_sql    = 'SELECT * FROM overtime_log WHERE YEAR(date)=%s'
    ot_params = [year]
    if month_f:
        ot_sql += ' AND MONTH(date)=%s'; ot_params.append(int(month_f))
    ot_sql += ' ORDER BY date DESC'
    ot_entries  = q_all(ot_sql, tuple(ot_params))
    ot_earned   = sum(float(e['hours']) for e in ot_entries if e.get('type') != 'taken')
    ot_taken    = sum(float(e['hours']) for e in ot_entries if e.get('type') == 'taken')
    ot_balance  = ot_earned - ot_taken

    return templates.TemplateResponse(request, 'history.html', {
        'entries':      entries,
        'type_filter':  type_f,
        'month_filter': month_f,
        'month_names':  MONTH_NAMES,
        'ot_entries':   ot_entries,
        'ot_earned':    ot_earned,
        'ot_taken':     ot_taken,
        'ot_balance':   ot_balance,
        'active':       'history',
        **year_context(year),
    })


@app.get('/settings')
async def settings(request: Request, year: Optional[str] = None):
    year   = _parse_year(year)
    config = get_or_create_config(year)
    return templates.TemplateResponse(request, 'settings.html', {
        'config': config,
        'active': 'settings',
        **year_context(year),
    })


# ── Routes: CRUD ────────────────────────────────────────────────

@app.post('/entries/save')
async def save_entry(request: Request):
    form          = await request.form()
    entry_id      = form.get('id', '').strip()
    d             = form.get('date', '')
    t             = form.get('type', '')
    notes         = form.get('notes', '').strip()
    okol_reason   = form.get('okol_reason', '').strip()
    l4_number     = form.get('l4_number', '').strip()
    za_swieto_day = form.get('za_swieto_day', '').strip()

    if t == 'okolicznosciowy' and okol_reason:
        notes = okol_reason + (f' | {notes}' if notes else '')
    if t == 'l4' and l4_number:
        notes = f'ZUS: {l4_number}' + (f' | {notes}' if notes else '')
    if t == 'za_swieto' and za_swieto_day:
        notes = f'Za: {za_swieto_day}' + (f' | {notes}' if notes else '')
    notes = notes or None

    if not d or not t:
        return Response('Brak daty lub typu', status_code=400)

    try:
        if entry_id:
            q_exec(
                "UPDATE leave_entries SET date=%s, type=%s, notes=%s WHERE id=%s",
                (d, t, notes, entry_id),
            )
        else:
            q_exec(
                "INSERT INTO leave_entries (date, type, notes) VALUES (%s, %s, %s)",
                (d, t, notes),
            )
    except pymysql.err.IntegrityError:
        return Response('Wpis dla tej daty już istnieje', status_code=409)

    return Response(status_code=200)


@app.post('/entries/{entry_id}/delete')
async def delete_entry(entry_id: int):
    q_exec('DELETE FROM leave_entries WHERE id=%s', (entry_id,))
    return Response(status_code=204, headers={'HX-Refresh': 'true'})


@app.post('/config/{year}/save')
async def save_config(year: int, request: Request):
    form = await request.form()
    get_or_create_config(year)
    q_exec("""
        UPDATE year_config
        SET vacation_limit=%s, ho_limit=%s, vacation_carried_over=%s
        WHERE year=%s
    """, (
        float(form.get('vacation_limit') or 26),
        int(form.get('ho_limit') or 24),
        float(form.get('vacation_carried_over') or 0),
        year,
    ))
    return HTMLResponse('<div class="alert alert--success">Zapisano!</div>', status_code=200)


@app.post('/overtime/save')
async def save_overtime(request: Request):
    form      = await request.form()
    d         = form.get('date', '')
    hours_str = form.get('hours', '').strip()
    ot_type   = form.get('type', 'earned')
    notes     = form.get('notes', '').strip() or None
    if not d or not hours_str:
        return Response('Brak danych', status_code=400)
    if ot_type not in ('earned', 'taken'):
        return Response('Nieprawidłowy typ', status_code=400)
    try:
        hours = float(hours_str)
    except ValueError:
        return Response('Nieprawidłowa liczba godzin', status_code=400)
    if hours <= 0:
        return Response('Liczba godzin musi być większa od 0', status_code=400)
    q_exec(
        "INSERT INTO overtime_log (date, hours, type, notes) VALUES (%s, %s, %s, %s)",
        (d, hours, ot_type, notes),
    )
    return Response(status_code=200)


@app.post('/overtime/{entry_id}/delete')
async def delete_overtime(entry_id: int):
    q_exec('DELETE FROM overtime_log WHERE id=%s', (entry_id,))
    return Response(status_code=204, headers={'HX-Refresh': 'true'})


@app.get('/export/csv')
async def export_csv(request: Request, year: Optional[str] = None, type: str = ''):
    year   = _parse_year(year)
    type_f = type

    sql    = 'SELECT * FROM leave_entries WHERE YEAR(date)=%s'
    params = [year]
    if type_f:
        sql += ' AND type=%s'; params.append(type_f)
    sql += ' ORDER BY date'
    entries = q_all(sql, tuple(params))

    TYPE_LABELS = {
        'vacation':        'Urlop',
        'home_office':     'Home Office',
        'okolicznosciowy': 'Urlop okolicznościowy',
        'bezplatny':       'Urlop bezpłatny',
        'l4':              'L4',
        'za_swieto':       'Urlop za święto',
    }
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(['Data', 'Typ', 'Notatka'])
    for e in entries:
        d_str = e['date'].strftime('%Y-%m-%d') if hasattr(e['date'], 'strftime') else str(e['date'])
        w.writerow([d_str, TYPE_LABELS.get(e['type'], e['type']), e['notes'] or ''])
    output.seek(0)
    return Response(
        '﻿' + output.getvalue(),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename=urlopy_{year}.csv'},
    )


@app.get('/sw.js')
async def service_worker():
    return FileResponse(
        'static/sw.js',
        media_type='application/javascript',
        headers={'Service-Worker-Allowed': '/'},
    )


@app.get('/health')
async def health():
    return JSONResponse({'status': 'ok'})


# ── Startup ─────────────────────────────────────────────────────

try:
    init_db()
except Exception as e:
    print(f'[warn] DB init: {e}')
