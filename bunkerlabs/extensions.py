from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memcached://127.0.0.1:11211",
    swallow_errors=True,
)

get_bunker_db = None
csrf_protect = None
role_required = None
