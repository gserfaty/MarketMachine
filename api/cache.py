"""Optional Redis layer (REDIS_URL): shared forecast cache + per-IP rate limit. Fails open: no Redis or any Redis error = no-op."""
from __future__ import annotations

import json
import logging
import os

from api import models as m
from housing import model

log = logging.getLogger("marketmachine.api")
TTL = 6 * 3600
_client = None
_warned = False


def _warn(e: Exception) -> None:
    global _warned
    if not _warned:
        _warned = True
        log.warning("Redis unavailable (%s); using in-process cache, no rate limit", e)


def client():
    global _client
    url = os.environ.get("REDIS_URL")
    if _client is None and url:
        import redis  # only the API installs redis; the Streamlit app never imports this module
        _client = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
    return _client


def _rkey(key: tuple) -> str:
    return "mm:" + ":".join(map(str, key))


def _enc(v: tuple[model.ForecastResult, m.ModelInfo]) -> str:
    return json.dumps({"res": model.result_to_json(v[0]), "info": v[1].model_dump()})


def _dec(s: str) -> tuple[model.ForecastResult, m.ModelInfo]:
    d = json.loads(s)
    return model.result_from_json(d["res"]), m.ModelInfo(**d["info"])


def load_forecast(key: tuple):
    try:
        r = client()
        raw = r.get(_rkey(key)) if r else None
        return _dec(raw) if raw else None
    except Exception as e:  # noqa: BLE001
        _warn(e)
        return None


def save_forecast(key: tuple, v) -> None:
    try:
        r = client()
        if r:
            r.set(_rkey(key), _enc(v), ex=TTL)
    except Exception as e:  # noqa: BLE001
        _warn(e)


def retry_after(ip: str) -> int | None:
    """Seconds to wait if `ip` is over RATE_LIMIT_PER_MIN (fixed 60 s window), else None."""
    try:
        r = client()
        if not r:
            return None
        k = f"mm:rl:{ip}"
        n = r.incr(k)
        if n == 1:
            r.expire(k, 60)
        if n > int(os.environ.get("RATE_LIMIT_PER_MIN", 60)):
            t = r.ttl(k)
            if t < 0:  # key lost its expiry (crash between INCR and EXPIRE): heal it
                r.expire(k, 60)
                t = 60
            return t
    except Exception as e:  # noqa: BLE001
        _warn(e)
    return None
