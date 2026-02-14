import re
from urllib.parse import urlparse

def validate_machine_name(name):
           
    if not name:
        return False, "El nombre de la máquina es obligatorio"
    
    name = name.strip()
    if len(name) > 100:
        return False, "El nombre de la máquina no puede exceder los 100 caracteres"

    if not re.match(r'^[\w\s\-_]+$', name, re.UNICODE):
        return False, "El nombre de la máquina contiene caracteres no permitidos"
        
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

def validate_writeup_type(type_name):
           
    if not type_name:
        return False, "El tipo de writeup es obligatorio"
        
    type_name = type_name.strip().lower()
    if type_name not in ['video', 'texto', 'text']:
        return False, "Tipo de writeup inválido (debe ser 'video' o 'texto')"
        
    return True, None

def validate_image_content(file_stream):
           
    try:
        from PIL import Image

        header = file_stream.read(1024)
        file_stream.seek(0)
        
        if not header:
            return False, "Archivo vacío"

        img = Image.open(file_stream)
        img.verify()                   
        
        if img.format not in ['JPEG', 'PNG', 'GIF', 'WEBP']:
                                            
            file_stream.seek(0)
            return False, f"Formato de imagen no permitido: {img.format}"

        file_stream.seek(0)
        return True, None
    except Exception as e:
        file_stream.seek(0)
        return False, "El archivo no es una imagen válida o está corrupto"
