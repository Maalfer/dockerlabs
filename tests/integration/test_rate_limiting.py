"""Tests de los limitadores de tasa: el middleware ASGI genérico (asgi.py) y
los limitadores propios en memoria de certificados.py (_gen_rate/_ver_rate).

MECÁNICA DE DETECCIÓN DE IP (hallazgo relevante): `rate_limit_middleware` usa
`request.client.host` crudo — NO lee `X-Forwarded-For` ni `cf-connecting-ip`
(a diferencia de `visit_counter_middleware`, que sí lee `cf-connecting-ip`, y
de `/go/<destino>` en pages_core.py, que también lee `cf-connecting-ip`). Por
defecto, `starlette.testclient.TestClient` fija `request.client` a
`("testclient", 50000)` para TODAS las instancias (es un default de clase, no
por instancia), así que:
  - mandar `headers={"X-Forwarded-For": "1.2.3.4"}` con el `client` fixture NO
    cambia la IP que ve el middleware (sigue siendo "testclient"): se
    comprobó y confirma que el middleware ignora esa cabecera en esta ruta.
  - para aislar un test de otros tests que también usan el `client` fixture
    compartido (y por tanto la misma key "testclient" en el dict global), se
    crea aquí un TestClient propio por test con `client=(ip, puerto)` para
    obtener una IP exclusiva, y se manipula `asgi.rate_limit_store` por esa
    key directamente en vez de disparar 300 peticiones HTTP reales.

Un fixture local (no toca conftest.py) guarda y restaura todo el dict
`asgi.rate_limit_store` alrededor de cada test de este fichero, así que ningún
test de aquí contamina a otro ni al resto del suite.
"""
import time

import pytest

# NOTA: `import asgi` a nivel de módulo rompería la recolección de pytest:
# `dockerlabs/database.py` exige `DATABASE_URL` ya fijada en el entorno, y eso
# solo lo hace la fixture de sesión `_test_database` de conftest.py en tiempo
# de ejecución (no en tiempo de colección). Por eso aquí, igual que en
# conftest.py/factories.py, el import de `asgi` vive dentro de una fixture,
# nunca en la cabecera del fichero.

pytestmark = pytest.mark.integration


@pytest.fixture
def asgi_mod(_test_database):
    return _test_database  # la fixture de conftest ya hace `import asgi` y lo yieldea


@pytest.fixture(autouse=True)
def _isolated_rate_limit_store(asgi_mod):
    snapshot = dict(asgi_mod.rate_limit_store)
    asgi_mod.rate_limit_store.clear()
    yield
    asgi_mod.rate_limit_store.clear()
    asgi_mod.rate_limit_store.update(snapshot)


def _client_with_ip(asgi_mod, ip: str):
    from fastapi.testclient import TestClient

    return TestClient(asgi_mod.app, client=(ip, 12345))


class TestAsgiRateLimitMiddleware:
    def test_forwarded_for_header_is_ignored_ip_comes_from_socket(self, client, asgi_mod):
        """Confirma la mecánica documentada arriba: X-Forwarded-For no mueve
        la aguja. Saturamos la key real ("testclient", la que usa el `client`
        fixture) y comprobamos que mandar un X-Forwarded-For distinto NO libra
        de los 429: el middleware sigue mirando el socket, no la cabecera."""
        asgi_mod.rate_limit_store["testclient"] = [time.time()] * asgi_mod.API_RATE_LIMIT
        r = client.get("/robots.txt", headers={"X-Forwarded-For": "9.9.9.9"})
        assert r.status_code == 429
        # Si hubiera respetado la cabecera, "9.9.9.9" tendría su propia key
        # sin saturar y esta petición habría pasado (200).
        assert "9.9.9.9" not in asgi_mod.rate_limit_store

    def test_request_under_limit_passes(self, asgi_mod):
        ip = "203.0.113.10"
        c = _client_with_ip(asgi_mod, ip)
        r = c.get("/robots.txt")
        assert r.status_code == 200
        assert len(asgi_mod.rate_limit_store[ip]) == 1

    def test_request_at_limit_gets_429_with_expected_body(self, asgi_mod):
        ip = "203.0.113.11"
        asgi_mod.rate_limit_store[ip] = [time.time()] * asgi_mod.API_RATE_LIMIT
        c = _client_with_ip(asgi_mod, ip)

        r = c.get("/robots.txt")
        assert r.status_code == 429
        body = r.json()
        assert body["error"] == "Rate limit exceeded"
        assert str(asgi_mod.API_RATE_LIMIT) in body["detail"]

    def test_old_hits_outside_window_do_not_count(self, asgi_mod):
        ip = "203.0.113.12"
        stale_time = time.time() - asgi_mod.RATE_WINDOW - 5
        asgi_mod.rate_limit_store[ip] = [stale_time] * asgi_mod.API_RATE_LIMIT
        c = _client_with_ip(asgi_mod, ip)

        r = c.get("/robots.txt")
        assert r.status_code == 200  # los hits viejos ya no cuentan, se descartan

    @pytest.mark.parametrize("path", ["/static/does-not-exist.css", "/img/maquina/999999"])
    def test_static_and_img_paths_are_exempt_even_when_saturated(self, asgi_mod, path):
        ip = "203.0.113.13"
        asgi_mod.rate_limit_store[ip] = [time.time()] * (asgi_mod.API_RATE_LIMIT * 2)
        c = _client_with_ip(asgi_mod, ip)

        r = c.get(path)
        assert r.status_code != 429  # exento: puede ser 404 (fichero/máquina inexistente) pero nunca 429

    def test_store_is_purged_once_it_exceeds_max_keys(self, asgi_mod):
        now = time.time()
        # Todas estas keys son "viejas" (último hit hace más de RATE_WINDOW):
        # _prune las borra a todas en cuanto el tamaño del dict dispara la poda.
        for i in range(asgi_mod.RATE_STORE_MAX_KEYS + 1):
            asgi_mod.rate_limit_store[f"stale-ip-{i}"] = [now - asgi_mod.RATE_WINDOW - 1]
        assert len(asgi_mod.rate_limit_store) > asgi_mod.RATE_STORE_MAX_KEYS

        c = _client_with_ip(asgi_mod, "203.0.113.14")
        r = c.get("/robots.txt")
        assert r.status_code == 200

        # Quedan las stale podadas; solo sobrevive la IP de esta petición
        # (y posiblemente alguna otra con hits recientes, pero muchas menos
        # que las ~10.000 insertadas).
        assert len(asgi_mod.rate_limit_store) < 100


class TestCertificadosInProcessLimiters:
    _CERT_ID = "DL-ABCDEF"  # formato válido (^DL-[0-9A-F]{6}$), no emitido

    def _reset(self):
        from dockerlabs.routes import certificados

        certificados._ver_rate.clear()
        certificados._gen_rate.clear()

    def test_verificar_endpoint_rate_limited_after_documented_threshold(self, client):
        from dockerlabs.routes import certificados

        self._reset()
        try:
            for _ in range(certificados.VER_MAX_PER_MIN):
                r = client.get(f"/api/certificado/verificar/{self._CERT_ID}")
                assert r.status_code == 200
                assert r.json()["valid"] is False  # cert_id bien formado pero no emitido

            r_over = client.get(f"/api/certificado/verificar/{self._CERT_ID}")
            assert r_over.status_code == 429
            body = r_over.json()
            assert body["valid"] is False
            assert "Demasiadas verificaciones" in body["message"]
        finally:
            self._reset()  # no contaminar otros tests que compartan la key "testclient"

    def test_verificar_limit_is_keyed_per_ip_not_per_cert_id(self, client):
        from dockerlabs.routes import certificados

        self._reset()
        try:
            # Agotar el límite con UN cert_id...
            for _ in range(certificados.VER_MAX_PER_MIN):
                client.get(f"/api/certificado/verificar/{self._CERT_ID}")
            # ...y comprobar que otro cert_id distinto, misma IP, también cae:
            # _allow() indexa por client_ip, no por cert_id.
            r = client.get("/api/certificado/verificar/DL-111111")
            assert r.status_code == 429
        finally:
            self._reset()
