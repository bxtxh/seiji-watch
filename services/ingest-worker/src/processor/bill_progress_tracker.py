"""
Bill progress tracking system for detailed legislative process monitoring.
Tracks bill progress through various stages and committees.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ...shared.src.shared.models.bill_process_history import (
    BillProcessActionType,
    BillProcessHistory,
    BillProcessResult,
    BillProcessStage,
)
from ..scraper.enhanced_diet_scraper import EnhancedBillData


class ProgressTrackingStatus(Enum):
    """Progress tracking status"""
    ACTIVE = "active"           # 現在追跡中
    COMPLETED = "completed"     # 追跡完了（成立・否決・廃案）
    SUSPENDED = "suspended"     # 一時停止
    ERROR = "error"             # エラー発生


@dataclass
class BillProgressSnapshot:
    """Bill progress snapshot at a specific point in time"""
    bill_id: str
    snapshot_date: datetime
    current_stage: str
    current_house: str
    current_committee: str | None = None
    last_action: str | None = None
    last_action_date: datetime | None = None
    voting_results: dict[str, Any] | None = None
    amendments: list[dict[str, Any]] | None = None
    next_expected_action: str | None = None
    confidence_score: float = 0.0
    data_source: str = "unknown"


@dataclass
class ProgressTrackingResult:
    """Result of progress tracking operation"""
    bill_id: str
    tracking_status: ProgressTrackingStatus
    current_snapshot: BillProgressSnapshot
    progress_history: list[BillProcessHistory] = field(default_factory=list)
    stage_transitions: list[dict[str, Any]] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)


class BillProgressTracker:
    """Advanced bill progress tracking system"""

    def __init__(self,
                 update_interval_hours: int = 24,
                 enable_alerts: bool = True):
        self.update_interval_hours = update_interval_hours
        self.enable_alerts = enable_alerts
        self.logger = logging.getLogger(__name__)

        # Stage progression mappings
        self.stage_progressions = {
            "参議院": [
                BillProcessStage.SUBMITTED,
                BillProcessStage.RECEIVED,
                BillProcessStage.COMMITTEE_REFERRED,
                BillProcessStage.COMMITTEE_REVIEW,
                BillProcessStage.COMMITTEE_VOTE,
                BillProcessStage.PLENARY_DEBATE,
                BillProcessStage.PLENARY_VOTE,
                BillProcessStage.INTER_HOUSE_SENT,
            ],
            "衆議院": [
                BillProcessStage.SUBMITTED,
                BillProcessStage.RECEIVED,
                BillProcessStage.COMMITTEE_REFERRED,
                BillProcessStage.COMMITTEE_REVIEW,
                BillProcessStage.COMMITTEE_VOTE,
                BillProcessStage.PLENARY_DEBATE,
                BillProcessStage.PLENARY_VOTE,
                BillProcessStage.INTER_HOUSE_SENT,
            ]
        }

        # Committee patterns for different houses
        self.committee_patterns = {
            "参議院": [
                r'内閣委員会', r'総務委員会', r'法務委員会', r'外交防衛委員会',
                r'財政金融委員会', r'文教科学委員会', r'厚生労働委員会',
                r'農林水産委員会', r'経済産業委員会', r'国土交通委員会',
                r'環境委員会', r'国家基本政策委員会', r'予算委員会',
                r'決算委員会', r'行政監視委員会', r'議院運営委員会',
            ],
            "衆議院": [
                r'内閣委員会', r'総務委員会', r'法務委員会', r'外務委員会',
                r'財務金融委員会', r'文部科学委員会', r'厚生労働委員会',
                r'農林水産委員会', r'経済産業委員会', r'国土交通委員会',
                r'環境委員会', r'安全保障委員会', r'予算委員会',
                r'決算行政監視委員会', r'議院運営委員会',
            ]
        }

        # Action detection patterns
        self.action_patterns = {
            BillProcessActionType.SUBMISSION: [r'提出', r'上程'],
            BillProcessActionType.COMMITTEE_REFERRAL: [r'付託', r'委員会付託'],
            BillProcessActionType.COMMITTEE_DISCUSSION: [r'委員会審議', r'質疑'],
            BillProcessActionType.COMMITTEE_VOTING: [r'委員会採決', r'委員会議決'],
            BillProcessActionType.PLENARY_DISCUSSION: [r'本会議討論', r'本会議審議'],
            BillProcessActionType.PLENARY_VOTING: [r'本会議採決', r'本会議議決'],
            BillProcessActionType.AMENDMENT: [r'修正', r'修正案'],
            BillProcessActionType.ENACTMENT: [r'成立', r'可決成立'],
            BillProcessActionType.REJECTION: [r'否決', r'不採択'],
            BillProcessActionType.WITHDRAWAL: [r'撤回', r'取り下げ'],
            BillProcessActionType.CONTINUATION: [r'継続審議', r'継続'],
        }

        # Result patterns
        self.result_patterns = {
            BillProcessResult.APPROVED: [r'可決', r'承認', r'採択'],
            BillProcessResult.REJECTED: [r'否決', r'不承認', r'不採択'],
            BillProcessResult.AMENDED: [r'修正可決', r'修正承認'],
            BillProcessResult.CONTINUED: [r'継続審議', r'継続'],
            BillProcessResult.WITHDRAWN: [r'撤回', r'取り下げ'],
            BillProcessResult.POSTPONED: [r'延期', r'保留'],
        }

    def track_bill_progress(self, bill_data: EnhancedBillData) -> ProgressTrackingResult:
        """Track progress for a single bill"""
        try:
            # Create current snapshot
            current_snapshot = self._create_progress_snapshot(bill_data)

            # Determine tracking status
            tracking_status = self._determine_tracking_status(bill_data)

            # Generate progress history
            progress_history = self._generate_progress_history(bill_data)

            # Analyze stage transitions
            stage_transitions = self._analyze_stage_transitions(progress_history)

            # Generate alerts
            alerts = self._generate_alerts(bill_data, current_snapshot, stage_transitions)

            return ProgressTrackingResult(
                bill_id=bill_data.bill_id,
                tracking_status=tracking_status,
                current_snapshot=current_snapshot,
                progress_history=progress_history,
                stage_transitions=stage_transitions,
                alerts=alerts,
                last_updated=datetime.now()
            )

        except Exception as e:
            self.logger.error(f"Error tracking progress for bill {bill_data.bill_id}: {e}")
            return ProgressTrackingResult(
                bill_id=bill_data.bill_id,
                tracking_status=ProgressTrackingStatus.ERROR,
                current_snapshot=BillProgressSnapshot(
                    bill_id=bill_data.bill_id,
                    snapshot_date=datetime.now(),
                    current_stage="error",
                    current_house="unknown",
                    confidence_score=0.0,
                    data_source="error"
                ),
                alerts=[f"Error tracking progress: {str(e)}"]
            )

    def _create_progress_snapshot(self, bill_data: EnhancedBillData) -> BillProgressSnapshot:
        """Create a progress snapshot from bill data"""

        # Determine current stage
        current_stage = self._map_status_to_stage(bill_data.status)

        # Extract committee information
        current_committee = self._extract_current_committee(bill_data)

        # Extract last action
        last_action, last_action_date = self._extract_last_action(bill_data)

        # Predict next expected action
        next_expected_action = self._predict_next_action(current_stage, bill_data.house_of_origin)

        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(bill_data)

        return BillProgressSnapshot(
            bill_id=bill_data.bill_id,
            snapshot_date=datetime.now(),
            current_stage=current_stage,
            current_house=bill_data.house_of_origin or "unknown",
            current_committee=current_committee,
            last_action=last_action,
            last_action_date=last_action_date,
            voting_results=bill_data.voting_results,
            amendments=bill_data.amendments,
            next_expected_action=next_expected_action,
            confidence_score=confidence_score,
            data_source=bill_data.source_house or "unknown"
        )

    def _determine_tracking_status(self, bill_data: EnhancedBillData) -> ProgressTrackingStatus:
        """Determine the tracking status for a bill"""

        if bill_data.status in ['成立', '可決成立', 'passed']:
            return ProgressTrackingStatus.COMPLETED
        elif bill_data.status in ['否決', '不採択', 'rejected']:
            return ProgressTrackingStatus.COMPLETED
        elif bill_data.status in ['廃案', '撤回', 'withdrawn', 'expired']:
            return ProgressTrackingStatus.COMPLETED
        elif bill_data.status in ['継続審議', 'continued']:
            return ProgressTrackingStatus.SUSPENDED
        else:
            return ProgressTrackingStatus.ACTIVE

    def _generate_progress_history(self, bill_data: EnhancedBillData) -> list[BillProcessHistory]:
        """Generate progress history from bill data"""
        history = []

        # Add submission event
        if bill_data.submitted_date:
            history.append(
                BillProcessHistory(
                    bill_id=bill_data.bill_id,
                    stage=BillProcessStage.SUBMITTED,
                    house=bill_data.house_of_origin or "unknown",
                    committee=None,
                    action_date=bill_data.submitted_date,
                    action_type=BillProcessActionType.SUBMISSION,
                    result=BillProcessResult.NOTED,
                    details={'submitter': bill_data.submitter},
                    notes=f"提出者: {bill_data.submitter}"
                )
            )

        # Add committee referral
        if bill_data.committee_referral_date:
            committee = self._extract_current_committee(bill_data)
            history.append(
                BillProcessHistory(
                    bill_id=bill_data.bill_id,
                    stage=BillProcessStage.COMMITTEE_REFERRED,
                    house=bill_data.house_of_origin or "unknown",
                    committee=committee,
                    action_date=bill_data.committee_referral_date,
                    action_type=BillProcessActionType.COMMITTEE_REFERRAL,
                    result=BillProcessResult.REFERRED,
                    details={'committee': committee},
                    notes=f"委員会: {committee}"
                )
            )

        # Add committee report
        if bill_data.committee_report_date:
            history.append(
                BillProcessHistory(
                    bill_id=bill_data.bill_id,
                    stage=BillProcessStage.COMMITTEE_VOTE,
                    house=bill_data.house_of_origin or "unknown",
                    committee=self._extract_current_committee(bill_data),
                    action_date=bill_data.committee_report_date,
                    action_type=BillProcessActionType.COMMITTEE_REPORT,
                    result=BillProcessResult.APPROVED,
                    details={'report_date': bill_data.committee_report_date},
                    notes="委員会報告"
                )
            )

        # Add final vote
        if bill_data.final_vote_date:
            vote_result = self._determine_vote_result(bill_data.status)
            history.append(
                BillProcessHistory(
                    bill_id=bill_data.bill_id,
                    stage=BillProcessStage.PLENARY_VOTE,
                    house=bill_data.house_of_origin or "unknown",
                    committee=None,
                    action_date=bill_data.final_vote_date,
                    action_type=BillProcessActionType.PLENARY_VOTING,
                    result=vote_result,
                    details={'voting_results': bill_data.voting_results},
                    notes=f"最終議決: {bill_data.status}"
                )
            )

        # Add amendments
        if bill_data.amendments:
            for amendment in bill_data.amendments:
                if isinstance(amendment, dict):
                    history.append(
                        BillProcessHistory(
                            bill_id=bill_data.bill_id,
                            stage=BillProcessStage.COMMITTEE_REVIEW,
                            house=bill_data.house_of_origin or "unknown",
                            committee=self._extract_current_committee(bill_data),
                            action_date=datetime.now(),  # Would be extracted if available
                            action_type=BillProcessActionType.AMENDMENT,
                            result=BillProcessResult.AMENDED,
                            details=amendment,
                            notes=amendment.get('description', '修正')
                        )
                    )

        return sorted(history, key=lambda x: x.action_date)

    def _analyze_stage_transitions(self, progress_history: list[BillProcessHistory]) -> list[dict[str, Any]]:
        """Analyze stage transitions from progress history"""
        transitions = []

        for i in range(len(progress_history) - 1):
            current = progress_history[i]
            next_item = progress_history[i + 1]

            if current.stage != next_item.stage:
                duration = (next_item.action_date - current.action_date).days
                transitions.append({
                    'from_stage': current.stage,
                    'to_stage': next_item.stage,
                    'transition_date': next_item.action_date,
                    'duration_days': duration,
                    'house': next_item.house,
                    'committee': next_item.committee,
                    'action_type': next_item.action_type,
                    'result': next_item.result
                })

        return transitions

    def _generate_alerts(self,
                        bill_data: EnhancedBillData,
                        snapshot: BillProgressSnapshot,
                        transitions: list[dict[str, Any]]) -> list[str]:
        """Generate alerts based on bill progress"""
        alerts = []

        if not self.enable_alerts:
            return alerts

        # Check for stalled bills
        if snapshot.last_action_date:
            days_since_action = (datetime.now() - snapshot.last_action_date).days
            if days_since_action > 30:
                alerts.append(f"法案が{days_since_action}日間更新されていません")

        # Check for unusual delays
        for transition in transitions:
            if transition['duration_days'] > 60:
                alerts.append(f"{transition['from_stage']}から{transition['to_stage']}への移行が{transition['duration_days']}日かかりました")

        # Check for low confidence
        if snapshot.confidence_score < 0.5:
            alerts.append(f"データ信頼度が低いです: {snapshot.confidence_score:.2f}")

        # Check for missing data
        if not bill_data.bill_outline:
            alerts.append("議案要旨が不足しています")

        if not bill_data.committee_assignments:
            alerts.append("委員会情報が不足しています")

        return alerts

    def _map_status_to_stage(self, status: str) -> str:
        """Map bill status to progress stage"""
        status_mappings = {
            '提出': BillProcessStage.SUBMITTED,
            '受理': BillProcessStage.RECEIVED,
            '委員会付託': BillProcessStage.COMMITTEE_REFERRED,
            '委員会審議': BillProcessStage.COMMITTEE_REVIEW,
            '委員会採決': BillProcessStage.COMMITTEE_VOTE,
            '本会議': BillProcessStage.PLENARY_DEBATE,
            '採決': BillProcessStage.PLENARY_VOTE,
            '可決': BillProcessStage.PLENARY_PASSED,
            '否決': BillProcessStage.REJECTED,
            '成立': BillProcessStage.ENACTED,
            '廃案': BillProcessStage.EXPIRED,
            '撤回': BillProcessStage.WITHDRAWN,
            '継続': BillProcessStage.CONTINUED,
        }

        for key, value in status_mappings.items():
            if key in status:
                return value

        return BillProcessStage.COMMITTEE_REVIEW  # Default

    def _extract_current_committee(self, bill_data: EnhancedBillData) -> str | None:
        """Extract current committee from bill data"""

        # Check committee assignments
        if bill_data.committee_assignments:
            if isinstance(bill_data.committee_assignments, dict):
                committees = bill_data.committee_assignments.get('committees', [])
                if committees:
                    return committees[0] if isinstance(committees, list) else str(committees)

        # Check bill outline for committee mentions
        if bill_data.bill_outline:
            for house in ['参議院', '衆議院']:
                if house in (bill_data.house_of_origin or ''):
                    for pattern in self.committee_patterns.get(house, []):
                        if re.search(pattern, bill_data.bill_outline):
                            return re.search(pattern, bill_data.bill_outline).group(0)

        return None

    def _extract_last_action(self, bill_data: EnhancedBillData) -> tuple[str | None, datetime | None]:
        """Extract last action and date from bill data"""

        # Check voting results
        if bill_data.voting_results:
            for key, value in bill_data.voting_results.items():
                if any(pattern in str(value) for pattern in ['可決', '否決', '採決']):
                    return str(value), bill_data.final_vote_date

        # Check amendments
        if bill_data.amendments:
            latest_amendment = bill_data.amendments[-1]
            if isinstance(latest_amendment, dict):
                return latest_amendment.get('description', '修正'), latest_amendment.get('date')

        # Fall back to status
        return bill_data.status, bill_data.final_vote_date or bill_data.committee_report_date

    def _predict_next_action(self, current_stage: str, house: str) -> str | None:
        """Predict next expected action based on current stage"""

        stage_progression = self.stage_progressions.get(house, self.stage_progressions['参議院'])

        try:
            current_index = stage_progression.index(current_stage)
            if current_index < len(stage_progression) - 1:
                next_stage = stage_progression[current_index + 1]

                # Map stage to action
                action_mappings = {
                    BillProcessStage.COMMITTEE_REFERRED: '委員会付託',
                    BillProcessStage.COMMITTEE_REVIEW: '委員会審議',
                    BillProcessStage.COMMITTEE_VOTE: '委員会採決',
                    BillProcessStage.PLENARY_DEBATE: '本会議討論',
                    BillProcessStage.PLENARY_VOTE: '本会議採決',
                    BillProcessStage.INTER_HOUSE_SENT: '他院送付',
                }

                return action_mappings.get(next_stage, '次の段階')
        except ValueError:
            pass

        return None

    def _calculate_confidence_score(self, bill_data: EnhancedBillData) -> float:
        """Calculate confidence score for progress tracking"""
        score = 0.0
        total_weight = 0.0

        # Data completeness (40%)
        completeness_fields = [
            'bill_outline', 'status', 'stage', 'house_of_origin',
            'committee_assignments', 'voting_results'
        ]

        complete_count = 0
        for field in completeness_fields:
            value = getattr(bill_data, field, None)
            if value:
                complete_count += 1

        completeness_score = complete_count / len(completeness_fields)
        score += completeness_score * 0.4
        total_weight += 0.4

        # Data freshness (30%)
        freshness_score = 1.0  # Assume fresh if no date available
        if bill_data.final_vote_date:
            days_old = (datetime.now() - bill_data.final_vote_date).days
            freshness_score = max(0.0, 1.0 - (days_old / 365.0))  # Decay over 1 year

        score += freshness_score * 0.3
        total_weight += 0.3

        # Source reliability (20%)
        source_score = 0.8  # Base score
        if bill_data.source_house == "両院":
            source_score = 0.9  # Higher for multi-source
        elif bill_data.data_quality_score:
            source_score = bill_data.data_quality_score

        score += source_score * 0.2
        total_weight += 0.2

        # Consistency (10%)
        consistency_score = 1.0  # Base score
        if bill_data.status and bill_data.stage:
            # Check if status and stage are consistent
            if ('可決' in bill_data.status and '否決' in bill_data.stage) or \
               ('否決' in bill_data.status and '可決' in bill_data.stage):
                consistency_score = 0.5

        score += consistency_score * 0.1
        total_weight += 0.1

        return round(score / total_weight if total_weight > 0 else 0.0, 2)

    def _determine_vote_result(self, status: str) -> str:
        """Determine vote result from status"""
        if '可決' in status:
            return BillProcessResult.APPROVED
        elif '否決' in status:
            return BillProcessResult.REJECTED
        elif '修正' in status:
            return BillProcessResult.AMENDED
        else:
            return BillProcessResult.NOTED

    async def track_multiple_bills(self, bills: list[EnhancedBillData]) -> list[ProgressTrackingResult]:
        """Track progress for multiple bills asynchronously"""
        results = []

        for bill in bills:
            try:
                result = self.track_bill_progress(bill)
                results.append(result)

                # Small delay to prevent overwhelming the system
                await asyncio.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error tracking bill {bill.bill_id}: {e}")
                continue

        return results

    def get_progress_summary(self, tracking_results: list[ProgressTrackingResult]) -> dict[str, Any]:
        """Get summary statistics for progress tracking results"""

        if not tracking_results:
            return {}

        total_bills = len(tracking_results)

        # Status distribution
        status_counts = {}
        for result in tracking_results:
            status = result.tracking_status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # Stage distribution
        stage_counts = {}
        for result in tracking_results:
            stage = result.current_snapshot.current_stage
            stage_counts[stage] = stage_counts.get(stage, 0) + 1

        # Alert analysis
        total_alerts = sum(len(result.alerts) for result in tracking_results)
        bills_with_alerts = sum(1 for result in tracking_results if result.alerts)

        # Confidence analysis
        confidence_scores = [result.current_snapshot.confidence_score for result in tracking_results]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        return {
            'total_bills': total_bills,
            'status_distribution': status_counts,
            'stage_distribution': stage_counts,
            'total_alerts': total_alerts,
            'bills_with_alerts': bills_with_alerts,
            'alert_rate': bills_with_alerts / total_bills if total_bills > 0 else 0.0,
            'avg_confidence_score': round(avg_confidence, 2),
            'confidence_distribution': {
                'high': sum(1 for s in confidence_scores if s >= 0.8),
                'medium': sum(1 for s in confidence_scores if 0.5 <= s < 0.8),
                'low': sum(1 for s in confidence_scores if s < 0.5),
            }
        }
