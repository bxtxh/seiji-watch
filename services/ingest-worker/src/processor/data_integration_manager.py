"""
Data Integration Manager - Central orchestration system for bill data processing.
Coordinates scraping, merging, validation, and progress tracking.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from ..scraper.enhanced_diet_scraper import EnhancedBillData, EnhancedDietScraper
from ..scraper.shugiin_scraper import ShugiinBillData, ShugiinScraper
from .bill_data_merger import BillDataMerger, ConflictResolutionStrategy, MergeResult
from .bill_data_validator import BillDataValidator, ValidationResult
from .bill_progress_tracker import BillProgressTracker, ProgressTrackingResult


class ProcessingStage(Enum):
    """Data processing stages"""

    SCRAPING = "scraping"
    MERGING = "merging"
    VALIDATION = "validation"
    TRACKING = "tracking"
    STORAGE = "storage"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ProcessingConfig:
    """Configuration for data processing"""

    # Scraping configuration
    enable_sangiin_scraping: bool = True
    enable_shugiin_scraping: bool = True
    scraping_delay_seconds: float = 2.0
    max_concurrent_requests: int = 3

    # Merging configuration
    conflict_resolution_strategy: ConflictResolutionStrategy = (
        ConflictResolutionStrategy.MOST_COMPLETE
    )
    similarity_threshold: float = 0.8

    # Validation configuration
    validation_level: str = "standard"
    strict_validation: bool = False
    require_japanese: bool = True

    # Progress tracking configuration
    enable_progress_tracking: bool = True
    tracking_update_interval: int = 24
    enable_alerts: bool = True

    # Processing configuration
    batch_size: int = 50
    max_retries: int = 3
    timeout_seconds: int = 300


@dataclass
class ProcessingResult:
    """Result of data processing operation"""

    session_id: str
    processing_stage: ProcessingStage
    start_time: datetime
    end_time: datetime | None = None

    # Data counts
    total_bills_processed: int = 0
    sangiin_bills_count: int = 0
    shugiin_bills_count: int = 0
    merged_bills_count: int = 0
    valid_bills_count: int = 0

    # Processing results
    merge_results: list[MergeResult] = field(default_factory=list)
    validation_results: list[ValidationResult] = field(default_factory=list)
    tracking_results: list[ProgressTrackingResult] = field(default_factory=list)

    # Quality metrics
    avg_data_quality_score: float = 0.0
    merge_conflict_rate: float = 0.0
    validation_success_rate: float = 0.0

    # Errors and warnings
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Performance metrics
    processing_time_seconds: float = 0.0
    bills_per_second: float = 0.0

    @property
    def is_successful(self) -> bool:
        """Check if processing was successful"""
        return (
            self.processing_stage == ProcessingStage.COMPLETED and len(self.errors) == 0
        )

    @property
    def has_warnings(self) -> bool:
        """Check if processing has warnings"""
        return len(self.warnings) > 0


class DataIntegrationManager:
    """Central manager for data integration and processing"""

    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.sangiin_scraper = (
            EnhancedDietScraper(
                delay_seconds=config.scraping_delay_seconds, enable_resilience=True
            )
            if config.enable_sangiin_scraping
            else None
        )

        self.shugiin_scraper = (
            ShugiinScraper(delay_seconds=config.scraping_delay_seconds)
            if config.enable_shugiin_scraping
            else None
        )

        self.data_merger = BillDataMerger(
            conflict_strategy=config.conflict_resolution_strategy,
            similarity_threshold=config.similarity_threshold,
        )

        self.data_validator = BillDataValidator(
            strict_mode=config.strict_validation,
            require_japanese=config.require_japanese,
        )

        self.progress_tracker = (
            BillProgressTracker(
                update_interval_hours=config.tracking_update_interval,
                enable_alerts=config.enable_alerts,
            )
            if config.enable_progress_tracking
            else None
        )

        # Processing state
        self.current_session_id: str | None = None
        self.processing_results: dict[str, ProcessingResult] = {}

    async def process_diet_session(self, session_number: str) -> ProcessingResult:
        """Process a complete diet session"""

        session_id = (
            f"session_{session_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.current_session_id = session_id

        result = ProcessingResult(
            session_id=session_id,
            processing_stage=ProcessingStage.SCRAPING,
            start_time=datetime.now(),
        )

        try:
            self.logger.info(f"Starting data processing for session {session_number}")

            # Stage 1: Scraping
            result.processing_stage = ProcessingStage.SCRAPING
            sangiin_bills, shugiin_bills = await self._scrape_session_data(
                session_number, result
            )

            # Stage 2: Merging
            result.processing_stage = ProcessingStage.MERGING
            merge_results = await self._merge_bill_data(
                sangiin_bills, shugiin_bills, result
            )

            # Stage 3: Validation
            result.processing_stage = ProcessingStage.VALIDATION
            await self._validate_merged_data(merge_results, result)

            # Stage 4: Progress Tracking
            if self.progress_tracker:
                result.processing_stage = ProcessingStage.TRACKING
                await self._track_bill_progress(merge_results, result)
            else:
                pass

            # Stage 5: Calculate final metrics
            result.processing_stage = ProcessingStage.COMPLETED
            self._calculate_final_metrics(result)

            result.end_time = datetime.now()
            result.processing_time_seconds = (
                result.end_time - result.start_time
            ).total_seconds()

            if result.total_bills_processed > 0:
                result.bills_per_second = (
                    result.total_bills_processed / result.processing_time_seconds
                )

            self.processing_results[session_id] = result

            self.logger.info(
                f"Successfully processed {result.total_bills_processed} bills for session {session_number}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Error processing session {session_number}: {e}")
            result.processing_stage = ProcessingStage.ERROR
            result.errors.append(f"Processing failed: {str(e)}")
            result.end_time = datetime.now()

            return result

    async def _scrape_session_data(
        self, session_number: str, result: ProcessingResult
    ) -> tuple[list[EnhancedBillData], list[ShugiinBillData]]:
        """Scrape data from both houses"""

        sangiin_bills = []
        shugiin_bills = []

        # Scrape Sangiin data
        if self.sangiin_scraper:
            try:
                self.logger.info(f"Scraping Sangiin data for session {session_number}")

                # Get basic bill list
                basic_bills = self.sangiin_scraper.fetch_current_bills()

                # Fetch detailed information for each bill
                for bill in basic_bills:
                    if bill.url:
                        try:
                            enhanced_bill = (
                                self.sangiin_scraper.fetch_enhanced_bill_details(
                                    bill.url
                                )
                            )
                            enhanced_bill.diet_session = session_number
                            sangiin_bills.append(enhanced_bill)
                        except Exception as e:
                            self.logger.warning(
                                f"Error fetching details for Sangiin bill {bill.bill_id}: {e}"
                            )
                            result.warnings.append(
                                f"Sangiin bill {bill.bill_id}: {str(e)}"
                            )

                result.sangiin_bills_count = len(sangiin_bills)
                self.logger.info(
                    f"Successfully scraped {len(sangiin_bills)} Sangiin bills"
                )

            except Exception as e:
                self.logger.error(f"Error scraping Sangiin data: {e}")
                result.errors.append(f"Sangiin scraping failed: {str(e)}")

        # Scrape Shugiin data
        if self.shugiin_scraper:
            try:
                self.logger.info(f"Scraping Shugiin data for session {session_number}")

                # Get bill list
                basic_bills = self.shugiin_scraper.fetch_bill_list(session_number)

                # Fetch detailed information for each bill
                for bill in basic_bills:
                    if bill.url:
                        try:
                            enhanced_bill = (
                                self.shugiin_scraper.fetch_enhanced_bill_data(bill.url)
                            )
                            enhanced_bill.diet_session = session_number
                            shugiin_bills.append(enhanced_bill)
                        except Exception as e:
                            self.logger.warning(
                                f"Error fetching details for Shugiin bill {bill.bill_id}: {e}"
                            )
                            result.warnings.append(
                                f"Shugiin bill {bill.bill_id}: {str(e)}"
                            )

                result.shugiin_bills_count = len(shugiin_bills)
                self.logger.info(
                    f"Successfully scraped {len(shugiin_bills)} Shugiin bills"
                )

            except Exception as e:
                self.logger.error(f"Error scraping Shugiin data: {e}")
                result.errors.append(f"Shugiin scraping failed: {str(e)}")

        return sangiin_bills, shugiin_bills

    async def _merge_bill_data(
        self,
        sangiin_bills: list[EnhancedBillData],
        shugiin_bills: list[ShugiinBillData],
        result: ProcessingResult,
    ) -> list[MergeResult]:
        """Merge bill data from both houses"""

        try:
            self.logger.info(
                f"Merging {len(sangiin_bills)} Sangiin bills with {len(shugiin_bills)} Shugiin bills"
            )

            merge_results = self.data_merger.merge_bills(sangiin_bills, shugiin_bills)

            result.merge_results = merge_results
            result.merged_bills_count = len(merge_results)

            # Calculate merge statistics
            merge_stats = self.data_merger.get_merge_statistics(merge_results)
            result.merge_conflict_rate = merge_stats.get("conflict_rate", 0.0)

            self.logger.info(
                f"Successfully merged {len(merge_results)} bills with {merge_stats.get('total_conflicts', 0)} conflicts"
            )

            return merge_results

        except Exception as e:
            self.logger.error(f"Error merging bill data: {e}")
            result.errors.append(f"Data merging failed: {str(e)}")
            return []

    async def _validate_merged_data(
        self, merge_results: list[MergeResult], result: ProcessingResult
    ) -> list[ValidationResult]:
        """Validate merged bill data"""

        try:
            self.logger.info(f"Validating {len(merge_results)} merged bills")

            validation_results = self.data_validator.validate_merge_results(
                merge_results, self.config.validation_level
            )

            result.validation_results = validation_results
            result.valid_bills_count = sum(1 for r in validation_results if r.is_valid)
            result.validation_success_rate = (
                result.valid_bills_count / len(validation_results)
                if validation_results
                else 0.0
            )

            # Calculate average quality score
            quality_scores = [r.quality_score for r in validation_results]
            result.avg_data_quality_score = (
                sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            )

            # Add validation warnings
            for validation_result in validation_results:
                if validation_result.get_critical_issues():
                    result.warnings.append(
                        f"Bill {validation_result.bill_id} has critical validation issues"
                    )

            self.logger.info(
                f"Successfully validated {result.valid_bills_count}/{len(validation_results)} bills"
            )

            return validation_results

        except Exception as e:
            self.logger.error(f"Error validating merged data: {e}")
            result.errors.append(f"Data validation failed: {str(e)}")
            return []

    async def _track_bill_progress(
        self, merge_results: list[MergeResult], result: ProcessingResult
    ) -> list[ProgressTrackingResult]:
        """Track bill progress"""

        try:
            self.logger.info(f"Tracking progress for {len(merge_results)} bills")

            bills_to_track = [mr.merged_bill for mr in merge_results]
            tracking_results = await self.progress_tracker.track_multiple_bills(
                bills_to_track
            )

            result.tracking_results = tracking_results

            # Add progress tracking warnings
            for tracking_result in tracking_results:
                if tracking_result.alerts:
                    result.warnings.extend(
                        [
                            f"Bill {tracking_result.bill_id}: {alert}"
                            for alert in tracking_result.alerts
                        ]
                    )

            self.logger.info(
                f"Successfully tracked progress for {len(tracking_results)} bills"
            )

            return tracking_results

        except Exception as e:
            self.logger.error(f"Error tracking bill progress: {e}")
            result.errors.append(f"Progress tracking failed: {str(e)}")
            return []

    def _calculate_final_metrics(self, result: ProcessingResult):
        """Calculate final processing metrics"""

        result.total_bills_processed = result.merged_bills_count

        # Log final statistics
        self.logger.info(f"Processing completed for session {result.session_id}")
        self.logger.info(f"  - Total bills processed: {result.total_bills_processed}")
        self.logger.info(f"  - Sangiin bills: {result.sangiin_bills_count}")
        self.logger.info(f"  - Shugiin bills: {result.shugiin_bills_count}")
        self.logger.info(f"  - Merged bills: {result.merged_bills_count}")
        self.logger.info(f"  - Valid bills: {result.valid_bills_count}")
        self.logger.info(
            f"  - Average quality score: {result.avg_data_quality_score:.2f}"
        )
        self.logger.info(f"  - Merge conflict rate: {result.merge_conflict_rate:.2%}")
        self.logger.info(
            f"  - Validation success rate: {result.validation_success_rate:.2%}"
        )
        self.logger.info(f"  - Errors: {len(result.errors)}")
        self.logger.info(f"  - Warnings: {len(result.warnings)}")

    async def process_multiple_sessions(
        self, session_numbers: list[str]
    ) -> list[ProcessingResult]:
        """Process multiple diet sessions"""

        results = []

        for session_number in session_numbers:
            try:
                result = await self.process_diet_session(session_number)
                results.append(result)

                # Brief pause between sessions
                await asyncio.sleep(1.0)

            except Exception as e:
                self.logger.error(f"Error processing session {session_number}: {e}")
                continue

        return results

    def get_processing_summary(self, results: list[ProcessingResult]) -> dict[str, Any]:
        """Get summary of processing results"""

        if not results:
            return {}

        total_bills = sum(r.total_bills_processed for r in results)
        total_time = sum(r.processing_time_seconds for r in results)
        successful_sessions = sum(1 for r in results if r.is_successful)

        return {
            "total_sessions": len(results),
            "successful_sessions": successful_sessions,
            "success_rate": successful_sessions / len(results),
            "total_bills_processed": total_bills,
            "total_processing_time": total_time,
            "average_bills_per_session": total_bills / len(results) if results else 0,
            "overall_throughput": total_bills / total_time if total_time > 0 else 0,
            "avg_data_quality": sum(r.avg_data_quality_score for r in results)
            / len(results),
            "avg_merge_conflict_rate": sum(r.merge_conflict_rate for r in results)
            / len(results),
            "avg_validation_success_rate": sum(
                r.validation_success_rate for r in results
            )
            / len(results),
            "total_errors": sum(len(r.errors) for r in results),
            "total_warnings": sum(len(r.warnings) for r in results),
            "stage_distribution": {
                stage.value: sum(1 for r in results if r.processing_stage == stage)
                for stage in ProcessingStage
            },
        }

    def get_session_result(self, session_id: str) -> ProcessingResult | None:
        """Get processing result for a specific session"""
        return self.processing_results.get(session_id)

    def get_all_session_results(self) -> dict[str, ProcessingResult]:
        """Get all processing results"""
        return self.processing_results.copy()

    def clear_old_results(self, days_to_keep: int = 7):
        """Clear old processing results"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        to_remove = []
        for session_id, result in self.processing_results.items():
            if result.start_time < cutoff_date:
                to_remove.append(session_id)

        for session_id in to_remove:
            del self.processing_results[session_id]

        self.logger.info(f"Cleared {len(to_remove)} old processing results")

    def export_processing_results(
        self, session_ids: list[str] | None = None
    ) -> dict[str, Any]:
        """Export processing results for analysis"""

        if session_ids is None:
            session_ids = list(self.processing_results.keys())

        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "config": {
                "conflict_resolution_strategy": self.config.conflict_resolution_strategy.value,
                "similarity_threshold": self.config.similarity_threshold,
                "validation_level": self.config.validation_level,
                "batch_size": self.config.batch_size,
            },
            "sessions": {},
        }

        for session_id in session_ids:
            result = self.processing_results.get(session_id)
            if result:
                export_data["sessions"][session_id] = {
                    "session_id": result.session_id,
                    "processing_stage": result.processing_stage.value,
                    "start_time": result.start_time.isoformat(),
                    "end_time": (
                        result.end_time.isoformat() if result.end_time else None
                    ),
                    "total_bills_processed": result.total_bills_processed,
                    "sangiin_bills_count": result.sangiin_bills_count,
                    "shugiin_bills_count": result.shugiin_bills_count,
                    "merged_bills_count": result.merged_bills_count,
                    "valid_bills_count": result.valid_bills_count,
                    "avg_data_quality_score": result.avg_data_quality_score,
                    "merge_conflict_rate": result.merge_conflict_rate,
                    "validation_success_rate": result.validation_success_rate,
                    "processing_time_seconds": result.processing_time_seconds,
                    "bills_per_second": result.bills_per_second,
                    "error_count": len(result.errors),
                    "warning_count": len(result.warnings),
                    "is_successful": result.is_successful,
                }

        return export_data
