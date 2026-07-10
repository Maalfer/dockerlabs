"""Certificados de finalización.

Un certificado existe en cuanto el usuario tiene un writeup publicado de una
máquina: no hay que pedirlo. `ensure_certificate()` renderiza el diploma y
archiva su PDF en `uploads/certificados/`, y se invoca automáticamente al
aprobar un writeup, de modo que `/u/<slug>` siempre lo encuentra ya hecho.

La fecha impresa es la del writeup (la finalización real), no la del momento en
que se renderiza; así el diploma es determinista y se puede regenerar sin que
cambie.
"""

import hashlib
import io
import logging
import os
import re
import time
from collections import defaultdict

from fastapi import Depends, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from dockerlabs.extensions import db
from dockerlabs.models import Certificate, Writeup, Machine, User

logger = logging.getLogger(__name__)

_CERT_ID_RE = re.compile(r'^DL-[0-9A-F]{6}$')
_SAFE_NAME_RE = re.compile(r'[^A-Za-z0-9_-]')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# BunkerLabs no tiene certificados: es de acceso cerrado. Solo se emiten diplomas
# para máquinas de estos orígenes; cualquier otro (p. ej. 'bunker') queda excluido.
CERT_ORIGENES = ('docker', 'empezar')

TEMPLATE_PATH = os.path.join(BASE_DIR, 'static', 'dockerlabs', 'images', 'diploma.png')
FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

BOX_CX       = 749
USER_BOX_TOP = 465
USER_BOX_BOT = 550
MACH_BOX_TOP = 613
MACH_BOX_BOT = 684
USER_BOX_W   = int((1103 - 436) * 0.88)
MACH_BOX_W   = int((1139 - 399) * 0.88)
DATE_CX      = 460
CERT_CX      = 1122
BOTTOM_Y     = 900
TEXT_COLOR   = (30, 65, 85)

_gen_rate: dict = defaultdict(list)
_ver_rate: dict = defaultdict(list)
# Generar ya no renderiza 13 s: sirve un fichero archivado o compone un PNG en
# 0,45 s. Un usuario con 59 diplomas tiene que poder descargarlos del tirón.
GEN_MAX_PER_MIN  = 60
VER_MAX_PER_MIN  = 20

# A partir de aquí se purgan las IPs sin actividad reciente, para que el
# diccionario no crezca indefinidamente con una IP por atacante.
RATE_STORE_MAX_KEYS = 10_000

_template_img = None


def _prune(store: dict, now: float) -> None:
    for key in [k for k, hits in store.items() if not hits or now - hits[-1] >= 60]:
        del store[key]


def _allow(store: dict, key: str, limit: int) -> bool:
    now = time.time()
    if len(store) > RATE_STORE_MAX_KEYS:
        _prune(store, now)
    store[key] = [t for t in store[key] if now - t < 60]
    if len(store[key]) >= limit:
        return False
    store[key].append(now)
    return True


def _cert_id_candidates(username: str, machine_name: str):
    """Ventanas sucesivas del digest, como candidatos a ID."""
    digest = hashlib.sha256(f"{username}:{machine_name}".encode()).hexdigest().upper()
    for i in range(0, 60, 6):
        yield "DL-" + digest[i:i + 6]


def certificate_id(username: str, machine_name: str) -> str:
    """ID preferente del certificado. Determinista por (usuario, máquina).

    Solo son 24 bits: con unos pocos miles de certificados las colisiones son
    probables (paradoja del cumpleaños). Para el ID definitivo usa
    `allocate_cert_id()`, que resuelve la colisión; este valor es únicamente el
    primer candidato, y el que se muestra cuando aún no hay fila emitida.
    """
    return next(_cert_id_candidates(username, machine_name))


def allocate_cert_id(username: str, machine_name: str, user_id: int) -> str:
    """ID único: el primer candidato libre, o el que ya tenga este certificado.

    Mantiene estable el ID de los certificados existentes y solo desplaza al
    segundo en llegar, de modo que los IDs ya publicados no cambian.
    """
    for candidate in _cert_id_candidates(username, machine_name):
        dueno = Certificate.query.filter_by(cert_id=candidate).first()
        if dueno is None or (dueno.user_id == user_id
                             and dueno.machine_name == machine_name):
            return candidate
    raise RuntimeError(
        f"No se encontró un cert_id libre para {username}/{machine_name}"
    )


def safe_name(value: str) -> str:
    cleaned = _SAFE_NAME_RE.sub('', value or '')[:60]
    return cleaned or 'maquina'


def _load_template():
    global _template_img
    from PIL import Image as _PILImage
    if _template_img is None:
        img = _PILImage.open(TEMPLATE_PATH)
        img.load()
        _template_img = img
    return _template_img.copy()


def render_diploma(display_name: str, display_machine: str, cert_id: str, date_str: str):
    """Dibuja el diploma y devuelve la imagen PIL resultante."""
    from PIL import ImageDraw, ImageFont

    img  = _load_template()
    draw = ImageDraw.Draw(img)

    def load_font(size):
        return ImageFont.truetype(FONT_PATH, size)

    def fit_font(text, max_w, max_h, start=52):
        size = start
        while size > 12:
            f  = load_font(size)
            bb = draw.textbbox((0, 0), text, font=f)
            if (bb[2] - bb[0]) <= max_w and (bb[3] - bb[1]) <= max_h:
                return f
            size -= 2
        return load_font(12)

    def draw_in_box(text, font, box_top, box_bot, cx):
        bb     = draw.textbbox((0, 0), text, font=font)
        x      = cx - (bb[2] - bb[0]) // 2
        box_cy = (box_top + box_bot) / 2
        y      = box_cy - (bb[1] + bb[3]) / 2
        draw.text((x, y), text, fill=TEXT_COLOR, font=font)

    def draw_centered_at(text, font, cx, center_y):
        bb = draw.textbbox((0, 0), text, font=font)
        x  = cx - (bb[2] - bb[0]) // 2
        y  = center_y - (bb[1] + bb[3]) / 2
        draw.text((x, y), text, fill=TEXT_COLOR, font=font)

    font_user = fit_font(display_name,    USER_BOX_W, USER_BOX_BOT - USER_BOX_TOP - 12, start=52)
    font_mach = fit_font(display_machine, MACH_BOX_W, MACH_BOX_BOT - MACH_BOX_TOP - 10, start=42)
    font_sm   = load_font(19)

    draw_in_box(display_name,    font_user, USER_BOX_TOP, USER_BOX_BOT, BOX_CX)
    draw_in_box(display_machine, font_mach, MACH_BOX_TOP, MACH_BOX_BOT, BOX_CX)
    draw_centered_at(date_str, font_sm, DATE_CX, BOTTOM_Y)
    draw_centered_at(cert_id,  font_sm, CERT_CX, BOTTOM_Y)

    return img


def display_name_for(user) -> str:
    """Nombre impreso en el diploma: el nombre real si lo configuró, si no el usuario."""
    if user.nombre_diploma and user.nombre_diploma.strip():
        return user.nombre_diploma.strip()
    return user.username


def pdf_relpath(user_id: int, cert_id: str, machine_name: str) -> str:
    return f"uploads/certificados/user_{user_id}/{cert_id}-{safe_name(machine_name)}.pdf"


def image_relpath(user_id: int, cert_id: str, machine_name: str) -> str:
    return f"uploads/certificados/user_{user_id}/{cert_id}-{safe_name(machine_name)}.webp"


CERT_ROOT = os.path.join(BASE_DIR, 'uploads', 'certificados')


def abspath_for(relpath: str) -> str:
    """Ruta absoluta, garantizando que no se sale de uploads/certificados."""
    abspath = os.path.abspath(os.path.join(BASE_DIR, relpath))
    if not abspath.startswith(CERT_ROOT + os.sep):
        raise ValueError(f"Ruta de certificado fuera de {CERT_ROOT}: {relpath!r}")
    return abspath


def _write_atomic(data: bytes, relpath: str) -> None:
    """Escritura atómica: un lector concurrente nunca ve un fichero a medias."""
    abspath = abspath_for(relpath)
    os.makedirs(os.path.dirname(abspath), exist_ok=True)
    tmp_path = f"{abspath}.tmp"
    with open(tmp_path, 'wb') as fh:
        fh.write(data)
    os.replace(tmp_path, abspath)


def _write_pdf(img, relpath: str) -> None:
    buf = io.BytesIO()
    img.convert('RGB').save(buf, format='PDF', resolution=150.0)
    _write_atomic(buf.getvalue(), relpath)


def _write_image(img, relpath: str) -> None:
    # WebP con method=2: 85 KB y 0,15 s. Un PNG del mismo diploma pesa 1 MB y
    # con optimize=True tarda 13 s, tiempo suficiente para que el navegador o
    # el proxy abandonen la descarga.
    buf = io.BytesIO()
    img.convert('RGB').save(buf, format='WEBP', quality=88, method=2)
    _write_atomic(buf.getvalue(), relpath)


def _remove_file(relpath: str) -> None:
    try:
        os.remove(abspath_for(relpath))
    except OSError:
        pass


def author_matches_user(autor: str, user) -> bool:
    """¿El autor de un writeup es este usuario?

    La comparación es insensible a mayúsculas, como en el resto de la
    aplicación, salvo cuando existen varias cuentas cuyos nombres solo
    difieren en la capitalización ('oscar' y 'Oscar'): en ese caso solo la
    coincidencia exacta desempata, o el writeup no se atribuye a nadie.
    """
    autor = autor or ''
    if autor == user.username:
        return True
    if autor.lower() != user.username.lower():
        return False
    homonimos = User.query.filter(func.lower(User.username) == autor.lower()).count()
    return homonimos == 1


def machine_certificable(machine_name: str) -> bool:
    """¿Esta máquina puede tener certificado? No, si es de BunkerLabs.

    Una máquina sin fila en el catálogo (borrada) se considera certificable: no
    se puede afirmar que fuera de bunker y ya podría tener un diploma emitido.
    """
    machine = Machine.query.filter(func.lower(Machine.nombre) == func.lower(machine_name)).first()
    return machine is None or machine.origen in CERT_ORIGENES


def machines_with_writeups(user) -> list:
    """Máquinas de las que el usuario tiene writeup publicado (nombre canónico)."""
    filas = (
        db.session.query(Writeup.autor, Writeup.maquina)
        .filter(func.lower(Writeup.autor) == func.lower(user.username))
        .distinct()
        .all()
    )
    vistas, maquinas = set(), []
    for autor, maquina in filas:
        if (author_matches_user(autor, user) and maquina.lower() not in vistas
                and machine_certificable(maquina)):
            vistas.add(maquina.lower())
            maquinas.append(maquina)
    return maquinas


def _writeup_for(user, machine_name: str):
    """Primer writeup del usuario para esa máquina, o None si no le pertenece."""
    candidatos = (
        Writeup.query
        .filter(func.lower(Writeup.maquina) == func.lower(machine_name),
                func.lower(Writeup.autor)   == func.lower(user.username))
        .order_by(Writeup.created_at.asc())
        .all()
    )
    for wu in candidatos:
        if author_matches_user(wu.autor, user):
            return wu
    return None


def ensure_certificate(user, machine_name: str, *, force: bool = False):
    """Garantiza que el PDF del certificado existe y devuelve su fila.

    Idempotente: si el PDF ya está en disco, con el `cert_id` correcto, no
    vuelve a renderizar salvo que se pase `force=True` (renombrado de usuario o
    cambio del nombre del diploma). Devuelve `None` si el usuario no tiene
    writeup publicado de esa máquina, es decir, si no le corresponde diploma.
    """
    writeup = _writeup_for(user, machine_name)
    if not writeup:
        return None

    # BunkerLabs no tiene certificados: no se emite diploma aunque haya writeup.
    if not machine_certificable(writeup.maquina):
        return None

    canonical = writeup.maquina
    cert_id   = allocate_cert_id(user.username, canonical, user.id)
    relpath   = pdf_relpath(user.id, cert_id, canonical)
    img_relpath = image_relpath(user.id, cert_id, canonical)

    existing = Certificate.query.filter_by(user_id=user.id, machine_name=canonical).first()
    if (existing and not force and existing.cert_id == cert_id
            and os.path.isfile(abspath_for(existing.pdf_path))
            and existing.image_path and os.path.isfile(abspath_for(existing.image_path))):
        return existing

    machine = Machine.query.filter(func.lower(Machine.nombre) == func.lower(canonical)).first()
    display_machine = machine.nombre if machine else canonical
    fecha = writeup.created_at.strftime("%d/%m/%Y") if writeup.created_at else ""

    img = render_diploma(display_name_for(user), display_machine, cert_id, fecha)
    _write_pdf(img, relpath)
    _write_image(img, img_relpath)

    if existing:
        if existing.pdf_path != relpath:
            _remove_file(existing.pdf_path)
        if existing.image_path and existing.image_path != img_relpath:
            _remove_file(existing.image_path)
        existing.cert_id    = cert_id
        existing.username   = user.username
        existing.pdf_path   = relpath
        existing.image_path = img_relpath
    else:
        existing = Certificate(
            cert_id=cert_id,
            user_id=user.id,
            username=user.username,
            machine_name=canonical,
            pdf_path=relpath,
            image_path=img_relpath,
        )
        db.session.add(existing)

    try:
        db.session.commit()
    except IntegrityError:
        # Otro worker registró el mismo certificado entre el SELECT y el INSERT.
        db.session.rollback()
        existing = Certificate.query.filter_by(user_id=user.id, machine_name=canonical).first()

    return existing


def sync_user_certificates(user, *, force: bool = False) -> dict:
    """Pone al día TODOS los certificados de un usuario.

    Emite los que falten, regenera los existentes si `force` (el `cert_id`
    depende del nombre de usuario, y el diploma del `nombre_diploma`), y retira
    los que ya no correspondan porque su writeup se eliminó.
    """
    maquinas = machines_with_writeups(user)

    emitidos = 0
    for maquina in maquinas:
        if ensure_certificate(user, maquina, force=force):
            emitidos += 1

    vigentes = {m.lower() for m in maquinas}
    retirados = 0
    for cert in Certificate.query.filter_by(user_id=user.id).all():
        if cert.machine_name.lower() not in vigentes:
            _remove_file(cert.pdf_path)
            if cert.image_path:
                _remove_file(cert.image_path)
            db.session.delete(cert)
            retirados += 1
    if retirados:
        db.session.commit()

    return {"emitidos": emitidos, "retirados": retirados}


def ensure_certificate_safe(username: str, machine_name: str) -> None:
    """Envoltorio a prueba de fallos para llamar desde flujos de escritura.

    Emitir un diploma nunca debe tumbar la aprobación de un writeup ni el
    guardado de un perfil, así que aquí los errores solo se registran.
    """
    try:
        user = User.query.filter(User.username == username).first()
        if not user:
            user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
        if user:
            ensure_certificate(user, machine_name)
    except Exception:
        db.session.rollback()
        logger.exception("No se pudo emitir el certificado de %s / %s", username, machine_name)


def revoke_certificate_safe(username: str, machine_name: str) -> None:
    """Retira el diploma si el usuario ya no tiene writeup publicado de la máquina.

    Se llama al borrar un writeup. Si le quedaba otro writeup de la misma
    máquina, el diploma sigue siendo legítimo y no se toca.
    """
    try:
        user = User.query.filter(User.username == username).first()
        if not user:
            user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
        if not user:
            return
        if _writeup_for(user, machine_name):
            return
        cert = (
            Certificate.query
            .filter(Certificate.user_id == user.id,
                    func.lower(Certificate.machine_name) == func.lower(machine_name))
            .first()
        )
        if cert:
            _remove_file(cert.pdf_path)
            if cert.image_path:
                _remove_file(cert.image_path)
            db.session.delete(cert)
            db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("No se pudo retirar el certificado de %s / %s", username, machine_name)


def sync_user_certificates_safe(user_id: int, *, force: bool = False) -> None:
    """Resincroniza los certificados de un usuario en segundo plano.

    Re-renderizar un diploma cuesta ~170 ms (PDF + WebP); un usuario con 59 de
    ellos tardaría 10 s. Se ejecuta como BackgroundTask, después de responder,
    con su propio ámbito de sesión: el del request ya se ha cerrado.
    """
    from dockerlabs.database import _request_scope_id, db_session

    token = _request_scope_id.set(object())
    try:
        user = User.query.get(user_id)
        if user:
            sync_user_certificates(user, force=force)
    except Exception:
        db.session.rollback()
        logger.exception("No se pudieron sincronizar los certificados de user_id=%s", user_id)
    finally:
        db_session.remove()
        _request_scope_id.reset(token)


def register_certificado_routes(api_router, get_session, db):

    @api_router.get("/certificado/{machine_name}/disponible")
    def api_certificado_disponible(
        machine_name: str,
        request: Request,
        session: dict = Depends(get_session),
    ):
        username = session.get("username", "")
        if not username:
            return {"disponible": False}
        user = User.query.filter(User.username == username).first()
        if not user:
            return {"disponible": False}
        if not machine_certificable(machine_name):
            return {"disponible": False}
        return {"disponible": bool(_writeup_for(user, machine_name))}

    @api_router.get("/certificados/mis-certificados")
    def api_mis_certificados(
        request: Request,
        session: dict = Depends(get_session),
    ):
        username = session.get("username", "")
        user_id  = session.get("user_id")
        if not username:
            return JSONResponse(status_code=401, content={"error": "No autenticado"})

        writeups = (
            Writeup.query
            .filter(func.lower(Writeup.autor) == func.lower(username))
            .order_by(Writeup.created_at.desc())
            .limit(500)
            .all()
        )

        emitidos = {
            c.machine_name.lower(): c
            for c in Certificate.query.filter_by(user_id=user_id).all()
        } if user_id else {}

        result = []
        seen: set = set()
        for wu in writeups:
            if wu.maquina in seen:
                continue
            seen.add(wu.maquina)
            if not machine_certificable(wu.maquina):
                continue
            machine = Machine.query.filter(
                func.lower(Machine.nombre) == func.lower(wu.maquina)
            ).first()
            emitido = emitidos.get(wu.maquina.lower())
            # El cert_id real es el de la fila: puede diferir del primer
            # candidato del hash si hubo colisión al emitirlo.
            cert_id = emitido.cert_id if emitido else certificate_id(username, wu.maquina)
            result.append({
                "maquina":    machine.nombre    if machine else wu.maquina,
                "dificultad": machine.dificultad if machine else "",
                "color":      machine.color      if machine else "#64748b",
                "fecha":      wu.created_at.strftime("%d/%m/%Y") if wu.created_at else "",
                "cert_id":    cert_id,
                "generado":   bool(emitido),
                "pdf_url":    f"/api/certificado/pdf/{cert_id}" if emitido else None,
                "imagen_url": f"/api/certificado/imagen/{cert_id}" if emitido else None,
            })

        return {"certificados": result}

    @api_router.get("/certificado/verificar/{cert_id}")
    def api_verificar_certificado(cert_id: str, request: Request):
        client_ip = request.client.host if request.client else "unknown"
        if not _allow(_ver_rate, client_ip, VER_MAX_PER_MIN):
            return JSONResponse(
                status_code=429,
                content={"valid": False, "message": "Demasiadas verificaciones. Intenta de nuevo en un minuto."}
            )

        raw = cert_id.strip().upper()
        if not _CERT_ID_RE.match(raw):
            return JSONResponse({"valid": False, "message": "Formato inválido. Usa el formato DL-XXXXXX"})

        # Los certificados emitidos están indexados: una sola consulta.
        emitido = Certificate.query.filter_by(cert_id=raw).first()
        if emitido:
            machine = Machine.query.filter(
                func.lower(Machine.nombre) == func.lower(emitido.machine_name)
            ).first()
            return {
                "valid":      True,
                "username":   emitido.username,
                "machine":    machine.nombre    if machine else emitido.machine_name,
                "dificultad": machine.dificultad if machine else "",
                "generado":   True,
                "pdf_url":    f"/api/certificado/pdf/{raw}",
                "imagen_url": f"/api/certificado/imagen/{raw}",
            }

        # Un certificado solo existe una vez emitido (tiene fila indexada). Ya no
        # se escanea `writeups_subidos` calculando un hash por fila: era un
        # barrido de tabla que cualquiera podía disparar sin autenticarse.
        return {"valid": False, "message": "Certificado no encontrado."}

    @api_router.get("/certificado/pdf/{cert_id}")
    def api_certificado_pdf(cert_id: str, request: Request):
        """Sirve el PDF archivado de un certificado. Público."""
        raw = cert_id.strip().upper()
        if not _CERT_ID_RE.match(raw):
            return JSONResponse(status_code=400, content={"error": "Formato de certificado inválido."})

        cert = Certificate.query.filter_by(cert_id=raw).first()
        if not cert:
            return JSONResponse(
                status_code=404,
                content={"error": "Certificado no encontrado."},
            )

        abspath = abspath_for(cert.pdf_path)
        if not os.path.isfile(abspath):
            # La fila existe pero el fichero no: reemitirlo es mejor que un 404.
            user = User.query.get(cert.user_id)
            if user:
                ensure_certificate(user, cert.machine_name, force=True)
            if not os.path.isfile(abspath_for(cert.pdf_path)):
                return JSONResponse(status_code=404, content={"error": "El PDF del certificado no está disponible."})
            abspath = abspath_for(cert.pdf_path)

        return FileResponse(
            abspath,
            media_type="application/pdf",
            filename=f"diploma-dockerlabs-{safe_name(cert.machine_name)}.pdf",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @api_router.get("/certificado/imagen/{cert_id}")
    def api_certificado_imagen(cert_id: str, request: Request):
        """Sirve el diploma como imagen, para verlo o incrustarlo. Público."""
        raw = cert_id.strip().upper()
        if not _CERT_ID_RE.match(raw):
            return JSONResponse(status_code=400, content={"error": "Formato de certificado inválido."})

        cert = Certificate.query.filter_by(cert_id=raw).first()
        if not cert:
            return JSONResponse(status_code=404, content={"error": "Certificado no encontrado."})

        if not cert.image_path or not os.path.isfile(abspath_for(cert.image_path)):
            # Falta el fichero (o la fila es anterior a que se guardara imagen):
            # reemitirlo es mejor que devolver un 404.
            user = User.query.get(cert.user_id)
            if user:
                ensure_certificate(user, cert.machine_name, force=True)
            cert = Certificate.query.filter_by(cert_id=raw).first()
            if not cert or not cert.image_path or not os.path.isfile(abspath_for(cert.image_path)):
                return JSONResponse(status_code=404, content={"error": "La imagen del certificado no está disponible."})

        return FileResponse(
            abspath_for(cert.image_path),
            media_type="image/webp",
            headers={
                "Cache-Control": "public, max-age=86400",
                "Content-Disposition": f'inline; filename="diploma-dockerlabs-{safe_name(cert.machine_name)}.webp"',
            },
        )

    @api_router.get("/certificado/{machine_name}")
    def api_generar_certificado(
        machine_name: str,
        request: Request,
        formato: str = "png",
        session: dict = Depends(get_session),
    ):
        client_ip = request.client.host if request.client else "unknown"
        if not _allow(_gen_rate, client_ip, GEN_MAX_PER_MIN):
            return JSONResponse(
                status_code=429,
                content={"error": "Demasiadas solicitudes. Espera un minuto antes de generar otro certificado."}
            )

        if not machine_name or len(machine_name) > 100:
            return JSONResponse(status_code=400, content={"error": "Nombre de máquina no válido"})

        formato = (formato or "png").lower()
        if formato not in ("png", "pdf"):
            return JSONResponse(status_code=400, content={"error": "Formato no soportado. Usa png o pdf."})

        username = session.get("username", "")
        if not username:
            return JSONResponse(status_code=401, content={"error": "No autenticado"})

        user_obj = User.query.filter(User.username == username).first()
        if not user_obj:
            return JSONResponse(status_code=401, content={"error": "No autenticado"})

        if not machine_certificable(machine_name):
            return JSONResponse(
                status_code=403,
                content={"error": "Esta máquina no tiene certificado."},
            )

        writeup = _writeup_for(user_obj, machine_name)
        if not writeup:
            return JSONResponse(
                status_code=403,
                content={"error": "No tienes un writeup publicado para esta máquina"},
            )

        cert = ensure_certificate(user_obj, machine_name)
        if not cert:
            return JSONResponse(status_code=500, content={"error": "No se pudo emitir el certificado."})

        filename_base = f"diploma-dockerlabs-{safe_name(machine_name)}"

        if formato == "pdf":
            return FileResponse(
                abspath_for(cert.pdf_path),
                media_type="application/pdf",
                filename=f"{filename_base}.pdf",
            )

        machine = Machine.query.filter(func.lower(Machine.nombre) == func.lower(machine_name)).first()
        img = render_diploma(
            display_name_for(user_obj),
            machine.nombre if machine else writeup.maquina,
            cert.cert_id,
            writeup.created_at.strftime("%d/%m/%Y") if writeup.created_at else "",
        )
        # optimize=True recomprime durante ~13 s y solo ahorra un 7 %: el
        # navegador abandonaba la descarga antes de recibir nada.
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG", compress_level=1)

        return Response(
            content=buf.getvalue(),
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.png"'},
        )
