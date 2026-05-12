import pytest


class TestUnauthenticated:
    @pytest.mark.parametrize('path', ['/', '/calendar', '/history', '/settings'])
    def test_redirects_to_login(self, client, path):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 303
        assert '/login' in r.headers['location']

    def test_redirect_includes_next_param(self, client):
        r = client.get('/history', follow_redirects=False)
        assert 'next=/history' in r.headers['location']


class TestHealth:
    def test_returns_ok(self, client):
        r = client.get('/health')
        assert r.status_code == 200
        assert r.json() == {'status': 'ok'}

    def test_no_auth_required(self, client):
        r = client.get('/health')
        assert r.status_code == 200


class TestDashboard:
    def test_renders(self, auth_db_client):
        r = auth_db_client.get('/')
        assert r.status_code == 200

    def test_contains_leave_content(self, auth_db_client):
        r = auth_db_client.get('/')
        assert 'urlop' in r.text.lower() or 'home office' in r.text.lower()

    def test_year_param_accepted(self, auth_db_client):
        r = auth_db_client.get('/?year=2025')
        assert r.status_code == 200

    def test_invalid_year_falls_back(self, auth_db_client):
        r = auth_db_client.get('/?year=abc')
        assert r.status_code == 200

    def test_year_clamped_to_max(self, auth_db_client):
        r = auth_db_client.get('/?year=9999')
        assert r.status_code == 200


class TestCalendar:
    def test_renders(self, auth_db_client):
        r = auth_db_client.get('/calendar')
        assert r.status_code == 200

    def test_month_param_accepted(self, auth_db_client):
        r = auth_db_client.get('/calendar?month=6')
        assert r.status_code == 200

    def test_year_and_month_accepted(self, auth_db_client):
        r = auth_db_client.get('/calendar?year=2025&month=3')
        assert r.status_code == 200


class TestHistory:
    def test_renders(self, auth_db_client):
        r = auth_db_client.get('/history')
        assert r.status_code == 200

    def test_type_filter(self, auth_db_client):
        r = auth_db_client.get('/history?type=vacation')
        assert r.status_code == 200

    def test_month_filter(self, auth_db_client):
        r = auth_db_client.get('/history?month=3')
        assert r.status_code == 200

    def test_combined_filters(self, auth_db_client):
        r = auth_db_client.get('/history?year=2025&type=home_office&month=6')
        assert r.status_code == 200


class TestSettings:
    def test_renders(self, auth_db_client):
        r = auth_db_client.get('/settings')
        assert r.status_code == 200

    def test_year_param_accepted(self, auth_db_client):
        r = auth_db_client.get('/settings?year=2025')
        assert r.status_code == 200
