"""Tests de dockerlabs/routes/seo.py: robots.txt, sitemap.xml y los estáticos
de primer nivel (favicon, service worker, manifest PWA)."""
import os
import xml.etree.ElementTree as ET

import pytest

from tests.factories import make_user, make_writeup

pytestmark = pytest.mark.integration


class TestRobots:
    def test_robots_txt_is_200_text(self, client):
        r = client.get("/robots.txt")
        assert r.status_code == 200
        assert "text/plain" in r.headers["content-type"]

    def test_robots_txt_disallows_private_routes(self, client):
        r = client.get("/robots.txt")
        # Subconjunto representativo de RUTAS_PRIVADAS (dockerlabs/routes/seo.py)
        for ruta in ("/api/", "/dashboard", "/gestion-usuarios", "/login", "/bunkerlabs"):
            assert f"Disallow: {ruta}" in r.text

    def test_robots_txt_references_sitemap(self, client):
        r = client.get("/robots.txt")
        assert "Sitemap: https://dockerlabs.es/sitemap.xml" in r.text


class TestSitemap:
    def test_sitemap_is_200_wellformed_xml(self, client):
        r = client.get("/sitemap.xml")
        assert r.status_code == 200
        root = ET.fromstring(r.text)  # lanza si no es XML válido
        assert root.tag.endswith("urlset")

    def test_sitemap_includes_static_pages(self, client):
        r = client.get("/sitemap.xml")
        assert "https://dockerlabs.es/" in r.text
        assert "https://dockerlabs.es/estadisticas" in r.text

    def test_sitemap_includes_profile_with_published_content(self, client, db):
        from dockerlabs.maquinas import recalcular_ranking_creadores
        from dockerlabs.writeups import recalcular_ranking_writeups
        from dockerlabs.models import Machine

        user = make_user(db, role="jugador", username="autorconwriteup")
        machine = Machine.query.first()
        if machine is None:
            from tests.factories import make_machine
            machine = make_machine(db, nombre="MaquinaParaWriteup")
        make_writeup(db, maquina=machine.nombre, autor=user.username)

        # _slugs_con_contenido() filtra por filas en CreatorRanking/WriteupRanking;
        # esos rankings los recalculan estas funciones (no se recalculan solos
        # al crear un Writeup directamente por factory).
        recalcular_ranking_creadores()
        recalcular_ranking_writeups()
        db.session.commit()

        r = client.get("/sitemap.xml")
        assert r.status_code == 200
        assert f"https://dockerlabs.es/perfil/{user.slug}" in r.text

    def test_sitemap_survives_db_error_in_profile_slug_loop(self, client, monkeypatch):
        """Ejercita el try/except+rollback alrededor de _slugs_con_contenido():
        un fallo en esa consulta no debe tumbar el sitemap completo, solo
        omitir el bloque de perfiles."""
        from dockerlabs.models import CreatorRanking

        class _BoomQuery:
            def __getattr__(self, _name):
                raise RuntimeError("fallo de BD simulado en CreatorRanking.query")

        monkeypatch.setattr(CreatorRanking, "query", _BoomQuery())

        r = client.get("/sitemap.xml")
        assert r.status_code == 200
        root = ET.fromstring(r.text)
        assert root.tag.endswith("urlset")
        assert "https://dockerlabs.es/estadisticas" in r.text  # páginas estáticas siguen presentes


class TestStaticRootFiles:
    _BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def test_favicon(self, client):
        path = os.path.join(self._BASE_DIR, "static", "dockerlabs", "images", "logos", "favicon.ico")
        r = client.get("/favicon.ico")
        assert r.status_code == (200 if os.path.isfile(path) else 404)

    def test_service_worker(self, client):
        path = os.path.join(self._BASE_DIR, "static", "dockerlabs", "pwa", "sw.js")
        r = client.get("/sw.js")
        assert r.status_code == (200 if os.path.isfile(path) else 404)

    def test_manifest(self, client):
        path = os.path.join(self._BASE_DIR, "static", "dockerlabs", "pwa", "manifest.webmanifest")
        r = client.get("/manifest.webmanifest")
        assert r.status_code == (200 if os.path.isfile(path) else 404)
