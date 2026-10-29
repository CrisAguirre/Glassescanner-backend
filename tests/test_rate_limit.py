import asyncio
import os

os.environ["ENVIRONMENT"] = "test"
os.environ["ADMIN_KEY"] = "test-admin-key-123456"
os.environ["MONGODB_URI"] = ""
os.environ.pop("RENDER", None)

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.main import RateLimitMiddleware, client_ip


def make_request(client=("1.2.3.4", 1234), forwarded_for=None):
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "scheme": "http",
        "server": ("testserver", 80),
        "root_path": "",
        "path": "/frames",
        "query_string": b"",
        "headers": headers,
        "client": client,
    }
    return Request(scope)


def test_client_ip_ignores_forwarded_for():
    """Un cliente no puede elegir su propia clave de rate limit."""
    req = make_request(forwarded_for="9.9.9.9, 8.8.8.8")
    assert client_ip(req) == "1.2.3.4"


async def _ok(_request):
    return JSONResponse({"ok": True})


def test_rate_limit_cannot_be_bypassed_with_forwarded_for():
    """Rotar X-Forwarded-For no renueva el cupo: la IP sale del socket."""
    middleware = RateLimitMiddleware(app=None, limit_per_minute=2)

    async def run():
        codes = []
        for i in range(3):
            req = make_request(forwarded_for=f"10.0.0.{i}")
            res = await middleware.dispatch(req, _ok)
            codes.append(res.status_code)
        return codes

    assert asyncio.run(run()) == [200, 200, 429]
