import pytest


class TestSecurityHeaders:
    """Every response must carry the required security headers."""

    def test_login_page_has_nosniff(self, client):
        r = client.get('/login')
        assert r.headers.get('X-Content-Type-Options') == 'nosniff'

    def test_login_page_has_x_frame_options(self, client):
        r = client.get('/login')
        assert r.headers.get('X-Frame-Options') == 'DENY'

    def test_login_page_has_referrer_policy(self, client):
        r = client.get('/login')
        assert r.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'

    def test_login_page_has_csp(self, client):
        r = client.get('/login')
        assert 'Content-Security-Policy' in r.headers

    def test_unauthenticated_redirect_has_x_frame_options(self, client):
        r = client.get('/', follow_redirects=False)
        assert r.headers.get('X-Frame-Options') == 'DENY'

    def test_health_has_nosniff(self, client):
        r = client.get('/health')
        assert r.headers.get('X-Content-Type-Options') == 'nosniff'

    def test_post_login_redirect_has_headers(self, client):
        r = client.post(
            '/login',
            data={'username': 'admin', 'password': 'secret', 'next': ''},
            follow_redirects=False,
        )
        assert r.headers.get('X-Frame-Options') == 'DENY'


class TestCSP:
    def _csp(self, client):
        return client.get('/login').headers.get('Content-Security-Policy', '')

    def test_default_src_self(self, client):
        assert "default-src 'self'" in self._csp(client)

    def test_allows_cdn_for_scripts(self, client):
        csp = self._csp(client)
        assert 'unpkg.com' in csp or 'cdn.jsdelivr.net' in csp

    def test_denies_frame_ancestors(self, client):
        assert "frame-ancestors 'none'" in self._csp(client)

    def test_restricts_form_action_to_self(self, client):
        assert "form-action 'self'" in self._csp(client)

    def test_restricts_base_uri(self, client):
        assert "base-uri 'self'" in self._csp(client)

    def test_allows_google_fonts(self, client):
        csp = self._csp(client)
        assert 'fonts.googleapis.com' in csp or 'fonts.gstatic.com' in csp


class TestAuthRequired:
    @pytest.mark.parametrize('path', ['/', '/calendar', '/history', '/settings'])
    def test_unauthenticated_gets_303(self, client, path):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 303

    @pytest.mark.parametrize('path', ['/', '/calendar', '/history', '/settings'])
    def test_unauthenticated_redirects_to_login(self, client, path):
        r = client.get(path, follow_redirects=False)
        assert r.headers['location'].startswith('/login')

    def test_next_param_in_redirect_location(self, client):
        r = client.get('/history', follow_redirects=False)
        assert 'next=/history' in r.headers['location']

    def test_static_files_bypass_auth(self, client):
        # 404 or 200 are fine; 303 (auth redirect) is wrong
        r = client.get('/static/nonexistent.css', follow_redirects=False)
        assert r.status_code != 303

    def test_health_bypasses_auth(self, client):
        r = client.get('/health')
        assert r.status_code == 200

    def test_login_page_bypasses_auth(self, client):
        r = client.get('/login')
        assert r.status_code == 200

    @pytest.mark.parametrize('path', ['/', '/calendar', '/history', '/settings'])
    def test_authenticated_gets_200(self, auth_db_client, path):
        r = auth_db_client.get(path)
        assert r.status_code == 200
