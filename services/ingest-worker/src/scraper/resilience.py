"""
Scraper Resilience & Optimization Module

Provides enhanced capabilities for:
- Duplicate detection and skipping
- Exponential backoff for failures
- Rate limiting compliance
- Progress tracking for long-running jobs
- Error recovery and retry logic
- Caching mechanisms
"""

import asyncio
import hashlib
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

import aiohttp
from aiohttp import ClientSession, ClientTimeout

try:
    import backoff
    BACKOFF_AVAILABLE = True
except ImportError:
    BACKOFF_AVAILABLE = False
    backoff = None


logger = logging.getLogger(__name__)

T = TypeVar('T')


class JobStatus(str, Enum):
    """Job execution status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class RetryStrategy(str, Enum):
    """Retry strategy options"""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"
    CUSTOM = "custom"


@dataclass
class ScrapingJob:
    """Represents a scraping job with progress tracking"""
    job_id: str
    job_type: str
    url: str
    status: JobStatus = JobStatus.PENDING
    start_time: datetime | None = None
    end_time: datetime | None = None
    progress: float = 0.0  # 0.0 to 1.0
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    retry_count: int = 0
    max_retries: int = 3
    error_message: str | None = None
    result_data: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert job to dictionary representation"""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "url": self.url,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "progress": self.progress,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "failed_items": self.failed_items,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_second: float = 0.5  # Max 1 request per 2 seconds
    burst_size: int = 5  # Allow small bursts
    cooldown_seconds: float = 10.0  # Cooldown after rate limit hit
    respect_retry_after: bool = True  # Respect Retry-After headers


@dataclass
class CacheConfig:
    """Cache configuration for duplicate detection"""
    enabled: bool = True
    cache_dir: str = "/tmp/diet_scraper_cache"
    max_age_hours: int = 24
    max_size_mb: int = 100
    hash_algorithm: str = "sha256"


class DuplicateDetector:
    """Detects and manages duplicate content"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache_dir = Path(config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.content_hashes: dict[str, str] = {}
        self.url_hashes: dict[str, str] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load existing cache from disk"""
        if not self.config.enabled:
            return

        cache_file = self.cache_dir / "content_hashes.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    cache_data = json.load(f)
                    self.content_hashes = cache_data.get("content_hashes", {})
                    self.url_hashes = cache_data.get("url_hashes", {})
                logger.info(
                    f"Loaded {len(self.content_hashes)} content hashes from cache")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")

    def _save_cache(self) -> None:
        """Save cache to disk"""
        if not self.config.enabled:
            return

        cache_file = self.cache_dir / "content_hashes.json"
        try:
            cache_data = {
                "content_hashes": self.content_hashes,
                "url_hashes": self.url_hashes,
                "last_updated": datetime.now().isoformat()
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _compute_hash(self, content: str) -> str:
        """Compute hash of content"""
        if self.config.hash_algorithm == "sha256":
            return hashlib.sha256(content.encode('utf-8')).hexdigest()
        elif self.config.hash_algorithm == "md5":
            return hashlib.md5(content.encode('utf-8')).hexdigest()
        else:
            raise ValueError(
                f"Unsupported hash algorithm: {self.config.hash_algorithm}")

    def is_duplicate_content(self, content: str, identifier: str = None) -> bool:
        """Check if content is duplicate"""
        if not self.config.enabled:
            return False

        content_hash = self._compute_hash(content)

        # Check if we've seen this exact content before
        if content_hash in self.content_hashes.values():
            logger.debug(
                f"Duplicate content detected: {identifier or content_hash[:16]}")
            return True

        # Store the hash for future reference
        if identifier:
            self.content_hashes[identifier] = content_hash

        return False

    def is_duplicate_url(self, url: str) -> bool:
        """Check if URL has been processed recently"""
        if not self.config.enabled:
            return False

        url_hash = self._compute_hash(url)

        if url_hash in self.url_hashes:
            # Check if the cached entry is still valid
            timestamp_str = self.url_hashes[url_hash]
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                if datetime.now() - timestamp < timedelta(hours=self.config.max_age_hours):
                    logger.debug(
                        f"Duplicate URL detected (within {self.config.max_age_hours}h): {url}")
                    return True
                else:
                    # Remove expired entry
                    del self.url_hashes[url_hash]
            except ValueError:
                # Invalid timestamp format, remove entry
                del self.url_hashes[url_hash]

        # Mark URL as processed
        self.url_hashes[url_hash] = datetime.now().isoformat()
        self._save_cache()
        return False

    def cleanup_cache(self) -> int:
        """Clean up expired cache entries"""
        if not self.config.enabled:
            return 0

        expired_count = 0
        cutoff_time = datetime.now() - timedelta(hours=self.config.max_age_hours)

        # Clean URL cache
        expired_urls = []
        for url_hash, timestamp_str in self.url_hashes.items():
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                if timestamp < cutoff_time:
                    expired_urls.append(url_hash)
            except ValueError:
                expired_urls.append(url_hash)

        for url_hash in expired_urls:
            del self.url_hashes[url_hash]
            expired_count += 1

        self._save_cache()
        logger.info(f"Cleaned up {expired_count} expired cache entries")
        return expired_count


class RateLimiter:
    """Rate limiter with burst support and backoff"""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.request_times: list[float] = []
        self.last_request_time = 0.0
        self.cooldown_until = 0.0

    async def wait_if_needed(self,
                             response_headers: dict[str,
                                                    str] | None = None) -> None:
        """Wait if rate limiting is needed"""
        current_time = time.time()

        # Check if we're in cooldown period
        if current_time < self.cooldown_until:
            wait_time = self.cooldown_until - current_time
            logger.info(f"Rate limiter cooldown: waiting {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)
            return

        # Respect Retry-After header if present
        if response_headers and self.config.respect_retry_after:
            retry_after = response_headers.get('Retry-After')
            if retry_after:
                try:
                    wait_time = float(retry_after)
                    logger.info(
                        f"Respecting Retry-After header: waiting {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                    return
                except ValueError:
                    pass

        # Clean up old request times
        cutoff_time = current_time - 1.0  # Keep 1 second of history
        self.request_times = [t for t in self.request_times if t > cutoff_time]

        # Check if we need to wait based on rate limit
        if len(self.request_times) >= self.config.burst_size:
            # Calculate required wait time
            oldest_request = min(self.request_times)
            required_interval = 1.0 / self.config.requests_per_second
            wait_time = required_interval - (current_time - oldest_request)

            if wait_time > 0:
                logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)

        # Minimum delay between requests
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.config.requests_per_second

        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            await asyncio.sleep(wait_time)

        # Record this request
        self.request_times.append(time.time())
        self.last_request_time = time.time()

    def trigger_cooldown(self) -> None:
        """Trigger cooldown period (called when rate limit exceeded)"""
        self.cooldown_until = time.time() + self.config.cooldown_seconds
        logger.warning(
            f"Rate limit exceeded, cooldown for {self.config.cooldown_seconds} seconds")


class ResilientScraper:
    """Enhanced scraper with resilience and optimization features"""

    def __init__(
        self,
        rate_limit_config: RateLimitConfig | None = None,
        cache_config: CacheConfig | None = None,
        max_concurrent_requests: int = 5,
        request_timeout: int = 30

    ):
        self.rate_limiter = RateLimiter(rate_limit_config or RateLimitConfig())
        self.duplicate_detector = DuplicateDetector(cache_config or CacheConfig())
        self.max_concurrent_requests = max_concurrent_requests
        self.request_timeout = request_timeout

        # Job tracking
        self.active_jobs: dict[str, ScrapingJob] = {}
        self.completed_jobs: dict[str, ScrapingJob] = {}

        # Session management
        self.session: ClientSession | None = None

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "duplicate_skips": 0,
            "rate_limit_waits": 0,
            "cache_hits": 0
        }

    async def __aenter__(self):
        """Async context manager entry"""
        timeout = ClientTimeout(total=self.request_timeout)
        self.session = ClientSession(
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; DietTracker/1.0; +https://github.com/diet-tracker)'
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def create_job(
        self,
        job_type: str,
        url: str,
        metadata: dict[str, Any] | None = None
    ) -> ScrapingJob:
        """Create a new scraping job"""
        job_id = f"{job_type}_{int(time.time())}_{len(self.active_jobs)}"

        job = ScrapingJob(
            job_id=job_id,
            job_type=job_type,
            url=url,
            metadata=metadata or {}
        )

        self.active_jobs[job_id] = job
        logger.info(f"Created scraping job: {job_id}")
        return job

    async def fetch_with_resilience(
        self,
        url: str,
        job: ScrapingJob | None = None,
        skip_duplicates: bool = True,
        max_retries: int = 3
    ) -> str | None:
        """
        Fetch URL with resilience features:
        - Rate limiting
        - Duplicate detection
        - Retry with exponential backoff
        - Progress tracking
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        # Check for duplicate URL if enabled
        if skip_duplicates and self.duplicate_detector.is_duplicate_url(url):
            self.stats["duplicate_skips"] += 1
            if job:
                job.status = JobStatus.COMPLETED
                job.progress = 1.0
                job.result_data = {"skipped": True, "reason": "duplicate_url"}
            return None

        # Apply rate limiting
        await self.rate_limiter.wait_if_needed()

        # Retry logic with exponential backoff
        for attempt in range(max_retries + 1):
            try:
                # Update job status
                if job:
                    job.status = JobStatus.RUNNING
                    if not job.start_time:
                        job.start_time = datetime.now()

                self.stats["total_requests"] += 1

                # Make the request
                async with self.session.get(url) as response:
                    # Check rate limiting headers
                    if response.status == 429:  # Too Many Requests
                        self.rate_limiter.trigger_cooldown()
                        await self.rate_limiter.wait_if_needed(dict(response.headers))
                        self.stats["rate_limit_waits"] += 1
                        # Retry after cooldown
                        async with self.session.get(url) as retry_response:
                            retry_response.raise_for_status()
                            content = await retry_response.text()
                    else:
                        response.raise_for_status()
                        content = await response.text()

                    # Check for duplicate content
                    if skip_duplicates and self.duplicate_detector.is_duplicate_content(
                            content, url):
                        self.stats["cache_hits"] += 1
                        if job:
                            job.status = JobStatus.COMPLETED
                            job.progress = 1.0
                            job.result_data = {
                                "skipped": True, "reason": "duplicate_content"}
                        return None

                    self.stats["successful_requests"] += 1

                    if job:
                        job.status = JobStatus.COMPLETED
                        job.end_time = datetime.now()
                        job.progress = 1.0
                        job.processed_items = 1
                        job.result_data = {"content_length": len(content)}

                    logger.debug(f"Successfully fetched: {url} ({len(content)} bytes)")
                    return content

            except (TimeoutError, aiohttp.ClientError) as e:
                if attempt < max_retries:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {url}, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Final attempt failed
                    self.stats["failed_requests"] += 1

                    if job:
                        job.status = JobStatus.FAILED
                        job.end_time = datetime.now()
                        job.error_message = str(e)

                    logger.error(
                        f"Failed to fetch {url} after {max_retries} retries: {e}")
                    raise

    async def fetch_multiple_urls(
        self,
        urls: list[str],
        job_type: str = "batch_fetch",
        skip_duplicates: bool = True,
        progress_callback: Callable[[float], None] | None = None
    ) -> dict[str, str | None]:
        """
        Fetch multiple URLs with concurrency control and progress tracking
        """
        job = self.create_job(job_type, f"batch:{len(urls)}_urls")
        job.total_items = len(urls)
        job.status = JobStatus.RUNNING
        job.start_time = datetime.now()

        results = {}
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        async def fetch_single(url: str) -> tuple[str, str | None]:
            async with semaphore:
                try:
                    content = await self.fetch_with_resilience(url, skip_duplicates=skip_duplicates)
                    job.processed_items += 1
                    if content is None:
                        job.processed_items += 1  # Count skipped as processed
                    return url, content
                except Exception as e:
                    job.failed_items += 1
                    logger.error(f"Failed to fetch {url}: {e}")
                    return url, None
                finally:
                    # Update progress
                    job.progress = (
                        job.processed_items + job.failed_items) / job.total_items
                    if progress_callback:
                        progress_callback(job.progress)

        # Execute all fetches concurrently
        tasks = [fetch_single(url) for url in urls]
        fetch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in fetch_results:
            if isinstance(result, Exception):
                job.failed_items += 1
                logger.error(f"Task failed with exception: {result}")
            else:
                url, content = result
                results[url] = content

        # Finalize job
        job.status = JobStatus.COMPLETED if job.failed_items == 0 else JobStatus.FAILED
        job.end_time = datetime.now()
        job.result_data = {
            "successful_fetches": len([c for c in results.values() if c is not None]),
            "failed_fetches": job.failed_items,
            "skipped_duplicates": len([c for c in results.values() if c is None])
        }

        # Move to completed jobs
        self.completed_jobs[job.job_id] = job
        if job.job_id in self.active_jobs:
            del self.active_jobs[job.job_id]

        logger.info(f"Batch fetch completed: {job.job_id}")
        logger.info(f"  Successful: {job.result_data['successful_fetches']}")
        logger.info(f"  Failed: {job.result_data['failed_fetches']}")
        logger.info(f"  Skipped: {job.result_data['skipped_duplicates']}")

        return results

    def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        """Get status of a specific job"""
        job = self.active_jobs.get(job_id) or self.completed_jobs.get(job_id)
        return job.to_dict() if job else None

    def get_all_jobs(self) -> dict[str, Any]:
        """Get status of all jobs"""
        return {
            "active_jobs": {
                job_id: job.to_dict() for job_id,
                job in self.active_jobs.items()},
            "completed_jobs": {
                job_id: job.to_dict() for job_id,
                job in self.completed_jobs.items()},
            "statistics": self.stats}

    def cleanup_completed_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up old completed jobs"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        expired_jobs = [
            job_id for job_id, job in self.completed_jobs.items()
            if job.end_time and job.end_time < cutoff_time
        ]

        for job_id in expired_jobs:
            del self.completed_jobs[job_id]

        # Also cleanup cache
        cache_cleanup_count = self.duplicate_detector.cleanup_cache()

        logger.info(
            f"Cleaned up {len(expired_jobs)} old jobs and {cache_cleanup_count} cache entries")
        return len(expired_jobs)

    def get_statistics(self) -> dict[str, Any]:
        """Get scraper statistics"""
        success_rate = (
            self.stats["successful_requests"] / max(1, self.stats["total_requests"])
        ) * 100

        return {
            **self.stats,
            "success_rate_percent": round(success_rate, 2),
            "active_jobs_count": len(self.active_jobs),
            "completed_jobs_count": len(self.completed_jobs)
        }
