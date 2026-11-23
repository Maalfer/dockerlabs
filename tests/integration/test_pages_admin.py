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

    def test_non_numeric_page_param_falls_back_to_first_page(self, client, login_as, db):
        # Antes: int("abc") sin atrapar → 500. Ahora se ignora y se sirve la página 1.
        login_as(make_user(db, role="admin"))
        assert client.get("/gestion-usuarios?page=abc&per_page=xyz").status_code == 200

    def test_orders_and_filters(self, client, login_as, db):
        from datetime import timedelta
        from dockerlabs.tiempo import utcnow
        admin = make_user(db, role="admin", username="zz-admin")
        viejo = make_user(db, role="jugador", username="aa-veterano")
        viejo.created_at = utcnow() - timedelta(days=400)
        viejo.last_seen_at = utcnow() - timedelta(days=200)
        db.session.commit()
        login_as(admin)

        html = client.get("/gestion-usuarios?orden=antiguos").text
        assert html.index("aa-veterano") < html.index("zz-admin")
        html = client.get("/gestion-usuarios?orden=recientes").text
        assert html.index("zz-admin") < html.index("aa-veterano")
        # nombres y correos a la vista, sin censura
        assert "user-censored" not in html and "•••" not in html
        assert "aa-veterano" not in client.get("/gestion-usuarios?registro=30").text
        assert "aa-veterano" not in client.get("/gestion-usuarios?acceso=30").text
        assert "aa-veterano" in client.get("/gestion-usuarios?rol=jugador&orden=inactivos").text
        assert client.get("/gestion-usuarios?orden=loquesea&rol=x&acceso=y&registro=z").status_code == 200

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

    def test_bunker_tab_lists_only_bunker_machines(self, client, login_as, db):
        admin = make_user(db, role="admin")
        login_as(admin)
        d = make_machine(db, nombre="SoloEnDocker", origen="docker")
        b = make_machine(db, nombre="SoloEnBunker", origen="bunker")

        docker = client.get("/gestion-maquinas")
        assert d.nombre in docker.text and b.nombre not in docker.text
        bunker = client.get("/gestion-maquinas?plataforma=bunker")
        assert b.nombre in bunker.text and d.nombre not in bunker.text

    def test_dificultad_filter(self, client, login_as, db):
        login_as(make_user(db, role="admin"))
        facil = make_machine(db, nombre="FiltroFacil", dificultad="Fácil")
        dificil = make_machine(db, nombre="FiltroDificil", dificultad="Difícil")
        r = client.get("/gestion-maquinas?dificultad=Difícil")
        assert dificil.nombre in r.text and facil.nombre not in r.text

    def test_invalid_params_are_sanitized(self, client, login_as, db):
        login_as(make_user(db, role="admin"))
        make_machine(db, nombre="ParamsRaros")
        r = client.get("/gestion-maquinas?page=-5&per_page=100000&plataforma=hack&dificultad=zzz")
        assert r.status_code == 200
        assert "ParamsRaros" in r.text

    def test_search_wildcards_are_literal(self, client, login_as, db):
        login_as(make_user(db, role="admin"))
        make_machine(db, nombre="Alpha")
        r = client.get("/gestion-maquinas?search=%25")      # «%» no debe comportarse como comodín
        assert r.status_code == 200
        assert "Alpha" not in r.text

    def test_delete_button_only_for_staff(self, client, login_as, db):
        autor = make_user(db, role="jugador", username="autor_btn")
        make_machine(db, nombre="MiMaquinaBtn", autor="autor_btn")
        login_as(autor)
        assert 'data-accion="eliminar"' not in client.get("/gestion-maquinas").text
        login_as(make_user(db, role="admin"))
        assert 'data-accion="eliminar"' in client.get("/gestion-maquinas").text

    def test_pagination_links_keep_filters_urlencoded(self, client, login_as, db):
        login_as(make_user(db, role="admin"))
        for i in range(25):
            make_machine(db, nombre=f"Pag{i:02d}&co", autor="Ana")
        r = client.get("/gestion-maquinas?search=Pag&per_page=10")
        assert 'aria-label="Paginación del listado"' in r.text
        assert "search=Pag" in r.text and "per_page=10" in r.text
        assert "page=2" in r.text

    def test_page_has_main_landmark_and_labelled_controls(self, client, login_as, db):
        login_as(make_user(db, role="admin"))
        make_machine(db, nombre="Etiquetada")
        html = client.get("/gestion-maquinas").text
        assert "<main" in html
        assert 'aria-label="Dificultad de Etiquetada"' in html
        assert 'alt="Logo de Etiquetada"' in html or 'aria-label="Sin logo"' in html


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

    def test_queue_shows_only_pending_and_archive_has_the_rest(self, client, login_as, db):
        from tests.factories import make_pending_machine_submission
        login_as(make_user(db, role="admin"))
        make_pending_machine_submission(db, nombre="EnCola")
        make_pending_machine_submission(db, nombre="YaAnadida", estado="aprobado")
        cola = client.get("/pending-machines").text
        assert "EnCola" in cola and "YaAnadida" not in cola
        archivo = client.get("/pending-machines?estado=aprobado").text
        assert "YaAnadida" in archivo and "EnCola" not in archivo

    def test_pagination_and_search(self, client, login_as, db):
        from tests.factories import make_pending_machine_submission
        login_as(make_user(db, role="moderador"))
        for i in range(13):
            make_pending_machine_submission(db, nombre=f"Maq{i:02d}")

        def tarjetas(url):
            return client.get(url).text.count('data-accion="eliminar"')

        html = client.get("/pending-machines").text
        assert html.count('data-accion="eliminar"') == 12
        assert 'rel="next"' in html
        assert tarjetas("/pending-machines?page=2") == 1
        assert client.get("/pending-machines?page=abc").status_code == 200
        assert tarjetas("/pending-machines?q=Maq07") == 1


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


class TestPaginaRetirada:
    def test_instrucciones_uso_redirige_al_inicio(self, client):
        r = client.get("/instrucciones-uso", follow_redirects=False)
        assert r.status_code == 301
        assert r.headers["location"] == "/"


class TestPublicStaticPages:
    @pytest.mark.parametrize("path", [
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
