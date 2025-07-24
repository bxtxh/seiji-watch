"""
Data Quality Auditor - Analyzes existing bill data quality and identifies improvement opportunities.
Provides comprehensive auditing capabilities for the enhanced bill database.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from ...shared.src.shared.models.bill import Bill


class QualityIssueType(Enum):
    """Types of quality issues that can be detected"""

    MISSING_REQUIRED_FIELD = "missing_required_field"
    EMPTY_FIELD = "empty_field"
    INVALID_FORMAT = "invalid_format"
    INCONSISTENT_DATA = "inconsistent_data"
    DUPLICATE_DATA = "duplicate_data"
    OUTDATED_DATA = "outdated_data"
    POOR_JAPANESE_TEXT = "poor_japanese_text"
    MISSING_RELATIONSHIPS = "missing_relationships"
    LOW_COMPLETENESS = "low_completeness"


class QualityIssueSeverity(Enum):
    """Severity levels for quality issues"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class QualityIssue:
    """Represents a data quality issue"""

    bill_id: str
    issue_type: QualityIssueType
    severity: QualityIssueSeverity
    field_name: str | None
    description: str
    current_value: Any
    suggested_fix: str | None
    confidence: float
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class QualityMetrics:
    """Quality metrics for a specific aspect of data"""

    total_records: int
    valid_records: int
    invalid_records: int
    completeness_rate: float
    accuracy_rate: float
    consistency_rate: float
    timeliness_rate: float
    overall_quality_score: float

    def __post_init__(self):
        if self.total_records > 0:
            self.completeness_rate = self.valid_records / self.total_records
            self.overall_quality_score = (
                self.completeness_rate * 0.3
                + self.accuracy_rate * 0.25
                + self.consistency_rate * 0.25
                + self.timeliness_rate * 0.2
            )


@dataclass
class QualityReport:
    """Comprehensive quality audit report"""

    audit_timestamp: datetime
    total_bills: int
    overall_metrics: QualityMetrics
    field_metrics: dict[str, QualityMetrics]
    issues: list[QualityIssue]
    recommendations: list[str]
    improvement_priorities: list[dict[str, Any]]

    # Statistics
    issues_by_type: dict[str, int] = field(default_factory=dict)
    issues_by_severity: dict[str, int] = field(default_factory=dict)
    most_problematic_fields: list[str] = field(default_factory=list)
    quality_trend: dict[str, Any] | None = None


class DataQualityAuditor:
    """Comprehensive data quality auditor for bill data"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.logger = logging.getLogger(__name__)

        # Quality thresholds
        self.quality_thresholds = {
            "completeness_min": 0.8,
            "accuracy_min": 0.9,
            "consistency_min": 0.85,
            "timeliness_days": 30,
            "text_min_length": 10,
            "japanese_text_ratio": 0.7,
        }

        # Required fields for enhanced bills
        self.required_fields = [
            "bill_id",
            "title",
            "status",
            "submitter",
            "diet_session",
            "house_of_origin",
            "submitted_date",
        ]

        # Enhanced fields to audit
        self.enhanced_fields = [
            "bill_outline",
            "background_context",
            "expected_effects",
            "key_provisions",
            "source_house",
            "data_quality_score",
        ]

        # Field importance weights
        self.field_weights = {
            "bill_outline": 0.3,
            "background_context": 0.2,
            "expected_effects": 0.2,
            "key_provisions": 0.15,
            "title": 0.1,
            "status": 0.05,
        }

    def conduct_full_audit(self) -> QualityReport:
        """Conduct comprehensive data quality audit"""
        self.logger.info("Starting comprehensive data quality audit")

        try:
            with self.SessionLocal() as session:
                # Get all bills
                bills = session.execute(select(Bill)).scalars().all()

                if not bills:
                    self.logger.warning("No bills found in database")
                    return self._create_empty_report()

                self.logger.info(f"Auditing {len(bills)} bills")

                # Analyze overall quality
                overall_metrics = self._calculate_overall_metrics(bills)

                # Analyze field-specific quality
                field_metrics = self._analyze_field_quality(bills)

                # Detect quality issues
                issues = self._detect_quality_issues(bills)

                # Generate recommendations
                recommendations = self._generate_recommendations(issues, field_metrics)

                # Determine improvement priorities
                priorities = self._determine_improvement_priorities(
                    issues, field_metrics
                )

                # Create report
                report = QualityReport(
                    audit_timestamp=datetime.now(),
                    total_bills=len(bills),
                    overall_metrics=overall_metrics,
                    field_metrics=field_metrics,
                    issues=issues,
                    recommendations=recommendations,
                    improvement_priorities=priorities,
                )

                # Add statistics
                report.issues_by_type = self._count_issues_by_type(issues)
                report.issues_by_severity = self._count_issues_by_severity(issues)
                report.most_problematic_fields = self._identify_problematic_fields(
                    field_metrics
                )

                self.logger.info(f"Audit completed: {len(issues)} issues found")
                return report

        except Exception as e:
            self.logger.error(f"Error in data quality audit: {e}")
            raise

    def _calculate_overall_metrics(self, bills: list[Bill]) -> QualityMetrics:
        """Calculate overall quality metrics"""
        total_bills = len(bills)

        # Count valid records based on required fields
        valid_records = 0
        for bill in bills:
            if self._is_bill_valid(bill):
                valid_records += 1

        # Calculate rates
        completeness_rate = valid_records / total_bills if total_bills > 0 else 0
        accuracy_rate = self._calculate_accuracy_rate(bills)
        consistency_rate = self._calculate_consistency_rate(bills)
        timeliness_rate = self._calculate_timeliness_rate(bills)

        return QualityMetrics(
            total_records=total_bills,
            valid_records=valid_records,
            invalid_records=total_bills - valid_records,
            completeness_rate=completeness_rate,
            accuracy_rate=accuracy_rate,
            consistency_rate=consistency_rate,
            timeliness_rate=timeliness_rate,
            overall_quality_score=0.0,  # Will be calculated in __post_init__
        )

    def _analyze_field_quality(self, bills: list[Bill]) -> dict[str, QualityMetrics]:
        """Analyze quality metrics for each field"""
        field_metrics = {}

        # Analyze each field
        all_fields = self.required_fields + self.enhanced_fields

        for field_name in all_fields:
            metrics = self._calculate_field_metrics(bills, field_name)
            field_metrics[field_name] = metrics

        return field_metrics

    def _calculate_field_metrics(
        self, bills: list[Bill], field_name: str
    ) -> QualityMetrics:
        """Calculate quality metrics for a specific field"""
        total_records = len(bills)
        valid_records = 0

        for bill in bills:
            value = getattr(bill, field_name, None)
            if self._is_field_value_valid(field_name, value):
                valid_records += 1

        completeness_rate = valid_records / total_records if total_records > 0 else 0
        accuracy_rate = self._calculate_field_accuracy(bills, field_name)
        consistency_rate = self._calculate_field_consistency(bills, field_name)
        timeliness_rate = self._calculate_field_timeliness(bills, field_name)

        return QualityMetrics(
            total_records=total_records,
            valid_records=valid_records,
            invalid_records=total_records - valid_records,
            completeness_rate=completeness_rate,
            accuracy_rate=accuracy_rate,
            consistency_rate=consistency_rate,
            timeliness_rate=timeliness_rate,
            overall_quality_score=0.0,  # Will be calculated in __post_init__
        )

    def _detect_quality_issues(self, bills: list[Bill]) -> list[QualityIssue]:
        """Detect quality issues in bill data"""
        issues = []

        for bill in bills:
            # Check required fields
            issues.extend(self._check_required_fields(bill))

            # Check enhanced fields
            issues.extend(self._check_enhanced_fields(bill))

            # Check data consistency
            issues.extend(self._check_data_consistency(bill))

            # Check Japanese text quality
            issues.extend(self._check_japanese_text_quality(bill))

            # Check data freshness
            issues.extend(self._check_data_freshness(bill))

        # Check for duplicates
        issues.extend(self._check_for_duplicates(bills))

        return issues

    def _check_required_fields(self, bill: Bill) -> list[QualityIssue]:
        """Check required fields for completeness"""
        issues = []

        for field_name in self.required_fields:
            value = getattr(bill, field_name, None)

            if value is None:
                issues.append(
    QualityIssue(
        bill_id=bill.bill_id,
        issue_type=QualityIssueType.MISSING_REQUIRED_FIELD,
        severity=QualityIssueSeverity.CRITICAL,
        field_name=field_name,
        description=f"Required field '{field_name}' is missing",
        current_value=None,
        suggested_fix=f"Populate '{field_name}' field with appropriate data",
        confidence=1.0,
         ) )
            elif isinstance(value, str) and not value.strip():
                issues.append(
    QualityIssue(
        bill_id=bill.bill_id,
        issue_type=QualityIssueType.EMPTY_FIELD,
        severity=QualityIssueSeverity.HIGH,
        field_name=field_name,
        description=f"Required field '{field_name}' is empty",
        current_value=value,
        suggested_fix=f"Populate '{field_name}' field with appropriate data",
        confidence=1.0,
         ) )

        return issues

    def _check_enhanced_fields(self, bill: Bill) -> list[QualityIssue]:
        """Check enhanced fields for quality"""
        issues = []

        for field_name in self.enhanced_fields:
            value = getattr(bill, field_name, None)

            if field_name in ["bill_outline", "background_context", "expected_effects"]:
                if value is None:
                    issues.append(
                        QualityIssue(
                            bill_id=bill.bill_id,
                            issue_type=QualityIssueType.MISSING_REQUIRED_FIELD,
                            severity=QualityIssueSeverity.HIGH,
                            field_name=field_name,
                            description=f"Enhanced field '{field_name}' is missing",
                            current_value=None,
                            suggested_fix=f"Extract '{field_name}' from bill documents",
                            confidence=0.9,
                        )
                    )
                elif (
                    isinstance(value, str)
                    and len(value.strip()) < self.quality_thresholds["text_min_length"]
                ):
                    issues.append(
    QualityIssue(
        bill_id=bill.bill_id,
        issue_type=QualityIssueType.POOR_JAPANESE_TEXT,
        severity=QualityIssueSeverity.MEDIUM,
        field_name=field_name,
        description=f"Field '{field_name}' has insufficient content",
        current_value=value,
        suggested_fix=f"Expand '{field_name}' content with more detailed information",
        confidence=0.8,
         ) )

        return issues

    def _check_data_consistency(self, bill: Bill) -> list[QualityIssue]:
        """Check data consistency within a bill"""
        issues = []

        # Check date consistency
        if bill.submitted_date and bill.updated_at:
            if bill.submitted_date > bill.updated_at.date():
                issues.append(
    QualityIssue(
        bill_id=bill.bill_id,
        issue_type=QualityIssueType.INCONSISTENT_DATA,
        severity=QualityIssueSeverity.HIGH,
        field_name="submitted_date",
        description="Submitted date is after last updated date",
        current_value=f"submitted: {bill.submitted_date}, updated: {bill.updated_at}",
        suggested_fix="Verify and correct date fields",
        confidence=0.95,
         ) )

        # Check status consistency
        if bill.status == "成立" and bill.stage != "enacted":
            issues.append(
    QualityIssue(
        bill_id=bill.bill_id,
        issue_type=QualityIssueType.INCONSISTENT_DATA,
        severity=QualityIssueSeverity.MEDIUM,
        field_name="status",
        description="Status indicates bill is enacted but stage doesn't match",
        current_value=f"status: {bill.status}, stage: {bill.stage}",
        suggested_fix="Align status and stage fields",
        confidence=0.85,
         ) )

        return issues

    def _check_japanese_text_quality(self, bill: Bill) -> list[QualityIssue]:
        """Check Japanese text quality"""
        issues = []

        text_fields = [
            "title",
            "bill_outline",
            "background_context",
            "expected_effects",
        ]

        for field_name in text_fields:
            value = getattr(bill, field_name, None)

            if isinstance(value, str) and value.strip():
                if not self._is_japanese_text_quality_good(value):
                    issues.append(
                        QualityIssue(
                            bill_id=bill.bill_id,
                            issue_type=QualityIssueType.POOR_JAPANESE_TEXT,
                            severity=QualityIssueSeverity.MEDIUM,
                            field_name=field_name,
                            description=f"Japanese text quality is poor in '{field_name}'",
                            current_value=(
                                value[:100] + "..." if len(value) > 100 else value
                            ),
                            suggested_fix="Improve Japanese text quality and formatting",
                            confidence=0.7,
                        )
                    )

        return issues

    def _check_data_freshness(self, bill: Bill) -> list[QualityIssue]:
        """Check data freshness"""
        issues = []

        if bill.updated_at:
            days_old = (datetime.now() - bill.updated_at).days

            if days_old > self.quality_thresholds["timeliness_days"]:
                severity = (
                    QualityIssueSeverity.HIGH
                    if days_old > 90
                    else QualityIssueSeverity.MEDIUM
                )

                issues.append(
                    QualityIssue(
                        bill_id=bill.bill_id,
                        issue_type=QualityIssueType.OUTDATED_DATA,
                        severity=severity,
                        field_name="updated_at",
                        description=f"Bill data is {days_old} days old",
                        current_value=bill.updated_at,
                        suggested_fix="Update bill data with latest information",
                        confidence=0.9,
                    )
                )

        return issues

    def _check_for_duplicates(self, bills: list[Bill]) -> list[QualityIssue]:
        """Check for duplicate bills"""
        issues = []
        seen_bills = {}

        for bill in bills:
            # Create a key for duplicate detection
            key = (bill.title, bill.diet_session, bill.house_of_origin)

            if key in seen_bills:
                issues.append(
                    QualityIssue(
                        bill_id=bill.bill_id,
                        issue_type=QualityIssueType.DUPLICATE_DATA,
                        severity=QualityIssueSeverity.HIGH,
                        field_name=None,
                        description=f"Potential duplicate of bill {seen_bills[key]}",
                        current_value=bill.bill_id,
                        suggested_fix="Review and merge or remove duplicate bills",
                        confidence=0.8,
                    )
                )
            else:
                seen_bills[key] = bill.bill_id

        return issues

    def _is_bill_valid(self, bill: Bill) -> bool:
        """Check if a bill meets basic validity criteria"""
        for field_name in self.required_fields:
            value = getattr(bill, field_name, None)
            if not self._is_field_value_valid(field_name, value):
                return False
        return True

    def _is_field_value_valid(self, field_name: str, value: Any) -> bool:
        """Check if a field value is valid"""
        if value is None:
            return False

        if isinstance(value, str):
            return bool(value.strip())

        return True

    def _is_japanese_text_quality_good(self, text: str) -> bool:
        """Check if Japanese text meets quality criteria"""
        if len(text) < self.quality_thresholds["text_min_length"]:
            return False

        # Check for Japanese characters
        japanese_chars = sum(1 for char in text if ord(char) >= 0x3040)
        ratio = japanese_chars / len(text)

        return ratio >= self.quality_thresholds["japanese_text_ratio"]

    def _calculate_accuracy_rate(self, bills: list[Bill]) -> float:
        """Calculate overall accuracy rate"""
        total_fields = 0
        accurate_fields = 0

        for bill in bills:
            for field_name in self.required_fields + self.enhanced_fields:
                value = getattr(bill, field_name, None)
                total_fields += 1

                if self._is_field_accurate(field_name, value):
                    accurate_fields += 1

        return accurate_fields / total_fields if total_fields > 0 else 0

    def _calculate_consistency_rate(self, bills: list[Bill]) -> float:
        """Calculate data consistency rate"""
        total_checks = 0
        consistent_checks = 0

        for bill in bills:
            # Check various consistency rules
            checks = [
                self._check_date_consistency(bill),
                self._check_status_consistency(bill),
                self._check_house_consistency(bill),
            ]

            total_checks += len(checks)
            consistent_checks += sum(checks)

        return consistent_checks / total_checks if total_checks > 0 else 0

    def _calculate_timeliness_rate(self, bills: list[Bill]) -> float:
        """Calculate data timeliness rate"""
        recent_bills = 0

        for bill in bills:
            if bill.updated_at:
                days_old = (datetime.now() - bill.updated_at).days
                if days_old <= self.quality_thresholds["timeliness_days"]:
                    recent_bills += 1

        return recent_bills / len(bills) if bills else 0

    def _calculate_field_accuracy(self, bills: list[Bill], field_name: str) -> float:
        """Calculate accuracy rate for a specific field"""
        accurate_count = 0

        for bill in bills:
            value = getattr(bill, field_name, None)
            if self._is_field_accurate(field_name, value):
                accurate_count += 1

        return accurate_count / len(bills) if bills else 0

    def _calculate_field_consistency(self, bills: list[Bill], field_name: str) -> float:
        """Calculate consistency rate for a specific field"""
        # This would implement field-specific consistency checks
        return 0.9  # Placeholder

    def _calculate_field_timeliness(self, bills: list[Bill], field_name: str) -> float:
        """Calculate timeliness rate for a specific field"""
        # This would implement field-specific timeliness checks
        return 0.85  # Placeholder

    def _is_field_accurate(self, field_name: str, value: Any) -> bool:
        """Check if a field value is accurate"""
        if value is None:
            return False

        # Field-specific accuracy checks
        if field_name == "status":
            valid_statuses = ["提出", "審議中", "可決", "否決", "成立", "廃案"]
            return value in valid_statuses

        if field_name == "house_of_origin":
            return value in ["参議院", "衆議院"]

        return True

    def _check_date_consistency(self, bill: Bill) -> bool:
        """Check date consistency for a bill"""
        if bill.submitted_date and bill.updated_at:
            return bill.submitted_date <= bill.updated_at.date()
        return True

    def _check_status_consistency(self, bill: Bill) -> bool:
        """Check status consistency for a bill"""
        if bill.status == "成立" and bill.stage:
            return bill.stage == "enacted"
        return True

    def _check_house_consistency(self, bill: Bill) -> bool:
        """Check house consistency for a bill"""
        if hasattr(bill, "source_house") and bill.source_house:
            return bill.source_house in ["参議院", "衆議院"]
        return True

    def _generate_recommendations(
        self, issues: list[QualityIssue], field_metrics: dict[str, QualityMetrics]
    ) -> list[str]:
        """Generate improvement recommendations"""
        recommendations = []

        # Critical issues
        critical_issues = [
            issue for issue in issues if issue.severity == QualityIssueSeverity.CRITICAL
        ]
        if critical_issues:
            recommendations.append(
                f"Address {len(critical_issues)} critical data quality issues immediately"
            )

        # Missing enhanced fields
        enhanced_field_issues = [
            issue for issue in issues if issue.field_name in self.enhanced_fields
        ]
        if enhanced_field_issues:
            recommendations.append(
                "Implement enhanced data extraction for missing bill outline and context fields"
            )

        # Poor completeness
        poor_completeness_fields = [
            field
            for field, metrics in field_metrics.items()
            if metrics.completeness_rate < self.quality_thresholds["completeness_min"]
        ]
        if poor_completeness_fields:
            recommendations.append(
                f"Improve data completeness for fields: {', '.join(poor_completeness_fields)}"
            )

        # Outdated data
        outdated_issues = [
            issue
            for issue in issues
            if issue.issue_type == QualityIssueType.OUTDATED_DATA
        ]
        if outdated_issues:
            recommendations.append(
                "Implement automated data refresh for outdated bills"
            )

        return recommendations

    def _determine_improvement_priorities(
        self, issues: list[QualityIssue], field_metrics: dict[str, QualityMetrics]
    ) -> list[dict[str, Any]]:
        """Determine improvement priorities"""
        priorities = []

        # Priority 1: Critical issues
        critical_count = len(
            [
                issue
                for issue in issues
                if issue.severity == QualityIssueSeverity.CRITICAL
            ]
        )
        if critical_count > 0:
            priorities.append(
                {
                    "priority": 1,
                    "description": "Fix critical data quality issues",
                    "impact": "High",
                    "effort": "Medium",
                    "affected_records": critical_count,
                }
            )

        # Priority 2: Enhanced fields
        enhanced_missing = len(
            [issue for issue in issues if issue.field_name in self.enhanced_fields]
        )
        if enhanced_missing > 0:
            priorities.append(
                {
                    "priority": 2,
                    "description": "Implement enhanced data extraction",
                    "impact": "High",
                    "effort": "High",
                    "affected_records": enhanced_missing,
                }
            )

        # Priority 3: Data consistency
        consistency_issues = len(
            [
                issue
                for issue in issues
                if issue.issue_type == QualityIssueType.INCONSISTENT_DATA
            ]
        )
        if consistency_issues > 0:
            priorities.append(
                {
                    "priority": 3,
                    "description": "Resolve data consistency issues",
                    "impact": "Medium",
                    "effort": "Medium",
                    "affected_records": consistency_issues,
                }
            )

        return priorities

    def _count_issues_by_type(self, issues: list[QualityIssue]) -> dict[str, int]:
        """Count issues by type"""
        counts = defaultdict(int)
        for issue in issues:
            counts[issue.issue_type.value] += 1
        return dict(counts)

    def _count_issues_by_severity(self, issues: list[QualityIssue]) -> dict[str, int]:
        """Count issues by severity"""
        counts = defaultdict(int)
        for issue in issues:
            counts[issue.severity.value] += 1
        return dict(counts)

    def _identify_problematic_fields(
        self, field_metrics: dict[str, QualityMetrics]
    ) -> list[str]:
        """Identify most problematic fields"""
        field_scores = [
            (field, metrics.overall_quality_score)
            for field, metrics in field_metrics.items()
        ]

        # Sort by quality score (ascending - worst first)
        field_scores.sort(key=lambda x: x[1])

        return [field for field, score in field_scores[:5]]

    def _create_empty_report(self) -> QualityReport:
        """Create an empty report when no data is available"""
        return QualityReport(
            audit_timestamp=datetime.now(),
            total_bills=0,
            overall_metrics=QualityMetrics(0, 0, 0, 0, 0, 0, 0, 0),
            field_metrics={},
            issues=[],
            recommendations=["No bills found in database"],
            improvement_priorities=[],
        )

    def get_quality_trend(self, days: int = 30) -> dict[str, Any]:
        """Get quality trend over time"""
        try:
            with self.SessionLocal() as session:
                # Get bills updated in the last N days
                cutoff_date = datetime.now() - timedelta(days=days)

                query = select(Bill).where(Bill.updated_at >= cutoff_date)
                recent_bills = session.execute(query).scalars().all()

                if not recent_bills:
                    return {"trend": "no_data", "message": "No recent bills to analyze"}

                # Calculate daily quality scores
                daily_scores = {}
                for bill in recent_bills:
                    date_key = bill.updated_at.date()
                    if date_key not in daily_scores:
                        daily_scores[date_key] = {"bills": [], "avg_score": 0}

                    # Calculate bill quality score
                    score = self._calculate_bill_quality_score(bill)
                    daily_scores[date_key]["bills"].append(score)

                # Calculate averages
                for date_key in daily_scores:
                    scores = daily_scores[date_key]["bills"]
                    daily_scores[date_key]["avg_score"] = sum(scores) / len(scores)

                # Determine trend
                scores = list(daily_scores.values())
                if len(scores) > 1:
                    first_half = scores[: len(scores) // 2]
                    second_half = scores[len(scores) // 2 :]

                    first_avg = sum(s["avg_score"] for s in first_half) / len(
                        first_half
                    )
                    second_avg = sum(s["avg_score"] for s in second_half) / len(
                        second_half
                    )

                    if second_avg > first_avg + 0.05:
                        trend = "improving"
                    elif second_avg < first_avg - 0.05:
                        trend = "declining"
                    else:
                        trend = "stable"
                else:
                    trend = "insufficient_data"

                return {
                    "trend": trend,
                    "period_days": days,
                    "total_bills": len(recent_bills),
                    "daily_scores": daily_scores,
                    "overall_average": (
                        sum(s["avg_score"] for s in scores) / len(scores)
                        if scores
                        else 0
                    ),
                }

        except Exception as e:
            self.logger.error(f"Error calculating quality trend: {e}")
            return {"trend": "error", "message": str(e)}

    def _calculate_bill_quality_score(self, bill: Bill) -> float:
        """Calculate quality score for a single bill"""
        score = 0.0
        max_score = 0.0

        # Check each field with weights
        for field_name, weight in self.field_weights.items():
            max_score += weight
            value = getattr(bill, field_name, None)

            if self._is_field_value_valid(field_name, value):
                if isinstance(value, str) and self._is_japanese_text_quality_good(
                    value
                ):
                    score += weight
                elif not isinstance(value, str):
                    score += weight
                else:
                    score += weight * 0.5  # Partial credit for present but poor quality

        return score / max_score if max_score > 0 else 0.0

    def export_report(
        self, report: QualityReport, format: str = "json"
    ) -> dict[str, Any]:
        """Export quality report in various formats"""
        if format == "json":
            return {
                "audit_timestamp": report.audit_timestamp.isoformat(),
                "total_bills": report.total_bills,
                "overall_metrics": {
                    "total_records": report.overall_metrics.total_records,
                    "valid_records": report.overall_metrics.valid_records,
                    "completeness_rate": report.overall_metrics.completeness_rate,
                    "accuracy_rate": report.overall_metrics.accuracy_rate,
                    "consistency_rate": report.overall_metrics.consistency_rate,
                    "timeliness_rate": report.overall_metrics.timeliness_rate,
                    "overall_quality_score": report.overall_metrics.overall_quality_score,
                },
                "field_metrics": {
                    field: {
                        "completeness_rate": metrics.completeness_rate,
                        "overall_quality_score": metrics.overall_quality_score,
                        "valid_records": metrics.valid_records,
                        "invalid_records": metrics.invalid_records,
                    }
                    for field, metrics in report.field_metrics.items()
                },
                "issues_summary": {
                    "total_issues": len(report.issues),
                    "by_type": report.issues_by_type,
                    "by_severity": report.issues_by_severity,
                },
                "recommendations": report.recommendations,
                "improvement_priorities": report.improvement_priorities,
                "most_problematic_fields": report.most_problematic_fields,
            }
        else:
            return {"error": f"Unsupported format: {format}"}
