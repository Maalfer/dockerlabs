"""No hay autenticación por token de API: solo la cookie de sesión."""
import pytest

from tests.factories import make_user

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("metodo,ruta", [
    ("get", "/api/admin/tokens"),
    ("post", "/api/admin/tokens"),
    ("post", "/api/admin/tokens/1/revoke"),
])
def test_endpoints_de_tokens_ya_no_existen(client, login_as, db, metodo, ruta):
    csrf = login_as(make_user(db, role="admin"))
    r = getattr(client, metodo)(ruta, headers={"X-CSRFToken": csrf})
    assert r.status_code in (404, 405)


@pytest.mark.parametrize("cabeceras", [
    {"Authorization": "Bearer dlab_cualquier-token"},
    {"X-Admin-Token": "dlab_cualquier-token"},
])
def test_una_cabecera_de_token_no_da_acceso(client, cabeceras):
    # Sin cookie de sesión, una cabecera de token no autentica a nadie
    assert client.get("/api/notifications", headers=cabeceras).status_code == 401
    assert client.get("/api/admin/writeup_reports", headers=cabeceras).status_code == 403
