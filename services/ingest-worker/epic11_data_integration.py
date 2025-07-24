#!/usr/bin/env python3
"""
EPIC 11 Data Integration - 収集済みデータのAirtable投入
Real data integration for Diet Issue Tracker MVP completion
"""

import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent / "shared" / "src"))

from shared.clients.airtable import AirtableClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Epic11DataIntegrator:
    """EPIC 11: Real data integration from collected JSON to Airtable"""

    def __init__(self):
        self.airtable = AirtableClient()
        self.data_file = "production_scraping_june2025_20250709_032237.json"
        self.batch_size = 10  # Airtable batch limit

    def load_production_data(self) -> dict[str, Any]:
        """Load collected production data from JSON"""
        data_path = Path(__file__).parent / self.data_file

        if not data_path.exists():
            raise FileNotFoundError(f"Production data file not found: {data_path}")

        with open(data_path, encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"Loaded production data from {data_path}")
        logger.info(f"Bills: {len(data['production_dataset']['bills'])}")
        logger.info(f"Voting Sessions: {len(data['production_dataset']['voting_sessions'])}")

        return data

    def transform_bill_data(self, bill: dict[str, Any]) -> dict[str, Any]:
        """Transform bill data to Airtable schema"""
        return {
            "fields": {
                "Bill_ID": bill["bill_id"],
                "Title": bill["title"],
                "Status": bill["status"],
                "Stage": bill["stage"],
                "Submitter": bill["submitter"],
                "Category": bill["category"],
                "URL": bill["url"],
                "Summary": bill.get("summary") or "",
                "Submission_Date": bill.get("submission_date"),
                "Collected_At": bill["collected_at"],
                "Created_At": datetime.now(UTC).isoformat()
            }
        }

    def transform_voting_session_data(self, voting_session: dict[str, Any]) -> dict[str, Any]:
        """Transform voting session data to Airtable schema"""
        return {
            "fields": {
                "Bill_Number": voting_session["bill_number"],
                "Bill_Title": voting_session["bill_title"],
                "Vote_Date": voting_session["vote_date"],
                "Vote_Type": voting_session["vote_type"],
                "Vote_Stage": voting_session["vote_stage"],
                "Committee_Name": voting_session.get("committee_name") or "",
                "Total_Votes": voting_session["total_votes"],
                "Yes_Votes": voting_session["yes_votes"],
                "No_Votes": voting_session["no_votes"],
                "Abstain_Votes": voting_session["abstain_votes"],
                "Absent_Votes": voting_session["absent_votes"],
                "Created_At": datetime.now(UTC).isoformat()
            }
        }

    def transform_vote_record_data(self, vote_record: dict[str, Any], voting_session_id: str) -> dict[str, Any]:
        """Transform individual vote record data to Airtable schema"""
        return {
            "fields": {
                "Member_Name": vote_record["member_name"],
                "Member_Name_Kana": vote_record["member_name_kana"],
                "Party_Name": vote_record["party_name"],
                "Constituency": vote_record["constituency"],
                "House": vote_record["house"],
                "Vote_Result": vote_record["vote_result"],
                "Voting_Session_ID": voting_session_id,
                "Created_At": datetime.now(UTC).isoformat()
            }
        }

    async def batch_insert_bills(self, bills: list[dict[str, Any]]) -> list[str]:
        """Insert bills in batches to Airtable"""
        logger.info(f"Starting batch insertion of {len(bills)} bills")

        inserted_ids = []
        failed_bills = []

        for i in range(0, len(bills), self.batch_size):
            batch = bills[i:i + self.batch_size]
            logger.info(f"Processing batch {i//self.batch_size + 1}: bills {i+1}-{min(i+self.batch_size, len(bills))}")

            try:
                # Transform bills to Airtable format
                airtable_bills = [self.transform_bill_data(bill) for bill in batch]

                # Create bills individually (safer for debugging)
                for j, airtable_bill in enumerate(airtable_bills):
                    try:
                        result = await self.airtable.create_bill(airtable_bill["fields"])
                        inserted_ids.append(result["id"])
                        logger.info(f"✅ Inserted bill: {bills[i+j]['title'][:50]}... (ID: {result['id']})")

                        # Rate limiting - wait between requests
                        await asyncio.sleep(0.2)  # 5 requests per second limit

                    except Exception as e:
                        logger.error(f"❌ Failed to insert bill: {bills[i+j]['title'][:50]}... Error: {e}")
                        failed_bills.append(bills[i+j])

            except Exception as e:
                logger.error(f"❌ Batch insertion failed for batch {i//self.batch_size + 1}: {e}")
                failed_bills.extend(batch)

        logger.info(f"✅ Bills insertion completed: {len(inserted_ids)} successful, {len(failed_bills)} failed")
        if failed_bills:
            logger.warning(f"Failed bills: {[bill['title'][:30] for bill in failed_bills]}")

        return inserted_ids

    async def batch_insert_voting_sessions(self, voting_sessions: list[dict[str, Any]]) -> list[str]:
        """Insert voting sessions to Airtable"""
        logger.info(f"Starting insertion of {len(voting_sessions)} voting sessions")

        inserted_ids = []

        for i, session in enumerate(voting_sessions):
            try:
                airtable_session = self.transform_voting_session_data(session)
                result = await self.airtable.create_voting_session(airtable_session["fields"])
                inserted_ids.append(result["id"])
                logger.info(f"✅ Inserted voting session: {session['bill_title'][:50]}... (ID: {result['id']})")

                # Insert individual vote records for this session
                if "vote_records" in session:
                    await self.insert_vote_records(session["vote_records"], result["id"])

                await asyncio.sleep(0.2)  # Rate limiting

            except Exception as e:
                logger.error(f"❌ Failed to insert voting session: {session['bill_title'][:50]}... Error: {e}")

        logger.info(f"✅ Voting sessions insertion completed: {len(inserted_ids)} successful")
        return inserted_ids

    async def insert_vote_records(self, vote_records: list[dict[str, Any]], voting_session_id: str):
        """Insert individual vote records for a voting session"""
        logger.info(f"Inserting {len(vote_records)} vote records for session {voting_session_id}")

        for record in vote_records:
            try:
                airtable_record = self.transform_vote_record_data(record, voting_session_id)
                await self.airtable.create_vote_record(airtable_record["fields"])
                logger.debug(f"✅ Inserted vote record: {record['member_name']} - {record['vote_result']}")
                await asyncio.sleep(0.1)  # Smaller delay for individual records

            except Exception as e:
                logger.error(f"❌ Failed to insert vote record: {record['member_name']} - {e}")

    async def integrate_production_data(self):
        """Main integration process - T96 implementation"""
        logger.info("🚀 EPIC 11 T96: Starting production data integration")

        try:
            # Step 1: Load production data
            data = self.load_production_data()
            production_dataset = data["production_dataset"]

            # Step 2: Insert bills
            logger.info("📋 Phase 1: Inserting Bills data")
            bills = production_dataset["bills"]
            bill_ids = await self.batch_insert_bills(bills)

            # Step 3: Insert voting sessions and vote records
            logger.info("🗳️ Phase 2: Inserting Voting Sessions and Vote Records")
            voting_sessions = production_dataset["voting_sessions"]
            voting_session_ids = await self.batch_insert_voting_sessions(voting_sessions)

            # Step 4: Summary report
            logger.info("📊 Integration Summary:")
            logger.info(f"  ✅ Bills inserted: {len(bill_ids)}/{len(bills)}")
            logger.info(f"  ✅ Voting sessions inserted: {len(voting_session_ids)}/{len(voting_sessions)}")
            logger.info(f"  📅 Data period: {data['execution_info']['target_period']}")
            logger.info(f"  🕐 Original collection: {data['execution_info']['timestamp']}")

            if len(bill_ids) >= 180:  # 90% success rate acceptable
                logger.info("🎉 EPIC 11 T96 COMPLETED SUCCESSFULLY")
                logger.info("✅ Production data integration ready for T97 (API Gateway modification)")
                return True
            else:
                logger.warning("⚠️ Integration partially successful but below threshold")
                return False

        except Exception as e:
            logger.error(f"❌ EPIC 11 T96 FAILED: {e}")
            raise

    async def verify_data_integration(self):
        """Verify that data was successfully integrated"""
        logger.info("🔍 Verifying data integration")

        try:
            # Check bills
            bills = await self.airtable.list_bills()
            logger.info(f"📋 Bills in Airtable: {len(bills.get('records', []))}")

            # Check voting sessions
            voting_sessions = await self.airtable.list_voting_sessions()
            logger.info(f"🗳️ Voting sessions in Airtable: {len(voting_sessions.get('records', []))}")

            if len(bills.get('records', [])) >= 180:
                logger.info("✅ Data integration verification PASSED")
                return True
            else:
                logger.warning("⚠️ Data integration verification FAILED - insufficient data")
                return False

        except Exception as e:
            logger.error(f"❌ Data integration verification ERROR: {e}")
            return False

async def main():
    """Execute EPIC 11 T96: Production Data Integration"""
    integrator = Epic11DataIntegrator()

    logger.info("=" * 60)
    logger.info("🚀 EPIC 11 T96: 収集済みJSONデータのAirtable投入")
    logger.info("Real Data Integration for Diet Issue Tracker MVP")
    logger.info("=" * 60)

    try:
        # Execute integration
        success = await integrator.integrate_production_data()

        if success:
            # Verify integration
            verification_success = await integrator.verify_data_integration()

            if verification_success:
                logger.info("🎯 EPIC 11 T96 MISSION ACCOMPLISHED!")
                logger.info("Next: T97 - API Gateway実データ連携修正")
            else:
                logger.error("❌ Integration verification failed")
                sys.exit(1)
        else:
            logger.error("❌ Integration failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"💥 EPIC 11 T96 execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
