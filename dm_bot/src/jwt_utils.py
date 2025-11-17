import jwt
import time
from typing import Dict, Any

def make_token(data: Dict[str, Any], secret: str, ttl_seconds: int = 900) -> str:
    payload = {
        **data,
        "exp": int(time.time()) + ttl_seconds,
        "iat": int(time.time()),
        "typ": "claim"
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def verify_token(token: str, secret: str) -> Dict[str, Any] | None:
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except Exception:
        return None
