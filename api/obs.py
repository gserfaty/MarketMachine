"""Observability: JSON access logs + Prometheus metrics. Imported only by the API, never by Streamlit."""
from __future__ import annotations

import logging
import os
import time
import uuid

from prometheus_client import Counter, Gauge, Histogram, make_asgi_app
from pythonjsonlogger.json import JsonFormatter

access = logging.getLogger("marketmachine.api.access")

REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["method", "route", "status"])
FORECAST_SECONDS = Histogram("forecast_compute_seconds", "Forecast training time", ["horizon"],
                             buckets=(1, 5, 15, 30, 60, 120, 300, 600))
CACHE = Counter("cache_requests_total", "In-process cache lookups", ["kind", "result"])
DATA_AS_OF = Gauge("forecast_data_as_of_timestamp_seconds", "Latest data month behind the forecast (unix)", ["horizon"])
_done = False


def setup() -> None:
    """JSON logs on stderr unless LOG_FORMAT=text. Idempotent."""
    global _done
    if os.environ.get("LOG_FORMAT", "json") == "text" or _done:
        return
    h = logging.StreamHandler()
    h.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger("marketmachine")
    root.addHandler(h)
    root.setLevel(logging.INFO)
    _done = True


async def middleware(request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex
    t0 = time.perf_counter()
    status = 500
    try:
        resp = await call_next(request)
        status = resp.status_code
        resp.headers["X-Request-ID"] = rid
        return resp
    finally:
        dt = time.perf_counter() - t0
        route = getattr(request.scope.get("route"), "path", None) or "unmatched"  # template, not raw path
        REQUESTS.labels(request.method, route, status).inc()
        LATENCY.labels(request.method, route, status).observe(dt)
        access.info("request", extra={"request_id": rid, "method": request.method, "route": route,
                                      "status": status, "duration_ms": round(dt * 1000, 2)})


metrics_app = make_asgi_app()
