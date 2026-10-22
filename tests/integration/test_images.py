"""Tests de dockerlabs/routes/images.py — servicio de imágenes (perfil, logos).

Cubre la cadena de fallback documentada en el propio módulo:
  perfil: profile_image_path (archivo) -> profile_image_data (blob BD,
          compatibilidad antigua) -> uploads/perfiles/user_{id}_*.ext ->
          estático por username -> default balu.webp
  logo:   logo_path (archivo) -> logo_data (blob BD) -> machine.imagen
          (estático) -> default logo.png

También fija el contrato de seguridad de API_PUBLICA.md / CLAUDE.md: las
respuestas de /img/ llevan una CSP 'sandbox' EN VIGOR (no Report-Only), para
que un SVG subido como logo/avatar no ejecute script si se abre como
documento de primer nivel.
"""
import os

import pytest

from tests.factories import make_machine, make_user

pytestmark = pytest.mark.integration

ENFORCED_IMG_CSP = "default-src 'none'; style-src 'unsafe-inline'; sandbox"


def _repo_root() -> str:
    # tests/integration/test_images.py -> tests/ -> repo root
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _write_uploaded_file(relative_path: str, content: bytes = b"\x89PNG\r\n\x1a\nfake-but-fine-for-fileresponse"):
    """Helper local (no toca conftest/factories): escribe un fichero real bajo
    el repo para que FileResponse lo pueda servir, y devuelve una función de
    limpieza. El directorio `uploads/` no existe en este clon local todavía."""
    full_path = os.path.join(_repo_root(), relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "wb") as f:
        f.write(content)

    def _cleanup():
        try:
            os.remove(full_path)
        except OSError:
            pass

    return full_path, _cleanup


class TestProfileImage:
    def test_no_photo_set_falls_back_to_default(self, client, db):
        user = make_user(db)
        r = client.get(f"/img/perfil/{user.id}")
        assert r.status_code == 200
        assert "webp" in r.headers.get("content-type", "")

    def test_nonexistent_user_id_still_returns_default_not_404(self, client, db):
        # Diseño fail-safe documentado: el user_id inexistente no debe tumbar
        # la respuesta con un 404, cae directo al tier 4 (default).
        r = client.get("/img/perfil/999999999")
        assert r.status_code == 200

    def test_profile_image_path_tier_is_served_when_file_exists(self, client, db):
        user = make_user(db)
        rel_path = f"uploads/perfiles/test_profile_{user.id}.png"
        _full, cleanup = _write_uploaded_file(rel_path)
        try:
            user.profile_image_path = rel_path
            user.profile_image_mime = "image/png"
            db.session.commit()

            r = client.get(f"/img/perfil/{user.id}")
            assert r.status_code == 200
            assert r.headers["content-type"] == "image/png"
        finally:
            cleanup()


class TestMachineLogo:
    def test_no_logo_set_falls_back_through_static_imagen_field(self, client, db):
        # make_machine ya pone `imagen` apuntando a un fichero estático real
        # (logo.png por defecto), así que esto ejercita el tier 3, no el 4.
        machine = make_machine(db)
        r = client.get(f"/img/maquina/{machine.id}")
        assert r.status_code == 200

    def test_nonexistent_machine_id_returns_default(self, client, db):
        r = client.get("/img/maquina/999999999")
        assert r.status_code == 200

    def test_logo_path_tier_is_served_when_file_exists(self, client, db):
        machine = make_machine(db)
        rel_path = f"uploads/logos/test_logo_{machine.id}.png"
        _full, cleanup = _write_uploaded_file(rel_path)
        try:
            machine.logo_path = rel_path
            machine.logo_mime = "image/png"
            db.session.commit()

            r = client.get(f"/img/maquina/{machine.id}")
            assert r.status_code == 200
            assert r.headers["content-type"] == "image/png"
        finally:
            cleanup()


class TestImgCspHeader:
    def test_profile_image_response_has_enforced_sandbox_csp(self, client, db):
        user = make_user(db)
        r = client.get(f"/img/perfil/{user.id}")
        assert r.headers.get("content-security-policy") == ENFORCED_IMG_CSP

    def test_machine_logo_response_has_enforced_sandbox_csp(self, client, db):
        machine = make_machine(db)
        r = client.get(f"/img/maquina/{machine.id}")
        assert r.headers.get("content-security-policy") == ENFORCED_IMG_CSP

    def test_csp_is_the_enforced_header_not_the_report_only_one(self, client, db):
        # El Report-Only es el genérico de toda la app (default-src 'self'...);
        # el de /img/ debe ser el sandbox estricto, EN VIGOR, no solo reportado.
        user = make_user(db)
        r = client.get(f"/img/perfil/{user.id}")
        report_only = r.headers.get("content-security-policy-report-only", "")
        enforced = r.headers.get("content-security-policy", "")
        assert enforced == ENFORCED_IMG_CSP
        assert enforced != report_only
        assert "sandbox" in enforced
