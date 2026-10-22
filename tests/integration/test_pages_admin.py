"""Tests de dockerlabs/routes/pages_admin.py: control de acceso y corrección
básica de las páginas HTML del panel de administración.

La lógica pura de bucketing (estadísticas, rangos de fecha...) la cubre
tests/unit/test_pages_admin_helpers.py; aquí solo se humo-testean las rutas:
control de acceso por rol, paginación, búsqueda y que no revienten con
parámetros raros.
"""
import pytest

from tests.factories import make_machine, make_user

pytestmark = pytest.mark.integration


class TestGestionUsuarios:
    @pytest.mark.parametrize("role", ["admin", "moderador"])
    def test_allowed_roles_can_access(self, client, login_as, db, role):
        user = make_user(db, role=role)
        login_as(user)
        r = client.get("/gestion-usuarios")
        assert r.status_code == 200

    def test_jugador_is_redirected_away(self, client, login_as, db):
        # require_auth_and_role devuelve un 302 a "/" para rol no permitido
        # (no un 403): así lo hace routers.require_auth_and_role.
        user = make_user(db, role="jugador")
        login_as(user)
        r = client.get("/gestion-usuarios", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/"

    def test_logged_out_redirects_to_login(self, client):
        r = client.get("/gestion-usuarios", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/login"

    def test_pagination_params_work(self, client, login_as, db):
        admin = make_user(db, role="admin")
        login_as(admin)
        for _ in range(3):
            make_user(db, role="jugador")
        r = client.get("/gestion-usuarios?page=1&per_page=20")
        assert r.status_code == 200

    def test_non_numeric_page_param_crashes_with_500(self, client, login_as, db):
        """HALLAZGO REAL: `page = int(request.query_params.get("page", 1))` no
        atrapa el ValueError de un valor no numérico: sube sin manejar y un
        cliente real recibiría un 500. Se documenta tal cual se comporta hoy,
        sin tocar el source. El `client` fixture normal no sirve para
        comprobar el status code: por defecto RELANZA en el proceso de test
        cualquier excepción no controlada del servidor (raise_server_exceptions,
        pensado para depuración), así que aquí se usa un TestClient aparte con
        esa opción desactivada (comportamiento del test client, no de la app)
        para poder ver el 500 real en vez de un ValueError en pytest."""
        from fastapi.testclient import TestClient
        import asgi

        admin = make_user(db, role="admin")
        login_as(admin)

        with TestClient(asgi.app, raise_server_exceptions=False, cookies=client.cookies) as c:
            r = c.get("/gestion-usuarios?page=abc")
        assert r.status_code == 500

    def test_search_filters_by_username(self, client, login_as, db):
        admin = make_user(db, role="admin")
        login_as(admin)
        target = make_user(db, role="jugador", username="buscameaqui")
        make_user(db, role="jugador", username="otrodistinto")

        r = client.get("/gestion-usuarios?search=buscameaqui")
        assert r.status_code == 200
        assert target.username in r.text
        assert "otrodistinto" not in r.text

    def test_search_filters_by_email(self, client, login_as, db):
        admin = make_user(db, role="admin")
        login_as(admin)
        target = make_user(db, role="jugador", email="matchable-email@example.test")

        r = client.get("/gestion-usuarios?search=matchable-email")
        assert r.status_code == 200
        assert target.username in r.text

    def test_search_filters_by_role(self, client, login_as, db):
        admin = make_user(db, role="admin")
        login_as(admin)
        mod = make_user(db, role="moderador")
        jugador = make_user(db, role="jugador")

        r = client.get("/gestion-usuarios?search=moderador")
        assert r.status_code == 200
        assert mod.username in r.text
        assert jugador.username not in r.text


class TestGestionMaquinas:
    @pytest.mark.parametrize("role", ["admin", "moderador", "jugador"])
    def test_allowed_roles_can_access(self, client, login_as, db, role):
        user = make_user(db, role=role)
        login_as(user)
        r = client.get("/gestion-maquinas")
        assert r.status_code == 200

    def test_logged_out_redirects_to_login(self, client):
        r = client.get("/gestion-maquinas", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/login"

    def test_jugador_sees_only_own_machines(self, client, login_as, db):
        author_a = make_user(db, role="jugador", username="autor_a")
        make_user(db, role="jugador", username="autor_b")

        m_mine = make_machine(db, nombre="MaquinaDeA", autor="autor_a")
        m_other = make_machine(db, nombre="MaquinaDeB", autor="autor_b")

        login_as(author_a)
        r = client.get("/gestion-maquinas")
        assert r.status_code == 200
        assert m_mine.nombre in r.text
        assert m_other.nombre not in r.text

    @pytest.mark.parametrize("role", ["admin", "moderador"])
    def test_admin_and_moderador_see_all_authors_machines(self, client, login_as, db, role):
        make_user(db, role="jugador", username="autor_a")
        make_user(db, role="jugador", username="autor_b")
        m_a = make_machine(db, nombre="MaquinaDeA2", autor="autor_a")
        m_b = make_machine(db, nombre="MaquinaDeB2", autor="autor_b")

        staff = make_user(db, role=role)
        login_as(staff)
        r = client.get("/gestion-maquinas")
        assert r.status_code == 200
        assert m_a.nombre in r.text
        assert m_b.nombre in r.text

    def test_search_filters_across_nombre_autor_dificultad(self, client, login_as, db):
        admin = make_user(db, role="admin")
        login_as(admin)
        target = make_machine(db, nombre="BuscablePorNombre", autor="AutorX", dificultad="Difícil")
        make_machine(db, nombre="OtraMaquina", autor="AutorY", dificultad="Fácil")

        r = client.get("/gestion-maquinas?search=BuscablePorNombre")
        assert r.status_code == 200
        assert target.nombre in r.text

        r2 = client.get("/gestion-maquinas?search=Dif%C3%ADcil")
        assert r2.status_code == 200
        assert target.nombre in r2.text


class TestPendingMachines:
    @pytest.mark.parametrize("role", ["admin", "moderador"])
    def test_allowed_roles_can_access(self, client, login_as, db, role):
        user = make_user(db, role=role)
        login_as(user)
        r = client.get("/pending-machines")
        assert r.status_code == 200

    def test_jugador_is_redirected_away(self, client, login_as, db):
        user = make_user(db, role="jugador")
        login_as(user)
        r = client.get("/pending-machines", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/"


class TestUserPending:
    @pytest.mark.parametrize("role", ["admin", "moderador", "jugador"])
    def test_any_logged_in_role_can_access(self, client, login_as, db, role):
        user = make_user(db, role=role)
        login_as(user)
        r = client.get("/user-pending")
        assert r.status_code == 200

    def test_logged_out_redirects_to_login(self, client):
        r = client.get("/user-pending", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/login"


class TestWriteupsRoutes:
    def test_writeups_analisis_admin_moderador_only(self, client, login_as, db):
        for role in ("admin", "moderador"):
            user = make_user(db, role=role)
            login_as(user)
            r = client.get("/writeups-analisis")
            assert r.status_code == 200

        jugador = make_user(db, role="jugador")
        login_as(jugador)
        r = client.get("/writeups-analisis", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/"

    @pytest.mark.parametrize("role", ["admin", "moderador", "jugador"])
    def test_writeups_recibidos_allows_all_three_roles(self, client, login_as, db, role):
        user = make_user(db, role=role)
        login_as(user)
        r = client.get("/writeups-recibidos")
        assert r.status_code == 200

    @pytest.mark.parametrize("role", ["admin", "moderador", "jugador"])
    def test_writeups_publicados_allows_all_three_roles(self, client, login_as, db, role):
        user = make_user(db, role=role)
        login_as(user)
        r = client.get("/writeups-publicados")
        assert r.status_code == 200


class TestEstadisticas:
    @pytest.mark.parametrize("role", ["admin", "moderador"])
    def test_allowed_roles_can_access(self, client, login_as, db, role):
        user = make_user(db, role=role)
        login_as(user)
        r = client.get("/estadisticas")
        assert r.status_code == 200

    def test_jugador_is_redirected_away(self, client, login_as, db):
        user = make_user(db, role="jugador")
        login_as(user)
        r = client.get("/estadisticas", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/"

    @pytest.mark.parametrize("qs", [
        "rango=hoy",
        "rango=mes",
        "rango=personalizado&desde=2026-01-01&hasta=2026-01-31",
        "rango=todo",
        "rango=no-existe",  # cae al default ("mes") en _resolve_range
        "rango=personalizado",  # sin desde/hasta: también cae al default
    ])
    def test_representative_query_params_do_not_crash(self, client, login_as, db, qs):
        admin = make_user(db, role="admin")
        login_as(admin)
        r = client.get(f"/estadisticas?{qs}")
        assert r.status_code == 200


class TestPublicStaticPages:
    @pytest.mark.parametrize("path", [
        "/instrucciones-uso",
        "/soporte",
        "/equipo",
        "/terminos-condiciones",
    ])
    def test_public_pages_do_not_require_auth(self, client, path):
        r = client.get(path)
        assert r.status_code == 200


class TestBugBounty:
    def test_bug_bounty_is_a_dead_redirect_to_home(self, client):
        r = client.get("/bug-bounty", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/"
