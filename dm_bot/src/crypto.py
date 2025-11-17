import hmac, hashlib

def verify_short_token(token: str, secret: str) -> int | None:
    try:
        mid_hex, sig = token.split(".", 1)
        expect = hmac.new(secret.encode(), mid_hex.encode(), hashlib.sha256).hexdigest()[:16]
        if hmac.compare_digest(sig, expect):
            return int(mid_hex, 16)
    except Exception:
        pass
    return None
