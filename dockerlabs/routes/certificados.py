import hashlib
import io
import os
import re
import time
from collections import defaultdict
from datetime import datetime

from fastapi import Depends, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from dockerlabs.models import Certificate, Writeup, Machine, User

_CERT_ID_RE = re.compile(r'^DL-[0-9A-F]{6}$')
_SAFE_NAME_RE = re.compile(r'[^A-Za-z0-9_-]')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

_gen_rate: dict = defaultdict(list)
_ver_rate: dict = defaultdict(list)
GEN_MAX_PER_MIN  = 5
VER_MAX_PER_MIN  = 20

def _allow(store: dict, key: str, limit: int) -> bool:
    now = time.time()
    store[key] = [t for t in store[key] if now - t < 60]
    if len(store[key]) >= limit:
        return False
    store[key].append(now)
    return True


def certificate_id(username: str, machine_name: str) -> str:
    """ID público del certificado. Determinista por (usuario, máquina)."""
    return "DL-" + hashlib.sha256(
        f"{username}:{machine_name}".encode()
    ).hexdigest()[:6].upper()


def safe_name(value: str) -> str:
    cleaned = _SAFE_NAME_RE.sub('', value or '')[:60]
    return cleaned or 'maquina'


def register_certificado_routes(api_router, get_session, db):

    TEMPLATE_PATH = os.path.join(
        os.path.dirname(__file__), '..', '..', 'static', 'dockerlabs', 'images', 'diploma.png'
    )
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

    from PIL import Image as _PILImage

    try:
        _template_img = _PILImage.open(TEMPLATE_PATH)
        _template_img.load()
    except Exception:
        _template_img = None

    def _load_template():
        if _template_img is not None:
            return _template_img.copy()
        return _PILImage.open(TEMPLATE_PATH).copy()

    def _render_diploma(display_name: str, display_machine: str, cert_id: str, date_str: str):
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

    def _pdf_relpath(user_id: int, cert_id: str, machine_name: str) -> str:
        return f"uploads/certificados/user_{user_id}/{cert_id}-{safe_name(machine_name)}.pdf"

    def _persist_certificate(user, machine_name: str, cert_id: str, img) -> Certificate:
        """Guarda el PDF del diploma en disco y registra/actualiza su fila.

        El PDF queda archivado para que `/u/<slug>` y `/api/certificado/pdf/...`
        puedan servirlo sin volver a renderizarlo.
        """
        relpath  = _pdf_relpath(user.id, cert_id, machine_name)
        abspath  = os.path.join(BASE_DIR, relpath)
        os.makedirs(os.path.dirname(abspath), exist_ok=True)

        pdf_buf = io.BytesIO()
        img.convert('RGB').save(pdf_buf, format='PDF', resolution=150.0)

        tmp_path = f"{abspath}.tmp"
        with open(tmp_path, 'wb') as fh:
            fh.write(pdf_buf.getvalue())
        os.replace(tmp_path, abspath)

        cert = Certificate.query.filter_by(
            user_id=user.id, machine_name=machine_name
        ).first()

        if cert:
            cert.cert_id  = cert_id
            cert.username = user.username
            cert.pdf_path = relpath
            cert.updated_at = datetime.utcnow()
        else:
            cert = Certificate(
                cert_id=cert_id,
                user_id=user.id,
                username=user.username,
                machine_name=machine_name,
                pdf_path=relpath,
            )
            db.session.add(cert)

        try:
            db.session.commit()
        except IntegrityError:
            # Otro worker registró el mismo certificado entre el SELECT y el INSERT.
            db.session.rollback()
            cert = Certificate.query.filter_by(
                user_id=user.id, machine_name=machine_name
            ).first()

        return cert

    @api_router.get("/certificado/{machine_name}/disponible")
    def api_certificado_disponible(
        machine_name: str,
        request: Request,
        session: dict = Depends(get_session),
    ):
        username = session.get("username", "")
        if not username:
            return {"disponible": False}
        writeup = Writeup.query.filter(
            func.lower(Writeup.maquina) == func.lower(machine_name),
            func.lower(Writeup.autor)   == func.lower(username),
        ).first()
        return {"disponible": bool(writeup)}

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
            c.machine_name: c
            for c in Certificate.query.filter_by(user_id=user_id).all()
        } if user_id else {}

        result = []
        seen: set = set()
        for wu in writeups:
            if wu.maquina in seen:
                continue
            seen.add(wu.maquina)
            machine = Machine.query.filter(
                func.lower(Machine.nombre) == func.lower(wu.maquina)
            ).first()
            cert_id = certificate_id(username, wu.maquina)
            emitido = emitidos.get(wu.maquina)
            result.append({
                "maquina":    machine.nombre    if machine else wu.maquina,
                "dificultad": machine.dificultad if machine else "",
                "color":      machine.color      if machine else "#64748b",
                "fecha":      wu.created_at.strftime("%d/%m/%Y") if wu.created_at else "",
                "cert_id":    cert_id,
                "generado":   bool(emitido),
                "pdf_url":    f"/api/certificado/pdf/{cert_id}" if emitido else None,
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

        target_hash = raw[3:]

        pairs = (
            db.session.query(Writeup.autor, Writeup.maquina)
            .distinct()
            .limit(10000)
            .all()
        )

        for autor, maquina in pairs:
            computed = hashlib.sha256(
                f"{autor}:{maquina}".encode()
            ).hexdigest()[:6].upper()
            if computed == target_hash:
                machine = Machine.query.filter(
                    func.lower(Machine.nombre) == func.lower(maquina)
                ).first()
                emitido = Certificate.query.filter_by(cert_id=raw).first()
                return {
                    "valid":      True,
                    "username":   autor,
                    "machine":    machine.nombre    if machine else maquina,
                    "dificultad": machine.dificultad if machine else "",
                    "generado":   bool(emitido),
                    "pdf_url":    f"/api/certificado/pdf/{raw}" if emitido else None,
                }

        return {"valid": False, "message": "Certificado no encontrado."}

    @api_router.get("/certificado/pdf/{cert_id}")
    def api_certificado_pdf(cert_id: str, request: Request):
        """Sirve el PDF archivado de un certificado ya generado. Público."""
        raw = cert_id.strip().upper()
        if not _CERT_ID_RE.match(raw):
            return JSONResponse(status_code=400, content={"error": "Formato de certificado inválido."})

        cert = Certificate.query.filter_by(cert_id=raw).first()
        if not cert:
            return JSONResponse(
                status_code=404,
                content={"error": "Certificado no generado o inexistente."},
            )

        abspath = os.path.join(BASE_DIR, cert.pdf_path)
        if not os.path.isfile(abspath):
            return JSONResponse(status_code=404, content={"error": "El PDF del certificado no está disponible."})

        return FileResponse(
            abspath,
            media_type="application/pdf",
            filename=f"diploma-dockerlabs-{safe_name(cert.machine_name)}.pdf",
            headers={"Cache-Control": "public, max-age=86400"},
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

        writeup = Writeup.query.filter(
            func.lower(Writeup.maquina) == func.lower(machine_name),
            func.lower(Writeup.autor)   == func.lower(username),
        ).first()
        if not writeup:
            return JSONResponse(
                status_code=403,
                content={"error": "No tienes un writeup publicado para esta máquina"},
            )

        machine = Machine.query.filter(
            func.lower(Machine.nombre) == func.lower(machine_name)
        ).first()
        display_machine = machine.nombre if machine else machine_name

        user_obj = User.query.filter(User.username == username).first()
        if not user_obj:
            return JSONResponse(status_code=401, content={"error": "No autenticado"})

        display_name = (
            user_obj.nombre_diploma.strip()
            if user_obj.nombre_diploma and user_obj.nombre_diploma.strip()
            else username
        )

        cert_id  = certificate_id(username, writeup.maquina)
        date_str = datetime.now().strftime("%d/%m/%Y")

        img = _render_diploma(display_name, display_machine, cert_id, date_str)

        # El PDF se archiva en cada generación: es la copia que consumen
        # `/u/<slug>` y `/api/certificado/pdf/<cert_id>`.
        cert = _persist_certificate(user_obj, writeup.maquina, cert_id, img)

        filename_base = f"diploma-dockerlabs-{safe_name(machine_name)}"

        if formato == "pdf":
            abspath = os.path.join(BASE_DIR, cert.pdf_path) if cert else None
            if abspath and os.path.isfile(abspath):
                return FileResponse(
                    abspath,
                    media_type="application/pdf",
                    filename=f"{filename_base}.pdf",
                )
            buf = io.BytesIO()
            img.convert('RGB').save(buf, format="PDF", resolution=150.0)
            return Response(
                content=buf.getvalue(),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{filename_base}.pdf"'},
            )

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)

        return Response(
            content=buf.getvalue(),
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.png"'},
        )
