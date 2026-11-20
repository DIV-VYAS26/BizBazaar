import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.middleware import BoundaryMiddleware
from app.routers.accounts import router as accounts_router
from app.routers.api import router
from app.routers.commerce import router as commerce_router
from app.routers.metadata import router as metadata_router
from app.routers.operations import router as operations_router
from app.schemas.api import ErrorEnvelope
from app.services.analytics_adapter import RealAnalyticsProvider

logger = logging.getLogger("bizbazaar")


def error_response(request, status, code, message, details=None):
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": getattr(request.state, "request_id", "unavailable"),
            }
        },
    )


def create_app(settings=None, analytics_provider=None):
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app):
        if settings.analytics_mode != "unavailable" and app.state.analytics_provider is None:
            app.state.analytics_provider = RealAnalyticsProvider(
                require_calculations=settings.analytics_mode == "real"
            )
        yield

    application = FastAPI(title="BizBazaar API", version="0.1.0", lifespan=lifespan)
    application.state.settings = settings
    application.state.analytics_provider = analytics_provider
    application.add_middleware(BoundaryMiddleware, settings=settings)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
        expose_headers=["X-Request-ID"],
    )

    @application.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError):
        return error_response(request, exc.status, exc.code, exc.message, exc.details)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Do not reflect arbitrary input values, credentials, or Pydantic exception context.
        details = [
            {"field": ".".join(map(str, item["loc"])), "type": item["type"]}
            for item in exc.errors()[:20]
        ]
        return error_response(request, 422, "INVALID_INPUT", "Request validation failed", details)

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error_response(
            request, exc.status_code, "HTTP_ERROR", "Request could not be handled"
        )

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        # Avoid exception strings/SQL parameters in logs; correlate with a safe request ID.
        logger.error(
            "Unhandled %s request_id=%s",
            type(exc).__name__,
            getattr(request.state, "request_id", "unavailable"),
        )
        return error_response(request, 500, "INTERNAL_ERROR", "Request could not be completed")

    responses = {
        status: {"model": ErrorEnvelope}
        for status in [
            401,
            403,
            404,
            409,
            413,
            422,
            429,
            500,
            503,
        ]
    }
    application.include_router(router, prefix="/api/v1", responses=responses)
    application.include_router(metadata_router, prefix="/api/v1", responses=responses)
    application.include_router(accounts_router, prefix="/api/v1", responses=responses)
    application.include_router(commerce_router, prefix="/api/v1", responses=responses)
    application.include_router(operations_router, prefix="/api/v1", responses=responses)
    return application


app = create_app()
