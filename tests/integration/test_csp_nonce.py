"""El nonce de cada <script nonce="..."> coincide con el de la cabecera CSP."""
import re

import pytest

from tests.factories import make_machine, make_user

pytestmark = pytest.mark.integration

_CABECERA_CSP = "content-security-policy-report-only"
_PAGINAS_PUBLICAS = [
    "/",
    "/login",
    "/register",
    "/recover",
    "/instrucciones-uso",
    "/soporte",
    "/equipo",
    "/enviar-maquina",
    "/como-se-crea-una-maquina",
    "/agradecimientos",
    "/politica-privacidad",
    "/politica-cookies",
    "/condiciones-uso",
    "/bunkerlabs/login",
]


def _nonce_cabecera(response) -> str:
    politica = response.headers.get(_CABECERA_CSP, "")
    m = re.search(r"'nonce-([^']+)'", politica)
    assert m, f"la respuesta no trae nonce en la cabecera CSP: {politica!r}"
    return m.group(1)


def _nonces_html(html: str) -> list:
    return re.findall(r'<script[^>]*\bnonce="([^"]*)"', html)


def _comprobar(response):
    assert response.status_code == 200
    esperado = _nonce_cabecera(response)
    nonces = _nonces_html(response.text)
    assert nonces, "la página no tiene ningún <script nonce> que comprobar"
    distintos = sorted({n for n in nonces if n != esperado})
    assert not distintos, f"scripts con nonce que no coincide con la cabecera: {distintos}"


@pytest.mark.parametrize("ruta", _PAGINAS_PUBLICAS)
def test_nonce_de_scripts_coincide_con_cabecera(client, ruta):
    _comprobar(client.get(ruta))


def test_nonce_en_pagina_de_descarga(client, db):
    maquina = make_machine(db)
    _comprobar(client.get(f"/maquinas/{maquina.id}/descargar"))


def test_nonce_en_dashboard_con_sesion(client, db, login_as):
    user = make_user(db, role="admin")
    login_as(user)
    _comprobar(client.get("/dashboard"))


def test_cada_peticion_usa_un_nonce_distinto(client):
    a = _nonce_cabecera(client.get("/soporte"))
    b = _nonce_cabecera(client.get("/soporte"))
    assert a != b
