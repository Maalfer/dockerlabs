"""Tests puros de los helpers privados de dockerlabs/routes/pages_admin.py.

El módulo importa `dockerlabs.models` (y por tanto `dockerlabs.database`), que
exige `DATABASE_URL` ya fijada en el entorno — lo hace la fixture de sesión
`_test_database` de conftest.py. Por eso el import vive en una fixture (se
resuelve en el setup del test, no en la recolección del módulo), igual que
hace `tests/factories.py`.
"""
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def pa():
    from dockerlabs.routes import pages_admin
    return pages_admin


def _today_midnight():
    now = datetime.utcnow()
    return datetime(now.year, now.month, now.day)


class TestParseDateFlexible:
    def test_accepts_iso_format(self, pa):
        assert pa._parse_date_flexible("2026-01-15") == datetime(2026, 1, 15)

    def test_accepts_spanish_format(self, pa):
        assert pa._parse_date_flexible("15/01/2026") == datetime(2026, 1, 15)

    def test_garbage_raises_value_error(self, pa):
        with pytest.raises(ValueError):
            pa._parse_date_flexible("no-es-una-fecha")


class TestBucketGranularity:
    def test_exactly_35_days_is_day(self, pa):
        start = datetime(2026, 1, 1)
        assert pa._bucket_granularity(start, start + timedelta(days=35)) == "day"

    def test_36_days_is_week(self, pa):
        start = datetime(2026, 1, 1)
        assert pa._bucket_granularity(start, start + timedelta(days=36)) == "week"

    def test_exactly_183_days_is_week(self, pa):
        start = datetime(2026, 1, 1)
        assert pa._bucket_granularity(start, start + timedelta(days=183)) == "week"

    def test_184_days_is_month(self, pa):
        start = datetime(2026, 1, 1)
        assert pa._bucket_granularity(start, start + timedelta(days=184)) == "month"


class TestBucketize:
    def test_day_granularity_fills_gaps_with_zero(self, pa):
        items = [
            SimpleNamespace(d=datetime(2026, 1, 1)),
            SimpleNamespace(d=datetime(2026, 1, 1)),
            SimpleNamespace(d=datetime(2026, 1, 3)),
        ]
        start, end = datetime(2026, 1, 1), datetime(2026, 1, 3, 23, 59, 59)
        result = pa._bucketize(items, lambda i: i.d, start, end)
        assert result == {"2026-01-01": 2, "2026-01-02": 0, "2026-01-03": 1}

    def test_week_granularity_groups_by_iso_week_label(self, pa):
        # Rango de 41 días (>35, <=183) para forzar granularidad semanal.
        start = datetime(2026, 1, 1)  # jueves
        end = start + timedelta(days=40)
        items = [
            SimpleNamespace(d=datetime(2026, 1, 5)),
            SimpleNamespace(d=datetime(2026, 1, 20)),
        ]
        result = pa._bucketize(items, lambda i: i.d, start, end)
        assert pa._bucket_granularity(start, end) == "week"
        # La clave del hueco (esqueleto) usa el AÑO CALENDARIO del lunes de esa
        # semana + su propio número de semana ISO: la semana que contiene el
        # 1-ene-2026 (jueves) empieza el lunes 29-dic-2025, así que su clave es
        # "2025-W01" (queda vacía: 0). Pero la clave de cada ITEM se calcula
        # con `d.year` (el año calendario del propio dato), no con el año del
        # lunes de inicio de semana: el 5-ene-2026 cae en la semana siguiente
        # (lunes 5-ene a domingo 11-ene), que es la semana ISO 2 de 2026, así
        # que su clave es "2026-W02", no "2025-W01". Es decir, el esqueleto y
        # los items usan una fórmula de año distinta y solo coinciden fuera de
        # las semanas que cruzan el límite de año — comportamiento real,
        # verificado, documentado tal cual (no es un bug que debamos arreglar
        # aquí: no se toca código de aplicación).
        assert "2025-W01" in result
        assert result["2025-W01"] == 0
        assert result["2026-W02"] == 1  # item del 5-ene
        assert result["2026-W04"] == 1  # item del 20-ene
        assert sum(result.values()) == 2

    def test_month_granularity_fills_gaps_with_zero(self, pa):
        start, end = datetime(2026, 1, 1), datetime(2026, 8, 1)
        items = [
            SimpleNamespace(d=datetime(2026, 2, 10)),
            SimpleNamespace(d=datetime(2026, 2, 20)),
        ]
        result = pa._bucketize(items, lambda i: i.d, start, end)
        assert result["2026-01"] == 0
        assert result["2026-02"] == 2
        assert result["2026-08"] == 0
        assert list(result.keys()) == [
            "2026-01", "2026-02", "2026-03", "2026-04",
            "2026-05", "2026-06", "2026-07", "2026-08",
        ]

    def test_items_outside_range_are_ignored(self, pa):
        items = [SimpleNamespace(d=datetime(2025, 12, 31)), SimpleNamespace(d=datetime(2026, 1, 1))]
        start, end = datetime(2026, 1, 1), datetime(2026, 1, 1, 23, 59, 59)
        result = pa._bucketize(items, lambda i: i.d, start, end)
        assert result == {"2026-01-01": 1}

    def test_none_date_is_ignored(self, pa):
        items = [SimpleNamespace(d=None), SimpleNamespace(d=datetime(2026, 1, 1))]
        start, end = datetime(2026, 1, 1), datetime(2026, 1, 1, 23, 59, 59)
        result = pa._bucketize(items, lambda i: i.d, start, end)
        assert result == {"2026-01-01": 1}


class TestBucketizeUnique:
    def test_counts_distinct_values_per_bucket(self, pa):
        items = [
            SimpleNamespace(d=datetime(2026, 1, 1), who="alice"),
            SimpleNamespace(d=datetime(2026, 1, 1), who="alice"),  # repetida, no debe duplicar
            SimpleNamespace(d=datetime(2026, 1, 1), who="bob"),
            SimpleNamespace(d=datetime(2026, 1, 2), who="carol"),
        ]
        start, end = datetime(2026, 1, 1), datetime(2026, 1, 2, 23, 59, 59)
        result = pa._bucketize_unique(items, lambda i: i.d, lambda i: i.who, start, end)
        assert result == {"2026-01-01": 2, "2026-01-02": 1}


class TestResolveRange:
    def test_hoy(self, pa):
        r = pa._resolve_range("hoy", "", "", None)
        today = _today_midnight()
        assert r["start"] == today
        assert r["end"] == datetime(today.year, today.month, today.day, 23, 59, 59)
        assert r["granularity"] == "day"

    def test_semana(self, pa):
        r = pa._resolve_range("semana", "", "", None)
        today = _today_midnight()
        assert r["start"] == today - timedelta(days=today.weekday())
        assert r["start"].weekday() == 0  # lunes

    def test_semana_anterior(self, pa):
        r = pa._resolve_range("semana_anterior", "", "", None)
        today = _today_midnight()
        this_monday = today - timedelta(days=today.weekday())
        assert r["start"] == this_monday - timedelta(days=7)
        assert r["end"].date() == (this_monday - timedelta(days=1)).date()

    def test_mes(self, pa):
        r = pa._resolve_range("mes", "", "", None)
        today = _today_midnight()
        assert r["start"] == datetime(today.year, today.month, 1)

    def test_7d_30d_90d(self, pa):
        today = _today_midnight()
        for rango, days_back in (("7d", 6), ("30d", 29), ("90d", 89)):
            r = pa._resolve_range(rango, "", "", None)
            assert r["start"] == today - timedelta(days=days_back)
            assert r["end"] == datetime(today.year, today.month, today.day, 23, 59, 59)

    def test_anio(self, pa):
        r = pa._resolve_range("anio", "", "", None)
        today = _today_midnight()
        assert r["start"] == datetime(today.year, 1, 1)

    def test_todo(self, pa):
        r = pa._resolve_range("todo", "", "", None)
        assert r["start"] == datetime(2000, 1, 1)
        assert r["label"] == "histórico"

    def test_unknown_preset_falls_back_to_mes(self, pa):
        r = pa._resolve_range("esto-no-existe", "", "", None)
        today = _today_midnight()
        assert r["start"] == datetime(today.year, today.month, 1)

    def test_mes_anterior_crosses_year_boundary(self, pa, monkeypatch):
        class FrozenDatetime(datetime):
            @classmethod
            def utcnow(cls):
                return datetime(2026, 1, 15)

        monkeypatch.setattr(pa, "datetime", FrozenDatetime)
        r = pa._resolve_range("mes_anterior", "", "", None)
        assert r["start"] == datetime(2025, 12, 1)
        assert r["end"] == datetime(2025, 12, 31, 23, 59, 59)
        assert r["label"] == "de 12/2025"

    def test_mes_anterior_regular_month(self, pa, monkeypatch):
        class FrozenDatetime(datetime):
            @classmethod
            def utcnow(cls):
                return datetime(2026, 6, 10)

        monkeypatch.setattr(pa, "datetime", FrozenDatetime)
        r = pa._resolve_range("mes_anterior", "", "", None)
        assert r["start"] == datetime(2026, 5, 1)
        assert r["end"] == datetime(2026, 5, 31, 23, 59, 59)

    def test_personalizado_valid_range(self, pa):
        r = pa._resolve_range("personalizado", "2026-01-01", "2026-01-31", None)
        assert r["rango"] == "personalizado"
        assert r["start"] == datetime(2026, 1, 1)
        assert r["end"] == datetime(2026, 1, 31, 23, 59, 59)

    def test_personalizado_invalid_dates_falls_back_to_mes(self, pa):
        r = pa._resolve_range("personalizado", "no-es-fecha", "tampoco", None)
        today = _today_midnight()
        assert r["rango"] == "mes"
        assert r["start"] == datetime(today.year, today.month, 1)

    def test_personalizado_missing_dates_falls_back_to_mes(self, pa):
        r = pa._resolve_range("personalizado", "", "", None)
        assert r["rango"] == "mes"

    def test_personalizado_hasta_before_desde_falls_back_to_mes(self, pa):
        r = pa._resolve_range("personalizado", "2026-02-10", "2026-01-01", None)
        assert r["rango"] == "mes"


class TestAverage:
    def test_empty_list_returns_zero(self, pa):
        assert pa._average([]) == 0

    def test_filters_none_values(self, pa):
        assert pa._average([1, None, 2, 3]) == 2.0

    def test_rounds_to_two_decimals(self, pa):
        assert pa._average([1, 2, 2]) == pytest.approx(1.67)

    def test_all_none_returns_zero(self, pa):
        assert pa._average([None, None]) == 0
