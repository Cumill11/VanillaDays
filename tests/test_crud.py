import pytest
from unittest.mock import patch
import pymysql.err


class TestSaveEntry:
    def test_new_entry_succeeds(self, auth_db_client):
        r = auth_db_client.post(
            '/entries/save',
            data={'date': '2025-06-15', 'type': 'vacation', 'notes': ''},
        )
        assert r.status_code == 200

    def test_edit_entry_succeeds(self, auth_db_client):
        r = auth_db_client.post(
            '/entries/save',
            data={'id': '1', 'date': '2025-06-15', 'type': 'vacation', 'notes': ''},
        )
        assert r.status_code == 200

    def test_missing_date_returns_400(self, auth_db_client):
        r = auth_db_client.post(
            '/entries/save',
            data={'date': '', 'type': 'vacation'},
        )
        assert r.status_code == 400

    def test_missing_type_returns_400(self, auth_db_client):
        r = auth_db_client.post(
            '/entries/save',
            data={'date': '2025-06-15', 'type': ''},
        )
        assert r.status_code == 400

    def test_duplicate_returns_409(self, auth_client):
        with patch('main.q_exec', side_effect=pymysql.err.IntegrityError):
            r = auth_client.post(
                '/entries/save',
                data={'date': '2025-06-15', 'type': 'vacation'},
            )
        assert r.status_code == 409

    def test_okolicznosciowy_accepts_reason(self, auth_db_client):
        r = auth_db_client.post(
            '/entries/save',
            data={
                'date': '2025-06-15',
                'type': 'okolicznosciowy',
                'okol_reason': 'ślub',
                'notes': '',
            },
        )
        assert r.status_code == 200

    def test_l4_accepts_zus_number(self, auth_db_client):
        r = auth_db_client.post(
            '/entries/save',
            data={'date': '2025-06-15', 'type': 'l4', 'l4_number': 'ZUS123', 'notes': ''},
        )
        assert r.status_code == 200

    def test_za_swieto_accepts_day(self, auth_db_client):
        r = auth_db_client.post(
            '/entries/save',
            data={
                'date': '2025-06-15',
                'type': 'za_swieto',
                'za_swieto_day': '2025-01-01',
                'notes': '',
            },
        )
        assert r.status_code == 200

    def test_requires_auth(self, client):
        r = client.post(
            '/entries/save',
            data={'date': '2025-06-15', 'type': 'vacation'},
            follow_redirects=False,
        )
        assert r.status_code == 303


class TestDeleteEntry:
    def test_delete_returns_204(self, auth_db_client):
        r = auth_db_client.post('/entries/42/delete')
        assert r.status_code == 204

    def test_delete_sets_hx_refresh(self, auth_db_client):
        r = auth_db_client.post('/entries/42/delete')
        assert r.headers.get('HX-Refresh') == 'true'

    def test_requires_auth(self, client):
        r = client.post('/entries/42/delete', follow_redirects=False)
        assert r.status_code == 303


class TestSaveConfig:
    def test_saves_and_returns_html(self, auth_db_client):
        r = auth_db_client.post(
            '/config/2025/save',
            data={
                'vacation_limit': '26',
                'ho_limit': '24',
                'vacation_carried_over': '0',
            },
        )
        assert r.status_code == 200
        assert 'Zapisano' in r.text

    def test_requires_auth(self, client):
        r = client.post('/config/2025/save', data={}, follow_redirects=False)
        assert r.status_code == 303


class TestSaveOvertime:
    def test_save_succeeds(self, auth_db_client):
        r = auth_db_client.post(
            '/overtime/save',
            data={'date': '2025-06-15', 'hours': '2.5', 'notes': ''},
        )
        assert r.status_code == 200

    def test_negative_hours_succeeds(self, auth_db_client):
        r = auth_db_client.post(
            '/overtime/save',
            data={'date': '2025-06-15', 'hours': '-1'},
        )
        assert r.status_code == 200

    def test_missing_date_returns_400(self, auth_db_client):
        r = auth_db_client.post(
            '/overtime/save',
            data={'date': '', 'hours': '2'},
        )
        assert r.status_code == 400

    def test_missing_hours_returns_400(self, auth_db_client):
        r = auth_db_client.post(
            '/overtime/save',
            data={'date': '2025-06-15', 'hours': ''},
        )
        assert r.status_code == 400

    def test_invalid_hours_returns_400(self, auth_db_client):
        r = auth_db_client.post(
            '/overtime/save',
            data={'date': '2025-06-15', 'hours': 'abc'},
        )
        assert r.status_code == 400

    def test_zero_hours_returns_400(self, auth_db_client):
        r = auth_db_client.post(
            '/overtime/save',
            data={'date': '2025-06-15', 'hours': '0'},
        )
        assert r.status_code == 400

    def test_requires_auth(self, client):
        r = client.post(
            '/overtime/save',
            data={'date': '2025-06-15', 'hours': '2'},
            follow_redirects=False,
        )
        assert r.status_code == 303


class TestDeleteOvertime:
    def test_delete_returns_204(self, auth_db_client):
        r = auth_db_client.post('/overtime/7/delete')
        assert r.status_code == 204

    def test_delete_sets_hx_refresh(self, auth_db_client):
        r = auth_db_client.post('/overtime/7/delete')
        assert r.headers.get('HX-Refresh') == 'true'

    def test_requires_auth(self, client):
        r = client.post('/overtime/7/delete', follow_redirects=False)
        assert r.status_code == 303


class TestExportCsv:
    def test_returns_csv_content_type(self, auth_db_client):
        r = auth_db_client.get('/export/csv')
        assert r.status_code == 200
        assert 'text/csv' in r.headers['content-type']

    def test_csv_has_header_row(self, auth_db_client):
        r = auth_db_client.get('/export/csv')
        assert 'Data' in r.text
        assert 'Typ' in r.text

    def test_filename_contains_year(self, auth_db_client):
        r = auth_db_client.get('/export/csv?year=2025')
        cd = r.headers.get('content-disposition', '')
        assert '2025' in cd

    def test_type_filter_accepted(self, auth_db_client):
        r = auth_db_client.get('/export/csv?type=vacation')
        assert r.status_code == 200

    def test_requires_auth(self, client):
        r = client.get('/export/csv', follow_redirects=False)
        assert r.status_code == 303
