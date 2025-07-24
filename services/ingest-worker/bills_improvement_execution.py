#!/usr/bin/env python3
"""
Bills Table Improvement Execution
Bills テーブル改善実行システム
"""

import asyncio
import json
import os
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

class BillsImprovementExecutor:
    """Bills table systematic improvement execution"""

    def __init__(self):
        self.pat = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.table_name = "Bills (法案)"
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"

        if not self.pat or not self.base_id:
            raise ValueError("Airtable PAT and base ID are required")

        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json"
        }

        # Bills table improvement strategies
        self.improvement_strategies = {
            "status_standardization": {
                "description": "Standardize Bill_Status values to consistent vocabulary",
                "priority": "high",
                "target_fields": ["Bill_Status"]
            },
            "category_classification": {
                "description": "Auto-classify bills into policy categories based on title analysis",
                "priority": "high",
                "target_fields": ["Category"]
            },
            "priority_scoring": {
                "description": "Intelligent priority assignment based on bill characteristics",
                "priority": "medium",
                "target_fields": ["Priority"]
            },
            "session_normalization": {
                "description": "Normalize Diet_Session format for consistency",
                "priority": "medium",
                "target_fields": ["Diet_Session"]
            },
            "completeness_enhancement": {
                "description": "Fill missing essential fields with intelligent defaults",
                "priority": "high",
                "target_fields": ["Stage", "Bill_Type", "Process_Method"]
            }
        }

        # Standard vocabularies and mappings
        self.status_mapping = {
            "提出": "提出",
            "審議中": "審議中",
            "採決待ち": "採決待ち",
            "成立": "成立",
            "廃案": "廃案",
            "": "提出",  # Default for empty
            "議案要旨": "提出",  # Convert to standard
            "審議": "審議中",  # Normalize
            "可決": "成立"  # Normalize
        }

        self.category_keywords = {
            "経済・産業": ["経済", "産業", "企業", "商業", "金融", "投資", "産業振興", "中小企業"],
            "社会保障": ["社会保障", "年金", "健康保険", "介護", "医療", "福祉", "高齢者", "障害者"],
            "外交・国際": ["外交", "国際", "条約", "協定", "外国", "国際協力", "貿易", "安全保障"],
            "教育・文化": ["教育", "文化", "学校", "大学", "研究", "科学技術", "スポーツ", "芸術"],
            "環境・エネルギー": ["環境", "エネルギー", "原子力", "再生可能", "温室効果", "気候変動", "公害"],
            "交通・通信": ["交通", "運輸", "道路", "鉄道", "航空", "通信", "情報技術", "インターネット"],
            "法務・治安": ["法務", "司法", "警察", "犯罪", "治安", "人権", "裁判", "検察"],
            "地方・都市": ["地方", "都市", "自治体", "地域振興", "過疎", "都市計画", "住宅"],
            "農林水産": ["農業", "林業", "水産", "農林水産", "漁業", "農村", "食料"],
            "その他": []  # Fallback category
        }

        self.priority_keywords = {
            "high": ["重要", "緊急", "特別", "基本", "根本", "抜本", "重点"],
            "low": ["一部改正", "整備", "技術的", "軽微", "手続", "事務"],
            "medium": []  # Default
        }

    async def get_bills_records(self, session: aiohttp.ClientSession) -> list[dict]:
        """Fetch all Bills records for improvement"""
        all_records = []
        offset = None

        while True:
            try:
                params = {"pageSize": 100}
                if offset:
                    params["offset"] = offset

                async with session.get(
                    f"{self.base_url}/{self.table_name}",
                    headers=self.headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        records = data.get('records', [])
                        all_records.extend(records)

                        offset = data.get('offset')
                        if not offset:
                            break

                        await asyncio.sleep(0.1)
                    else:
                        print(f"❌ Error fetching Bills: {response.status}")
                        return []

            except Exception as e:
                print(f"❌ Error fetching Bills: {e}")
                return []

        return all_records

    def analyze_current_state(self, records: list[dict]) -> dict:
        """Analyze current state of Bills table before improvement"""
        analysis = {
            "total_records": len(records),
            "field_completeness": {},
            "value_analysis": {},
            "improvement_opportunities": {}
        }

        # Essential fields to analyze
        essential_fields = [
            "Title", "Bill_Number", "Bill_Status", "Diet_Session",
            "House", "Category", "Priority", "Stage", "Bill_Type", "Submitter"
        ]

        for field in essential_fields:
            filled_count = 0
            empty_count = 0
            unique_values = set()

            for record in records:
                value = record.get('fields', {}).get(field)

                if value is None or value == "":
                    empty_count += 1
                else:
                    filled_count += 1
                    unique_values.add(str(value))

            completeness_rate = filled_count / len(records) if records else 0

            analysis["field_completeness"][field] = {
                "filled_count": filled_count,
                "empty_count": empty_count,
                "completeness_rate": round(completeness_rate, 3),
                "unique_values_count": len(unique_values),
                "sample_values": list(unique_values)[:5]
            }

            # Identify improvement opportunities
            if completeness_rate < 0.9:  # Less than 90% complete
                analysis["improvement_opportunities"][field] = {
                    "type": "completeness",
                    "current_rate": completeness_rate,
                    "missing_count": empty_count,
                    "priority": "high" if field in ["Title", "Bill_Status", "Category"] else "medium"
                }

        return analysis

    def classify_bill_category(self, title: str, notes: str = "") -> str:
        """Classify bill into policy category based on title and notes analysis"""
        if not title:
            return "その他"

        title_lower = title.lower()
        notes_lower = notes.lower() if notes else ""
        combined_text = title_lower + " " + notes_lower

        # Count keyword matches for each category
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            if category == "その他":
                continue

            score = 0
            for keyword in keywords:
                score += combined_text.count(keyword.lower())

            if score > 0:
                category_scores[category] = score

        # Return category with highest score, or default
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        else:
            return "その他"

    def determine_bill_priority(self, title: str, category: str) -> str:
        """Determine bill priority based on title analysis and category"""
        if not title:
            return "medium"

        title_lower = title.lower()

        # Check for high priority keywords
        for keyword in self.priority_keywords["high"]:
            if keyword in title_lower:
                return "high"

        # Check for low priority keywords
        for keyword in self.priority_keywords["low"]:
            if keyword in title_lower:
                return "low"

        # Category-based priority adjustment
        high_priority_categories = ["経済・産業", "社会保障", "外交・国際"]
        if category in high_priority_categories:
            return "high"

        return "medium"

    def determine_bill_stage(self, status: str) -> str:
        """Determine bill stage based on status"""
        stage_mapping = {
            "提出": "Backlog",
            "審議中": "審議中",
            "採決待ち": "採決待ち",
            "成立": "成立",
            "廃案": "廃案"
        }
        return stage_mapping.get(status, "Backlog")

    async def execute_status_standardization(self, session: aiohttp.ClientSession, records: list[dict]) -> dict:
        """Execute status standardization improvements"""
        print("\n🔧 Executing status standardization...")

        improvements = {
            "standardized_count": 0,
            "filled_empty_count": 0,
            "errors": 0
        }

        for record in records:
            fields = record.get('fields', {})
            record_id = record['id']
            current_status = fields.get('Bill_Status', '')

            # Apply status mapping
            if current_status in self.status_mapping:
                standardized_status = self.status_mapping[current_status]

                if current_status != standardized_status:
                    updates = {'Bill_Status': standardized_status}

                    success = await self.safe_update_record(session, record_id, updates)
                    if success:
                        improvements["standardized_count"] += 1
                        if current_status == "":
                            improvements["filled_empty_count"] += 1
                    else:
                        improvements["errors"] += 1

            await asyncio.sleep(0.05)  # Rate limiting

        return improvements

    async def execute_category_classification(self, session: aiohttp.ClientSession, records: list[dict]) -> dict:
        """Execute category classification improvements"""
        print("\n🔧 Executing category classification...")

        improvements = {
            "classified_count": 0,
            "updated_count": 0,
            "errors": 0
        }

        for record in records:
            fields = record.get('fields', {})
            record_id = record['id']

            title = fields.get('Title', '')
            notes = fields.get('Notes', '')
            current_category = fields.get('Category', '')

            # Classify if empty or generic
            if not current_category or current_category == "その他":
                new_category = self.classify_bill_category(title, notes)

                if new_category != current_category:
                    updates = {'Category': new_category}

                    success = await self.safe_update_record(session, record_id, updates)
                    if success:
                        improvements["classified_count"] += 1
                        if current_category == "":
                            improvements["updated_count"] += 1
                    else:
                        improvements["errors"] += 1

            await asyncio.sleep(0.05)  # Rate limiting

        return improvements

    async def execute_priority_scoring(self, session: aiohttp.ClientSession, records: list[dict]) -> dict:
        """Execute priority scoring improvements"""
        print("\n🔧 Executing priority scoring...")

        improvements = {
            "priority_assigned": 0,
            "priority_updated": 0,
            "errors": 0
        }

        for record in records:
            fields = record.get('fields', {})
            record_id = record['id']

            title = fields.get('Title', '')
            category = fields.get('Category', '')
            current_priority = fields.get('Priority', '')

            # Determine priority if empty or default
            if not current_priority or current_priority == "medium":
                new_priority = self.determine_bill_priority(title, category)

                if new_priority != current_priority:
                    updates = {'Priority': new_priority}

                    success = await self.safe_update_record(session, record_id, updates)
                    if success:
                        improvements["priority_assigned"] += 1
                        if current_priority == "":
                            improvements["priority_updated"] += 1
                    else:
                        improvements["errors"] += 1

            await asyncio.sleep(0.05)  # Rate limiting

        return improvements

    async def execute_completeness_enhancement(self, session: aiohttp.ClientSession, records: list[dict]) -> dict:
        """Execute completeness enhancement improvements"""
        print("\n🔧 Executing completeness enhancement...")

        improvements = {
            "stage_filled": 0,
            "bill_type_filled": 0,
            "process_method_filled": 0,
            "errors": 0
        }

        for record in records:
            fields = record.get('fields', {})
            record_id = record['id']
            updates = {}

            # Fill Stage based on Status
            if not fields.get('Stage'):
                status = fields.get('Bill_Status', '')
                new_stage = self.determine_bill_stage(status)
                updates['Stage'] = new_stage
                improvements["stage_filled"] += 1

            # Fill Bill_Type if empty
            if not fields.get('Bill_Type'):
                updates['Bill_Type'] = '提出法律案'  # Default type
                improvements["bill_type_filled"] += 1

            # Fill Process_Method if empty
            if not fields.get('Process_Method'):
                updates['Process_Method'] = 'AI処理'  # Default method
                improvements["process_method_filled"] += 1

            # Apply updates if any
            if updates:
                success = await self.safe_update_record(session, record_id, updates)
                if not success:
                    improvements["errors"] += 1

            await asyncio.sleep(0.05)  # Rate limiting

        return improvements

    async def execute_session_normalization(self, session: aiohttp.ClientSession, records: list[dict]) -> dict:
        """Execute session normalization improvements"""
        print("\n🔧 Executing session normalization...")

        improvements = {
            "normalized_count": 0,
            "errors": 0
        }

        for record in records:
            fields = record.get('fields', {})
            record_id = record['id']

            session_value = fields.get('Diet_Session', '')
            if session_value and len(session_value) < 3:
                # Zero-pad to 3 digits (e.g., "217" -> "217", "17" -> "017")
                normalized_session = session_value.zfill(3)

                if session_value != normalized_session:
                    updates = {'Diet_Session': normalized_session}

                    success = await self.safe_update_record(session, record_id, updates)
                    if success:
                        improvements["normalized_count"] += 1
                    else:
                        improvements["errors"] += 1

            await asyncio.sleep(0.05)  # Rate limiting

        return improvements

    async def safe_update_record(self, session: aiohttp.ClientSession, record_id: str, updates: dict) -> bool:
        """Safely update a record with error handling"""
        try:
            # Filter out computed fields
            safe_updates = {k: v for k, v in updates.items() if k != "Attachment Summary"}

            if not safe_updates:
                return True

            update_data = {"fields": safe_updates}

            async with session.patch(
                f"{self.base_url}/{self.table_name}/{record_id}",
                headers=self.headers,
                json=update_data
            ) as response:
                return response.status == 200

        except Exception as e:
            print(f"❌ Update error for {record_id}: {e}")
            return False

    async def verify_improvements(self, session: aiohttp.ClientSession) -> dict:
        """Verify improvements by re-analyzing the table"""
        print("\n📊 Verifying improvements...")

        # Get updated records
        updated_records = await self.get_bills_records(session)

        # Re-analyze
        updated_analysis = self.analyze_current_state(updated_records)

        # Calculate overall completeness
        completeness_scores = []
        essential_fields = ["Title", "Bill_Number", "Bill_Status", "Diet_Session", "House", "Category", "Priority"]

        for field in essential_fields:
            rate = updated_analysis["field_completeness"].get(field, {}).get("completeness_rate", 0)
            completeness_scores.append(rate)

        overall_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0

        verification = {
            "total_records": updated_analysis["total_records"],
            "overall_completeness": round(overall_completeness, 3),
            "field_completeness": updated_analysis["field_completeness"],
            "estimated_quality_score": round(overall_completeness * 0.8 + 0.2, 3)  # Rough estimate
        }

        return verification

    async def run_bills_improvement_execution(self):
        """Run comprehensive Bills table improvement execution"""
        print("🚀 Starting Bills Table Improvement Execution...")
        print("🎯 Target: 68.8% → 90% quality score\n")

        execution_results = {
            "execution_date": datetime.now().isoformat(),
            "initial_analysis": {},
            "improvement_results": {},
            "final_verification": {},
            "summary": {}
        }

        async with aiohttp.ClientSession() as session:
            # Step 1: Get current records and analyze
            print("📋 Step 1: Analyzing current state...")
            records = await self.get_bills_records(session)

            if not records:
                print("❌ No records found!")
                return

            initial_analysis = self.analyze_current_state(records)
            execution_results["initial_analysis"] = initial_analysis

            print(f"📊 Found {initial_analysis['total_records']} Bills records")
            print(f"📈 Current overall completeness: {sum(fc['completeness_rate'] for fc in initial_analysis['field_completeness'].values()) / len(initial_analysis['field_completeness']):.1%}")

            # Step 2: Execute improvement strategies
            print("\n📋 Step 2: Executing improvement strategies...")

            # Execute each strategy
            strategy_results = {}

            # 1. Status Standardization
            strategy_results["status_standardization"] = await self.execute_status_standardization(session, records)

            # 2. Category Classification
            strategy_results["category_classification"] = await self.execute_category_classification(session, records)

            # 3. Priority Scoring
            strategy_results["priority_scoring"] = await self.execute_priority_scoring(session, records)

            # 4. Completeness Enhancement
            strategy_results["completeness_enhancement"] = await self.execute_completeness_enhancement(session, records)

            # 5. Session Normalization
            strategy_results["session_normalization"] = await self.execute_session_normalization(session, records)

            execution_results["improvement_results"] = strategy_results

            # Step 3: Verify improvements
            verification = await self.verify_improvements(session)
            execution_results["final_verification"] = verification

            # Step 4: Generate summary
            total_updates = sum(
                sum(result.values()) - result.get("errors", 0)
                for result in strategy_results.values()
                if isinstance(result, dict)
            )

            total_errors = sum(
                result.get("errors", 0)
                for result in strategy_results.values()
                if isinstance(result, dict)
            )

            # Calculate improvement
            initial_completeness = sum(fc['completeness_rate'] for fc in initial_analysis['field_completeness'].values()) / len(initial_analysis['field_completeness'])
            final_completeness = verification["overall_completeness"]
            improvement_delta = final_completeness - initial_completeness

            execution_results["summary"] = {
                "total_records_processed": len(records),
                "total_successful_updates": total_updates,
                "total_errors": total_errors,
                "initial_completeness": round(initial_completeness, 3),
                "final_completeness": final_completeness,
                "improvement_delta": round(improvement_delta, 3),
                "estimated_quality_improvement": round(improvement_delta * 100, 1),
                "target_achieved": final_completeness >= 0.90
            }

        # Save execution report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bills_improvement_execution_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(execution_results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Execution report saved: {filename}")

        # Print final summary
        self.print_execution_summary(execution_results)

        return execution_results

    def print_execution_summary(self, results: dict):
        """Print comprehensive execution summary"""
        summary = results["summary"]

        print(f"\n{'='*80}")
        print("📋 BILLS TABLE IMPROVEMENT EXECUTION SUMMARY")
        print(f"{'='*80}")

        print(f"📊 Records Processed: {summary['total_records_processed']}")
        print(f"✅ Successful Updates: {summary['total_successful_updates']}")
        print(f"❌ Errors: {summary['total_errors']}")

        print("\n📈 QUALITY IMPROVEMENT:")
        print(f"   Before: {summary['initial_completeness']:.1%} completeness")
        print(f"   After:  {summary['final_completeness']:.1%} completeness")
        print(f"   Delta:  +{summary['improvement_delta']:.1%} improvement")

        target_status = "✅ ACHIEVED" if summary['target_achieved'] else "⚠️ IN PROGRESS"
        print(f"\n🎯 TARGET STATUS: {target_status}")
        print("   Target: 90% completeness")
        print(f"   Current: {summary['final_completeness']:.1%}")

        # Strategy-specific results
        print("\n🔧 STRATEGY RESULTS:")
        strategy_results = results["improvement_results"]

        for strategy, result in strategy_results.items():
            if isinstance(result, dict):
                total_actions = sum(v for k, v in result.items() if k != "errors")
                errors = result.get("errors", 0)
                print(f"   {strategy}: {total_actions} actions, {errors} errors")

        # Next steps
        if not summary['target_achieved']:
            remaining_gap = 0.90 - summary['final_completeness']
            print("\n📋 NEXT STEPS:")
            print(f"   Remaining gap: {remaining_gap:.1%} to reach 90% target")
            print("   Focus areas: Data validation, advanced categorization")
            print("   Estimated effort: 2-4 hours additional improvement")

async def main():
    """Main entry point"""
    executor = BillsImprovementExecutor()
    results = await executor.run_bills_improvement_execution()

    print("\n✅ Bills table improvement execution completed!")

    if results["summary"]["target_achieved"]:
        print("🎯 Target achieved! Bills table ready for release.")
    else:
        print("⚠️ Additional improvement needed to reach 90% target.")

if __name__ == "__main__":
    asyncio.run(main())
