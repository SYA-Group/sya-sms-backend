# backend/utils/sms_utils.py
import logging
import time
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Replace with the exact domains of SMS providers you trust
ALLOWED_DOMAINS = {
    "api.trusted-sms.com",
    "api.another-sms.com",
    "rest.nexmo.com",
    "api.infobip.com",
    "api.ng.termii.com",
   'bulk.whysms.com',
}

def is_allowed_api_url(url: str) -> bool:
    """Return True if hostname is in whitelist (basic SSRF protection)."""
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        return hostname in ALLOWED_DOMAINS
    except Exception:
        return False

def mask_token(token: str) -> str:
    if not token:
        return ""
    if len(token) <= 8:
        return "****"
    return token[:4] + "…" + token[-4:]

def retry_post(session_post, url, json_payload, headers, timeout=10, retries=3):
    """
    Simple exponential backoff retry wrapper around requests.Session.post.
    session_post: e.g., session.post
    """
    backoff = 1.0
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            resp = session_post(url, json=json_payload, headers=headers, timeout=timeout)
            return resp
        except Exception as ex:
            last_exc = ex
            logger.warning("POST attempt %d failed for %s: %s (waiting %.1fs)", attempt, url, ex, backoff)
            time.sleep(backoff)
            backoff *= 2
    raise last_exc
