import sys
import os
from pathlib import Path

_app_dir = Path(__file__).parent.parent / 'app'
# Add app/ to sys.path and set cwd so relative paths (static/, templates/) resolve correctly
sys.path.insert(0, str(_app_dir))
os.chdir(_app_dir)

# Set env vars before importing main (init_db and SECRET_KEY check run at import)
import bcrypt
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest-minimum-32-bytes!!')
os.environ.setdefault('LOGIN_USERNAME', 'admin')
os.environ.setdefault('LOGIN_PASSWORD_HASH',
    bcrypt.hashpw(b'secret', bcrypt.gensalt(4)).decode())
os.environ.setdefault('DB_HOST', '')       # empty → init_db fails gracefully
os.environ.setdefault('DB_PASSWORD', '')
os.environ['COOKIE_SECURE'] = '0'         # secure cookies break http://testserver

import pytest
from unittest.mock import patch
from starlette.testclient import TestClient

import main

# ── Shared mock data ─────────────────────────────────────────────

MOCK_CONFIG = {
    'id': 1, 'year': 2026,
    'vacation_limit': 26.0, 'ho_limit': 24,
    'vacation_carried_over': 0.0, 'overtime_balance': 0.0,
}


def make_q_one(vac=5, ho=3, okol=0, bezp=0, l4=0, za=0, ot=8.0, config=None):
    """Returns a q_one side_effect that answers all get_balance sub-queries."""
    cfg = config or dict(MOCK_CONFIG)

    def _impl(sql, params=()):
        if 'year_config' in sql:            return cfg
        if 'days_used' in sql:              return {'days_used': vac}
        if "type='home_office'" in sql:     return {'cnt': ho}
        if "type='okolicznosciowy'" in sql: return {'cnt': okol}
        if "type='bezplatny'" in sql:       return {'cnt': bezp}
        if "type='l4'" in sql:              return {'cnt': l4}
        if "type='za_swieto'" in sql:       return {'cnt': za}
        if 'overtime_log' in sql:           return {'total': ot}
        return None

    return _impl


# ── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def client():
    with TestClient(main.app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Clear in-memory rate-limit state between tests."""
    main._rl.clear()
    yield
    main._rl.clear()


@pytest.fixture
def auth_client(client):
    """TestClient with an active session. Login is env-var only — no DB needed."""
    r = client.post(
        '/login',
        data={'username': 'admin', 'password': 'secret', 'next': ''},
        follow_redirects=False,
    )
    assert r.status_code == 303, f'Login failed: {r.text}'
    return client


@pytest.fixture
def mock_db():
    """Patch all DB helpers with sensible defaults (no real DB required)."""
    with (
        patch('main.q_one', side_effect=make_q_one()),
        patch('main.q_all', return_value=[]),
        patch('main.q_exec', return_value=1),
    ):
        yield


@pytest.fixture
def auth_db_client(auth_client, mock_db):
    """Authenticated client with DB mocked — the common case for page tests."""
    return auth_client
