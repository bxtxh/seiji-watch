"""FastAPI application for Diet Issue Tracker API Gateway."""

import logging
import os
import time
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Import monitoring utilities
try:
    from .monitoring.logger import (
        RequestContextMiddleware,
        log_api_request,
        log_error,
        log_security_event,
        structured_logger,
    )
    from .monitoring.metrics import RequestTracker, health_checker, metrics_collector
except ImportError:
    # Fallback for standalone execution
    from monitoring.logger import (
        RequestContextMiddleware,
        log_api_request,
        log_error,
        log_security_event,
    )
    from monitoring.metrics import RequestTracker, health_checker, metrics_collector

# Import cache and services
try:
    from shared.clients.airtable import AirtableClient

    from .batch.member_tasks import MemberTaskManager
    from .batch.task_queue import batch_processor, task_queue
    from .cache.redis_client import RedisCache
    from .services.member_service import MemberService
    from .services.policy_analysis_service import PolicyAnalysisService
except ImportError:
    # Fallback for standalone execution
    from batch.member_tasks import MemberTaskManager
    from batch.task_queue import task_queue
    from cache.redis_client import RedisCache

    from services.member_service import MemberService
    from services.policy_analysis_service import PolicyAnalysisService
    from shared.clients.airtable import AirtableClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Rate limiting storage
rate_limit_storage: dict[str, list[float]] = defaultdict(list)

# Initialize services
redis_cache = RedisCache()
airtable_client = AirtableClient()
member_service = MemberService(airtable_client, redis_cache)
policy_analysis_service = PolicyAnalysisService(airtable_client, redis_cache)

# Initialize batch processing
airtable_config = {
    "api_key": os.getenv("AIRTABLE_API_KEY"),
    "base_id": os.getenv("AIRTABLE_BASE_ID"),
}
redis_config = {"url": os.getenv("REDIS_URL", "redis://localhost:6379")}
member_task_manager = MemberTaskManager(task_queue, airtable_config, redis_config)


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

        # Content Security Policy (development-friendly)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "style-src-elem 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com; "
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
            timestamp
            for timestamp in rate_limit_storage[client_id]
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
                "rate_limit_exceeded",
                "warning",
                f"Rate limit exceeded for client: {client_id}",
                client_id=client_id[:32],  # Truncate for privacy
                endpoint=str(request.url.path),
            )

            # Record metrics
            metrics_collector.record_rate_limit_violation(
                client_id, str(request.url.path)
            )

            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": 60,
                },
            )

        return await call_next(request)


# Create FastAPI app
app = FastAPI(
    title="Diet Issue Tracker API",
    description="API Gateway for Diet Issue Tracker MVP",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# Application lifecycle events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        # Initialize Redis connection
        await redis_cache.connect()
        logger.info("Redis cache connected successfully")

        # Warm up member cache
        warmup_result = await member_service.warmup_member_cache()
        if warmup_result["success"]:
            logger.info(
                f"Member cache warmed up with {warmup_result['cached_members']} members"
            )
        else:
            logger.warning(
                f"Member cache warmup failed: "
                f"{warmup_result.get('error', 'Unknown error')}"
            )

    except Exception as e:
        logger.error(f"Startup initialization failed: {e}")
        # Continue startup even if cache fails (graceful degradation)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown."""
    try:
        await redis_cache.disconnect()
        logger.info("Redis cache disconnected")
    except Exception as e:
        logger.error(f"Shutdown cleanup failed: {e}")


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
                    response_size=response.headers.get("content-length", 0),
                )

                # Record metrics
                metrics_collector.record_request(
                    request.method,
                    request.url.path,
                    response.status_code,
                    response_time_ms,
                )

                return response

            except Exception as e:
                response_time_ms = (time.time() - start_time) * 1000

                # Log error
                log_error(
                    f"Request failed: {request.method} {request.url.path}",
                    error=e,
                    response_time_ms=response_time_ms,
                )

                # Record error metrics
                metrics_collector.record_error(
                    error_type=type(e).__name__,
                    endpoint=request.url.path,
                    details={"method": request.method},
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

# Add rate limiting (development: 1000 req/min for testing)
app.add_middleware(RateLimitMiddleware, requests_per_minute=1000)

# CORS middleware - Step 2: Specific origin and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080",
    ],  # Support frontend ports
    allow_credentials=False,  # Keep False for security
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "accept",
        "accept-language",
        "authorization",
        "content-language",
        "content-type",
        "x-requested-with",
        "x-csrf-token",
        "x-request-id",  # Add our custom headers
    ],
    expose_headers=["X-Total-Count"],
    max_age=600,
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        # Run all health checks
        health_results = await health_checker.run_checks()
        overall_status = health_checker.get_overall_status(health_results)

        # Add Redis and member service health checks
        redis_health = await redis_cache.health_check()
        airtable_health = await airtable_client.health_check()
        member_cache_health = await member_service.get_cache_health()

        response_data = {
            "status": overall_status,
            "service": "api-gateway",
            "version": "1.0.0",
            "timestamp": time.time(),
            "checks": {
                name: {
                    "status": result.status,
                    "response_time_ms": result.response_time_ms,
                    "details": result.details,
                }
                for name, result in health_results.items()
            },
            "external_services": {
                "redis": {"healthy": redis_health},
                "airtable": {"healthy": airtable_health},
                "member_cache": member_cache_health,
            },
            "metrics_summary": metrics_collector.get_summary_stats(),
        }

        # Return appropriate HTTP status (allow degraded as 200 for development)
        status_code = 200 if overall_status in ["healthy", "degraded"] else 503
        return JSONResponse(content=response_data, status_code=status_code)

    except Exception as e:
        log_error("Health check failed", error=e)
        return JSONResponse(
            content={
                "status": "unhealthy",
                "service": "api-gateway",
                "version": "1.0.0",
                "error": str(e),
            },
            status_code=503,
        )


# Metrics endpoints
@app.get("/metrics")
async def get_metrics():
    """Get metrics in Prometheus format."""
    try:
        metrics_data = metrics_collector.get_metrics_for_export("prometheus")
        return PlainTextResponse(
            content=metrics_data, media_type="text/plain; charset=utf-8"
        )
    except Exception as e:
        log_error("Failed to export metrics", error=e)
        raise HTTPException(status_code=500, detail="Failed to export metrics")


@app.get("/metrics/json")
async def get_metrics_json():
    """Get metrics in JSON format."""
    try:
        metrics_data = metrics_collector.get_metrics_for_export("json")
        return JSONResponse(content=metrics_data)
    except Exception as e:
        log_error("Failed to export metrics as JSON", error=e)
        raise HTTPException(status_code=500, detail="Failed to export metrics")


@app.get("/status")
async def get_status():
    """Get detailed system status."""
    try:
        return JSONResponse(
            content={
                "service": "api-gateway",
                "version": "1.0.0",
                "status": "operational",
                "metrics": metrics_collector.get_summary_stats(),
                "timestamp": time.time(),
            }
        )
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
        "health": "/health",
    }


# Include routers
from .routes import (
    airtable_webhooks,
    batch_management,
    bills,
    enhanced_issues,
    issues,
    monitoring,
    speeches,
)

app.include_router(issues.router)
app.include_router(enhanced_issues.router)
app.include_router(airtable_webhooks.router)
app.include_router(batch_management.router)
app.include_router(monitoring.router)
app.include_router(speeches.router)
app.include_router(bills.router)


# Basic API endpoints for MVP
@app.get("/embeddings/stats")
async def get_embedding_stats():
    """Get embedding statistics from real Airtable data."""
    try:
        # Get real data counts from Airtable
        bills = await airtable_client.list_bills(max_records=1000)
        votes = await airtable_client.list_votes(max_records=1000)

        bills_count = len(bills)
        votes_count = len(votes)

        return {
            "status": "healthy",
            "bills": bills_count,
            "votes": votes_count,
            "speeches": 0,  # Not implemented yet
            "message": (
                f"Real data integration complete - "
                f"{bills_count} bills, {votes_count} votes"
            ),
        }
    except Exception as e:
        log_error("Failed to get embedding stats", error=e)
        return {
            "status": "error",
            "bills": 0,
            "votes": 0,
            "speeches": 0,
            "message": f"Failed to fetch real data: {str(e)}",
        }


@app.post("/search")
async def search_bills(request: Request):
    """Search bills endpoint using real Airtable data."""
    try:
        # Parse request body
        body = await request.json()
        query = body.get("query", "")
        limit = body.get("limit", 10)
        body.get("min_certainty", 0.7)

        if not query.strip():
            return {
                "success": False,
                "message": "検索クエリが必要です",
                "results": [],
                "total_found": 0,
            }

        # Search in Airtable using structured fields
        search_formula = f"""OR(
            SEARCH('{query}', {{Name}}) > 0,
            SEARCH('{query}', {{Bill_Status}}) > 0,
            SEARCH('{query}', {{Category}}) > 0,
            SEARCH('{query}', {{Submitter}}) > 0,
            SEARCH('{query}', {{Stage}}) > 0,
            SEARCH('{query}', {{Bill_Number}}) > 0
        )"""

        # Get matching bills from Airtable
        matching_bills = await airtable_client.list_bills(
            filter_formula=search_formula,
            max_records=limit * 2,  # Get more results to account for processing
        )

        # Transform results to expected format
        search_results = []
        for i, bill in enumerate(matching_bills[:limit]):
            fields = bill.get("fields", {})
            name = fields.get("Name", "")
            notes = fields.get("Notes", "")

            # Extract basic info from notes if available
            result = {
                "bill_id": bill.get("id"),
                "title": name[:100] if name else f"法案 {i + 1}",
                "summary": notes[:200] + "..." if len(notes) > 200 else notes,
                "status": "実データ",
                "search_method": "airtable_text",
                "relevance_score": 0.8,  # Static for now, would need vector search for dynamic scoring
                "category": "実データ統合",
                "stage": "データ確認済み",
                "related_issues": [query],
            }
            search_results.append(result)

        return {
            "success": True,
            "results": search_results,
            "total_found": len(matching_bills),
            "query": query,
            "search_method": "airtable_real_data",
        }

    except Exception as e:
        log_error("Search request failed", error=e)
        return {
            "success": False,
            "message": f"検索に失敗しました: {str(e)}",
            "results": [],
            "total_found": 0,
        }


# Member data collection endpoints
@app.post("/admin/members/collect")
async def collect_member_profiles(request: Request):
    """Manually trigger member profile collection."""
    try:
        body = await request.json()
        house = body.get("house", "both")

        # Trigger member profile collection
        collection_result = await member_service.collect_member_profiles(house)

        log_api_request(
            request,
            200,
            0,
            f"Member collection: {collection_result['collected']} collected",
        )

        return {
            "success": True,
            "result": collection_result,
            "message": f"Collected {collection_result['collected']} members, updated {collection_result['updated']} members",
        }

    except Exception as e:
        log_error("Member profile collection failed", error=e)
        return {
            "success": False,
            "error": str(e),
            "message": "議員プロフィール収集に失敗しました",
        }


@app.post("/admin/cache/warmup")
async def warmup_cache():
    """Manually trigger cache warmup."""
    try:
        warmup_result = await member_service.warmup_member_cache()

        return {
            "success": warmup_result["success"],
            "cached_members": warmup_result.get("cached_members", 0),
            "message": (
                "キャッシュウォームアップが完了しました"
                if warmup_result["success"]
                else "キャッシュウォームアップに失敗しました"
            ),
        }

    except Exception as e:
        log_error("Cache warmup failed", error=e)
        return {
            "success": False,
            "error": str(e),
            "message": "キャッシュウォームアップに失敗しました",
        }


@app.get("/admin/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    try:
        cache_health = await member_service.get_cache_health()
        return {"success": True, "cache_health": cache_health}

    except Exception as e:
        log_error("Failed to get cache stats", error=e)
        return {
            "success": False,
            "error": str(e),
            "message": "キャッシュ統計の取得に失敗しました",
        }


# Batch processing endpoints
@app.post("/admin/batch/member-statistics")
async def schedule_member_statistics_batch(request: Request):
    """Schedule batch calculation of member statistics."""
    try:
        body = await request.json()
        member_ids = body.get("member_ids", [])
        priority = body.get("priority", "normal")

        if not member_ids:
            return {
                "success": False,
                "error": "member_ids is required",
                "message": "議員IDリストが必要です",
            }

        job_id = member_task_manager.schedule_member_statistics_batch(
            member_ids, priority
        )

        return {
            "success": True,
            "job_id": job_id,
            "member_count": len(member_ids),
            "priority": priority,
            "message": f"{len(member_ids)}人の議員統計計算をスケジュールしました",
        }

    except Exception as e:
        log_error("Failed to schedule member statistics batch", error=e)
        return {
            "success": False,
            "error": str(e),
            "message": "議員統計バッチ処理のスケジュールに失敗しました",
        }


@app.post("/admin/batch/policy-stance")
async def schedule_policy_stance_analysis(request: Request):
    """Schedule policy stance analysis for a member."""
    try:
        body = await request.json()
        member_id = body.get("member_id")
        issue_tags = body.get("issue_tags", [])
        priority = body.get("priority", "normal")

        if not member_id:
            return {
                "success": False,
                "error": "member_id is required",
                "message": "議員IDが必要です",
            }

        job_id = member_task_manager.schedule_policy_stance_analysis(
            member_id, issue_tags, priority
        )

        return {
            "success": True,
            "job_id": job_id,
            "member_id": member_id,
            "issue_count": len(issue_tags),
            "priority": priority,
            "message": f"議員{member_id}の政策スタンス分析をスケジュールしました",
        }

    except Exception as e:
        log_error("Failed to schedule policy stance analysis", error=e)
        return {
            "success": False,
            "error": str(e),
            "message": "政策スタンス分析のスケジュールに失敗しました",
        }


@app.get("/admin/batch/job/{job_id}")
async def get_batch_job_status(job_id: str):
    """Get batch job status."""
    try:
        job_status = task_queue.get_job_status(job_id)
        return {"success": True, "job_status": job_status}

    except Exception as e:
        log_error(f"Failed to get job status for {job_id}", error=e)
        return {
            "success": False,
            "error": "Internal server error",
            "message": "ジョブステータスの取得に失敗しました",
        }


@app.get("/admin/batch/queues")
async def get_queue_stats():
    """Get queue statistics."""
    try:
        queue_stats = task_queue.get_queue_stats()
        return {"success": True, "queue_stats": queue_stats}

    except Exception as e:
        log_error("Failed to get queue stats", error=e)
        return {
            "success": False,
            "error": str(e),
            "message": "キュー統計の取得に失敗しました",
        }


@app.get("/admin/batch/failed-jobs")
async def get_failed_jobs():
    """Get failed jobs."""
    try:
        failed_jobs = task_queue.get_failed_jobs(limit=50)
        return {"success": True, "failed_jobs": failed_jobs, "count": len(failed_jobs)}

    except Exception as e:
        log_error("Failed to get failed jobs", error=e)
        return {
            "success": False,
            "error": str(e),
            "message": "失敗したジョブの取得に失敗しました",
        }


# Policy analysis endpoints
@app.get("/api/policy/issues")
async def get_available_issues():
    """Get list of available policy issues."""
    try:
        issues = await policy_analysis_service.get_available_issues()
        return {"success": True, "issues": issues, "count": len(issues)}

    except Exception as e:
        log_error("Failed to get available issues", error=e)
        return {
            "success": False,
            "error": str(e),
            "message": "政策イシューの取得に失敗しました",
        }


@app.get("/api/policy/member/{member_id}/analysis")
async def get_member_policy_analysis(member_id: str, force_refresh: bool = False):
    """Get comprehensive policy analysis for a member."""
    try:
        analysis = await policy_analysis_service.get_analysis_summary(member_id)
        return {"success": True, "analysis": analysis}

    except Exception as e:
        log_error(f"Failed to get policy analysis for member {member_id}", error=e)
        return {
            "success": False,
            "error": str(e),
            "message": "政策分析の取得に失敗しました",
        }


@app.get("/api/policy/member/{member_id}/stance/{issue_tag}")
async def get_member_issue_stance(member_id: str, issue_tag: str):
    """Get member's stance on a specific issue."""
    try:
        position = await policy_analysis_service.get_member_issue_stance(
            member_id, issue_tag
        )

        if position:
            return {
                "success": True,
                "position": {
                    "member_id": member_id,
                    "issue_tag": position.issue_tag,
                    "stance": position.stance.value,
                    "confidence": position.confidence,
                    "vote_count": position.vote_count,
                    "supporting_evidence": position.supporting_evidence,
                    "last_updated": position.last_updated.isoformat(),
                },
            }
        else:
            return {
                "success": False,
                "message": f"議員{member_id}の{issue_tag}に関するスタンスが見つかりません",
            }

    except Exception as e:
        log_error(
            f"Failed to get stance for member {member_id} on {issue_tag}", error=e
        )
        return {
            "success": False,
            "error": str(e),
            "message": "政策スタンスの取得に失敗しました",
        }


@app.post("/api/policy/compare")
async def compare_members_on_issue(request: Request):
    """Compare multiple members on a specific issue."""
    try:
        body = await request.json()
        member_ids = body.get("member_ids", [])
        issue_tag = body.get("issue_tag")

        if not member_ids:
            return {
                "success": False,
                "error": "member_ids is required",
                "message": "議員IDリストが必要です",
            }

        if not issue_tag:
            return {
                "success": False,
                "error": "issue_tag is required",
                "message": "イシュータグが必要です",
            }

        comparison = await policy_analysis_service.compare_members_on_issue(
            member_ids, issue_tag
        )

        return {"success": True, "comparison": comparison}

    except Exception as e:
        log_error("Failed to compare members on issue", error=e)
        return {
            "success": False,
            "error": str(e),
            "message": "議員比較の実行に失敗しました",
        }


@app.get("/api/policy/member/{member_id}/similar")
async def get_similar_members(member_id: str, issue_tags: str | None = None):
    """Get members with similar policy positions."""
    try:
        issue_list = issue_tags.split(",") if issue_tags else None
        similar_members = await policy_analysis_service.get_similar_members(
            member_id, issue_list
        )

        return {
            "success": True,
            "member_id": member_id,
            "similar_members": similar_members,
            "count": len(similar_members),
        }

    except Exception as e:
        log_error(f"Failed to get similar members for {member_id}", error=e)
        return {
            "success": False,
            "error": str(e),
            "message": "類似議員の取得に失敗しました",
        }


@app.get("/api/policy/trends/{issue_tag}")
async def get_policy_trends(issue_tag: str, days: int = 30):
    """Get policy trends for an issue."""
    try:
        trends = await policy_analysis_service.get_policy_trends(issue_tag, days)

        return {"success": True, "trends": trends}

    except Exception as e:
        log_error(f"Failed to get policy trends for {issue_tag}", error=e)
        return {
            "success": False,
            "error": str(e),
            "message": "政策トレンドの取得に失敗しました",
        }


# Member profile endpoints
@app.get("/api/members/{member_id}")
async def get_member_profile(member_id: str):
    """Get member profile information."""
    try:
        member_data = await member_service.get_member_with_cache(member_id)

        if not member_data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Member not found",
                    "message": "指定された議員が見つかりません",
                },
            )

        return {
            "success": True,
            "member_id": member_id,
            "name": member_data.get("Name", "名前不明"),
            "name_kana": member_data.get("Name_Kana", ""),
            "house": member_data.get("House", "house_of_representatives"),
            "party": member_data.get("Party_Name", "無所属"),
            "constituency": member_data.get("Constituency", "選挙区不明"),
            "terms_served": member_data.get("Terms_Served", 1),
            "committees": member_data.get("Committees", []),
            "profile_image": member_data.get("Profile_Image"),
            "official_url": member_data.get("Official_URL"),
            "elected_date": member_data.get("Elected_Date"),
            "birth_date": member_data.get("Birth_Date"),
            "education": member_data.get("Education"),
            "career": member_data.get("Career"),
        }

    except Exception as e:
        log_error(f"Failed to get member profile for {member_id}", error=e)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "議員プロフィールの取得に失敗しました",
            },
        )


@app.get("/api/members/{member_id}/voting-stats")
async def get_member_voting_stats(member_id: str):
    """Get member's voting statistics."""
    try:
        # For MVP, return mock data
        # In production, this would call a voting statistics service
        mock_stats = {
            "total_votes": 156,
            "attendance_rate": 0.92,
            "party_alignment_rate": 0.87,
            "voting_pattern": {
                "yes_votes": 128,
                "no_votes": 18,
                "abstentions": 6,
                "absences": 4,
            },
        }

        return {"success": True, "member_id": member_id, "stats": mock_stats}

    except Exception as e:
        log_error(f"Failed to get voting stats for {member_id}", error=e)
        return {
            "success": False,
            "error": str(e),
            "message": "投票統計の取得に失敗しました",
        }


@app.get("/api/members")
async def get_members_list(
    page: int = 1,
    limit: int = 50,
    house: str | None = None,
    party: str | None = None,
    search: str | None = None,
):
    """Get paginated list of members with optional filters."""
    try:
        # Calculate offset
        offset = (page - 1) * limit

        # For MVP, return mock data
        # In production, this would call member service with filters
        mock_members = [
            {
                "member_id": f"member_{i:03d}",
                "name": f"議員{i}",
                "name_kana": f"ぎいん{i}",
                "house": (
                    "house_of_representatives" if i % 2 == 0 else "house_of_councillors"
                ),
                "party": (
                    "自由民主党"
                    if i % 3 == 0
                    else "立憲民主党"
                    if i % 3 == 1
                    else "日本維新の会"
                ),
                "constituency": f"東京都第{(i % 10) + 1}区",
                "terms_served": (i % 5) + 1,
            }
            for i in range(1, 51)
        ]

        # Apply filters
        filtered_members = mock_members
        if house:
            filtered_members = [m for m in filtered_members if m["house"] == house]
        if party:
            filtered_members = [m for m in filtered_members if m["party"] == party]
        if search:
            filtered_members = [
                m for m in filtered_members if search.lower() in m["name"].lower()
            ]

        # Apply pagination
        total_count = len(filtered_members)
        paginated_members = filtered_members[offset : offset + limit]

        return {
            "success": True,
            "members": paginated_members,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "has_next": offset + limit < total_count,
                "has_prev": page > 1,
            },
            "filters": {"house": house, "party": party, "search": search},
        }

    except Exception as e:
        log_error("Failed to get members list", error=e)
        return {
            "success": False,
            "error": str(e),
            "message": "議員一覧の取得に失敗しました",
        }


# Issue Category API endpoints (for EPIC 7)
@app.get("/api/issues/categories")
async def get_categories(max_records: int = 100):
    """Get all issue categories."""
    try:
        categories = await airtable_client.get_issue_categories(max_records=max_records)
        return categories
    except Exception as e:
        log_error("Failed to get categories", error=e)
        raise HTTPException(status_code=500, detail="Failed to fetch categories")


@app.get("/api/issues/categories/tree")
async def get_category_tree():
    """Get category tree structure."""
    try:
        tree = await airtable_client.get_category_tree()
        return tree
    except Exception as e:
        log_error("Failed to get category tree", error=e)
        raise HTTPException(status_code=500, detail="Failed to fetch category tree")


@app.get("/api/issues/categories/{category_id}")
async def get_category_detail(category_id: str):
    """Get specific category details."""
    try:
        category = await airtable_client.get_issue_category(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return category
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Failed to get category {category_id}", error=e)
        raise HTTPException(status_code=500, detail="Failed to fetch category")


@app.get("/api/issues/categories/{category_id}/children")
async def get_category_children(category_id: str):
    """Get child categories."""
    try:
        children = await airtable_client.get_category_children(category_id)
        return children
    except Exception as e:
        log_error(f"Failed to get children for category {category_id}", error=e)
        raise HTTPException(status_code=500, detail="Failed to fetch category children")


@app.get("/api/issues/categories/search")
async def search_categories(query: str, max_records: int = 50):
    """Search categories by title."""
    try:
        results = await airtable_client.search_categories(
            query, max_records=max_records
        )
        return results
    except Exception as e:
        log_error(f"Failed to search categories with query: {query}", error=e)
        raise HTTPException(status_code=500, detail="Failed to search categories")


@app.get("/api/bills")
async def get_bills(max_records: int = 100, category: str | None = None):
    """Get bills, optionally filtered by category."""
    try:
        # Build filter for category if specified
        filter_formula = None
        if category:
            # Assuming category is stored in Notes field based on our data integration
            filter_formula = f"SEARCH('{category}', {{Notes}}) > 0"

        # Get real bills from Airtable
        bills = await airtable_client.list_bills(
            filter_formula=filter_formula, max_records=max_records
        )

        # Transform the data to match expected format
        transformed_bills = []
        for bill in bills:
            fields = bill.get("fields", {})
            transformed_bill = {
                "id": bill.get("id"),
                "fields": {
                    "Name": fields.get("Name", ""),
                    "Notes": fields.get("Notes", ""),
                    "Status": "実データ統合済み",
                    "Category": "実データ",
                    "Title": fields.get("Name", "")[:100],  # Use Name as Title
                    "Summary": (
                        fields.get("Notes", "")[:200] + "..."
                        if len(fields.get("Notes", "")) > 200
                        else fields.get("Notes", "")
                    ),
                },
            }
            transformed_bills.append(transformed_bill)

        log_api_request(
            None, 200, 0, f"Bills fetched: {len(transformed_bills)} records"
        )
        return transformed_bills

    except Exception as e:
        log_error("Failed to get bills from Airtable", error=e)
        raise HTTPException(status_code=500, detail="Failed to fetch bills")


@app.get("/api/bills/{bill_id}")
async def get_bill_detail(bill_id: str):
    """Get detailed information about a specific bill."""
    try:
        # Get bill from Airtable
        bill = await airtable_client.get_bill(bill_id)

        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")

        fields = bill.get("fields", {})

        # Transform bill data for frontend
        bill_detail = {
            "id": bill.get("id"),
            "fields": {
                "Name": fields.get("Name", ""),
                "Notes": fields.get("Notes", ""),
                "Title": fields.get("Name", ""),
                "Summary": fields.get("Notes", ""),
                "Status": "実データ統合済み",
                "Category": "実データ",
                "Full_Content": fields.get("Notes", ""),  # Full notes as content
            },
            "metadata": {
                "source": "airtable",
                "last_updated": bill.get("createdTime", ""),
                "record_id": bill.get("id"),
            },
        }

        log_api_request(None, 200, 0, f"Bill detail fetched: {bill_id}")
        return bill_detail

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Failed to get bill detail for {bill_id}", error=e)
        raise HTTPException(status_code=500, detail="Failed to fetch bill detail")


# CORS preflight handled automatically by CORSMiddleware


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
