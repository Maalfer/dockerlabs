"""Tests puros de dockerlabs/routes/certificados.py: solo las funciones que
no necesitan una fila real de BD para decidir su resultado.

`author_matches_user()` y `machine_certificable()` SÍ hacen consultas
(`User.query`/`Machine.query`) y se cubren en
tests/integration/test_certificados_api.py (otro agente), no aquí.

El módulo importa `dockerlabs.extensions`/`dockerlabs.models`, que exigen
`DATABASE_URL` ya fijada — por eso el import vive en una fixture, igual que
en tests/factories.py.
"""
import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def certificados():
    from dockerlabs.routes import certificados
    return certificados


class TestSafeName:
    def test_strips_to_alnum_underscore_hyphen(self, certificados):
        assert certificados.safe_name("Hello World! @#$ 2026") == "HelloWorld2026"

    def test_keeps_underscores_and_hyphens(self, certificados):
        assert certificados.safe_name("my-machine_01") == "my-machine_01"

    def test_truncates_to_60_chars(self, certificados):
        result = certificados.safe_name("A" * 100)
        assert len(result) == 60
        assert result == "A" * 60

    def test_empty_string_returns_maquina(self, certificados):
        assert certificados.safe_name("") == "maquina"

    def test_none_returns_maquina(self, certificados):
        assert certificados.safe_name(None) == "maquina"

    def test_all_symbols_returns_maquina(self, certificados):
        assert certificados.safe_name("!!!@@@###") == "maquina"


class TestAbspathFor:
    def test_normal_relative_path_is_accepted(self, certificados):
        relpath = "uploads/certificados/user_1/DL-ABCDEF-machine.webp"
        result = certificados.abspath_for(relpath)
        assert result.startswith(certificados.CERT_ROOT)
        assert result.endswith("DL-ABCDEF-machine.webp")

    @pytest.mark.parametrize("escaping_relpath", [
        "uploads/certificados/../../etc/passwd",
        "../../etc/passwd",
        "uploads/certificados/../../../../etc/passwd",
        "uploads/certificados/../../../" + "x" * 5,
    ])
    def test_path_traversal_escape_raises_value_error(self, certificados, escaping_relpath):
        with pytest.raises(ValueError):
            certificados.abspath_for(escaping_relpath)

    def test_root_itself_is_not_mistaken_for_an_escape(self, certificados):
        # Un path que cae justo en una carpeta con el mismo prefijo que
        # CERT_ROOT pero que en realidad no es un hijo (p.ej. "...-evil") no
        # debe colarse: la comprobación exige el separador de carpeta tras el
        # prefijo. Usamos un relpath normal con subcarpeta para confirmar que
        # SÍ se acepta un hijo legítimo de más de un nivel.
        relpath = "uploads/certificados/user_42/sub/DL-000000-m.webp"
        result = certificados.abspath_for(relpath)
        assert result.startswith(certificados.CERT_ROOT + "/")

    # author_matches_user() y machine_certificable() requieren consultar
    # User/Machine en BD real: cubiertos en
    # tests/integration/test_certificados_api.py.
