from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configurar rate limiting para Cloudflare
# Usamos memoria local ya que Cloudflare maneja el rate limiting a nivel de red
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
    swallow_errors=True,
)

get_bunker_db = None
csrf_protect = None
role_required = None
