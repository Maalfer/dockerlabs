"""Tests de dockerlabs/routes/api_publica.py — API pública: versión, resumen,
rankings y envío de máquinas.

NOTA sobre homónimos (oscar/Oscar): se comprobó empíricamente contra esta
misma BD de test que `User.username` tiene restricción UNIQUE case-insensitive
a nivel de columna/collation (crear "oscar" y luego "Oscar" lanza
IntegrityError). Es decir, esta BD BLOQUEA los homónimos por completo: nunca
se puede llegar al escenario de desempate que resuelve
`resolver_usuarios_por_nombre()` (exacto > id más bajo) porque dos cuentas así
no pueden coexistir. Por eso aquí solo se prueba la resolución normal de un
único usuario por ranking, y se deja esta nota para quien revise el
desempate con una collation distinta (p.ej. utf8mb4_bin) en otro entorno.
"""
import re

import pytest

from tests.factories import make_machine, make_user, make_writeup

pytestmark = pytest.mark.integration


class TestVersion:
    def test_public_no_auth_required(self, client):
        r = client.get("/api/version")
        assert r.status_code == 200

    def test_matches_version_file_and_semver_shape(self, client):
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        expected = (repo_root / "VERSION").read_text(encoding="utf-8").strip()

        r = client.get("/api/version")
        body = r.json()
        assert body["version"] == expected
        assert re.match(r"^\d+\.\d+\.\d+", body["version"])

    def test_has_cache_control_header(self, client):
        r = client.get("/api/version")
        assert r.headers.get("cache-control") == "public, max-age=60"


class TestApiSummary:
    def test_public_no_auth_required(self, client):
        r = client.get("/api")
        assert r.status_code == 200

    def test_aggregated_counts_match_seeded_data(self, client, db):
        autor = make_user(db, username="autor_summary")
        m1 = make_machine(db, nombre="SummaryMachine1", autor=autor.username)
        make_machine(db, nombre="SummaryMachine2", autor=autor.username)
        # Una máquina 'bunker' no debe contar en el resumen público (filtra origen='docker').
        make_machine(db, nombre="SummaryBunkerMachine", origen="bunker", autor=autor.username)
        make_writeup(db, maquina=m1.nombre, autor=autor.username)

        r = client.get("/api")
        body = r.json()

        nombres = set(body["maquinas"])
        assert "SummaryMachine1" in nombres
        assert "SummaryMachine2" in nombres
        assert "SummaryBunkerMachine" not in nombres

        assert body["metadata"]["total_writeups"] >= 1
        assert len(body["writeups"]["textos"]) + len(body["writeups"]["videos"]) == body["metadata"]["total_writeups"]


class TestRankingAutores:
    def test_public_no_auth_required(self, client):
        r = client.get("/api/ranking_autores")
        assert r.status_code == 200

    def test_single_user_resolves_to_their_profile_image(self, client, db):
        from dockerlabs.models import CreatorRanking

        user = make_user(db, username="autorrankuser")
        row = CreatorRanking(nombre=user.username, maquinas=3)
        db.session.add(row)
        db.session.commit()

        r = client.get("/api/ranking_autores")
        body = r.json()
        entry = next(e for e in body if e["nombre"] == user.username)
        assert entry["imagen"] == f"/img/perfil/{user.id}"
        assert entry["maquinas"] == 3

    def test_ranking_entry_with_no_matching_user_falls_back_to_default_image(self, client, db):
        from dockerlabs.models import CreatorRanking

        row = CreatorRanking(nombre="nadie_registrado_xyz", maquinas=1)
        db.session.add(row)
        db.session.commit()

        r = client.get("/api/ranking_autores")
        body = r.json()
        entry = next(e for e in body if e["nombre"] == "nadie_registrado_xyz")
        assert entry["imagen"] == "/static/dockerlabs/images/balu.webp"


class TestRankingWriteups:
    def test_public_no_auth_required(self, client):
        r = client.get("/api/ranking_writeups")
        assert r.status_code == 200

    def test_single_user_resolves_to_their_profile_image(self, client, db):
        from dockerlabs.models import WriteupRanking

        user = make_user(db, username="writeuprankuser")
        row = WriteupRanking(nombre=user.username, puntos=42)
        db.session.add(row)
        db.session.commit()

        r = client.get("/api/ranking_writeups")
        body = r.json()
        entry = next(e for e in body if e["nombre"] == user.username)
        assert entry["imagen_url"] == f"/img/perfil/{user.id}"
        assert entry["puntos"] == 42


class TestSubmitMachine:
    def test_requires_login(self, client):
        r = client.post(
            "/api/submit-machine",
            json={
                "nombre": "MiMaquina",
                "link_maquina": "https://example.test/m.zip",
                "dificultad": "Fácil",
                "discord_user": "autor#0001",
            },
        )
        assert r.status_code == 401

    def test_requires_csrf(self, client, login_as, db):
        user = make_user(db)
        login_as(user)  # cookie puesta, sin header CSRF
        r = client.post(
            "/api/submit-machine",
            json={
                "nombre": "MiMaquina",
                "link_maquina": "https://example.test/m.zip",
                "dificultad": "Fácil",
                "discord_user": "autor#0001",
            },
        )
        assert r.status_code == 403

    @pytest.mark.parametrize("bad_nombre", ["<script>", "a\"b", "a'b", "a`b", "a\\b"])
    def test_dangerous_chars_in_nombre_rejected(self, client, login_as, db, bad_nombre):
        user = make_user(db)
        csrf = login_as(user)
        r = client.post(
            "/api/submit-machine",
            json={
                "nombre": bad_nombre,
                "link_maquina": "https://example.test/m.zip",
                "dificultad": "Fácil",
                "discord_user": "autor#0001",
            },
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 400

    def test_control_char_in_nombre_rejected(self, client, login_as, db):
        user = make_user(db)
        csrf = login_as(user)
        r = client.post(
            "/api/submit-machine",
            json={
                "nombre": "mala\x01maquina",
                "link_maquina": "https://example.test/m.zip",
                "dificultad": "Fácil",
                "discord_user": "autor#0001",
            },
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 400

    def test_oversized_nombre_rejected(self, client, login_as, db):
        user = make_user(db)
        csrf = login_as(user)
        r = client.post(
            "/api/submit-machine",
            json={
                "nombre": "A" * 101,
                "link_maquina": "https://example.test/m.zip",
                "dificultad": "Fácil",
                "discord_user": "autor#0001",
            },
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 400

    def test_exactly_100_char_nombre_accepted(self, client, login_as, db):
        user = make_user(db)
        csrf = login_as(user)
        r = client.post(
            "/api/submit-machine",
            json={
                "nombre": "A" * 100,
                "link_maquina": "https://example.test/m.zip",
                "dificultad": "Fácil",
                "discord_user": "autor#0001",
            },
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 200

    @pytest.mark.parametrize("field", ["link_maquina", "writeup_url"])
    def test_dangerous_url_scheme_rejected(self, client, login_as, db, field):
        user = make_user(db)
        csrf = login_as(user)
        payload = {
            "nombre": "MaquinaOk",
            "link_maquina": "https://example.test/m.zip",
            "dificultad": "Fácil",
            "discord_user": "autor#0001",
            "writeup_url": "",
        }
        payload[field] = "javascript:alert(1)"
        r = client.post("/api/submit-machine", json=payload, headers={"X-CSRFToken": csrf})
        assert r.status_code == 400

    def test_valid_submission_creates_pending_with_estado_pendiente(self, client, login_as, db):
        from dockerlabs.models import PendingMachineSubmission

        user = make_user(db, username="submitter_ok")
        csrf = login_as(user)
        r = client.post(
            "/api/submit-machine",
            json={
                "nombre": "MaquinaValida",
                "link_maquina": "https://example.test/m.zip",
                "dificultad": "Fácil",
                "discord_user": "autor#0001",
                "writeup_url": "https://blog.test/writeup",
            },
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 200
        assert r.json()["success"] is True

        db.session.rollback()
        sub = PendingMachineSubmission.query.filter_by(nombre="MaquinaValida").first()
        assert sub is not None
        assert sub.estado == "pendiente"
        assert sub.autor_solicitante == "submitter_ok"
