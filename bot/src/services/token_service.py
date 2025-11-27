import hmac
import hashlib
from ..config import settings

def make_short_token(message_id: int) -> str:
    if not settings.SHARED_SECRET:
        raise RuntimeError("SECRET for short-token is not set")

    mid_hex = format(message_id, "x")
    sig = hmac.new(
        settings.SHARED_SECRET.encode(),
        mid_hex.encode(),
        hashlib.sha256
    ).hexdigest()[:16]

    return f"{mid_hex}.{sig}"
