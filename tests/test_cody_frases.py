"""Valida el repertorio de frases de Cody (static/dockerlabs/data/frases.json)."""
import json
from pathlib import Path

RUTA = Path(__file__).resolve().parent.parent / "static" / "dockerlabs" / "data" / "frases.json"
DATOS = json.loads(RUTA.read_text(encoding="utf-8"))


def test_estructura():
    assert isinstance(DATOS["frases"], list) and DATOS["frases"]
    assert 0 <= DATOS["prefProb"] <= 1


def test_frases_validas_y_unicas():
    textos = [f["t"] for f in DATOS["frases"]]
    assert len(textos) == len(set(textos)), "hay frases duplicadas"
    for f in DATOS["frases"]:
        assert f["t"].strip() and f["a"].strip(), f
        assert len(f["t"]) <= 125, "frase demasiado larga para el bocadillo: " + f["t"]
        assert f["c"] in DATOS["categorias"], f


def test_contextos_apuntan_a_categorias_existentes():
    usadas = {f["c"] for f in DATOS["frases"]}
    for ctx, cats in DATOS["contextos"].items():
        assert cats, ctx
        for c in cats:
            assert c in DATOS["categorias"], (ctx, c)
            assert c in usadas, "contexto %s prefiere una categoría sin frases: %s" % (ctx, c)
