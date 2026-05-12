import pytest
from datetime import date
from markupsafe import Markup

import main


class TestFmtDays:
    def test_whole_days(self):
        assert main.fmt_days(5) == '5 dni'

    def test_zero(self):
        assert main.fmt_days(0) == '0 dni'

    def test_one_day(self):
        assert main.fmt_days(1) == '1 dni'

    def test_half_day_shows_hours(self):
        assert main.fmt_days(0.5) == '4h'

    def test_days_and_hours_combined(self):
        assert main.fmt_days(1.5) == '1 dni 4h'

    def test_quarter_day(self):
        assert main.fmt_days(0.25) == '2h'

    def test_fractional_rounding(self):
        result = main.fmt_days(2.5)
        assert '2 dni' in result
        assert 'h' in result


class TestFmtDatePl:
    def test_formats_date_components(self):
        d = date(2025, 6, 15)
        result = main.fmt_date_pl(d)
        assert '15' in result
        assert 'cze' in result
        assert '2025' in result

    def test_includes_weekday(self):
        d = date(2025, 6, 16)  # Monday
        result = main.fmt_date_pl(d)
        assert 'Pon' in result

    def test_none_returns_empty_string(self):
        assert main.fmt_date_pl(None) == ''


class TestEasterDate:
    @pytest.mark.parametrize('year,expected', [
        (2024, date(2024, 3, 31)),
        (2025, date(2025, 4, 20)),
        (2026, date(2026, 4,  5)),
        (2027, date(2027, 3, 28)),
    ])
    def test_known_years(self, year, expected):
        assert main.easter_date(year) == expected

    def test_returns_date_object(self):
        assert isinstance(main.easter_date(2025), date)

    def test_always_sunday(self):
        for y in range(2020, 2030):
            assert main.easter_date(y).weekday() == 6  # Sunday


class TestGetPolishHolidays:
    def test_returns_dict(self):
        assert isinstance(main.get_polish_holidays(2025), dict)

    def test_has_thirteen_holidays(self):
        assert len(main.get_polish_holidays(2025)) == 13

    def test_new_year(self):
        assert '2025-01-01' in main.get_polish_holidays(2025)

    def test_epiphany(self):
        assert '2025-01-06' in main.get_polish_holidays(2025)

    def test_christmas(self):
        hols = main.get_polish_holidays(2025)
        assert '2025-12-25' in hols
        assert '2025-12-26' in hols

    def test_easter_included(self):
        hols = main.get_polish_holidays(2025)
        easter = main.easter_date(2025)
        assert easter.isoformat() in hols

    def test_easter_monday_included(self):
        from datetime import timedelta
        hols = main.get_polish_holidays(2025)
        easter_monday = (main.easter_date(2025) + timedelta(1)).isoformat()
        assert easter_monday in hols


class TestParseYear:
    def test_valid_string(self):
        assert main._parse_year('2025') == 2025

    def test_valid_int(self):
        assert main._parse_year(2025) == 2025

    def test_clamps_to_min(self):
        assert main._parse_year('1900') == 2020

    def test_clamps_to_max(self):
        y = main._parse_year('9999')
        assert y <= date.today().year + 2

    def test_none_returns_current_year(self):
        assert main._parse_year(None) == date.today().year

    def test_invalid_string_returns_current_year(self):
        assert main._parse_year('abc') == date.today().year

    def test_custom_default(self):
        assert main._parse_year(None, default=2024) == 2024

    def test_custom_default_not_used_for_valid_input(self):
        assert main._parse_year('2025', default=2024) == 2025


class TestSafeNext:
    def test_empty_returns_root(self):
        assert main._safe_next('') == '/'

    def test_valid_path(self):
        assert main._safe_next('/history') == '/history'

    def test_root_path(self):
        assert main._safe_next('/') == '/'

    def test_nested_path(self):
        assert main._safe_next('/calendar?month=6') == '/calendar?month=6'

    def test_protocol_relative_rejected(self):
        assert main._safe_next('//evil.com') == '/'

    def test_backslash_trick_rejected(self):
        assert main._safe_next('/\\evil.com') == '/'

    def test_no_leading_slash_rejected(self):
        assert main._safe_next('evil') == '/'

    def test_http_url_rejected(self):
        assert main._safe_next('http://evil.com') == '/'

    def test_https_url_rejected(self):
        assert main._safe_next('https://evil.com') == '/'


class TestGetWarnings:
    def _balance(self, vac_rem=10, ho_rem=10, okol_rem=2):
        return {
            'vacation':        {'remaining': vac_rem},
            'home_office':     {'remaining': ho_rem},
            'okolicznosciowy': {'remaining': okol_rem},
        }

    def test_no_warnings_when_plenty_left(self):
        # year=2020 avoids end-of-year "info" trigger
        warns = main.get_warnings(2020, self._balance())
        assert warns == []

    def test_vacation_exhausted_is_error(self):
        warns = main.get_warnings(2020, self._balance(vac_rem=0))
        assert any(w[0] == 'error' for w in warns)

    def test_vacation_low_is_warning(self):
        warns = main.get_warnings(2020, self._balance(vac_rem=2))
        assert any(w[0] == 'warning' for w in warns)

    def test_vacation_exactly_3_is_warning(self):
        warns = main.get_warnings(2020, self._balance(vac_rem=3))
        assert any(w[0] == 'warning' for w in warns)

    def test_vacation_4_is_no_warning(self):
        warns = main.get_warnings(2020, self._balance(vac_rem=4))
        vac_warns = [w for w in warns if 'urlop' in w[1].lower() and w[0] in ('error', 'warning')]
        assert vac_warns == []

    def test_ho_exhausted_is_warning(self):
        warns = main.get_warnings(2020, self._balance(ho_rem=0))
        assert any('HO' in w[1] for w in warns)

    def test_ho_low_is_warning(self):
        warns = main.get_warnings(2020, self._balance(ho_rem=1))
        assert any('HO' in w[1] for w in warns)

    def test_okol_exhausted_is_warning(self):
        warns = main.get_warnings(2020, self._balance(okol_rem=0))
        assert any('okolicznoś' in w[1].lower() or 'okoliczno' in w[2].lower() for w in warns)

    def test_warning_is_3_tuple(self):
        warns = main.get_warnings(2020, self._balance(vac_rem=0))
        for w in warns:
            assert len(w) == 3


class TestTojsonFilter:
    def test_returns_markup_instance(self):
        result = main._tojson_filter({'key': 'value'})
        assert isinstance(result, Markup)

    def test_serializes_dict(self):
        result = main._tojson_filter({'x': 1})
        assert '"x"' in result
        assert '1' in result

    def test_serializes_list(self):
        result = main._tojson_filter([1, 2, 3])
        assert result == Markup('[1, 2, 3]')

    def test_serializes_date(self):
        d = date(2025, 6, 15)
        result = main._tojson_filter({'d': d})
        assert '2025-06-15' in result

    def test_serializes_nested_dates(self):
        d = date(2025, 1, 1)
        result = main._tojson_filter([{'date': d}])
        assert '2025-01-01' in result

    def test_serializes_decimal(self):
        from decimal import Decimal
        result = main._tojson_filter({'hours': Decimal('2.5')})
        assert '2.5' in result

    def test_non_serializable_raises(self):
        with pytest.raises(TypeError):
            main._tojson_filter({'bad': object()})


class TestGetCalendarDays:
    def test_returns_list_of_dates(self):
        days = main.get_calendar_days(2025, 6)
        assert all(isinstance(d, date) for d in days)

    def test_starts_on_monday(self):
        days = main.get_calendar_days(2025, 1)
        assert days[0].weekday() == 0

    def test_ends_on_sunday(self):
        days = main.get_calendar_days(2025, 1)
        assert days[-1].weekday() == 6

    def test_includes_all_days_of_month(self):
        days = main.get_calendar_days(2025, 6)
        june_days = [d for d in days if d.month == 6]
        assert len(june_days) == 30

    def test_february_leap_year(self):
        days = main.get_calendar_days(2024, 2)
        feb_days = [d for d in days if d.month == 2]
        assert len(feb_days) == 29

    def test_length_multiple_of_seven(self):
        days = main.get_calendar_days(2025, 3)
        assert len(days) % 7 == 0
