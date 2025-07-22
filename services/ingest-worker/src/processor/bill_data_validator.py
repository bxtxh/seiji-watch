"""
Bill data validation module for quality assurance and consistency checking.
Validates data completeness, format, and integrity.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ..scraper.enhanced_diet_scraper import EnhancedBillData
from .bill_data_merger import MergeResult


class ValidationSeverity(Enum):
    """Validation issue severity levels"""

    CRITICAL = "critical"  # Data corruption or missing required fields
    WARNING = "warning"  # Data quality issues or inconsistencies
    INFO = "info"  # Minor issues or suggestions


@dataclass
class ValidationIssue:
    """Individual validation issue"""

    field_name: str
    issue_type: str
    severity: ValidationSeverity
    message: str
    suggested_fix: str | None = None
    current_value: Any | None = None
    expected_format: str | None = None


@dataclass
class ValidationResult:
    """Result of data validation"""

    bill_id: str
    is_valid: bool
    quality_score: float
    issues: list[ValidationIssue] = field(default_factory=list)
    completeness_score: float = 0.0
    consistency_score: float = 0.0
    format_score: float = 0.0

    def get_critical_issues(self) -> list[ValidationIssue]:
        """Get critical validation issues"""
        return [
            issue
            for issue in self.issues
            if issue.severity == ValidationSeverity.CRITICAL
        ]

    def get_warning_issues(self) -> list[ValidationIssue]:
        """Get warning validation issues"""
        return [
            issue
            for issue in self.issues
            if issue.severity == ValidationSeverity.WARNING
        ]

    def get_info_issues(self) -> list[ValidationIssue]:
        """Get info validation issues"""
        return [
            issue for issue in self.issues if issue.severity == ValidationSeverity.INFO
        ]


class BillDataValidator:
    """Comprehensive bill data validator"""

    def __init__(self, strict_mode: bool = False, require_japanese: bool = True):
        self.strict_mode = strict_mode
        self.require_japanese = require_japanese
        self.logger = logging.getLogger(__name__)

        # Required fields for different validation levels
        self.required_fields = {
            "basic": ["bill_id", "title", "status", "stage", "submitter", "category"],
            "standard": [
                "bill_id",
                "title",
                "status",
                "stage",
                "submitter",
                "category",
                "diet_session",
                "house_of_origin",
            ],
            "comprehensive": [
                "bill_id",
                "title",
                "status",
                "stage",
                "submitter",
                "category",
                "diet_session",
                "house_of_origin",
                "bill_outline",
                "source_house",
            ],
        }

        # Field format patterns
        self.format_patterns = {
            "bill_id": r"^[A-Z0-9\-]+$",
            "diet_session": r"^\d{1,3}$",
            "submitted_date": r"^\d{4}-\d{2}-\d{2}$",
            "implementation_date": r"^\d{4}-\d{2}-\d{2}$",
            "house_of_origin": r"^(参議院|衆議院)$",
            "source_house": r"^(参議院|衆議院|両院)$",
            "submitter": r"^(政府|議員)$",
            "data_quality_score": r"^[0-1](\.\d+)?$",
        }

        # Japanese text patterns
        self.japanese_patterns = {
            "hiragana": r"[ひらがな]",
            "katakana": r"[カタカナ]",
            "kanji": r"[一-龯]",
            "japanese_text": r"[一-龯ひらがなカタカナ]",
        }

        # Status value mappings
        self.valid_statuses = {
            "成立",
            "可決",
            "否決",
            "審議中",
            "委員会審議",
            "継続審議",
            "撤回",
            "廃案",
            "backlog",
            "under_review",
            "pending_vote",
            "passed",
            "rejected",
            "withdrawn",
            "expired",
        }

        # Stage value mappings
        self.valid_stages = {
            "submitted",
            "committee_review",
            "plenary_debate",
            "voting",
            "passed",
            "rejected",
            "withdrawn",
            "提出",
            "委員会審議",
            "本会議",
            "採決",
            "成立",
            "否決",
            "撤回",
            "廃案",
        }

        # Category mappings
        self.valid_categories = {
            "budget",
            "taxation",
            "social_security",
            "foreign_affairs",
            "economy",
            "education",
            "environment",
            "infrastructure",
            "defense",
            "judiciary",
            "administration",
            "other",
            "予算・決算",
            "税制",
            "社会保障",
            "外交・国際",
            "経済・産業",
            "教育・文化",
            "環境・エネルギー",
            "インフラ・交通",
            "防衛・安全保障",
            "司法・法務",
            "行政・公務員",
            "その他",
        }

    def validate_bill(
        self, bill_data: EnhancedBillData, validation_level: str = "standard"
    ) -> ValidationResult:
        """Validate a single bill"""

        result = ValidationResult(
            bill_id=bill_data.bill_id or "unknown", is_valid=True, quality_score=0.0
        )

        # Validate required fields
        self._validate_required_fields(bill_data, result, validation_level)

        # Validate field formats
        self._validate_field_formats(bill_data, result)

        # Validate data consistency
        self._validate_data_consistency(bill_data, result)

        # Validate Japanese text content
        if self.require_japanese:
            self._validate_japanese_content(bill_data, result)

        # Validate logical relationships
        self._validate_logical_relationships(bill_data, result)

        # Calculate scores
        result.completeness_score = self._calculate_completeness_score(
            bill_data, validation_level
        )
        result.consistency_score = self._calculate_consistency_score(result)
        result.format_score = self._calculate_format_score(result)

        # Calculate overall quality score
        result.quality_score = self._calculate_overall_quality_score(result)

        # Determine if bill is valid
        result.is_valid = len(result.get_critical_issues()) == 0

        return result

    def validate_bills(
        self, bills: list[EnhancedBillData], validation_level: str = "standard"
    ) -> list[ValidationResult]:
        """Validate multiple bills"""
        results = []

        for bill in bills:
            try:
                result = self.validate_bill(bill, validation_level)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error validating bill {bill.bill_id}: {e}")
                # Create error result
                error_result = ValidationResult(
                    bill_id=bill.bill_id or "unknown",
                    is_valid=False,
                    quality_score=0.0,
                    issues=[
                        ValidationIssue(
                            field_name="_validation",
                            issue_type="validation_error",
                            severity=ValidationSeverity.CRITICAL,
                            message=f"Validation failed: {str(e)}",
                            current_value=str(e),
                        )
                    ],
                )
                results.append(error_result)

        return results

    def validate_merge_results(
        self, merge_results: list[MergeResult], validation_level: str = "standard"
    ) -> list[ValidationResult]:
        """Validate merge results"""
        results = []

        for merge_result in merge_results:
            try:
                # Validate the merged bill
                validation_result = self.validate_bill(
                    merge_result.merged_bill, validation_level
                )

                # Add merge-specific validations
                self._validate_merge_quality(merge_result, validation_result)

                results.append(validation_result)
            except Exception as e:
                self.logger.error(
                    f"Error validating merge result for {merge_result.merged_bill.bill_id}: {e}"
                )
                continue

        return results

    def _validate_required_fields(
        self,
        bill_data: EnhancedBillData,
        result: ValidationResult,
        validation_level: str,
    ):
        """Validate required fields"""
        required_fields = self.required_fields.get(
            validation_level, self.required_fields["standard"]
        )

        for field_name in required_fields:
            value = getattr(bill_data, field_name, None)

            if value is None or (isinstance(value, str) and not value.strip()):
                result.issues.append(
                    ValidationIssue(
                        field_name=field_name,
                        issue_type="missing_required_field",
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Required field '{field_name}' is missing or empty",
                        suggested_fix=f"Provide a value for '{field_name}'",
                        current_value=value,
                    )
                )

    def _validate_field_formats(
        self, bill_data: EnhancedBillData, result: ValidationResult
    ):
        """Validate field formats"""
        for field_name, pattern in self.format_patterns.items():
            value = getattr(bill_data, field_name, None)

            if value is not None:
                if isinstance(value, str):
                    if not re.match(pattern, value):
                        result.issues.append(
                            ValidationIssue(
                                field_name=field_name,
                                issue_type="invalid_format",
                                severity=ValidationSeverity.WARNING,
                                message=f"Field '{field_name}' has invalid format",
                                suggested_fix=f"Ensure '{field_name}' matches pattern: {pattern}",
                                current_value=value,
                                expected_format=pattern,
                            )
                        )
                elif isinstance(value, int | float):
                    # Convert to string for pattern matching
                    str_value = str(value)
                    if not re.match(pattern, str_value):
                        result.issues.append(
                            ValidationIssue(
                                field_name=field_name,
                                issue_type="invalid_format",
                                severity=ValidationSeverity.WARNING,
                                message=f"Field '{field_name}' has invalid format",
                                current_value=value,
                                expected_format=pattern,
                            )
                        )

    def _validate_data_consistency(
        self, bill_data: EnhancedBillData, result: ValidationResult
    ):
        """Validate data consistency"""

        # Check status consistency
        if bill_data.status and bill_data.status not in self.valid_statuses:
            result.issues.append(
                ValidationIssue(
                    field_name="status",
                    issue_type="invalid_value",
                    severity=ValidationSeverity.WARNING,
                    message=f"Status '{bill_data.status}' is not in valid status list",
                    suggested_fix=f"Use one of: {', '.join(list(self.valid_statuses)[:5])}...",
                    current_value=bill_data.status,
                )
            )

        # Check stage consistency
        if bill_data.stage and bill_data.stage not in self.valid_stages:
            result.issues.append(
                ValidationIssue(
                    field_name="stage",
                    issue_type="invalid_value",
                    severity=ValidationSeverity.WARNING,
                    message=f"Stage '{bill_data.stage}' is not in valid stage list",
                    suggested_fix=f"Use one of: {', '.join(list(self.valid_stages)[:5])}...",
                    current_value=bill_data.stage,
                )
            )

        # Check category consistency
        if bill_data.category and bill_data.category not in self.valid_categories:
            result.issues.append(
                ValidationIssue(
                    field_name="category",
                    issue_type="invalid_value",
                    severity=ValidationSeverity.WARNING,
                    message=f"Category '{bill_data.category}' is not in valid category list",
                    suggested_fix=f"Use one of: {', '.join(list(self.valid_categories)[:5])}...",
                    current_value=bill_data.category,
                )
            )

        # Check data quality score range
        if bill_data.data_quality_score is not None:
            if not (0.0 <= bill_data.data_quality_score <= 1.0):
                result.issues.append(
                    ValidationIssue(
                        field_name="data_quality_score",
                        issue_type="out_of_range",
                        severity=ValidationSeverity.WARNING,
                        message=f"Data quality score {bill_data.data_quality_score} is out of range [0.0, 1.0]",
                        suggested_fix="Ensure data quality score is between 0.0 and 1.0",
                        current_value=bill_data.data_quality_score,
                    )
                )

    def _validate_japanese_content(
        self, bill_data: EnhancedBillData, result: ValidationResult
    ):
        """Validate Japanese text content"""
        text_fields = [
            "title",
            "bill_outline",
            "background_context",
            "expected_effects",
            "summary",
        ]

        for field_name in text_fields:
            value = getattr(bill_data, field_name, None)

            if value and isinstance(value, str):
                # Check if contains Japanese characters
                if not re.search(self.japanese_patterns["japanese_text"], value):
                    result.issues.append(
                        ValidationIssue(
                            field_name=field_name,
                            issue_type="missing_japanese_text",
                            severity=ValidationSeverity.INFO,
                            message=f"Field '{field_name}' does not contain Japanese characters",
                            suggested_fix="Ensure Japanese text fields contain appropriate Japanese content",
                            current_value=value[:100] + "..."
                            if len(value) > 100
                            else value,
                        )
                    )

                # Check for minimum length
                if len(value.strip()) < 10:
                    result.issues.append(
                        ValidationIssue(
                            field_name=field_name,
                            issue_type="insufficient_content",
                            severity=ValidationSeverity.INFO,
                            message=f"Field '{field_name}' has insufficient content (< 10 characters)",
                            suggested_fix="Ensure text fields contain meaningful content",
                            current_value=value,
                        )
                    )

    def _validate_logical_relationships(
        self, bill_data: EnhancedBillData, result: ValidationResult
    ):
        """Validate logical relationships between fields"""

        # Check status-stage consistency
        if bill_data.status and bill_data.stage:
            status_stage_mapping = {
                "成立": ["成立", "passed"],
                "可決": ["採決", "voting", "passed"],
                "否決": ["否決", "rejected"],
                "審議中": ["審議中", "committee_review", "under_review"],
            }

            if bill_data.status in status_stage_mapping:
                valid_stages = status_stage_mapping[bill_data.status]
                if bill_data.stage not in valid_stages:
                    result.issues.append(
                        ValidationIssue(
                            field_name="stage",
                            issue_type="inconsistent_status_stage",
                            severity=ValidationSeverity.WARNING,
                            message=f"Stage '{bill_data.stage}' is inconsistent with status '{bill_data.status}'",
                            suggested_fix=f"Use stage that matches status: {', '.join(valid_stages)}",
                            current_value=bill_data.stage,
                        )
                    )

        # Check submitter-submitter_type consistency
        if bill_data.submitter and bill_data.submitter_type:
            if bill_data.submitter != bill_data.submitter_type:
                result.issues.append(
                    ValidationIssue(
                        field_name="submitter_type",
                        issue_type="inconsistent_submitter_fields",
                        severity=ValidationSeverity.WARNING,
                        message=f"Submitter '{bill_data.submitter}' and submitter_type '{bill_data.submitter_type}' are inconsistent",
                        suggested_fix="Ensure submitter and submitter_type fields match",
                        current_value=bill_data.submitter_type,
                    )
                )

        # Check date logical order
        dates = [
            ("submitted_date", bill_data.submitted_date),
            ("first_reading_date", bill_data.first_reading_date),
            ("committee_referral_date", bill_data.committee_referral_date),
            ("committee_report_date", bill_data.committee_report_date),
            ("final_vote_date", bill_data.final_vote_date),
            ("promulgated_date", bill_data.promulgated_date),
        ]

        # Convert string dates to datetime objects for comparison
        parsed_dates = []
        for field_name, date_value in dates:
            if date_value:
                try:
                    if isinstance(date_value, str):
                        parsed_date = datetime.strptime(date_value, "%Y-%m-%d")
                    elif isinstance(date_value, datetime):
                        parsed_date = date_value
                    else:
                        continue
                    parsed_dates.append((field_name, parsed_date))
                except ValueError:
                    continue

        # Check chronological order
        for i in range(len(parsed_dates) - 1):
            current_field, current_date = parsed_dates[i]
            next_field, next_date = parsed_dates[i + 1]

            if current_date > next_date:
                result.issues.append(
                    ValidationIssue(
                        field_name=next_field,
                        issue_type="chronological_order_violation",
                        severity=ValidationSeverity.WARNING,
                        message=f"Date in '{next_field}' is earlier than '{current_field}'",
                        suggested_fix="Ensure dates are in chronological order",
                        current_value=str(next_date.date()),
                    )
                )

    def _validate_merge_quality(
        self, merge_result: MergeResult, validation_result: ValidationResult
    ):
        """Validate merge quality"""

        # Check merge quality score
        if merge_result.merge_quality_score < 0.5:
            validation_result.issues.append(
                ValidationIssue(
                    field_name="_merge_quality",
                    issue_type="low_merge_quality",
                    severity=ValidationSeverity.WARNING,
                    message=f"Merge quality score {merge_result.merge_quality_score:.2f} is below threshold (0.5)",
                    suggested_fix="Review merge conflicts and improve data quality",
                    current_value=merge_result.merge_quality_score,
                )
            )

        # Check for high number of conflicts
        if len(merge_result.conflicts) > 5:
            validation_result.issues.append(
                ValidationIssue(
                    field_name="_merge_conflicts",
                    issue_type="high_conflict_count",
                    severity=ValidationSeverity.WARNING,
                    message=f"High number of merge conflicts: {len(merge_result.conflicts)}",
                    suggested_fix="Review data sources and improve data consistency",
                    current_value=len(merge_result.conflicts),
                )
            )

        # Check for low-confidence conflicts
        low_confidence_conflicts = [
            c for c in merge_result.conflicts if c.confidence < 0.6
        ]
        if low_confidence_conflicts:
            validation_result.issues.append(
                ValidationIssue(
                    field_name="_merge_confidence",
                    issue_type="low_confidence_resolution",
                    severity=ValidationSeverity.INFO,
                    message=f"{len(low_confidence_conflicts)} conflicts resolved with low confidence",
                    suggested_fix="Review low-confidence merge resolutions manually",
                    current_value=len(low_confidence_conflicts),
                )
            )

    def _calculate_completeness_score(
        self, bill_data: EnhancedBillData, validation_level: str
    ) -> float:
        """Calculate completeness score"""
        required_fields = self.required_fields.get(
            validation_level, self.required_fields["standard"]
        )

        # Count non-empty required fields
        filled_required = 0
        for field_name in required_fields:
            value = getattr(bill_data, field_name, None)
            if value is not None and (not isinstance(value, str) or value.strip()):
                filled_required += 1

        # Count filled optional fields
        optional_fields = [
            "bill_outline",
            "background_context",
            "expected_effects",
            "key_provisions",
            "related_laws",
            "implementation_date",
            "submitting_members",
            "supporting_members",
            "submitting_party",
            "sponsoring_ministry",
            "committee_assignments",
            "voting_results",
        ]

        filled_optional = 0
        for field_name in optional_fields:
            value = getattr(bill_data, field_name, None)
            if value is not None:
                if isinstance(value, str) and value.strip():
                    filled_optional += 1
                elif isinstance(value, list | dict) and len(value) > 0:
                    filled_optional += 1
                elif not isinstance(value, str | list | dict):
                    filled_optional += 1

        # Calculate weighted score
        required_score = (
            filled_required / len(required_fields) if required_fields else 0.0
        )
        optional_score = (
            filled_optional / len(optional_fields) if optional_fields else 0.0
        )

        # Weight required fields more heavily
        return (required_score * 0.8) + (optional_score * 0.2)

    def _calculate_consistency_score(self, result: ValidationResult) -> float:
        """Calculate consistency score based on validation issues"""
        # Start with perfect score
        score = 1.0

        # Deduct for each issue based on severity
        for issue in result.issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                score -= 0.2
            elif issue.severity == ValidationSeverity.WARNING:
                score -= 0.1
            elif issue.severity == ValidationSeverity.INFO:
                score -= 0.05

        return max(score, 0.0)

    def _calculate_format_score(self, result: ValidationResult) -> float:
        """Calculate format score based on format validation issues"""
        # Start with perfect score
        score = 1.0

        # Deduct for format issues
        format_issues = [
            issue
            for issue in result.issues
            if issue.issue_type in ["invalid_format", "out_of_range"]
        ]
        score -= len(format_issues) * 0.1

        return max(score, 0.0)

    def _calculate_overall_quality_score(self, result: ValidationResult) -> float:
        """Calculate overall quality score"""
        # Weighted average of component scores
        weights = {
            "completeness": 0.4,
            "consistency": 0.3,
            "format": 0.3,
        }

        score = (
            result.completeness_score * weights["completeness"]
            + result.consistency_score * weights["consistency"]
            + result.format_score * weights["format"]
        )

        return round(score, 2)

    def get_validation_summary(
        self, validation_results: list[ValidationResult]
    ) -> dict[str, Any]:
        """Get summary statistics for validation results"""

        if not validation_results:
            return {}

        total_bills = len(validation_results)
        valid_bills = sum(1 for r in validation_results if r.is_valid)
        invalid_bills = total_bills - valid_bills

        # Issue statistics
        total_issues = sum(len(r.issues) for r in validation_results)
        critical_issues = sum(len(r.get_critical_issues()) for r in validation_results)
        warning_issues = sum(len(r.get_warning_issues()) for r in validation_results)
        info_issues = sum(len(r.get_info_issues()) for r in validation_results)

        # Quality scores
        quality_scores = [r.quality_score for r in validation_results]
        avg_quality = sum(quality_scores) / len(quality_scores)

        # Completeness scores
        completeness_scores = [r.completeness_score for r in validation_results]
        avg_completeness = sum(completeness_scores) / len(completeness_scores)

        # Common issues
        issue_types = {}
        for result in validation_results:
            for issue in result.issues:
                issue_types[issue.issue_type] = issue_types.get(issue.issue_type, 0) + 1

        return {
            "total_bills": total_bills,
            "valid_bills": valid_bills,
            "invalid_bills": invalid_bills,
            "validation_rate": valid_bills / total_bills,
            "total_issues": total_issues,
            "critical_issues": critical_issues,
            "warning_issues": warning_issues,
            "info_issues": info_issues,
            "avg_quality_score": round(avg_quality, 2),
            "avg_completeness_score": round(avg_completeness, 2),
            "common_issues": dict(
                sorted(issue_types.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            "quality_distribution": {
                "excellent": sum(1 for s in quality_scores if s >= 0.9),
                "good": sum(1 for s in quality_scores if 0.7 <= s < 0.9),
                "fair": sum(1 for s in quality_scores if 0.5 <= s < 0.7),
                "poor": sum(1 for s in quality_scores if s < 0.5),
            },
        }
