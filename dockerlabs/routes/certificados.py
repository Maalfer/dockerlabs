import hashlib
import io
import os
import re
import time
from collections import defaultdict
from datetime import datetime

from fastapi import Depends, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func

from dockerlabs.models import Writeup, Machine, User

_CERT_ID_RE = re.compile(r'^DL-[0-9A-F]{6}$')

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
        if not username:
            return JSONResponse(status_code=401, content={"error": "No autenticado"})

        writeups = (
            Writeup.query
            .filter(func.lower(Writeup.autor) == func.lower(username))
            .order_by(Writeup.created_at.desc())
            .limit(500)
            .all()
        )

        result = []
        seen: set = set()
        for wu in writeups:
            if wu.maquina in seen:
                continue
            seen.add(wu.maquina)
            machine = Machine.query.filter(
                func.lower(Machine.nombre) == func.lower(wu.maquina)
            ).first()
            cert_id = "DL-" + hashlib.sha256(
                f"{username}:{wu.maquina}".encode()
            ).hexdigest()[:6].upper()
            result.append({
                "maquina":    machine.nombre    if machine else wu.maquina,
                "dificultad": machine.dificultad if machine else "",
                "color":      machine.color      if machine else "#64748b",
                "fecha":      wu.created_at.strftime("%d/%m/%Y") if wu.created_at else "",
                "cert_id":    cert_id,
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
                return {
                    "valid":      True,
                    "username":   autor,
                    "machine":    machine.nombre    if machine else maquina,
                    "dificultad": machine.dificultad if machine else "",
                }

        return {"valid": False, "message": "Certificado no encontrado."}

    @api_router.get("/certificado/{machine_name}")
    def api_generar_certificado(
        machine_name: str,
        request: Request,
        session: dict = Depends(get_session),
    ):
        from PIL import ImageDraw, ImageFont

        client_ip = request.client.host if request.client else "unknown"
        if not _allow(_gen_rate, client_ip, GEN_MAX_PER_MIN):
            return JSONResponse(
                status_code=429,
                content={"error": "Demasiadas solicitudes. Espera un minuto antes de generar otro certificado."}
            )

        if not machine_name or len(machine_name) > 100:
            return JSONResponse(status_code=400, content={"error": "Nombre de máquina no válido"})

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
        display_name = (
            user_obj.nombre_diploma.strip()
            if user_obj and user_obj.nombre_diploma and user_obj.nombre_diploma.strip()
            else username
        )

        cert_id  = "DL-" + hashlib.sha256(f"{username}:{writeup.maquina}".encode()).hexdigest()[:6].upper()
        date_str = datetime.now().strftime("%d/%m/%Y")

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

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)

        safe     = "".join(c for c in machine_name[:60] if c.isalnum() or c in "-_")
        filename = f"diploma-dockerlabs-{safe}.png"

        return Response(
            content=buf.getvalue(),
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
