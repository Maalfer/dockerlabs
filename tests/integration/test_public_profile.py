"""Tests de dockerlabs/routes/public_profile.py — API pública de perfil.

`GET /u/<slug>` y `GET /perfil/<slug>` no necesitan sesión; ambas respetan
`User.perfil_publico` (en privado, 404 idéntico al de un slug inexistente, sin
filtrar si la cuenta existe). `POST /api/perfil/visibilidad` sí exige sesión +
CSRF.
"""
import pytest

from tests.factories import make_completed_machine, make_machine, make_user, make_writeup

pytestmark = pytest.mark.integration


def _make_ranking(db, nombre, puntos):
    """Helper local (no toca conftest/factories): no hay factory para
    WriteupRanking en tests/factories.py, así que se crea la fila a mano."""
    from dockerlabs.models import WriteupRanking

    row = WriteupRanking(nombre=nombre, puntos=puntos)
    db.session.add(row)
    db.session.commit()
    return row


# ---------------------------------------------------------------------------
# GET /u/{slug} — JSON público
# ---------------------------------------------------------------------------


class TestPublicProfileJson:
    def test_slug_resolves(self, client, db):
        user = make_user(db, username="perfilslug1")
        assert user.slug  # auto-asignado por register_slug_events

        r = client.get(f"/u/{user.slug}")
        assert r.status_code == 200
        assert r.json()["username"] == "perfilslug1"
        assert r.json()["slug"] == user.slug

    def test_literal_username_also_resolves_as_alias(self, client, db):
        user = make_user(db, username="perfilslug2")
        # Forzar que el slug difiera del username, para probar que el
        # username literal funciona como alias aunque no coincida con el slug.
        user.slug = "otro-slug-bien-distinto"
        db.session.commit()

        r = client.get(f"/u/{user.username}")
        assert r.status_code == 200
        assert r.json()["username"] == "perfilslug2"

    def test_private_profile_returns_404(self, client, db):
        user = make_user(db, username="perfilprivado1", perfil_publico=False)
        r = client.get(f"/u/{user.slug}")
        assert r.status_code == 404

    def test_private_profile_404_matches_nonexistent_404(self, client, db):
        """El 404 de un perfil en privado debe ser indistinguible del de un
        slug que no existe en absoluto: no se puede filtrar si la cuenta
        existe o no solo por la respuesta."""
        user = make_user(db, username="perfilprivado2", perfil_publico=False)

        r_private = client.get(f"/u/{user.slug}")
        r_missing = client.get("/u/este-slug-no-existe-nunca-jamas")

        assert r_private.status_code == r_missing.status_code == 404
        assert r_private.json()["error"] == r_missing.json()["error"] == "Perfil no encontrado"
        assert set(r_private.json().keys()) == set(r_missing.json().keys())


# ---------------------------------------------------------------------------
# Exclusión de BunkerLabs del perfil público
# ---------------------------------------------------------------------------


class TestBunkerExclusion:
    def test_bunker_machine_hides_fields_and_excluded_from_progress(self, client, db):
        user = make_user(db, username="bunkeruser1")
        make_machine(db, origen="docker", nombre="DockerDone1", clase="facil")
        make_machine(
            db, origen="bunker", nombre="BunkerDone1", clase="facil",
            descripcion="secreto-bunker", link_descarga="https://secreto.test/x.zip",
        )
        make_completed_machine(db, user_id=user.id, machine_name="DockerDone1")
        make_completed_machine(db, user_id=user.id, machine_name="BunkerDone1")

        r = client.get(f"/u/{user.slug}")
        assert r.status_code == 200
        body = r.json()

        hechas = {m["nombre"]: m for m in body["maquinas_hechas"]}
        assert "BunkerDone1" in hechas
        bunker_item = hechas["BunkerDone1"]
        # Solo se expone nombre+dificultad+logo (CLAUDE.md); nunca descripción
        # ni enlace de descarga.
        assert bunker_item["dificultad"] == "Fácil"
        assert "descripcion" not in bunker_item
        assert "descarga" not in bunker_item

        docker_item = hechas["DockerDone1"]
        assert docker_item["descripcion"] == "Descripción de prueba"
        assert docker_item["descarga"] == "https://example.test/machine.zip"

        # El denominador del progreso es solo el catálogo docker: con una
        # única máquina docker (resuelta) en el catálogo, debe ser 100%,
        # ignorando la máquina bunker también "hecha".
        assert body["progreso"]["maquinas_totales"] == 1
        assert body["progreso"]["maquinas_hechas"] == 1
        assert body["progreso"]["porcentaje"] == 100.0

    def test_bunker_writeup_not_listed_publicly(self, client, db):
        user = make_user(db, username="bunkeruser2")
        make_machine(db, origen="bunker", nombre="BunkerWriteupPub1")
        make_writeup(db, maquina="BunkerWriteupPub1", autor="bunkeruser2")

        r = client.get(f"/u/{user.slug}")
        assert r.status_code == 200
        nombres = {w["maquina"] for w in r.json()["writeups"]}
        assert "BunkerWriteupPub1" not in nombres


# ---------------------------------------------------------------------------
# Desglose por dificultad: agrupa por Machine.clase, no por Machine.dificultad
# ---------------------------------------------------------------------------


class TestDifficultyBreakdownGroupsByClase:
    def test_groups_by_clase_not_by_unnormalized_dificultad(self, client, db):
        user = make_user(db, username="clasetest1")
        make_machine(db, origen="docker", nombre="ClaseM1", clase="facil", dificultad="Fácil")
        make_machine(db, origen="docker", nombre="ClaseM2", clase="facil", dificultad="Facil")
        make_completed_machine(db, user_id=user.id, machine_name="ClaseM1")
        make_completed_machine(db, user_id=user.id, machine_name="ClaseM2")

        r = client.get(f"/u/{user.slug}")
        body = r.json()
        por_dificultad = body["progreso"]["por_dificultad"]

        assert por_dificultad["Fácil"]["hechas"] == 2
        assert por_dificultad["Fácil"]["totales"] == 2
        # Las dos variantes sin normalizar de "dificultad" caen en el MISMO
        # bucket (el de "clase"); no hay un bucket separado para "Facil".
        buckets_similares = [k for k in por_dificultad if k.lower().startswith("f")]
        assert buckets_similares == ["Fácil"]


# ---------------------------------------------------------------------------
# Posición en el ranking de writeups
# ---------------------------------------------------------------------------


class TestRankingPosition:
    def test_three_distinct_scores_get_positions_1_2_3(self, client, db):
        u1 = make_user(db, username="rank1")
        u2 = make_user(db, username="rank2")
        u3 = make_user(db, username="rank3")
        _make_ranking(db, "rank1", 300)
        _make_ranking(db, "rank2", 200)
        _make_ranking(db, "rank3", 100)

        assert client.get(f"/u/{u1.slug}").json()["estadisticas"]["ranking_writeups"] == 1
        assert client.get(f"/u/{u2.slug}").json()["estadisticas"]["ranking_writeups"] == 2
        assert client.get(f"/u/{u3.slug}").json()["estadisticas"]["ranking_writeups"] == 3

    def test_tied_scores_get_the_same_rank(self, client, db):
        """`_ranking_position()` cuenta cuántos tienen MÁS puntos y suma 1:
        con un empate, ninguno de los dos tiene más puntos que el otro, así
        que ambos caen en la posición 1 (ranking "de competición", sin huecos
        ni posiciones 1 y 2 repartidas arbitrariamente)."""
        u1 = make_user(db, username="tie1")
        u2 = make_user(db, username="tie2")
        _make_ranking(db, "tie1", 150)
        _make_ranking(db, "tie2", 150)

        assert client.get(f"/u/{u1.slug}").json()["estadisticas"]["ranking_writeups"] == 1
        assert client.get(f"/u/{u2.slug}").json()["estadisticas"]["ranking_writeups"] == 1

    def test_user_without_ranking_row_has_null_position(self, client, db):
        user = make_user(db, username="sinranking1")
        body = client.get(f"/u/{user.slug}").json()
        assert body["estadisticas"]["ranking_writeups"] is None


# ---------------------------------------------------------------------------
# GET /perfil/{slug} — variante HTML, mismas reglas de privacidad
# ---------------------------------------------------------------------------


class TestPerfilHtmlVariant:
    def test_public_profile_renders_200(self, client, db):
        user = make_user(db, username="htmlperfil1")
        r = client.get(f"/perfil/{user.slug}")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_private_profile_404(self, client, db):
        user = make_user(db, username="htmlperfil2", perfil_publico=False)
        r = client.get(f"/perfil/{user.slug}")
        assert r.status_code == 404

    def test_nonexistent_slug_404(self, client):
        r = client.get("/perfil/no-existe-este-slug-tampoco")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/perfil/visibilidad
# ---------------------------------------------------------------------------


class TestVisibilidadToggle:
    def test_requires_login(self, client):
        r = client.post("/api/perfil/visibilidad", json={"publico": False})
        assert r.status_code == 401

    def test_requires_csrf(self, client, login_as, db):
        user = make_user(db, username="vistoggle1")
        login_as(user)  # cookie puesta, sin header CSRF

        r = client.post("/api/perfil/visibilidad", json={"publico": False})
        assert r.status_code == 403

    def test_toggle_off_then_on_changes_u_endpoint_behavior(self, client, login_as, db):
        user = make_user(db, username="vistoggle2")
        csrf = login_as(user)

        r_off = client.post(
            "/api/perfil/visibilidad", json={"publico": False}, headers={"X-CSRFToken": csrf},
        )
        assert r_off.status_code == 200
        assert r_off.json()["publico"] is False

        r_check_off = client.get(f"/u/{user.slug}")
        assert r_check_off.status_code == 404

        r_on = client.post(
            "/api/perfil/visibilidad", json={"publico": True}, headers={"X-CSRFToken": csrf},
        )
        assert r_on.status_code == 200
        assert r_on.json()["publico"] is True

        r_check_on = client.get(f"/u/{user.slug}")
        assert r_check_on.status_code == 200
