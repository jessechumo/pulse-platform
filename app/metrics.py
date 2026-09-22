import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "pulse_http_requests_total",
    "Total HTTP requests processed",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "pulse_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Records request count and latency, keyed by the matched route template.

    Using the route template (e.g. "/items/{id}") instead of the raw path
    keeps cardinality bounded -- real path params would otherwise blow up
    the number of Prometheus label combinations.
    """

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        path = _route_template(request)
        REQUEST_COUNT.labels(request.method, path, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, path).observe(duration)

        return response


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    if route is not None:
        return route.path
    return request.url.path


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
