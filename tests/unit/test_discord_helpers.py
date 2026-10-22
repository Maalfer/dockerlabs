"""Tests puros de dockerlabs/discord_notify.py — sin BD, sin red real.

Se parchea `dockerlabs.discord_notify._send` por un stub async que solo
registra el embed recibido (nunca llega a abrir un socket). Las funciones
públicas son corutinas: se ejecutan con `asyncio.run` ya que el proyecto no
usa el plugin pytest-asyncio.
"""
import asyncio
from types import SimpleNamespace

import pytest

import dockerlabs.discord_notify as discord_notify
from dockerlabs.discord_notify import _footer, _hex_to_int

pytestmark = pytest.mark.unit


@pytest.fixture
def sent_embeds(monkeypatch):
    """Sustituye _send por un stub que registra los embeds recibidos."""
    sent = []

    async def _fake_send(embed):
        sent.append(embed)

    monkeypatch.setattr(discord_notify, "_send", _fake_send)
    return sent


class TestHexToInt:
    def test_valid_hex_with_hash_prefix(self):
        assert _hex_to_int("#8bc34a", 0) == int("8bc34a", 16)

    def test_valid_hex_without_hash_prefix(self):
        assert _hex_to_int("8bc34a", 0) == int("8bc34a", 16)

    def test_garbage_string_returns_fallback(self):
        assert _hex_to_int("not-a-color", 999) == 999

    def test_none_raises_attribute_error(self):
        # Comportamiento real y sorprendente: el except solo captura
        # (TypeError, ValueError), no AttributeError. `None.lstrip(...)`
        # revienta sin que el fallback entre en juego. Esto implica que
        # `notify_new_machine` también reventaría si `machine.color` es None
        # (getattr(..., None) no salva el caso: el valor por defecto YA es
        # None). Lo documentamos tal cual está, sin tocar el código de la app.
        with pytest.raises(AttributeError):
            _hex_to_int(None, 999)


class TestFooter:
    def test_footer_includes_text_and_icon_url(self, monkeypatch):
        monkeypatch.setenv("APP_URL", "https://dockerlabs.es")
        footer = _footer("DockerLabs")
        assert footer == {
            "text": "DockerLabs",
            "icon_url": "https://dockerlabs.es/static/dockerlabs/images/logos/logo.png",
        }

    def test_footer_respects_app_url_without_trailing_slash(self, monkeypatch):
        monkeypatch.setenv("APP_URL", "https://custom.test/")
        footer = _footer("X")
        assert footer["icon_url"] == "https://custom.test/static/dockerlabs/images/logos/logo.png"


class TestNotifyNewMachine:
    def test_docker_origin_links_to_root_and_uses_dockerlabs_footer(self, sent_embeds, monkeypatch):
        monkeypatch.setenv("APP_URL", "https://dockerlabs.es")
        machine = SimpleNamespace(
            id=1, nombre="M1", dificultad="Fácil", autor="A", color="#8bc34a", origen="docker",
        )
        asyncio.run(discord_notify.notify_new_machine(machine))

        assert len(sent_embeds) == 1
        embed = sent_embeds[0]
        assert embed["url"] == "https://dockerlabs.es"
        assert embed["footer"]["text"] == "DockerLabs"
        assert embed["title"] == "M1"
        assert embed["color"] == int("8bc34a", 16)
        assert embed["thumbnail"]["url"] == "https://dockerlabs.es/img/maquina/1"
        assert embed["fields"] == [
            {"name": "Dificultad", "value": "Fácil", "inline": True},
            {"name": "Autor", "value": "A", "inline": True},
        ]

    def test_bunker_origin_links_to_bunkerlabs_and_uses_bunkerlabs_footer(self, sent_embeds, monkeypatch):
        monkeypatch.setenv("APP_URL", "https://dockerlabs.es")
        machine = SimpleNamespace(
            id=2, nombre="M2", dificultad="Difícil", autor="B", color="garbage", origen="bunker",
        )
        asyncio.run(discord_notify.notify_new_machine(machine))

        embed = sent_embeds[0]
        assert embed["url"] == "https://dockerlabs.es/bunkerlabs"
        assert embed["footer"]["text"] == "BunkerLabs"
        # Color inválido ("garbage") no es hex -> cae al color de fallback.
        from dockerlabs.discord_notify import _FALLBACK_MACHINE_COLOR
        assert embed["color"] == _FALLBACK_MACHINE_COLOR


class TestNotifyWriteupsBatch:
    def test_empty_list_is_a_noop(self, sent_embeds):
        asyncio.run(discord_notify.notify_writeups_batch([]))
        assert sent_embeds == []

    def test_long_batch_description_is_truncated_to_discord_limit(self, sent_embeds):
        # Muchas entradas largas para forzar que la descripción combinada
        # supere el límite de 4000 caracteres de un embed de Discord.
        writeups = [
            SimpleNamespace(maquina="Maquina" + "X" * 50 + str(i), autor="Autor" + "Y" * 50, tipo="texto")
            for i in range(200)
        ]
        asyncio.run(discord_notify.notify_writeups_batch(writeups))

        assert len(sent_embeds) == 1
        description = sent_embeds[0]["description"]
        assert len(description) == 4000

    def test_small_batch_is_not_truncated(self, sent_embeds):
        writeups = [SimpleNamespace(maquina="M1", autor="A1", tipo="texto")]
        asyncio.run(discord_notify.notify_writeups_batch(writeups))
        description = sent_embeds[0]["description"]
        assert description == "**M1** — A1 · texto"
