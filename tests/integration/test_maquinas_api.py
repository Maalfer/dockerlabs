"""Tests de dockerlabs/routes/maquinas_api.py — logo, guest-access,
estadísticas, valoraciones y máquinas completadas.

Rutas cubiertas (todas en `api_router`, prefijo `/api`):
  POST /api/gestion-maquinas/upload-logo
  POST /api/gestion-maquinas/toggle-guest-access
  GET  /api/gestion-maquinas/machine-stats/{id}
  POST /api/rate_machine
  GET  /api/get_machine_rating/{nombre}
  GET  /api/completed_machines/{machine_name}
  POST /api/toggle_completed_machine
"""
import io
import itertools

import pytest
from PIL import Image

from tests.conftest import csrf_headers
from tests.factories import make_machine, make_rating, make_user

pytestmark = pytest.mark.integration


def _admin(db):
    return make_user(db, role="admin")


def _mod(db):
    return make_user(db, role="moderador")


def _jugador(db, **overrides):
    return make_user(db, role="jugador", **overrides)


def _png_bytes(size=(10, 10), color="red"):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes(size=(10, 10), color="blue"):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


UPLOAD_LOGO_URL = "/api/gestion-maquinas/upload-logo"


class TestUploadLogoValidation:
    def test_oversized_file_rejected(self, client, login_as, db):
        maquina = make_machine(db, origen="docker")
        admin = _admin(db)
        csrf = login_as(admin)
        big = b"\x00" * (2 * 1024 * 1024 + 10)
        r = client.post(
            UPLOAD_LOGO_URL,
            data={"machine_id": str(maquina.id), "origen": maquina.origen},
            files={"logo": ("big.png", big, "image/png")},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 400
        assert "grande" in r.json()["error"].lower()

    def test_non_image_content_type_rejected(self, client, login_as, db):
        maquina = make_machine(db, origen="docker")
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(
            UPLOAD_LOGO_URL,
            data={"machine_id": str(maquina.id), "origen": maquina.origen},
            files={"logo": ("file.txt", b"hola", "text/plain")},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 400
        assert "imagen" in r.json()["error"].lower()

    def test_pil_invalid_bytes_rejected(self, client, login_as, db):
        maquina = make_machine(db, origen="docker")
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(
            UPLOAD_LOGO_URL,
            data={"machine_id": str(maquina.id), "origen": maquina.origen},
            files={"logo": ("fake.png", b"esto no es una imagen de verdad", "image/png")},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 400
        assert "válida" in r.json()["error"].lower()

    def test_valid_png_accepted_and_served_back_as_webp(self, client, login_as, db):
        maquina = make_machine(db, origen="docker")
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(
            UPLOAD_LOGO_URL,
            data={"machine_id": str(maquina.id), "origen": maquina.origen},
            files={"logo": ("logo.png", _png_bytes(), "image/png")},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 200, r.text

        img_r = client.get(f"/img/maquina/{maquina.id}")
        assert img_r.status_code == 200
        assert img_r.headers["content-type"] == "image/webp"

    def test_valid_jpeg_accepted_and_served_back_as_webp(self, client, login_as, db):
        maquina = make_machine(db, origen="docker")
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(
            UPLOAD_LOGO_URL,
            data={"machine_id": str(maquina.id), "origen": maquina.origen},
            files={"logo": ("logo.jpg", _jpeg_bytes(), "image/jpeg")},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 200, r.text

        img_r = client.get(f"/img/maquina/{maquina.id}")
        assert img_r.status_code == 200
        assert img_r.headers["content-type"] == "image/webp"

    def test_old_logo_file_removed_when_new_one_uploaded(self, client, login_as, db, monkeypatch):
        import os

        import dockerlabs.routes.maquinas_api as maquinas_api_mod
        from dockerlabs.models import Machine
        from dockerlabs.routers import BASE_DIR

        # El nombre de fichero final incluye un timestamp a resolución de
        # segundo (`int(time.time())`); si las dos subidas de este test
        # cayeran en el mismo segundo real, generarían el MISMO nombre de
        # fichero y el test no probaría nada. Se fuerza una secuencia de
        # timestamps crecientes para que sea determinista.
        counter = itertools.count(1_700_000_000)
        monkeypatch.setattr(maquinas_api_mod.time, "time", lambda: next(counter))

        maquina = make_machine(db, origen="docker")
        admin = _admin(db)
        csrf = login_as(admin)

        r1 = client.post(
            UPLOAD_LOGO_URL,
            data={"machine_id": str(maquina.id), "origen": maquina.origen},
            files={"logo": ("a.png", _png_bytes(), "image/png")},
            headers=csrf_headers(csrf),
        )
        assert r1.status_code == 200, r1.text
        db.session.rollback()
        old_logo_path = Machine.query.get(maquina.id).logo_path
        assert old_logo_path
        old_abspath = os.path.join(BASE_DIR, old_logo_path)
        assert os.path.isfile(old_abspath)

        r2 = client.post(
            UPLOAD_LOGO_URL,
            data={"machine_id": str(maquina.id), "origen": maquina.origen},
            files={"logo": ("b.jpg", _jpeg_bytes(), "image/jpeg")},
            headers=csrf_headers(csrf),
        )
        assert r2.status_code == 200, r2.text
        db.session.rollback()
        new_logo_path = Machine.query.get(maquina.id).logo_path
        assert new_logo_path != old_logo_path
        assert not os.path.exists(old_abspath)
        assert os.path.isfile(os.path.join(BASE_DIR, new_logo_path))


class TestUploadLogoOwnership:
    def test_jugador_can_upload_for_own_machine(self, client, login_as, db):
        jugador = _jugador(db)
        maquina = make_machine(db, origen="docker", autor=jugador.username)
        csrf = login_as(jugador)
        r = client.post(
            UPLOAD_LOGO_URL,
            data={"machine_id": str(maquina.id), "origen": maquina.origen},
            files={"logo": ("logo.png", _png_bytes(), "image/png")},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 200, r.text

    def test_jugador_forbidden_for_others_machine(self, client, login_as, db):
        jugador = _jugador(db)
        maquina = make_machine(db, origen="docker", autor="OtroAutor")
        csrf = login_as(jugador)
        r = client.post(
            UPLOAD_LOGO_URL,
            data={"machine_id": str(maquina.id), "origen": maquina.origen},
            files={"logo": ("logo.png", _png_bytes(), "image/png")},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 403


class TestToggleGuestAccess:
    URL = "/api/gestion-maquinas/toggle-guest-access"

    def test_jugador_forbidden(self, client, login_as, db):
        jugador = _jugador(db)
        maquina = make_machine(db, guest_access=False)
        csrf = login_as(jugador)
        r = client.post(self.URL, data={"id": str(maquina.id)}, headers=csrf_headers(csrf))
        assert r.status_code == 403

    def test_admin_flips_guest_access_back_and_forth(self, client, login_as, db):
        maquina = make_machine(db, guest_access=False)
        admin = _admin(db)
        csrf = login_as(admin)

        r1 = client.post(self.URL, data={"id": str(maquina.id)}, headers=csrf_headers(csrf))
        assert r1.status_code == 200
        assert r1.json()["guest_access"] is True

        r2 = client.post(self.URL, data={"id": str(maquina.id)}, headers=csrf_headers(csrf))
        assert r2.status_code == 200
        assert r2.json()["guest_access"] is False

    def test_moderador_can_toggle(self, client, login_as, db):
        maquina = make_machine(db, guest_access=False)
        mod = _mod(db)
        csrf = login_as(mod)
        r = client.post(self.URL, data={"id": str(maquina.id)}, headers=csrf_headers(csrf))
        assert r.status_code == 200
        assert r.json()["guest_access"] is True


class TestMachineStats:
    def _url(self, machine_id):
        return f"/api/gestion-maquinas/machine-stats/{machine_id}"

    def test_jugador_forbidden_for_others_machine(self, client, login_as, db):
        jugador = _jugador(db)
        maquina = make_machine(db, autor="OtroAutor")
        csrf = login_as(jugador)
        r = client.get(self._url(maquina.id), headers=csrf_headers(csrf))
        assert r.status_code == 403

    def test_jugador_can_see_own_machine_stats(self, client, login_as, db):
        jugador = _jugador(db)
        maquina = make_machine(db, autor=jugador.username)
        csrf = login_as(jugador)
        r = client.get(self._url(maquina.id), headers=csrf_headers(csrf))
        assert r.status_code == 200

    def test_rating_average_matches_manual_computation(self, client, login_as, db):
        maquina = make_machine(db)
        u1 = make_user(db, role="jugador")
        u2 = make_user(db, role="jugador")
        make_rating(
            db, usuario_id=u1.id, maquina_nombre=maquina.nombre,
            dificultad_score=5, aprendizaje_score=4, recomendaria_score=3, diversion_score=2,
        )
        make_rating(
            db, usuario_id=u2.id, maquina_nombre=maquina.nombre,
            dificultad_score=1, aprendizaje_score=2, recomendaria_score=3, diversion_score=4,
        )
        # avg por criterio: dificultad=3, aprendizaje=3, recomendaria=3, diversion=3
        # rating_avg = round((3+3+3+3)/4, 1) = 3.0
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.get(self._url(maquina.id), headers=csrf_headers(csrf))
        assert r.status_code == 200
        body = r.json()
        assert body["rating_count"] == 2
        assert body["rating_avg"] == 3.0


class TestRateMachine:
    URL = "/api/rate_machine"

    def _payload(self, maquina_nombre, score):
        return {
            "maquina_nombre": maquina_nombre,
            "dificultad_score": score,
            "aprendizaje_score": score,
            "recomendaria_score": score,
            "diversion_score": score,
        }

    @pytest.mark.parametrize("score", [1, 5])
    def test_boundary_scores_accepted(self, client, login_as, db, score):
        maquina = make_machine(db)
        user = _jugador(db)
        login_as(user)
        r = client.post(self.URL, json=self._payload(maquina.nombre, score))
        assert r.status_code == 200, r.text

    @pytest.mark.parametrize("score", [0, 6])
    def test_out_of_range_scores_rejected(self, client, login_as, db, score):
        maquina = make_machine(db)
        user = _jugador(db)
        login_as(user)
        r = client.post(self.URL, json=self._payload(maquina.nombre, score))
        assert r.status_code == 400

    def test_second_rating_updates_instead_of_duplicating(self, client, login_as, db):
        from dockerlabs.models import Rating

        maquina = make_machine(db)
        user = _jugador(db)
        login_as(user)

        r1 = client.post(self.URL, json=self._payload(maquina.nombre, 2))
        assert r1.status_code == 200
        r2 = client.post(self.URL, json=self._payload(maquina.nombre, 5))
        assert r2.status_code == 200

        db.session.rollback()
        rows = Rating.query.filter_by(usuario_id=user.id, maquina_nombre=maquina.nombre).all()
        assert len(rows) == 1
        assert rows[0].dificultad_score == 5
        assert rows[0].diversion_score == 5


class TestGetMachineRating:
    def test_public_average_across_four_dimensions(self, client, db):
        maquina = make_machine(db)
        u1 = make_user(db, role="jugador")
        make_rating(
            db, usuario_id=u1.id, maquina_nombre=maquina.nombre,
            dificultad_score=4, aprendizaje_score=4, recomendaria_score=4, diversion_score=4,
        )
        r = client.get(f"/api/get_machine_rating/{maquina.nombre}")
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 1
        assert body["average"] == 4.0
        assert body["details"]["dificultad"] == 4.0
        assert body["user_rating"] is None  # anónimo: sin valoración propia

    def test_includes_caller_own_rating_when_logged_in(self, client, login_as, db):
        maquina = make_machine(db)
        user = _jugador(db)
        make_rating(
            db, usuario_id=user.id, maquina_nombre=maquina.nombre,
            dificultad_score=3, aprendizaje_score=3, recomendaria_score=3, diversion_score=3,
        )
        login_as(user)
        r = client.get(f"/api/get_machine_rating/{maquina.nombre}")
        assert r.status_code == 200
        assert r.json()["user_rating"] == {
            "dificultad": 3, "aprendizaje": 3, "recomendaria": 3, "diversion": 3,
        }


class TestCompletedMachines:
    def test_get_completed_requires_login(self, client, db):
        maquina = make_machine(db)
        r = client.get(f"/api/completed_machines/{maquina.nombre}")
        assert r.status_code == 401

    def test_toggle_semantics_create_delete_recreate(self, client, login_as, db):
        # A diferencia de /api/rate_machine (sin CSRF), este endpoint SÍ
        # declara `csrf_ok: bool = Depends(verify_csrf_token)`.
        maquina = make_machine(db)
        user = _jugador(db)
        csrf = login_as(user)
        headers = csrf_headers(csrf)

        r1 = client.post("/api/toggle_completed_machine", json={"machine_name": maquina.nombre}, headers=headers)
        assert r1.status_code == 200
        assert r1.json()["completed"] is True
        g1 = client.get(f"/api/completed_machines/{maquina.nombre}")
        assert g1.json()["completed"] is True

        r2 = client.post("/api/toggle_completed_machine", json={"machine_name": maquina.nombre}, headers=headers)
        assert r2.status_code == 200
        assert r2.json()["completed"] is False
        g2 = client.get(f"/api/completed_machines/{maquina.nombre}")
        assert g2.json()["completed"] is False

        r3 = client.post("/api/toggle_completed_machine", json={"machine_name": maquina.nombre}, headers=headers)
        assert r3.status_code == 200
        assert r3.json()["completed"] is True
        g3 = client.get(f"/api/completed_machines/{maquina.nombre}")
        assert g3.json()["completed"] is True

    def test_rejects_machine_not_in_catalog(self, client, login_as, db):
        user = _jugador(db)
        csrf = login_as(user)
        r = client.post(
            "/api/toggle_completed_machine",
            json={"machine_name": "NoExisteDeVerdad404"},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 400
