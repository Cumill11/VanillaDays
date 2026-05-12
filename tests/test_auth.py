import main
import pytest


class TestLoginGet:
    def test_shows_form(self, client):
        r = client.get('/login', follow_redirects=False)
        assert r.status_code == 200
        assert '<form' in r.text
        assert 'Zaloguj się' in r.text

    def test_redirects_when_already_authenticated(self, auth_client):
        r = auth_client.get('/login', follow_redirects=False)
        assert r.status_code == 303
        assert r.headers['location'] == '/'

    def test_next_param_echoed_in_form(self, client):
        r = client.get('/login?next=/history', follow_redirects=False)
        assert r.status_code == 200
        assert 'name="next"' in r.text
        assert '/history' in r.text

    def test_unsafe_next_sanitized_in_form(self, client):
        r = client.get('/login?next=//evil.com', follow_redirects=False)
        assert r.status_code == 200
        assert '//evil.com' not in r.text


class TestLoginPost:
    def test_correct_credentials_redirects_to_root(self, client):
        r = client.post(
            '/login',
            data={'username': 'admin', 'password': 'secret', 'next': ''},
            follow_redirects=False,
        )
        assert r.status_code == 303
        assert r.headers['location'] == '/'

    def test_correct_credentials_with_valid_next(self, client):
        r = client.post(
            '/login',
            data={'username': 'admin', 'password': 'secret', 'next': '/history'},
            follow_redirects=False,
        )
        assert r.status_code == 303
        assert r.headers['location'] == '/history'

    def test_wrong_password_shows_error(self, client):
        r = client.post(
            '/login',
            data={'username': 'admin', 'password': 'WRONG', 'next': ''},
        )
        assert r.status_code == 200
        assert 'Nieprawidłowe hasło' in r.text

    def test_wrong_username_shows_error(self, client):
        r = client.post(
            '/login',
            data={'username': 'notadmin', 'password': 'secret', 'next': ''},
        )
        assert r.status_code == 200
        assert 'Nieprawidłowe hasło' in r.text

    def test_empty_credentials_shows_error(self, client):
        r = client.post('/login', data={'username': '', 'password': '', 'next': ''})
        assert r.status_code == 200
        assert 'Nieprawidłowe hasło' in r.text

    def test_already_authenticated_redirects(self, auth_client):
        r = auth_client.post(
            '/login',
            data={'username': 'admin', 'password': 'secret', 'next': ''},
            follow_redirects=False,
        )
        assert r.status_code == 303
        assert r.headers['location'] == '/'

    def test_unsafe_next_falls_back_to_root(self, client):
        for bad_next in ['//evil.com', '/\\evil.com', 'http://evil.com', 'evil']:
            r = client.post(
                '/login',
                data={'username': 'admin', 'password': 'secret', 'next': bad_next},
                follow_redirects=False,
            )
            assert r.status_code == 303
            assert r.headers['location'] == '/', f'Expected / for next={bad_next!r}'


class TestRateLimit:
    def _fail(self, client, n=1):
        for _ in range(n):
            client.post('/login', data={'username': 'admin', 'password': 'WRONG', 'next': ''})

    def test_first_four_failures_show_wrong_password(self, client):
        for _ in range(4):
            r = client.post('/login', data={'username': 'admin', 'password': 'WRONG', 'next': ''})
            assert 'Nieprawidłowe hasło' in r.text

    def test_fifth_failure_triggers_lockout_message(self, client):
        self._fail(client, 4)
        r = client.post('/login', data={'username': 'admin', 'password': 'WRONG', 'next': ''})
        assert 'min.' in r.text
        assert 'Nieprawidłowe hasło' not in r.text

    def test_correct_password_blocked_after_lockout(self, client):
        self._fail(client, 5)
        r = client.post(
            '/login',
            data={'username': 'admin', 'password': 'secret', 'next': ''},
            follow_redirects=False,
        )
        assert r.status_code == 200
        assert 'min.' in r.text

    def test_successful_login_clears_failures(self, client):
        self._fail(client, 2)
        assert main._rl  # failures recorded

        client.post(
            '/login',
            data={'username': 'admin', 'password': 'secret', 'next': ''},
            follow_redirects=False,
        )
        assert not main._rl  # cleared after success


class TestLogout:
    def test_logout_redirects_to_login(self, auth_client):
        r = auth_client.post('/logout', follow_redirects=False)
        assert r.status_code == 303
        assert r.headers['location'] == '/login'

    def test_logout_clears_session(self, auth_client):
        auth_client.post('/logout', follow_redirects=False)
        # After logout, protected routes redirect to login
        r = auth_client.get('/', follow_redirects=False)
        assert r.status_code == 303
        assert '/login' in r.headers['location']
