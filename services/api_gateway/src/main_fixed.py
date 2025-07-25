"""
SECURITY FIXED FastAPI application for Diet Issue Tracker API Gateway.
Added authentication middleware, rate limiting, and secure error handling.
"""

import logging
import os
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

# Import security and error handling
from middleware.auth import get_current_user_optional
from routes.airtable_webhooks import router as webhooks_router
from routes.batch_management import router as batch_router
from routes.enhanced_issues_fixed import router as enhanced_issues_router
from routes.monitoring import router as monitoring_router
from starlette.middleware.base import BaseHTTPMiddleware
from utils.error_handling import ErrorCode, ServiceError, handle_service_error

# Import monitoring utilities
try:
    from .monitoring.logger import (
        RequestContextMiddleware,
        log_api_request,
        log_error,
    )
    from .monitoring.metrics import health_checker, metrics_collector
except ImportError:
    # Fallback for standalone execution
    from monitoring.logger import (
        RequestContextMiddleware,
        log_api_request,
        log_error,
    )
    from monitoring.metrics import health_checker, metrics_collector

# Import cache and services
try:
    from .batch.task_queue import task_queue
    from .cache.redis_client import RedisCache
except ImportError:
    # Fallback for standalone execution
    from batch.task_queue import task_queue
    from cache.redis_client import RedisCache


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app with enhanced security
app = FastAPI(
    title="Seiji Watch API Gateway",
    description="Secure API Gateway for Diet Issue Tracker with dual-level policy issue extraction",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
)

# Security middleware - CORS with strict settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        [
            "https://seiji-watch.com",
            "https://www.seiji-watch.com",
            "http://localhost:3000",  # Development only
        ]
        if os.getenv("ENVIRONMENT") != "production"
        else ["https://seiji-watch.com", "https://www.seiji-watch.com"]
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
    max_age=3600,
)

# Trusted host middleware for additional security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "api.seiji-watch.com",
        "*.seiji-watch.com",
        "localhost",  # Development only
        "127.0.0.1",  # Development only
    ],
)

# Security headers middleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


app.add_middleware(SecurityHeadersMiddleware)

# Request context and logging middleware
app.add_middleware(RequestContextMiddleware)

# Request tracking middleware


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Track requests for monitoring and rate limiting."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Get user info if available
        user = None
        try:
            auth_header = request.headers.get("authorization")
            if auth_header:
                user = await get_current_user_optional(auth_header)
        except Exception:
            pass

        # Log request
        log_api_request(
            method=request.method,
            url=str(request.url),
            user_id=user.get("user_id") if user else None,
            ip_address=request.client.host if request.client else None,
        )

        # Process request
        try:
            response = await call_next(request)

            # Log successful response
            metrics_collector.record_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration=time.time() - start_time,
            )

            return response

        except Exception as e:
            # Log error
            log_error(
                error=str(e),
                context={
                    "method": request.method,
                    "url": str(request.url),
                    "user_id": user.get("user_id") if user else None,
                },
            )

            # Convert to appropriate HTTP response
            if isinstance(e, ServiceError):
                raise handle_service_error(e)
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": ErrorCode.UNEXPECTED_ERROR.value,
                        "message": "An unexpected error occurred",
                    },
                )


app.add_middleware(RequestTrackingMiddleware)

# Global exception handler


@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    """Handle ServiceError exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code.value,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured error response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": exc.detail,
            "status_code": exc.status_code,
        },
    )


# Import and register routes

# Register all routers with security
app.include_router(enhanced_issues_router, tags=["Enhanced Issues"])
app.include_router(webhooks_router, tags=["Webhooks"])
app.include_router(batch_router, tags=["Batch Processing"])
app.include_router(monitoring_router, tags=["Monitoring"])

# Health check endpoint (no authentication required)


@app.get("/health", tags=["Health"])
async def health_check():
    """Application health check."""
    try:
        health_status = await health_checker.check_all_services()

        return {
            "status": "healthy" if health_status["overall_healthy"] else "unhealthy",
            "timestamp": health_status["timestamp"],
            "services": health_status["services"],
            "version": "1.0.0",
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e), "version": "1.0.0"},
        )


# Startup event


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Seiji Watch API Gateway...")

    try:
        # Initialize Redis cache
        redis_cache = RedisCache()
        await redis_cache.connect()
        logger.info("Redis cache connected")

        # Initialize metrics collector
        metrics_collector.start()
        logger.info("Metrics collection started")

        # Initialize task queue
        await task_queue.start()
        logger.info("Task queue started")

        logger.info("API Gateway startup completed successfully")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


# Shutdown event


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down API Gateway...")

    try:
        # Stop task queue
        await task_queue.stop()

        # Stop metrics collection
        metrics_collector.stop()

        # Close Redis connection
        redis_cache = RedisCache()
        await redis_cache.disconnect()

        logger.info("API Gateway shutdown completed")

    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Root endpoint


@app.get("/", tags=["Root"])
async def root():
    """API Gateway root endpoint."""
    return {
        "message": "Seiji Watch API Gateway",
        "version": "1.0.0",
        "status": "operational",
        "features": [
            "Dual-level policy issue extraction",
            "Secure authentication with JWT",
            "Rate limiting and security controls",
            "Comprehensive monitoring and logging",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    # Development server
    uvicorn.run(
        "main_fixed:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
