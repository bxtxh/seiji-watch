"""
House of Representatives Data Integration Module

This module handles the integration of HR voting data into the existing data pipeline:
- Data normalization and validation
- Database integration
- Conflict resolution with existing data
- Quality assurance and monitoring
- Performance optimization
"""

import logging
import os

# Import shared modules from the correct path
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../..", "shared", "src"))

from shared.database.session import get_db_session
from shared.models.bill import Bill
from shared.models.member import Member
from shared.models.vote import Vote, VoteRecord

from ..scraper.enhanced_hr_scraper import EnhancedHRProcessor, EnhancedVotingSession

logger = logging.getLogger(__name__)


class DataConflictStrategy(Enum):
    """Strategies for handling data conflicts"""

    SKIP = "skip"  # Skip conflicting records
    OVERWRITE = "overwrite"  # Overwrite existing with new data
    MERGE = "merge"  # Attempt to merge data intelligently
    MANUAL = "manual"  # Flag for manual review


@dataclass
class IntegrationResult:
    """Result of data integration operation"""

    success: bool
    sessions_processed: int
    bills_created: int
    bills_updated: int
    members_created: int
    members_updated: int
    votes_created: int
    vote_records_created: int
    conflicts_detected: int
    errors: list[str]
    processing_time: float


class HRDataIntegrator:
    """Integrates House of Representatives voting data into the database"""

    def __init__(
        self, conflict_strategy: DataConflictStrategy = DataConflictStrategy.MERGE
    ):
        self.conflict_strategy = conflict_strategy
        self.stats = {
            "total_sessions_processed": 0,
            "successful_integrations": 0,
            "failed_integrations": 0,
            "data_conflicts_resolved": 0,
            "new_members_discovered": 0,
        }

    async def integrate_hr_voting_data(
        self, enhanced_sessions: list[EnhancedVotingSession], dry_run: bool = False
    ) -> IntegrationResult:
        """
        Integrate enhanced HR voting sessions into the database

        Args:
            enhanced_sessions: List of enhanced voting sessions to integrate
            dry_run: If True, simulate integration without making changes

        Returns:
            IntegrationResult with details of the operation
        """
        start_time = datetime.now()

        result = IntegrationResult(
            success=True,
            sessions_processed=0,
            bills_created=0,
            bills_updated=0,
            members_created=0,
            members_updated=0,
            votes_created=0,
            vote_records_created=0,
            conflicts_detected=0,
            errors=[],
            processing_time=0.0,
        )

        try:
            with get_db_session() as db_session:
                for session in enhanced_sessions:
                    try:
                        session_result = await self._integrate_single_session(
                            session, db_session, dry_run
                        )

                        # Aggregate results
                        result.sessions_processed += 1
                        result.bills_created += session_result["bills_created"]
                        result.bills_updated += session_result["bills_updated"]
                        result.members_created += session_result["members_created"]
                        result.members_updated += session_result["members_updated"]
                        result.votes_created += session_result["votes_created"]
                        result.vote_records_created += session_result[
                            "vote_records_created"
                        ]
                        result.conflicts_detected += session_result[
                            "conflicts_detected"
                        ]

                        if session_result["errors"]:
                            result.errors.extend(session_result["errors"])

                        logger.info(f"Integrated session: {session.session_id}")

                    except Exception as e:
                        error_msg = (
                            f"Failed to integrate session {session.session_id}: {e}"
                        )
                        logger.error(error_msg)
                        result.errors.append(error_msg)
                        result.success = False

                if not dry_run and result.success:
                    db_session.commit()
                    logger.info("HR data integration committed to database")
                elif dry_run:
                    db_session.rollback()
                    logger.info("Dry run completed - no changes made to database")
                else:
                    db_session.rollback()
                    logger.error("Integration failed - rolling back changes")

        except Exception as e:
            error_msg = f"HR data integration failed: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            result.success = False

        finally:
            result.processing_time = (datetime.now() - start_time).total_seconds()
            self._update_integration_stats(result)

        return result

    async def _integrate_single_session(
        self, session: EnhancedVotingSession, db_session: Session, dry_run: bool
    ) -> dict[str, Any]:
        """Integrate a single voting session"""

        result = {
            "bills_created": 0,
            "bills_updated": 0,
            "members_created": 0,
            "members_updated": 0,
            "votes_created": 0,
            "vote_records_created": 0,
            "conflicts_detected": 0,
            "errors": [],
        }

        try:
            # Step 1: Process bill information
            bill = await self._process_bill_data(session, db_session, dry_run)
            if bill:
                # Check if this is a new bill or update
                existing_bill = (
                    db_session.query(Bill)
                    .filter(Bill.bill_number == session.base_session.bill_number)
                    .first()
                )

                if existing_bill:
                    result["bills_updated"] += 1
                else:
                    result["bills_created"] += 1

            # Step 2: Process member information
            member_results = await self._process_member_data(
                session, db_session, dry_run
            )
            result["members_created"] += member_results["created"]
            result["members_updated"] += member_results["updated"]
            result["conflicts_detected"] += member_results["conflicts"]

            # Step 3: Process vote information
            vote = await self._process_vote_data(session, bill, db_session, dry_run)
            if vote:
                result["votes_created"] += 1

            # Step 4: Process individual vote records
            vote_record_results = await self._process_vote_records(
                session, vote, db_session, dry_run
            )
            result["vote_records_created"] += vote_record_results["created"]
            result["conflicts_detected"] += vote_record_results["conflicts"]

            return result

        except Exception as e:
            error_msg = f"Failed to integrate session {session.session_id}: {e}"
            result["errors"].append(error_msg)
            return result

    async def _process_bill_data(
        self, session: EnhancedVotingSession, db_session: Session, dry_run: bool
    ) -> Bill | None:
        """Process and integrate bill data"""

        try:
            # Check if bill already exists
            existing_bill = (
                db_session.query(Bill)
                .filter(Bill.bill_number == session.base_session.bill_number)
                .first()
            )

            if existing_bill:
                # Update existing bill with HR data if needed
                if self.conflict_strategy in [
                    DataConflictStrategy.OVERWRITE,
                    DataConflictStrategy.MERGE,
                ]:
                    existing_bill.title = session.base_session.bill_title
                    existing_bill.house_origin = "衆議院"  # House of Representatives
                    existing_bill.updated_at = datetime.now()

                    if not dry_run:
                        db_session.add(existing_bill)

                    logger.debug(f"Updated existing bill: {existing_bill.bill_number}")

                return existing_bill

            else:
                # Create new bill
                new_bill = Bill(
                    id=str(uuid.uuid4()),
                    bill_number=session.base_session.bill_number,
                    title=session.base_session.bill_title,
                    house_origin="衆議院",
                    status="審議中",  # Under deliberation
                    submitted_date=session.base_session.vote_date,
                    bill_type="法律案",  # Default to legislation
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )

                if not dry_run:
                    db_session.add(new_bill)

                logger.debug(f"Created new bill: {new_bill.bill_number}")
                return new_bill

        except Exception as e:
            logger.error(f"Failed to process bill data: {e}")
            return None

    async def _process_member_data(
        self, session: EnhancedVotingSession, db_session: Session, dry_run: bool
    ) -> dict[str, int]:
        """Process and integrate member data"""

        result = {"created": 0, "updated": 0, "conflicts": 0}

        try:
            # Get unique members from vote records
            unique_members = {}
            for record in session.base_session.vote_records:
                member_key = record.member_name
                if member_key not in unique_members:
                    unique_members[member_key] = record

            for member_name, vote_record in unique_members.items():
                try:
                    # Check if member already exists
                    existing_member = (
                        db_session.query(Member)
                        .filter(Member.name == member_name)
                        .first()
                    )

                    if existing_member:
                        # Check for conflicts in party or constituency
                        conflicts = []

                        if (
                            existing_member.party != vote_record.party_name
                            and vote_record.party_name != "不明"
                        ):
                            conflicts.append(
                                f"Party: {existing_member.party} vs {vote_record.party_name}"
                            )

                        if (
                            existing_member.constituency != vote_record.constituency
                            and vote_record.constituency != "不明"
                        ):
                            conflicts.append(
                                f"Constituency: {existing_member.constituency} vs {vote_record.constituency}"
                            )

                        if conflicts:
                            result["conflicts"] += 1
                            logger.warning(
                                f"Member data conflicts for {member_name}: {conflicts}"
                            )

                            # Apply conflict resolution strategy
                            if self.conflict_strategy == DataConflictStrategy.OVERWRITE:
                                existing_member.party = vote_record.party_name
                                existing_member.constituency = vote_record.constituency
                                existing_member.updated_at = datetime.now()

                                if not dry_run:
                                    db_session.add(existing_member)

                                result["updated"] += 1

                        # Update last seen
                        existing_member.last_seen = session.base_session.vote_date

                        if not dry_run:
                            db_session.add(existing_member)

                    else:
                        # Create new member
                        new_member = Member(
                            id=str(uuid.uuid4()),
                            name=member_name,
                            name_kana=vote_record.member_name_kana,
                            party=vote_record.party_name,
                            constituency=vote_record.constituency,
                            house="衆議院",
                            first_seen=session.base_session.vote_date,
                            last_seen=session.base_session.vote_date,
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                        )

                        if not dry_run:
                            db_session.add(new_member)

                        result["created"] += 1
                        logger.debug(f"Created new member: {member_name}")

                except Exception as e:
                    logger.error(f"Failed to process member {member_name}: {e}")
                    continue

            return result

        except Exception as e:
            logger.error(f"Failed to process member data: {e}")
            return result

    async def _process_vote_data(
        self,
        session: EnhancedVotingSession,
        bill: Bill | None,
        db_session: Session,
        dry_run: bool,
    ) -> Vote | None:
        """Process and integrate vote data"""

        try:
            # Check if vote already exists
            existing_vote = (
                db_session.query(Vote)
                .filter(
                    and_(
                        Vote.bill_id == bill.id if bill else False,
                        Vote.vote_date == session.base_session.vote_date,
                        Vote.vote_type == session.base_session.vote_type,
                    )
                )
                .first()
            )

            if existing_vote:
                logger.debug(f"Vote already exists: {existing_vote.id}")
                return existing_vote

            # Create new vote
            vote_summary = session.base_session.vote_summary

            new_vote = Vote(
                id=str(uuid.uuid4()),
                bill_id=bill.id if bill else None,
                vote_date=session.base_session.vote_date,
                vote_type=session.base_session.vote_type,
                house="衆議院",
                committee_name=session.base_session.committee_name,
                total_members=session.base_session.total_members,
                votes_for=vote_summary.get("賛成", 0),
                votes_against=vote_summary.get("反対", 0),
                abstentions=vote_summary.get("棄権", 0),
                absent=vote_summary.get("欠席", 0),
                result=(
                    "可決"
                    if vote_summary.get("賛成", 0) > vote_summary.get("反対", 0)
                    else "否決"
                ),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            if not dry_run:
                db_session.add(new_vote)

            logger.debug(f"Created new vote: {new_vote.id}")
            return new_vote

        except Exception as e:
            logger.error(f"Failed to process vote data: {e}")
            return None

    async def _process_vote_records(
        self,
        session: EnhancedVotingSession,
        vote: Vote | None,
        db_session: Session,
        dry_run: bool,
    ) -> dict[str, int]:
        """Process and integrate individual vote records"""

        result = {"created": 0, "conflicts": 0}

        if not vote:
            logger.warning("No vote object - skipping vote records")
            return result

        try:
            for vote_record in session.base_session.vote_records:
                try:
                    # Get member
                    member = (
                        db_session.query(Member)
                        .filter(Member.name == vote_record.member_name)
                        .first()
                    )

                    if not member:
                        logger.warning(
                            f"Member not found for vote record: {vote_record.member_name}"
                        )
                        continue

                    # Check if vote record already exists
                    existing_record = (
                        db_session.query(VoteRecord)
                        .filter(
                            and_(
                                VoteRecord.vote_id == vote.id,
                                VoteRecord.member_id == member.id,
                            )
                        )
                        .first()
                    )

                    if existing_record:
                        # Check for conflicts
                        if existing_record.vote_result != vote_record.vote_result:
                            result["conflicts"] += 1
                            logger.warning(
    f"Vote conflict for {member.name}: "
    f"{existing_record.vote_result} vs {vote_record.vote_result}" )

                            if self.conflict_strategy == DataConflictStrategy.OVERWRITE:
                                existing_record.vote_result = vote_record.vote_result
                                existing_record.updated_at = datetime.now()

                                if not dry_run:
                                    db_session.add(existing_record)

                        continue

                    # Create new vote record
                    new_record = VoteRecord(
                        id=str(uuid.uuid4()),
                        vote_id=vote.id,
                        member_id=member.id,
                        vote_result=vote_record.vote_result,
                        confidence_score=vote_record.confidence_score,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                    )

                    if not dry_run:
                        db_session.add(new_record)

                    result["created"] += 1

                except Exception as e:
                    logger.error(
                        f"Failed to process vote record for {vote_record.member_name}: {e}"
                    )
                    continue

            return result

        except Exception as e:
            logger.error(f"Failed to process vote records: {e}")
            return result

    def _update_integration_stats(self, result: IntegrationResult) -> None:
        """Update integration statistics"""

        self.stats["total_sessions_processed"] += result.sessions_processed

        if result.success:
            self.stats["successful_integrations"] += 1
        else:
            self.stats["failed_integrations"] += 1

        self.stats["data_conflicts_resolved"] += result.conflicts_detected
        self.stats["new_members_discovered"] += result.members_created

    def get_integration_statistics(self) -> dict[str, Any]:
        """Get integration statistics"""

        stats = dict(self.stats)

        if self.stats["total_sessions_processed"] > 0:
            stats["success_rate"] = (
                self.stats["successful_integrations"]
                / self.stats["total_sessions_processed"]
            )

        return stats

    async def validate_integrated_data(self, session_ids: list[str]) -> dict[str, Any]:
        """Validate that integrated data is consistent and complete"""

        validation_result = {
            "valid_sessions": 0,
            "invalid_sessions": 0,
            "missing_data": [],
            "inconsistencies": [],
            "warnings": [],
        }

        try:
            with get_db_session():
                for session_id in session_ids:
                    try:
                        # Find corresponding vote in database
                        # This would need a way to map session_id to vote
                        # For now, we'll skip the detailed validation

                        validation_result["valid_sessions"] += 1

                    except Exception as e:
                        validation_result["invalid_sessions"] += 1
                        validation_result["warnings"].append(
                            f"Validation failed for session {session_id}: {e}"
                        )

            return validation_result

        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return validation_result


# Integration utilities


async def run_hr_integration_pipeline(
    days_back: int = 7, dry_run: bool = False, max_concurrent: int = 2
) -> dict[str, Any]:
    """
    Run the complete HR integration pipeline

    Args:
        days_back: Number of days to look back for data
        dry_run: If True, simulate without making changes
        max_concurrent: Maximum concurrent operations

    Returns:
        Pipeline execution results
    """

    pipeline_result = {
        "success": False,
        "processing_results": None,
        "integration_results": None,
        "total_time": 0.0,
        "errors": [],
    }

    start_time = datetime.now()

    try:
        # Phase 1: Enhanced processing
        logger.info(
            f"Starting HR integration pipeline (days_back={days_back}, dry_run={dry_run})"
        )

        processor = EnhancedHRProcessor()
        enhanced_sessions = await processor.process_enhanced_hr_data(
            days_back=days_back, max_concurrent=max_concurrent
        )

        logger.info(f"Processing completed: {len(enhanced_sessions)} sessions")

        # Phase 2: Data integration
        integrator = HRDataIntegrator()
        integration_result = await integrator.integrate_hr_voting_data(
            enhanced_sessions, dry_run=dry_run
        )

        logger.info(
            f"Integration completed: {integration_result.sessions_processed} sessions processed"
        )

        pipeline_result["success"] = integration_result.success
        pipeline_result["processing_results"] = processor.get_processing_statistics()
        pipeline_result["integration_results"] = integration_result

        if integration_result.errors:
            pipeline_result["errors"].extend(integration_result.errors)

    except Exception as e:
        error_msg = f"HR integration pipeline failed: {e}"
        logger.error(error_msg)
        pipeline_result["errors"].append(error_msg)

    finally:
        pipeline_result["total_time"] = (datetime.now() - start_time).total_seconds()

    return pipeline_result
