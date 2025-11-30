import re
from urllib.parse import urlparse

def validate_machine_name(name):
    """
    Validates machine name.
    Allowed: Alphanumeric, spaces, hyphens, underscores.
    Length: 1-100 characters.
    """
    if not name:
        return False, "El nombre de la máquina es obligatorio"
    
    name = name.strip()
    if len(name) > 100:
        return False, "El nombre de la máquina no puede exceder los 100 caracteres"
    
    # Allow alphanumeric, spaces, hyphens, underscores and unicode characters
    if not re.match(r'^[\w\s\-_]+$', name, re.UNICODE):
        return False, "El nombre de la máquina contiene caracteres no permitidos"
        
    return True, None

def validate_author_name(name):
    """
    Validates author name.
    Allowed: Unicode letters, digits, spaces, hyphens, underscores.
    Blocked: Dangerous characters that could be used for XSS attacks.
    Length: 1-100 characters.
    """
    if not name:
        return False, "El nombre del autor es obligatorio"
    
    name = name.strip()
    if len(name) > 100:
        return False, "El nombre del autor no puede exceder los 100 caracteres"
    
    # Block dangerous characters that could be used for XSS attacks
    dangerous_chars = ['<', '>', '"', "'", '/', '\\', '`', '&']
    for char in dangerous_chars:
        if char in name:
            return False, "El nombre del autor contiene caracteres no permitidos"
    
    # Block control characters (newlines, tabs, null bytes, etc.)
    if re.search(r'[\x00-\x1F\x7F]', name):
        return False, "El nombre del autor contiene caracteres no permitidos"
    
    # Allow Unicode letters, digits, spaces, hyphens, and underscores
    # \w matches Unicode word characters (letters and digits from any language)
    if not re.match(r'^[\w\s\-]+$', name, re.UNICODE):
        return False, "El nombre del autor contiene caracteres no permitidos"
        
    return True, None

def validate_url(url):
    """
    Validates URL format and safety.
    Allows various URL formats while blocking dangerous patterns.
    """
    if not url:
        return True, None # Optional URL is valid if empty
        
    url = url.strip()
    
    if len(url) > 2000:
        return False, "La URL es demasiado larga (máximo 2000 caracteres)"
    
    # Check for dangerous characters that could be used for XSS
    dangerous_chars = ['"', "'", '<', '>', '`', '\n', '\r', '\t']
    for char in dangerous_chars:
        if char in url:
            return False, f"La URL contiene caracteres no permitidos"
            
    # Check for dangerous schemes (case insensitive)
    lower_url = url.lower()
    if lower_url.startswith(('javascript:', 'data:', 'vbscript:', 'file:', 'about:')):
        return False, "Esquema de URL no permitido"

    try:
        # If URL has a scheme, validate it
        parsed = urlparse(url)
        if parsed.scheme and parsed.scheme not in ('http', 'https', ''):
            return False, "Solo se permiten URLs con http o https"
    except Exception:
        return False, "Error al analizar la URL"
        
    return True, None

def validate_writeup_type(type_name):
    """
    Validates writeup type.
    Allowed: 'video', 'texto' (case insensitive)
    """
    if not type_name:
        return False, "El tipo de writeup es obligatorio"
        
    type_name = type_name.strip().lower()
    if type_name not in ['video', 'texto', 'text']:
        return False, "Tipo de writeup inválido (debe ser 'video' o 'texto')"
        
    return True, None

def validate_image_content(file_stream):
    """
    Validates that the file stream contains a valid image using PIL.
    Resets stream position after check.
    """
    try:
        from PIL import Image
        
        # Read initial bytes to check header (optional but good for quick fail)
        header = file_stream.read(1024)
        file_stream.seek(0)
        
        if not header:
            return False, "Archivo vacío"

        img = Image.open(file_stream)
        img.verify() # Verify integrity
        
        if img.format not in ['JPEG', 'PNG', 'GIF', 'WEBP']:
             # Reset stream before returning
            file_stream.seek(0)
            return False, f"Formato de imagen no permitido: {img.format}"
            
        # Reset stream for subsequent saving
        file_stream.seek(0)
        return True, None
    except Exception as e:
        file_stream.seek(0)
        return False, "El archivo no es una imagen válida o está corrupto"
