from collections import OrderedDict
from threading import Lock
from time import monotonic
from uuid import uuid4

from starlette.responses import JSONResponse

from app.core.security import SESSION_COOKIE, digest


class BoundaryMiddleware:
    """Bound request bodies before multipart parsing; limit local-demo request bursts.

    The limiter is per process. A public multi-worker deployment needs a shared ingress limiter.
    """

    def __init__(self, app, settings):
        self.app = app
        self.settings = settings
        self.buckets = OrderedDict()
        self.lock = Lock()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        headers = dict(scope.get("headers", []))

        async def fail(status, code, message):
            response = JSONResponse(
                {
                    "error": {
                        "code": code,
                        "message": message,
                        "details": None,
                        "request_id": request_id,
                    }
                },
                status_code=status,
            )
            await response(scope, receive, safe_send)

        async def safe_send(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-request-id", request_id.encode()),
                    (b"x-content-type-options", b"nosniff"),
                    (b"cache-control", b"no-store"),
                ]
            await send(message)

        cookie = headers.get(b"cookie", b"").decode("latin1")
        from http.cookies import SimpleCookie

        parsed_cookie = SimpleCookie()
        try:
            parsed_cookie.load(cookie)
        except Exception:
            pass
        value = parsed_cookie.get(SESSION_COOKIE)
        client = scope.get("client")
        key = digest(value.value) if value else digest(str(client[0] if client else "unknown"))
        now = monotonic()
        with self.lock:
            start, count = self.buckets.pop(key, (now, 0))
            if now - start >= 60:
                start, count = now, 0
            count += 1
            self.buckets[key] = (start, count)
            if len(self.buckets) > 1024:
                self.buckets.popitem(last=False)
        if count > 120:
            return await fail(429, "RATE_LIMITED", "Request limit reached; retry later")

        chunks = []
        size = 0
        while True:
            part = await receive()
            if part["type"] == "http.disconnect":
                return
            size += len(part.get("body", b""))
            if size > self.settings.max_body_bytes:
                return await fail(413, "BODY_TOO_LARGE", "Request body exceeds the size limit")
            chunks.append(part.get("body", b""))
            if not part.get("more_body", False):
                break
        body = b"".join(chunks)
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, safe_send)
