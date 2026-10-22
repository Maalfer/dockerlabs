"""Tests de dockerlabs/routes/certificados.py — certificados de finalización.

Varias funciones puras (`author_matches_user`, `machine_certificable`,
`ensure_certificate`, `sync_user_certificates`) se prueban directamente contra
BD real (vía la fixture `db`), sin pasar por HTTP; los endpoints públicos y
privados se prueban vía `client`.

Nota sobre el entorno local (Mac de desarrollo, no el VPS de producción):
`render_diploma()` usa una fuente fija de Linux
(`/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`) que no existe en esta
máquina. Para poder ejercitar de verdad el renderizado (necesario para probar
`ensure_certificate`, `sync_user_certificates` y el fallback de reemisión de
pdf/imagen con un escenario real) se redirige `FONT_PATH` con monkeypatch a una
DejaVuSans-Bold.ttf real que sí existe aquí (viene con LibreOffice). Esto es
puramente un ajuste de entorno de test local: no toca ningún fichero de
`dockerlabs/`.
"""
import os
import shutil

import pytest

from tests.factories import make_certificate, make_machine, make_user, make_writeup

pytestmark = pytest.mark.integration

_LOCAL_FONT_FALLBACK = "/Applications/LibreOffice.app/Contents/Resources/fonts/truetype/DejaVuSans-Bold.ttf"


@pytest.fixture(autouse=True)
def _real_font_for_local_dev(monkeypatch):
    from dockerlabs.routes import certificados

    if not os.path.isfile(certificados.FONT_PATH) and os.path.isfile(_LOCAL_FONT_FALLBACK):
        monkeypatch.setattr(certificados, "FONT_PATH", _LOCAL_FONT_FALLBACK)


def _cleanup_cert_files(user_id: int) -> None:
    """Helper local (no toca conftest/factories): borra los diplomas reales
    que `ensure_certificate()` archiva en disco durante estos tests, para no
    dejar ficheros sueltos en el clon local entre ejecuciones."""
    from dockerlabs.routes.certificados import BASE_DIR

    path = os.path.join(BASE_DIR, "uploads", "certificados", f"user_{user_id}")
    shutil.rmtree(path, ignore_errors=True)


# ---------------------------------------------------------------------------
# author_matches_user
# ---------------------------------------------------------------------------


class TestAuthorMatchesUser:
    def test_exact_match_is_true(self, db):
        from dockerlabs.routes.certificados import author_matches_user

        user = make_user(db, username="exacto1")
        assert author_matches_user("exacto1", user) is True

    def test_different_user_is_false(self, db):
        from dockerlabs.routes.certificados import author_matches_user

        user = make_user(db, username="usuarioa1")
        assert author_matches_user("usuariob1", user) is False

    def test_unique_case_insensitive_match_is_true(self, db):
        from dockerlabs.routes.certificados import author_matches_user

        user = make_user(db, username="casoinsensible1")
        assert author_matches_user("CasoInsensible1", user) is True

    def test_db_collation_blocks_case_only_homonyms(self, db):
        """Verificación empírica pedida por el encargo: la collation por
        defecto de esta MariaDB de test es case-insensitive para `username`
        (confirmado antes de escribir este test con un script aparte: crear
        'oscartest' y luego 'Oscartest' revienta con IntegrityError 1062
        'Duplicate entry'). Así que NO se pueden tener dos cuentas reales que
        solo difieran en mayúsculas en esta base — por eso el caso ambiguo de
        más abajo necesita un doble (monkeypatch) en vez de filas reales."""
        from sqlalchemy.exc import IntegrityError

        make_user(db, username="homonimotest1")
        with pytest.raises(IntegrityError):
            make_user(db, username="Homonimotest1")
        db.session.rollback()

    def test_ambiguous_homonyms_returns_false(self, db, monkeypatch):
        """Rama ambigua (>1 cuenta homónima solo por mayúsculas): no
        reproducible con filas reales en esta BD (ver test anterior), así que
        se fuerza con un doble de `User.query` que simula 2 coincidencias."""
        from dockerlabs.routes import certificados

        class _FakeQuery:
            def filter(self, *a, **kw):
                return self

            def count(self):
                return 2

        class _FakeUserNS:
            # `username` tiene que existir como atributo de clase: el código
            # real construye `func.lower(User.username)` ANTES de llamar a
            # `.filter(...)`, así que SQLAlchemy necesita poder envolverlo en
            # una expresión aunque el resultado nunca se evalúe de verdad
            # (el `_FakeQuery.filter` de arriba ignora sus argumentos).
            username = "placeholder"
            query = _FakeQuery()

        user = make_user(db, username="ambiguo1")
        monkeypatch.setattr(certificados, "User", _FakeUserNS)
        assert certificados.author_matches_user("Ambiguo1", user) is False


# ---------------------------------------------------------------------------
# machine_certificable
# ---------------------------------------------------------------------------


class TestMachineCertificable:
    def test_docker_machine_is_certifiable(self, db):
        from dockerlabs.routes.certificados import machine_certificable

        make_machine(db, origen="docker", nombre="DockerCert1")
        assert machine_certificable("DockerCert1") is True

    def test_bunker_machine_is_not_certifiable(self, db):
        from dockerlabs.routes.certificados import machine_certificable

        make_machine(db, origen="bunker", nombre="BunkerCert1")
        assert machine_certificable("BunkerCert1") is False

    def test_nonexistent_machine_is_certifiable_fail_open(self, db):
        """Documentado en el propio código: una máquina sin fila en el
        catálogo (borrada) se considera certificable, porque no se puede
        afirmar que fuera de bunker."""
        from dockerlabs.routes.certificados import machine_certificable

        assert machine_certificable("EstaMaquinaNoExisteEnElCatalogo") is True


# ---------------------------------------------------------------------------
# ensure_certificate / sync_user_certificates
# ---------------------------------------------------------------------------


class TestEnsureCertificateAndSync:
    def test_creates_row_for_docker_writeup(self, db):
        from dockerlabs.models import Certificate
        from dockerlabs.routes.certificados import ensure_certificate

        user = make_user(db, username="certuser1")
        make_machine(db, origen="docker", nombre="CertMachine1")
        make_writeup(db, maquina="CertMachine1", autor="certuser1")
        try:
            cert = ensure_certificate(user, "CertMachine1")
            assert cert is not None
            row = Certificate.query.filter_by(user_id=user.id, machine_name="CertMachine1").first()
            assert row is not None
            assert row.cert_id == cert.cert_id
        finally:
            _cleanup_cert_files(user.id)

    def test_is_idempotent_same_cert_id_no_duplicate_row(self, db):
        from dockerlabs.models import Certificate
        from dockerlabs.routes.certificados import ensure_certificate

        user = make_user(db, username="certuser2")
        make_machine(db, origen="docker", nombre="CertMachine2")
        make_writeup(db, maquina="CertMachine2", autor="certuser2")
        try:
            cert1 = ensure_certificate(user, "CertMachine2")
            cert2 = ensure_certificate(user, "CertMachine2")
            assert cert1.cert_id == cert2.cert_id
            count = Certificate.query.filter_by(user_id=user.id, machine_name="CertMachine2").count()
            assert count == 1
        finally:
            _cleanup_cert_files(user.id)

    def test_none_for_bunker_writeup_even_though_writeup_exists(self, db):
        from dockerlabs.models import Certificate
        from dockerlabs.routes.certificados import ensure_certificate

        user = make_user(db, username="certuser3")
        make_machine(db, origen="bunker", nombre="BunkerWriteupMachine1")
        writeup = make_writeup(db, maquina="BunkerWriteupMachine1", autor="certuser3")

        cert = ensure_certificate(user, "BunkerWriteupMachine1")
        assert cert is None
        assert writeup is not None  # el writeup existe de verdad...
        assert Certificate.query.filter_by(user_id=user.id, machine_name="BunkerWriteupMachine1").first() is None

    def test_sync_emits_docker_and_skips_bunker(self, db):
        from dockerlabs.models import Certificate
        from dockerlabs.routes.certificados import sync_user_certificates

        user = make_user(db, username="certuser4")
        make_machine(db, origen="docker", nombre="SyncDocker1")
        make_machine(db, origen="bunker", nombre="SyncBunker1")
        make_writeup(db, maquina="SyncDocker1", autor="certuser4")
        make_writeup(db, maquina="SyncBunker1", autor="certuser4")
        try:
            result = sync_user_certificates(user)
            assert result["emitidos"] == 1
            certs = Certificate.query.filter_by(user_id=user.id).all()
            assert {c.machine_name for c in certs} == {"SyncDocker1"}
        finally:
            _cleanup_cert_files(user.id)


# ---------------------------------------------------------------------------
# GET /api/certificado/verificar/{cert_id} (público)
# ---------------------------------------------------------------------------


class TestVerificarPublico:
    def test_valid_existing_cert_succeeds(self, client, db):
        from dockerlabs.routes import certificados

        certificados._ver_rate.clear()
        user = make_user(db, username="veruser1")
        cert = make_certificate(db, user=user, machine_name="VerMachine1", cert_id="DL-ABCDEF")

        r = client.get(f"/api/certificado/verificar/{cert.cert_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is True
        assert body["username"] == "veruser1"

    def test_well_formed_but_unknown_id_not_found(self, client):
        from dockerlabs.routes import certificados

        certificados._ver_rate.clear()
        r = client.get("/api/certificado/verificar/DL-123456")
        assert r.status_code == 200
        assert r.json()["valid"] is False

    @pytest.mark.parametrize("bad_id", ["DL-ABCDE", "DL-ABCDEFF", "XX-ABCDEF", "DLABCDEF", "DL-GHIJKL"])
    def test_malformed_id_rejected_by_format(self, client, bad_id):
        from dockerlabs.routes import certificados

        certificados._ver_rate.clear()
        r = client.get(f"/api/certificado/verificar/{bad_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is False
        assert "formato" in body["message"].lower()

    def test_lowercase_hex_is_normalized_not_rejected_as_malformed(self, client):
        """Sorprendente: el endpoint hace `cert_id.strip().upper()` ANTES de
        validar el formato contra `DL-[0-9A-F]{6}`, así que un hex en
        minúsculas SÍ pasa la validación de formato (se normaliza primero) y
        solo falla por "no encontrado" si no hay un certificado real con ese
        ID; no se rechaza como "formato inválido"."""
        from dockerlabs.routes import certificados

        certificados._ver_rate.clear()
        r = client.get("/api/certificado/verificar/dl-abcdef")
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is False
        assert "no encontrado" in body["message"].lower()

    def test_rate_limit_kicks_in_after_threshold(self, client):
        from dockerlabs.routes import certificados

        certificados._ver_rate.clear()
        for _ in range(certificados.VER_MAX_PER_MIN):
            r = client.get("/api/certificado/verificar/DL-000000")
            assert r.status_code == 200
        r = client.get("/api/certificado/verificar/DL-000000")
        assert r.status_code == 429


# ---------------------------------------------------------------------------
# GET /api/certificado/pdf/{cert_id} y /api/certificado/imagen/{cert_id} (público)
# ---------------------------------------------------------------------------


class TestPdfImagenPublico:
    def test_malformed_cert_id_rejected_with_400(self, client):
        r = client.get("/api/certificado/pdf/not-a-valid-id")
        assert r.status_code == 400
        r2 = client.get("/api/certificado/imagen/not-a-valid-id")
        assert r2.status_code == 400

    def test_serve_real_files_after_ensure_certificate(self, client, db):
        """Camino feliz: el PDF/imagen archivados por ensure_certificate()
        existen de verdad en disco, así que se sirven directamente sin pasar
        por el fallback de reemisión."""
        from dockerlabs.routes.certificados import ensure_certificate

        user = make_user(db, username="pdfuser1")
        make_machine(db, origen="docker", nombre="PdfMachine1")
        make_writeup(db, maquina="PdfMachine1", autor="pdfuser1")
        cert = ensure_certificate(user, "PdfMachine1")
        assert cert is not None
        try:
            r_img = client.get(f"/api/certificado/imagen/{cert.cert_id}")
            assert r_img.status_code == 200
            assert r_img.headers["content-type"] == "image/webp"

            r_pdf = client.get(f"/api/certificado/pdf/{cert.cert_id}")
            assert r_pdf.status_code == 200
            assert r_pdf.headers["content-type"] == "application/pdf"
        finally:
            _cleanup_cert_files(user.id)

    def test_missing_file_with_real_writeup_triggers_reemission_fallback(self, client, db):
        """`make_certificate()` crea la fila con pdf_path/image_path falsos:
        no hay fichero real en disco. El fallback del endpoint intenta
        reemitir de verdad llamando a `ensure_certificate(force=True)`; como
        aquí SÍ hay un writeup real detrás, la reemisión funciona y el
        endpoint acaba sirviendo el fichero recién generado (200), en vez de
        devolver 404.

        Importante: hay que sembrar el certificado con el `cert_id`
        REALMENTE determinista de (usuario, máquina) — `certificate_id()` —
        en vez de uno aleatorio. `ensure_certificate(force=True)` reasigna
        `existing.cert_id` al id determinista durante la reemisión; si el
        `cert_id` sembrado no coincidiera con ese valor, la fila cambiaría de
        ID a mitad de la petición y la búsqueda posterior por el ID original
        (`raw`) ya no encontraría la fila (sorprendente, pero es el
        comportamiento real: se comprobó primero con un cert_id aleatorio y
        el endpoint devolvía 404 en vez de 200 por este motivo exacto)."""
        from dockerlabs.routes.certificados import certificate_id

        user = make_user(db, username="pdfuser2")
        make_machine(db, origen="docker", nombre="PdfMachine2")
        make_writeup(db, maquina="PdfMachine2", autor="pdfuser2")
        cert = make_certificate(
            db, user=user, machine_name="PdfMachine2",
            cert_id=certificate_id("pdfuser2", "PdfMachine2"),
        )
        try:
            r = client.get(f"/api/certificado/imagen/{cert.cert_id}")
            assert r.status_code == 200
        finally:
            _cleanup_cert_files(user.id)

    def test_missing_file_without_writeup_stays_404(self, client, db):
        """Sin writeup real detrás, `ensure_certificate()` dentro del
        fallback devuelve None (nada que reemitir), así que el endpoint sigue
        sin tener nada que servir y responde 404 de verdad."""
        user = make_user(db, username="pdfuser3")
        make_machine(db, origen="docker", nombre="PdfMachine3")
        cert = make_certificate(db, user=user, machine_name="PdfMachine3")

        r = client.get(f"/api/certificado/imagen/{cert.cert_id}")
        assert r.status_code == 404

        r2 = client.get(f"/api/certificado/pdf/{cert.cert_id}")
        assert r2.status_code == 404

    def test_unknown_cert_id_404(self, client):
        r = client.get("/api/certificado/imagen/DL-FFFFFF")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/certificado/{machine_name} (generar, requiere login)
# ---------------------------------------------------------------------------


class TestGenerarCertificado:
    def test_requires_login(self, client):
        r = client.get("/api/certificado/CualquierMaquina")
        assert r.status_code == 401

    def test_403_when_no_writeup(self, client, login_as, db):
        user = make_user(db, username="genuser1")
        make_machine(db, origen="docker", nombre="GenMachine1")
        login_as(user)

        r = client.get("/api/certificado/GenMachine1")
        assert r.status_code == 403

    def test_403_when_machine_not_certifiable(self, client, login_as, db):
        user = make_user(db, username="genuser2")
        make_machine(db, origen="bunker", nombre="GenMachineBunker1")
        make_writeup(db, maquina="GenMachineBunker1", autor="genuser2")
        login_as(user)

        r = client.get("/api/certificado/GenMachineBunker1")
        assert r.status_code == 403

    def test_success_default_png_format(self, client, login_as, db):
        user = make_user(db, username="genuser3")
        make_machine(db, origen="docker", nombre="GenMachine3")
        make_writeup(db, maquina="GenMachine3", autor="genuser3")
        login_as(user)
        try:
            r = client.get("/api/certificado/GenMachine3")
            assert r.status_code == 200
            assert r.headers["content-type"] == "image/png"
        finally:
            _cleanup_cert_files(user.id)

    def test_formato_pdf_is_actually_broken_no_physical_pdf_archived(self, client, login_as, db):
        """HALLAZGO (no es un fallo del test, es el comportamiento real):
        `ensure_certificate()` ya NO archiva un PDF físico — el comentario del
        propio módulo dice "ya no se archiva un PDF por certificado... el PDF
        se compone al vuelo" — pero la rama `formato == "pdf"` de
        `api_generar_certificado` sigue haciendo
        `FileResponse(abspath_for(cert.pdf_path), ...)` esperando un fichero
        que nunca se escribe. El resultado es que `GET
        /api/certificado/<maquina>?formato=pdf` SIEMPRE revienta con un
        `RuntimeError` (archivo inexistente) en vez de servir el PDF — a
        diferencia de `GET /api/certificado/pdf/<cert_id>` (el endpoint
        público de verificación), que sí compone el PDF al vuelo desde el
        WebP y funciona bien (ver `test_serve_real_files_after_ensure_certificate`
        más arriba). Se deja documentado aquí en vez de forzar un 200 falso;
        no se toca `dockerlabs/routes/certificados.py` (fuera de alcance)."""
        user = make_user(db, username="genuser4")
        make_machine(db, origen="docker", nombre="GenMachine4")
        make_writeup(db, maquina="GenMachine4", autor="genuser4")
        login_as(user)
        try:
            with pytest.raises(RuntimeError, match="does not exist"):
                client.get("/api/certificado/GenMachine4", params={"formato": "pdf"})
        finally:
            _cleanup_cert_files(user.id)

    def test_invalid_formato_rejected_with_400(self, client, login_as, db):
        user = make_user(db, username="genuser5")
        make_machine(db, origen="docker", nombre="GenMachine5")
        make_writeup(db, maquina="GenMachine5", autor="genuser5")
        login_as(user)

        r = client.get("/api/certificado/GenMachine5", params={"formato": "xyz"})
        assert r.status_code == 400

    def test_logs_certificate_request(self, client, login_as, db):
        user = make_user(db, username="genuser6")
        make_machine(db, origen="docker", nombre="GenMachine6")
        make_writeup(db, maquina="GenMachine6", autor="genuser6")
        login_as(user)
        try:
            r = client.get("/api/certificado/GenMachine6")
            assert r.status_code == 200

            db.session.rollback()
            from dockerlabs.models import CertificateRequestLog

            assert CertificateRequestLog.query.filter_by(user_id=user.id).count() == 1
        finally:
            _cleanup_cert_files(user.id)

    def test_rate_limit_kicks_in_after_threshold(self, client, login_as, db):
        from dockerlabs.routes import certificados

        certificados._gen_rate.clear()
        user = make_user(db, username="genuser7")
        make_machine(db, origen="docker", nombre="GenMachine7")
        make_writeup(db, maquina="GenMachine7", autor="genuser7")
        login_as(user)
        try:
            for _ in range(certificados.GEN_MAX_PER_MIN):
                r = client.get("/api/certificado/GenMachine7")
                assert r.status_code == 200
            r = client.get("/api/certificado/GenMachine7")
            assert r.status_code == 429
        finally:
            _cleanup_cert_files(user.id)
