import os
import time
import threading
import calendar as cal_module
import csv
import io
import json
import hmac
import secrets
from datetime import date, timedelta
from decimal import Decimal

import bcrypt
import pymysql
import pymysql.cursors
from flask import (
    Flask, Response, jsonify, redirect, render_template, request,
    send_from_directory, session,
)
from markupsafe import Markup
from dotenv import load_dotenv

# .env leży w katalogu nadrzędnym (root projektu), app.py w podfolderze VanillaDays/
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))


def _env_bool(name: str, default: str = 'false') -> bool:
    return os.getenv(name, default).strip().lower() in ('1', 'true', 'yes', 'on')


# ── App setup ───────────────────────────────────────────────────

app = Flask(__name__, static_folder='static', static_url_path='/static',
            template_folder='templates')

_secret = os.getenv('SECRET_KEY')
if not _secret:
    raise RuntimeError('SECRET_KEY is not set in environment')

app.secret_key = _secret
app.config['SESSION_COOKIE_NAME']     = 'session'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE']   = _env_bool('HTTPS_ONLY')
app.permanent_session_lifetime        = timedelta(hours=12)

# Auth — runs before every request
UNPROTECTED_PATHS = {'/login', '/health', '/sw.js'}


def _csrf_token() -> str:
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


@app.context_processor
def _inject_csrf():
    return {'csrf_token': _csrf_token()}


@app.before_request
def require_auth():
    path = request.path
    if path.startswith('/static') or path in UNPROTECTED_PATHS:
        return None
    if not session.get('logged_in'):
        return redirect(f'/login?next={request.path}', code=303)
    if request.method == 'POST':
        sent     = request.form.get('csrf_token') or request.headers.get('X-CSRFToken', '')
        expected = session.get('_csrf_token', '')
        if not expected or not hmac.compare_digest(sent, expected):
            return Response('Nieprawidłowy token CSRF — odśwież stronę.', status=403)
    return None


# Security headers — applied to every response (including redirects)
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


@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = _CSP
    return response


# ── Rate limiter ────────────────────────────────────────────────

_rl_lock = threading.Lock()
_rl: dict[str, dict] = {}
_MAX_ATTEMPTS = 5
_LOCKOUT_SECS = 15 * 60

_TRUSTED_PROXY = _env_bool('TRUSTED_PROXY')


def _get_ip() -> str:
    if _TRUSTED_PROXY:
        forwarded = request.headers.get('X-Forwarded-For', '')
        if forwarded:
            return forwarded.split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'


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


app.jinja_env.globals['fmt_days']    = fmt_days
app.jinja_env.globals['fmt_date_pl'] = fmt_date_pl
app.jinja_env.filters['tojson']      = _tojson_filter


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


def _csv_safe(val) -> str:
    """Neutralize CSV/spreadsheet formula injection in user-supplied cells."""
    s = '' if val is None else str(val)
    if s[:1] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + s
    return s


def _safe_next(url: str) -> str:
    """Accept only same-origin relative paths; reject anything else."""
    if not url:
        return '/'
    # Reject protocol-relative (//evil.com) and backslash tricks (/\evil.com)
    if not url.startswith('/') or url.startswith('//') or url.startswith('/\\'):
        return '/'
    return url


# ── Routes: auth ────────────────────────────────────────────────

@app.route('/login', methods=['GET'])
def login_get():
    if session.get('logged_in'):
        return redirect('/', code=303)
    return render_template('login.html', error=None,
                           next=_safe_next(request.args.get('next', '')))


@app.route('/login', methods=['POST'])
def login_post():
    if session.get('logged_in'):
        return redirect('/', code=303)

    form  = request.form
    ip    = _get_ip()
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
        try:
            pw_ok = stored and expected_user and username == expected_user and bcrypt.checkpw(password, stored)
        except ValueError:
            pw_ok = False
        if pw_ok:
            _clear_failures(ip)
            session.permanent = True
            session['logged_in'] = True
            return redirect(_safe_next(form.get('next', '')), code=303)
        else:
            _record_failure(ip)
            _, wait = _check_rate_limit(ip)
            if wait:
                error = f'Za dużo nieudanych prób. Spróbuj za {wait // 60} min.'
            else:
                error = 'Nieprawidłowe hasło.'

    return render_template('login.html', error=error, next=form.get('next', ''))


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect('/login', code=303)


# ── Routes: pages ───────────────────────────────────────────────

@app.route('/')
def dashboard():
    year    = _parse_year(request.args.get('year'))
    balance = get_balance(year)
    recent  = q_all(
        "SELECT * FROM leave_entries WHERE YEAR(date)=%s ORDER BY date DESC LIMIT 10", (year,)
    )
    return render_template('dashboard.html',
        balance=balance,
        stats=get_stats(year),
        warnings=get_warnings(year, balance),
        recent=recent,
        active='dashboard',
        **year_context(year),
    )


@app.route('/calendar')
def calendar_page():
    year  = _parse_year(request.args.get('year'))
    month = request.args.get('month', type=int)
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

    return render_template('calendar.html',
        month=month,
        month_name=MONTH_NAMES[month - 1],
        days=days,
        entries_by_date=entries_by_date,
        overtime_by_date=overtime_by_date,
        holidays=get_polish_holidays(year),
        prev_month=prev_m,
        prev_year=prev_y,
        next_month=next_m,
        next_year=next_y,
        active='calendar',
        **year_context(year),
    )


@app.route('/history')
def history():
    year    = _parse_year(request.args.get('year'))
    type_f  = request.args.get('type', '')
    month_f = request.args.get('month', '')

    month_num = int(month_f) if month_f.isdigit() and 1 <= int(month_f) <= 12 else None
    month_f   = str(month_num) if month_num else ''

    sql    = 'SELECT * FROM leave_entries WHERE YEAR(date)=%s'
    params = [year]
    if type_f:
        sql += ' AND type=%s'; params.append(type_f)
    if month_num:
        sql += ' AND MONTH(date)=%s'; params.append(month_num)
    sql += ' ORDER BY date DESC'
    entries = q_all(sql, tuple(params))

    ot_sql    = 'SELECT * FROM overtime_log WHERE YEAR(date)=%s'
    ot_params = [year]
    if month_num:
        ot_sql += ' AND MONTH(date)=%s'; ot_params.append(month_num)
    ot_sql += ' ORDER BY date DESC'
    ot_entries  = q_all(ot_sql, tuple(ot_params))
    ot_earned   = sum(float(e['hours']) for e in ot_entries if e.get('type') != 'taken')
    ot_taken    = sum(float(e['hours']) for e in ot_entries if e.get('type') == 'taken')
    ot_balance  = ot_earned - ot_taken

    return render_template('history.html',
        entries=entries,
        type_filter=type_f,
        month_filter=month_f,
        month_names=MONTH_NAMES,
        ot_entries=ot_entries,
        ot_earned=ot_earned,
        ot_taken=ot_taken,
        ot_balance=ot_balance,
        active='history',
        **year_context(year),
    )


@app.route('/settings')
def settings():
    year   = _parse_year(request.args.get('year'))
    config = get_or_create_config(year)
    return render_template('settings.html',
        config=config,
        active='settings',
        **year_context(year),
    )


# ── Routes: CRUD ────────────────────────────────────────────────

@app.route('/entries/save', methods=['POST'])
def save_entry():
    form          = request.form
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
        return Response('Brak daty lub typu', status=400)

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
        return Response('Wpis dla tej daty już istnieje', status=409)

    return Response(status=200)


@app.route('/entries/<int:entry_id>/delete', methods=['POST'])
def delete_entry(entry_id):
    q_exec('DELETE FROM leave_entries WHERE id=%s', (entry_id,))
    return Response(status=204, headers={'HX-Refresh': 'true'})


@app.route('/config/<int:year>/save', methods=['POST'])
def save_config(year):
    form = request.form
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
    return Response('<div class="alert alert--success">Zapisano!</div>', status=200)


@app.route('/overtime/save', methods=['POST'])
def save_overtime():
    form      = request.form
    d         = form.get('date', '')
    hours_str = form.get('hours', '').strip()
    ot_type   = form.get('type', 'earned')
    notes     = form.get('notes', '').strip() or None
    if not d or not hours_str:
        return Response('Brak danych', status=400)
    if ot_type not in ('earned', 'taken'):
        return Response('Nieprawidłowy typ', status=400)
    try:
        hours = float(hours_str)
    except ValueError:
        return Response('Nieprawidłowa liczba godzin', status=400)
    if hours <= 0:
        return Response('Liczba godzin musi być większa od 0', status=400)
    q_exec(
        "INSERT INTO overtime_log (date, hours, type, notes) VALUES (%s, %s, %s, %s)",
        (d, hours, ot_type, notes),
    )
    return Response(status=200)


@app.route('/overtime/<int:entry_id>/delete', methods=['POST'])
def delete_overtime(entry_id):
    q_exec('DELETE FROM overtime_log WHERE id=%s', (entry_id,))
    return Response(status=204, headers={'HX-Refresh': 'true'})


@app.route('/export/csv')
def export_csv():
    year   = _parse_year(request.args.get('year'))
    type_f = request.args.get('type', '')

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
        w.writerow([
            _csv_safe(d_str),
            _csv_safe(TYPE_LABELS.get(e['type'], e['type'])),
            _csv_safe(e['notes'] or ''),
        ])
    output.seek(0)
    return Response(
        '﻿' + output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename=urlopy_{year}.csv'},
    )


@app.route('/sw.js')
def service_worker():
    resp = send_from_directory(app.static_folder, 'sw.js', mimetype='application/javascript')
    resp.headers['Service-Worker-Allowed'] = '/'
    return resp


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


# ── Startup ─────────────────────────────────────────────────────

try:
    init_db()
except Exception as e:
    print(f'[warn] DB init: {e}')


if __name__ == '__main__':
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', '8000')),
        debug=_env_bool('FLASK_DEBUG'),
    )
