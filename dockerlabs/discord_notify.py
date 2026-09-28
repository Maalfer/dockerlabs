"""Notificaciones a Discord (webhook) cuando se publica contenido nuevo en DockerLabs.

Requiere DISCORD_WEBHOOK_URL en el entorno (.env). Si no está configurado, o si
el envío falla, se registra en el log y se continúa sin romper el flujo que
llamó a esta función (nunca debe tumbar un alta de máquina o una aprobación
de writeup por un fallo de Discord).
"""
import os
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

_COLOR_WRITEUP = 0x5865F2  # blurple, para no competir con los colores de dificultad
_FALLBACK_MACHINE_COLOR = 0x2ECC71


def _app_url() -> str:
    return os.environ.get("APP_URL", "https://dockerlabs.es").rstrip("/")


def _webhook_url() -> str:
    return os.environ.get("DISCORD_WEBHOOK_URL", "").strip()


def _news_role_mention() -> str:
    """Mención al rol "「🐋」 DockerLabs News" del servidor (1258 miembros suscritos
    a avisos), igual que hacían a mano los anuncios manuales anteriores."""
    role_id = os.environ.get("DISCORD_NEWS_ROLE_ID", "").strip()
    return f"<@&{role_id}>" if role_id else ""


def _hex_to_int(hex_color: str, fallback: int) -> int:
    try:
        return int(hex_color.lstrip("#"), 16)
    except (TypeError, ValueError):
        return fallback


def _footer(text: str) -> dict:
    return {"text": text, "icon_url": f"{_app_url()}/static/dockerlabs/images/logos/logo.png"}


async def _send(embed: dict) -> None:
    webhook_url = _webhook_url()
    if not webhook_url:
        logger.debug("DISCORD_WEBHOOK_URL no configurado — notificación omitida")
        return

    payload = {
        "content": _news_role_mention(),
        "embeds": [embed],
        "allowed_mentions": {"parse": ["roles"]},
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code >= 300:
                logger.warning("Discord webhook respondió %s: %s", resp.status_code, resp.text[:300])
    except Exception:
        logger.exception("Error enviando notificación a Discord")


async def notify_new_machine(machine) -> None:
    app_url = _app_url()
    es_bunker = machine.origen == "bunker"
    link = f"{app_url}/bunkerlabs" if es_bunker else app_url

    embed = {
        "author": {"name": "Nueva máquina"},
        "title": machine.nombre,
        "url": link,
        "color": _hex_to_int(getattr(machine, "color", None), _FALLBACK_MACHINE_COLOR),
        "thumbnail": {"url": f"{app_url}/img/maquina/{machine.id}"},
        "fields": [
            {"name": "Dificultad", "value": machine.dificultad, "inline": True},
            {"name": "Autor", "value": machine.autor, "inline": True},
        ],
        "footer": _footer("BunkerLabs" if es_bunker else "DockerLabs"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await _send(embed)


async def notify_new_writeup(maquina: str, autor: str, url: str, tipo: str, machine_id: int | None = None) -> None:
    embed = {
        "author": {"name": "Nuevo writeup"},
        "title": maquina,
        "url": url,
        "color": _COLOR_WRITEUP,
        "fields": [
            {"name": "Autor", "value": autor, "inline": True},
            {"name": "Tipo", "value": tipo, "inline": True},
        ],
        "footer": _footer("DockerLabs"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if machine_id is not None:
        embed["thumbnail"] = {"url": f"{_app_url()}/img/maquina/{machine_id}"}
    await _send(embed)


async def notify_writeups_batch(writeups: list) -> None:
    """writeups: lista de objetos con .maquina, .autor, .tipo (p.ej. Writeup)."""
    if not writeups:
        return
    lineas = [f"**{w.maquina}** — {w.autor} · {w.tipo}" for w in writeups]
    embed = {
        "author": {"name": f"{len(writeups)} writeups nuevos"},
        "description": "\n".join(lineas)[:4000],
        "color": _COLOR_WRITEUP,
        "footer": _footer("DockerLabs"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await _send(embed)
