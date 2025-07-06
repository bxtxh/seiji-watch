"""FastAPI application for Diet Issue Tracker API Gateway."""

import os
import logging
import time
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, List

# Import monitoring utilities
from .monitoring.logger import (
    structured_logger, RequestContextMiddleware,
    log_api_request, log_error, log_security_event
)
from .monitoring.metrics import (
    metrics_collector, health_checker, RequestTracker
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiting storage
rate_limit_storage: Dict[str, List[float]] = defaultdict(list)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        response.headers["Content-Security-Policy"] = csp
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # 1 minute window
    
    def get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Use forwarded IP if available (for load balancer scenarios)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to direct client IP
        client_ip = request.client.host if request.client else "unknown"
        return client_ip
    
    def is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited."""
        now = time.time()
        
        # Clean old requests outside the window
        rate_limit_storage[client_id] = [
            timestamp for timestamp in rate_limit_storage[client_id]
            if now - timestamp < self.window_size
        ]
        
        # Check if client exceeded rate limit
        if len(rate_limit_storage[client_id]) >= self.requests_per_minute:
            return True
        
        # Record this request
        rate_limit_storage[client_id].append(now)
        return False
    
    async def dispatch(self, request: Request, call_next):
        client_id = self.get_client_id(request)
        
        if self.is_rate_limited(client_id):
            # Log security event
            log_security_event(
                'rate_limit_exceeded',
                'warning',
                f"Rate limit exceeded for client: {client_id}",
                client_id=client_id[:32],  # Truncate for privacy
                endpoint=str(request.url.path)
            )
            
            # Record metrics
            metrics_collector.record_rate_limit_violation(client_id, str(request.url.path))
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": 60
                }
            )
        
        return await call_next(request)

# Create FastAPI app
app = FastAPI(
    title="Diet Issue Tracker API",
    description="API Gateway for Diet Issue Tracker MVP",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging and monitoring requests."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        with RequestTracker(metrics_collector):
            try:
                response = await call_next(request)
                
                # Calculate response time
                response_time_ms = (time.time() - start_time) * 1000
                
                # Log request
                log_api_request(
                    request,
                    response.status_code,
                    response_time_ms,
                    response_size=response.headers.get('content-length', 0)
                )
                
                # Record metrics
                metrics_collector.record_request(
                    request.method,
                    request.url.path,
                    response.status_code,
                    response_time_ms
                )
                
                return response
                
            except Exception as e:
                response_time_ms = (time.time() - start_time) * 1000
                
                # Log error
                log_error(
                    f"Request failed: {request.method} {request.url.path}",
                    error=e,
                    response_time_ms=response_time_ms
                )
                
                # Record error metrics
                metrics_collector.record_error(
                    error_type=type(e).__name__,
                    endpoint=request.url.path,
                    details={'method': request.method}
                )
                
                raise

# Trust only specific hosts in production
allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# Add request context for logging
app.add_middleware(RequestContextMiddleware)

# Add request logging and monitoring
app.add_middleware(RequestLoggingMiddleware)

# Add security headers
app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting (5 req/s = 300 req/min for unauthenticated users)
app.add_middleware(RateLimitMiddleware, requests_per_minute=300)

# CORS middleware - Configure properly for production
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["X-Total-Count"]
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        # Run all health checks
        health_results = await health_checker.run_checks()
        overall_status = health_checker.get_overall_status(health_results)
        
        response_data = {
            "status": overall_status,
            "service": "api-gateway",
            "version": "1.0.0",
            "timestamp": time.time(),
            "checks": {
                name: {
                    "status": result.status,
                    "response_time_ms": result.response_time_ms,
                    "details": result.details
                }
                for name, result in health_results.items()
            },
            "metrics_summary": metrics_collector.get_summary_stats()
        }
        
        # Return appropriate HTTP status
        status_code = 200 if overall_status == 'healthy' else 503
        return JSONResponse(content=response_data, status_code=status_code)
        
    except Exception as e:
        log_error("Health check failed", error=e)
        return JSONResponse(
            content={
                "status": "unhealthy",
                "service": "api-gateway",
                "version": "1.0.0",
                "error": str(e)
            },
            status_code=503
        )

# Metrics endpoints
@app.get("/metrics")
async def get_metrics():
    """Get metrics in Prometheus format."""
    try:
        metrics_data = metrics_collector.get_metrics_for_export('prometheus')
        return PlainTextResponse(
            content=metrics_data,
            media_type='text/plain; charset=utf-8'
        )
    except Exception as e:
        log_error("Failed to export metrics", error=e)
        raise HTTPException(status_code=500, detail="Failed to export metrics")

@app.get("/metrics/json")
async def get_metrics_json():
    """Get metrics in JSON format."""
    try:
        metrics_data = metrics_collector.get_metrics_for_export('json')
        return JSONResponse(content=metrics_data)
    except Exception as e:
        log_error("Failed to export metrics as JSON", error=e)
        raise HTTPException(status_code=500, detail="Failed to export metrics")

@app.get("/status")
async def get_status():
    """Get detailed system status."""
    try:
        return JSONResponse(content={
            "service": "api-gateway",
            "version": "1.0.0",
            "status": "operational",
            "metrics": metrics_collector.get_summary_stats(),
            "timestamp": time.time()
        })
    except Exception as e:
        log_error("Failed to get system status", error=e)
        raise HTTPException(status_code=500, detail="Failed to get system status")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Diet Issue Tracker API Gateway",
        "docs": "/docs",
        "health": "/health"
    }

# Include routers
from .routes import issues, speeches

app.include_router(issues.router)
app.include_router(speeches.router)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)