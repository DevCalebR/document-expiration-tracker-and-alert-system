from starlette.middleware.base import BaseHTTPMiddleware

from config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if settings.SECURE_HEADERS_ENABLED:
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "no-referrer")
            response.headers.setdefault(
                "Permissions-Policy",
                "camera=(), microphone=(), geolocation=(), interest-cohort=()",
            )
            response.headers.setdefault("Content-Security-Policy", settings.SECURE_HEADERS_CSP)
            if settings.SECURE_HEADERS_HSTS_SECONDS > 0:
                response.headers.setdefault(
                    "Strict-Transport-Security",
                    f"max-age={settings.SECURE_HEADERS_HSTS_SECONDS}; includeSubDomains",
                )
        return response
