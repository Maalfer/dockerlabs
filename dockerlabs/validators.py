import re
from urllib.parse import urlparse
import bleach

def validate_machine_name(name):
           
    if not name:
        return False, "El nombre de la máquina es obligatorio"
    
    name = name.strip()
    if len(name) > 100:
        return False, "El nombre de la máquina no puede exceder los 100 caracteres"

    if not re.match(r'^[\w\s\-_]+$', name, re.UNICODE):
        return False, "El nombre de la máquina contiene caracteres no permitidos"
        
    return True, None

def validate_team_name(name):
    """Valida el nombre de un equipo: longitud 3-50 y charset seguro
    (letras, números, espacios, guion, guion bajo y punto). Evita XSS
    porque el nombre se incrusta en notificaciones renderizadas."""
    if not name:
        return False, "El nombre del equipo es obligatorio"
    name = name.strip()
    if len(name) < 3 or len(name) > 50:
        return False, "El nombre del equipo debe tener entre 3 y 50 caracteres"
    if not re.match(r'^[\w\s\-_.]+$', name, re.UNICODE):
        return False, "El nombre del equipo solo puede contener letras, números, espacios, guiones, guion bajo y puntos"
    return True, None

def validate_author_name(name):
           
    if not name:
        return False, "El nombre del autor es obligatorio"
    
    name = name.strip()
    if len(name) > 100:
        return False, "El nombre del autor no puede exceder los 100 caracteres"

    dangerous_chars = ['<', '>', '"', "'", '/', '\\', '`', '&']
    for char in dangerous_chars:
        if char in name:
            return False, "El nombre del autor contiene caracteres no permitidos"

    if re.search(r'[\x00-\x1F\x7F]', name):
        return False, "El nombre del autor contiene caracteres no permitidos"

    if not re.match(r'^[\w\s\-]+$', name, re.UNICODE):
        return False, "El nombre del autor contiene caracteres no permitidos"
        
    return True, None

def validate_url(url):
           
    if not url:
        return True, None                                 
        
    url = url.strip()
    
    if len(url) > 2000:
        return False, "La URL es demasiado larga (máximo 2000 caracteres)"

    dangerous_chars = ['"', "'", '<', '>', '`', '\n', '\r', '\t']
    for char in dangerous_chars:
        if char in url:
            return False, f"La URL contiene caracteres no permitidos"

    lower_url = url.lower()
    if lower_url.startswith(('javascript:', 'data:', 'vbscript:', 'file:', 'about:')):
        return False, "Esquema de URL no permitido"

    try:
                                          
        parsed = urlparse(url)
        if parsed.scheme and parsed.scheme not in ('http', 'https', ''):
            return False, "Solo se permiten URLs con http o https"
    except Exception:
        return False, "Error al analizar la URL"
        
    return True, None

def is_public_http_url(url):
    """Comprueba que una URL http(s) apunta a un host PUBLICO (mitiga SSRF).
    Resuelve el host y rechaza IPs privadas, loopback, link-local, reservadas
    o multicast. Devuelve (bool, motivo)."""
    import ipaddress, socket
    try:
        parsed = urlparse((url or "").strip())
    except Exception:
        return False, "URL inválida"
    if parsed.scheme not in ("http", "https"):
        return False, "Esquema de URL no permitido"
    host = parsed.hostname
    if not host:
        return False, "URL sin host"
    h = host.lower()
    if h == "localhost" or h.endswith(".localhost") or h.endswith(".local") or h.endswith(".internal"):
        return False, "Host no permitido"
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except Exception:
        return False, "No se pudo resolver el host"
    for info in infos:
        ip = info[4][0]
        try:
            ipobj = ipaddress.ip_address(ip)
        except ValueError:
            return False, "Dirección IP inválida"
        if (not ipobj.is_global) or ipobj.is_private or ipobj.is_loopback \
                or ipobj.is_link_local or ipobj.is_reserved or ipobj.is_multicast:
            return False, "La URL apunta a una dirección interna no permitida"
    return True, None

def validate_writeup_type(type_name):
           
    if not type_name:
        return False, "El tipo de writeup es obligatorio"
        
    type_name = type_name.strip().lower()
    if type_name not in ['video', 'texto', 'text']:
        return False, "Tipo de writeup inválido (debe ser 'video' o 'texto')"
        
    return True, None

def validate_image_content(file_stream, max_size_mb=5):

    try:
        from PIL import Image

        header = file_stream.read(1024)
        file_stream.seek(0)

        if not header:
            return False, "Archivo vacío"

        # Validate file size
        file_stream.seek(0, 2)  # Seek to end
        file_size = file_stream.tell()
        file_stream.seek(0)  # Seek back to start

        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            return False, f"El archivo es demasiado grande (máximo {max_size_mb}MB)"

        img = Image.open(file_stream)
        img.verify()

        if img.format not in ['JPEG', 'PNG', 'GIF', 'WEBP', 'BMP', 'TIFF', 'AVIF', 'ICO', 'PPM', 'TGA']:

            file_stream.seek(0)
            return False, f"Formato de imagen no permitido: {img.format}"

        file_stream.seek(0)
        return True, None
    except Exception as e:
        file_stream.seek(0)
        return False, "El archivo no es una imagen válida o está corrupto"

def sanitize_html(text, allowed_tags=None, allowed_attributes=None):
    """
    Sanitiza texto HTML para prevenir XSS.
    Por defecto, permite etiquetas básicas de formato.
    """
    if not text:
        return text

    if allowed_tags is None:
        allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li', 'code', 'pre']

    if allowed_attributes is None:
        allowed_attributes = {
            'a': ['href', 'title'],
            '*': ['class']
        }

    try:
        return bleach.clean(
            text,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )
    except Exception:
        return text

def sanitize_text(text):
    """
    Sanitiza texto plano eliminando cualquier HTML/JS potencialmente peligroso.
    """
    if not text:
        return text

    try:
        return bleach.clean(text, tags=[], attributes={}, strip=True)
    except Exception:
        return text

def validate_password_complexity(password):
    """
    Valida la complejidad de la contraseña.
    Requiere: mínimo 8 caracteres, 1 mayúscula, 1 minúscula, 1 número, 1 carácter especial
    """
    if not password:
        return False, "La contraseña es obligatoria"
    
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    
    if len(password) > 128:
        return False, "La contraseña no puede exceder 128 caracteres"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    if not (has_upper and has_lower and has_digit and has_special):
        return False, "La contraseña debe contener al menos una mayúscula, una minúscula, un número y un carácter especial (!@#$%^&*()_+-=[]{}|;:,.<>?)"
    
    return True, None
