#!/usr/bin/env python3
"""
Comprehensive Data Quality Analysis System (T131)
全テーブル包括的データ品質評価システム - EPIC 13
"""

import asyncio
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import aiohttp
from dotenv import load_dotenv

load_dotenv("/Users/shogen/seiji-watch/.env.local")


@dataclass
class QualityMetrics:
    """Data quality metrics for a table"""

    table_name: str
    total_records: int

    # Core quality dimensions
    completeness_score: float  # 完全性: 必須フィールド充足率
    uniqueness_score: float  # 一意性: 重複・冗長データ検出率
    validity_score: float  # 妥当性: データ形式・範囲の正確性
    consistency_score: float  # 一貫性: テーブル間参照整合性
    accuracy_score: float  # 正確性: 情報源との一致度
    timeliness_score: float  # 鮮度: データ更新頻度・最新性

    # Overall quality score
    overall_quality_score: float

    # Detailed analysis
    field_completeness: dict[str, float]
    duplicate_records: list[str]
    invalid_records: list[str]
    consistency_issues: list[str]
    recommendations: list[str]


@dataclass
class DatabaseQualityReport:
    """Comprehensive database quality report"""

    analysis_date: str
    total_tables: int
    total_records: int

    table_metrics: dict[str, QualityMetrics]
    overall_database_score: float

    critical_issues: list[str]
    improvement_priorities: list[str]
    quality_trends: dict[str, Any]

    target_achievements: dict[str, bool]


class ComprehensiveDataQualityAnalyzer:
    """Advanced data quality analyzer for all tables"""

    def __init__(self):
        self.pat = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"

        if not self.pat or not self.base_id:
            raise ValueError("Airtable PAT and base ID are required")

        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json",
        }

        # Rate limiting
        self._request_semaphore = asyncio.Semaphore(3)
        self._last_request_time = 0

        # Table configurations with quality targets
        self.table_configs = {
            "Members (議員)": {
                "target_score": 95.0,
                "required_fields": ["Name", "House", "Is_Active"],
                "optional_fields": [
                    "Name_Kana",
                    "Constituency",
                    "Party",
                    "First_Elected",
                    "Terms_Served",
                    "Birth_Date",
                    "Gender",
                    "Previous_Occupations",
                    "Education",
                    "Website_URL",
                    "Twitter_Handle",
                ],
                "unique_fields": ["Name", "House"],  # Combined uniqueness
                "reference_fields": {"Party": "Parties (政党)"},
                "validation_rules": {
                    "House": ["衆議院", "参議院"],
                    "Is_Active": [True, False],
                    "Terms_Served": {"type": "int", "min": 1, "max": 20},
                },
            },
            "Bills (法案)": {
                "target_score": 90.0,
                "required_fields": ["Title", "Bill_Number", "Status", "Session"],
                "optional_fields": [
                    "Submitter",
                    "Category",
                    "Summary",
                    "Full_Text_URL",
                    "Date_Submitted",
                    "Date_Passed",
                    "Vote_Results",
                ],
                "unique_fields": ["Bill_Number"],
                "reference_fields": {
                    "Submitter": "Members (議員)",
                    "Session": "Sessions (会議)",
                },
                "validation_rules": {
                    "Status": ["提出", "審議中", "可決", "否決", "廃案"],
                    "Bill_Number": {"pattern": r"^\d+号$"},
                },
            },
            "Sessions (会議)": {
                "target_score": 95.0,
                "required_fields": ["Session_Name", "Date", "Session_Type"],
                "optional_fields": ["Committee", "Agenda", "Attendance", "Minutes_URL"],
                "unique_fields": ["Session_Name", "Date"],  # Combined uniqueness
                "reference_fields": {},
                "validation_rules": {
                    "Session_Type": ["本会議", "委員会", "公聴会"],
                    "Date": {"type": "date"},
                },
            },
            "Speeches (発言)": {
                "target_score": 85.0,
                "required_fields": ["Speaker", "Content", "Session", "Timestamp"],
                "optional_fields": [
                    "Duration",
                    "Transcript_Quality",
                    "Audio_URL",
                    "Video_URL",
                ],
                "unique_fields": [],  # Speeches can be similar
                "reference_fields": {
                    "Speaker": "Members (議員)",
                    "Session": "Sessions (会議)",
                },
                "validation_rules": {
                    "Transcript_Quality": {"type": "float", "min": 0.0, "max": 1.0}
                },
            },
            "Parties (政党)": {
                "target_score": 98.0,
                "required_fields": ["Name", "Is_Active"],
                "optional_fields": [
                    "Founded_Date",
                    "Leader",
                    "Seats_Count",
                    "Website_URL",
                ],
                "unique_fields": ["Name"],
                "reference_fields": {"Leader": "Members (議員)"},
                "validation_rules": {
                    "Is_Active": [True, False],
                    "Seats_Count": {"type": "int", "min": 0, "max": 500},
                },
            },
            "Issues (イシュー)": {
                "target_score": 90.0,
                "required_fields": ["Title", "Category_L1"],
                "optional_fields": [
                    "Category_L2",
                    "Category_L3",
                    "Description",
                    "Related_Bills",
                ],
                "unique_fields": ["Title"],
                "reference_fields": {"Related_Bills": "Bills (法案)"},
                "validation_rules": {
                    "Category_L1": [
                        "社会保障",
                        "経済・産業",
                        "外交・国際",
                        "教育・文化",
                        "環境・エネルギー",
                        "法務・司法",
                        "その他",
                    ]
                },
            },
        }

    async def rate_limit_delay(self):
        """Rate limiting implementation"""
        async with self._request_semaphore:
            now = asyncio.get_event_loop().time()
            time_since_last = now - self._last_request_time
            if time_since_last < 0.5:
                await asyncio.sleep(0.5 - time_since_last)
            self._last_request_time = asyncio.get_event_loop().time()

    async def get_all_records(
        self, session: aiohttp.ClientSession, table_name: str
    ) -> list[dict]:
        """Get all records from a specific table"""
        all_records = []
        offset = None

        while True:
            try:
                await self.rate_limit_delay()
                url = f"{self.base_url}/{table_name}"
                params = {}
                if offset:
                    params["offset"] = offset

                async with session.get(
                    url, headers=self.headers, params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        all_records.extend(data.get("records", []))

                        offset = data.get("offset")
                        if not offset:
                            break
                    else:
                        print(f"⚠️ Error fetching {table_name}: {response.status}")
                        break

            except Exception as e:
                print(f"⚠️ Error in get_all_records for {table_name}: {e}")
                break

        return all_records

    def calculate_completeness_score(
        self, records: list[dict], config: dict
    ) -> tuple[float, dict[str, float]]:
        """Calculate data completeness score"""
        if not records:
            return 0.0, {}

        required_fields = config["required_fields"]
        optional_fields = config["optional_fields"]
        all_fields = required_fields + optional_fields

        field_completeness = {}
        total_weighted_score = 0.0
        total_weight = 0.0

        for field in all_fields:
            filled_count = 0
            for record in records:
                fields = record.get("fields", {})
                if field in fields and fields[field]:
                    # Handle different data types
                    value = fields[field]
                    if isinstance(value, str) and value.strip():
                        filled_count += 1
                    elif isinstance(value, int | float | bool):
                        filled_count += 1
                    elif isinstance(value, list) and len(value) > 0:
                        filled_count += 1
                    elif value is not None:
                        filled_count += 1

            field_score = filled_count / len(records)
            field_completeness[field] = field_score

            # Weight: required fields more important
            weight = 1.0 if field in required_fields else 0.5
            total_weighted_score += field_score * weight
            total_weight += weight

        overall_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
        return overall_score, field_completeness

    def calculate_uniqueness_score(
        self, records: list[dict], config: dict
    ) -> tuple[float, list[str]]:
        """Calculate data uniqueness score"""
        if not records:
            return 1.0, []

        unique_fields = config["unique_fields"]
        if not unique_fields:
            return 1.0, []  # No uniqueness requirements

        duplicate_records = []
        seen_combinations = set()
        duplicate_count = 0

        for record in records:
            fields = record.get("fields", {})

            # Create combination key from unique fields
            key_parts = []
            for field in unique_fields:
                value = fields.get(field, "")
                if isinstance(value, str):
                    key_parts.append(value.strip().lower())
                else:
                    key_parts.append(str(value))

            key = "||".join(key_parts)

            if key in seen_combinations and key.strip():
                duplicate_count += 1
                duplicate_records.append(record["id"])
            else:
                seen_combinations.add(key)

        uniqueness_score = 1.0 - (duplicate_count / len(records))
        return uniqueness_score, duplicate_records

    def calculate_validity_score(
        self, records: list[dict], config: dict
    ) -> tuple[float, list[str]]:
        """Calculate data validity score"""
        if not records:
            return 1.0, []

        validation_rules = config.get("validation_rules", {})
        if not validation_rules:
            return 1.0, []

        invalid_records = []
        total_validations = 0
        passed_validations = 0

        for record in records:
            fields = record.get("fields", {})

            for field, rule in validation_rules.items():
                if field not in fields:
                    continue

                value = fields[field]
                total_validations += 1
                is_valid = True

                if isinstance(rule, list):
                    # Enum validation
                    is_valid = value in rule
                elif isinstance(rule, dict):
                    if rule.get("type") == "int":
                        try:
                            int_val = int(value) if value is not None else 0
                            min_val = rule.get("min", float("-inf"))
                            max_val = rule.get("max", float("inf"))
                            is_valid = min_val <= int_val <= max_val
                        except (ValueError, TypeError):
                            is_valid = False
                    elif rule.get("type") == "float":
                        try:
                            float_val = float(value) if value is not None else 0.0
                            min_val = rule.get("min", float("-inf"))
                            max_val = rule.get("max", float("inf"))
                            is_valid = min_val <= float_val <= max_val
                        except (ValueError, TypeError):
                            is_valid = False
                    elif rule.get("type") == "date":
                        try:
                            datetime.fromisoformat(str(value))
                            is_valid = True
                        except (ValueError, TypeError):
                            is_valid = False
                    elif rule.get("pattern"):
                        pattern = rule["pattern"]
                        is_valid = (
                            bool(re.match(pattern, str(value))) if value else False
                        )

                if is_valid:
                    passed_validations += 1
                elif record["id"] not in invalid_records:
                    invalid_records.append(record["id"])

        validity_score = (
            passed_validations / total_validations if total_validations > 0 else 1.0
        )
        return validity_score, invalid_records

    async def calculate_consistency_score(
        self, session: aiohttp.ClientSession, records: list[dict], config: dict
    ) -> tuple[float, list[str]]:
        """Calculate data consistency score (referential integrity)"""
        if not records:
            return 1.0, []

        reference_fields = config.get("reference_fields", {})
        if not reference_fields:
            return 1.0, []

        consistency_issues = []
        total_references = 0
        valid_references = 0

        # Get reference table data
        reference_data = {}
        for field, ref_table in reference_fields.items():
            try:
                ref_records = await self.get_all_records(session, ref_table)
                reference_data[ref_table] = {r["id"] for r in ref_records}
            except Exception as e:
                print(f"⚠️ Error fetching reference table {ref_table}: {e}")
                reference_data[ref_table] = set()

        # Check referential integrity
        for record in records:
            fields = record.get("fields", {})

            for field, ref_table in reference_fields.items():
                if field not in fields:
                    continue

                ref_value = fields[field]
                total_references += 1

                if isinstance(ref_value, list):
                    # Multiple references
                    all_valid = True
                    for ref_id in ref_value:
                        if ref_id not in reference_data.get(ref_table, set()):
                            all_valid = False
                            break
                    if all_valid:
                        valid_references += 1
                    else:
                        consistency_issues.append(f"{record['id']}.{field}")
                else:
                    # Single reference
                    if ref_value in reference_data.get(ref_table, set()):
                        valid_references += 1
                    else:
                        consistency_issues.append(f"{record['id']}.{field}")

        consistency_score = (
            valid_references / total_references if total_references > 0 else 1.0
        )
        return consistency_score, consistency_issues

    def calculate_accuracy_score(self, records: list[dict], config: dict) -> float:
        """Calculate data accuracy score (placeholder - would need external validation)"""
        # For now, use a heuristic based on data completeness and format correctness
        # In a real implementation, this would compare against authoritative sources

        if not records:
            return 1.0

        # Simple heuristic: records with more complete required fields are likely
        # more accurate
        required_fields = config["required_fields"]
        total_score = 0.0

        for record in records:
            fields = record.get("fields", {})
            filled_required = sum(1 for field in required_fields if fields.get(field))
            accuracy = filled_required / len(required_fields)
            total_score += accuracy

        return total_score / len(records)

    def calculate_timeliness_score(self, records: list[dict]) -> float:
        """Calculate data timeliness score"""
        if not records:
            return 1.0

        now = datetime.now()
        total_score = 0.0

        for record in records:
            # Use Created_At or Updated_At fields if available
            created_at = record.get("createdTime")
            updated_at = record.get("fields", {}).get("Updated_At")

            most_recent = None
            if updated_at:
                try:
                    most_recent = datetime.fromisoformat(
                        updated_at.replace("Z", "+00:00")
                    )
                except Exception:
                    pass

            if not most_recent and created_at:
                try:
                    most_recent = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                except Exception:
                    pass

            if most_recent:
                days_old = (now - most_recent.replace(tzinfo=None)).days
                # Score decreases with age: 1.0 for <30 days, 0.5 for 1 year, 0.0 for >2
                # years
                if days_old <= 30:
                    score = 1.0
                elif days_old <= 365:
                    score = 1.0 - (days_old - 30) / 365 * 0.5
                elif days_old <= 730:
                    score = 0.5 - (days_old - 365) / 365 * 0.5
                else:
                    score = 0.0
                total_score += score
            else:
                total_score += 0.5  # Default score for records without timestamps

        return total_score / len(records)

    def generate_recommendations(
        self, metrics: QualityMetrics, config: dict
    ) -> list[str]:
        """Generate improvement recommendations"""
        recommendations = []

        if metrics.completeness_score < 0.8:
            low_completeness_fields = [
                field
                for field, score in metrics.field_completeness.items()
                if score < 0.5 and field in config["required_fields"]
            ]
            if low_completeness_fields:
                recommendations.append(
                    f"必須フィールドの充実が必要: {', '.join(low_completeness_fields)}"
                )

        if metrics.uniqueness_score < 0.95:
            recommendations.append(
                f"重複データの整理が必要 ({len(metrics.duplicate_records)}件の重複)"
            )

        if metrics.validity_score < 0.9:
            recommendations.append(
                f"データ形式の修正が必要 ({len(metrics.invalid_records)}件の不正データ)"
            )

        if metrics.consistency_score < 0.95:
            recommendations.append(
                f"参照整合性の修正が必要 ({len(metrics.consistency_issues)}件の不整合)"
            )

        if metrics.timeliness_score < 0.7:
            recommendations.append("データの定期更新が必要")

        if metrics.overall_quality_score < config["target_score"] / 100:
            recommendations.append(
                f"目標品質スコア{config['target_score']}%未達 (現在{metrics.overall_quality_score*100:.1f}%)"
            )

        return recommendations

    async def analyze_table_quality(
        self, session: aiohttp.ClientSession, table_name: str
    ) -> QualityMetrics:
        """Analyze quality metrics for a single table"""
        print(f"🔍 Analyzing {table_name}...")

        config = self.table_configs.get(table_name, {})
        if not config:
            print(f"⚠️ No configuration found for {table_name}")
            return None

        # Get all records
        records = await self.get_all_records(session, table_name)
        if not records:
            print(f"⚠️ No records found in {table_name}")
            return None

        print(f"📊 Found {len(records)} records in {table_name}")

        # Calculate all quality dimensions
        completeness_score, field_completeness = self.calculate_completeness_score(
            records, config
        )
        uniqueness_score, duplicate_records = self.calculate_uniqueness_score(
            records, config
        )
        validity_score, invalid_records = self.calculate_validity_score(records, config)
        consistency_score, consistency_issues = await self.calculate_consistency_score(
            session, records, config
        )
        accuracy_score = self.calculate_accuracy_score(records, config)
        timeliness_score = self.calculate_timeliness_score(records)

        # Calculate overall quality score (weighted average)
        weights = {
            "completeness": 0.25,
            "uniqueness": 0.20,
            "validity": 0.20,
            "consistency": 0.15,
            "accuracy": 0.10,
            "timeliness": 0.10,
        }

        overall_score = (
            completeness_score * weights["completeness"]
            + uniqueness_score * weights["uniqueness"]
            + validity_score * weights["validity"]
            + consistency_score * weights["consistency"]
            + accuracy_score * weights["accuracy"]
            + timeliness_score * weights["timeliness"]
        )

        # Create metrics object
        metrics = QualityMetrics(
            table_name=table_name,
            total_records=len(records),
            completeness_score=completeness_score,
            uniqueness_score=uniqueness_score,
            validity_score=validity_score,
            consistency_score=consistency_score,
            accuracy_score=accuracy_score,
            timeliness_score=timeliness_score,
            overall_quality_score=overall_score,
            field_completeness=field_completeness,
            duplicate_records=duplicate_records,
            invalid_records=invalid_records,
            consistency_issues=consistency_issues,
            recommendations=self.generate_recommendations(
                QualityMetrics(
                    table_name,
                    len(records),
                    completeness_score,
                    uniqueness_score,
                    validity_score,
                    consistency_score,
                    accuracy_score,
                    timeliness_score,
                    overall_score,
                    field_completeness,
                    duplicate_records,
                    invalid_records,
                    consistency_issues,
                    [],
                ),
                config,
            ),
        )

        print(
            f"✅ {table_name} analysis complete: {overall_score*100:.1f}% quality score"
        )
        return metrics

    def generate_database_report(
        self, table_metrics: dict[str, QualityMetrics]
    ) -> DatabaseQualityReport:
        """Generate comprehensive database quality report"""
        total_records = sum(m.total_records for m in table_metrics.values())
        total_tables = len(table_metrics)

        # Calculate overall database score (weighted by record count)
        weighted_score = 0.0
        for metrics in table_metrics.values():
            weight = metrics.total_records / total_records if total_records > 0 else 0
            weighted_score += metrics.overall_quality_score * weight

        # Identify critical issues
        critical_issues = []
        for table_name, metrics in table_metrics.items():
            config = self.table_configs.get(table_name, {})
            target = config.get("target_score", 90.0)

            if metrics.overall_quality_score * 100 < target:
                critical_issues.append(
                    f"{table_name}: {metrics.overall_quality_score*100:.1f}% < {target}%目標"
                )

        # Generate improvement priorities
        improvement_priorities = []
        for table_name, metrics in table_metrics.items():
            if metrics.recommendations:
                improvement_priorities.extend(
                    [f"{table_name}: {rec}" for rec in metrics.recommendations]
                )

        # Check target achievements
        target_achievements = {}
        for table_name, metrics in table_metrics.items():
            config = self.table_configs.get(table_name, {})
            target = config.get("target_score", 90.0)
            target_achievements[table_name] = (
                metrics.overall_quality_score * 100 >= target
            )

        return DatabaseQualityReport(
            analysis_date=datetime.now().isoformat(),
            total_tables=total_tables,
            total_records=total_records,
            table_metrics=table_metrics,
            overall_database_score=weighted_score,
            critical_issues=critical_issues,
            improvement_priorities=improvement_priorities[:20],  # Top 20 priorities
            quality_trends={},  # Would be populated with historical data
            target_achievements=target_achievements,
        )

    def print_quality_report(self, report: DatabaseQualityReport):
        """Print comprehensive quality report"""
        print("\n" + "=" * 80)
        print("🔍 DATABASE QUALITY ANALYSIS REPORT")
        print("=" * 80)
        print(f"📅 Analysis Date: {report.analysis_date}")
        print(f"📊 Total Tables: {report.total_tables}")
        print(f"📊 Total Records: {report.total_records:,}")
        print(f"🎯 Overall Database Score: {report.overall_database_score*100:.1f}%")

        print("\n📋 TABLE-BY-TABLE QUALITY METRICS:")
        print("-" * 80)

        for table_name, metrics in report.table_metrics.items():
            config = self.table_configs.get(table_name, {})
            target = config.get("target_score", 90.0)
            status = "✅" if metrics.overall_quality_score * 100 >= target else "❌"

            print(f"\n{status} {table_name}")
            print(f"   📊 Records: {metrics.total_records:,}")
            print(
                f"   🎯 Overall Score: {metrics.overall_quality_score*100:.1f}% (Target: {target}%)"
            )
            print(f"   📈 Completeness: {metrics.completeness_score*100:.1f}%")
            print(f"   🔍 Uniqueness: {metrics.uniqueness_score*100:.1f}%")
            print(f"   ✅ Validity: {metrics.validity_score*100:.1f}%")
            print(f"   🔗 Consistency: {metrics.consistency_score*100:.1f}%")
            print(f"   🎪 Accuracy: {metrics.accuracy_score*100:.1f}%")
            print(f"   ⏰ Timeliness: {metrics.timeliness_score*100:.1f}%")

            if metrics.recommendations:
                print("   💡 Recommendations:")
                for rec in metrics.recommendations[:3]:  # Top 3 recommendations
                    print(f"      • {rec}")

        print("\n🚨 CRITICAL ISSUES:")
        print("-" * 40)
        if report.critical_issues:
            for issue in report.critical_issues:
                print(f"   ❌ {issue}")
        else:
            print("   ✅ No critical issues detected!")

        print("\n📋 TARGET ACHIEVEMENTS:")
        print("-" * 40)
        for table_name, achieved in report.target_achievements.items():
            status = "✅" if achieved else "❌"
            print(f"   {status} {table_name}")

        achieved_count = sum(report.target_achievements.values())
        total_count = len(report.target_achievements)
        print(
            f"\n🎯 Targets Achieved: {achieved_count}/{total_count} ({achieved_count/total_count*100:.1f}%)"
        )

        print("\n📈 IMPROVEMENT PRIORITIES:")
        print("-" * 40)
        for i, priority in enumerate(report.improvement_priorities[:10], 1):
            print(f"   {i}. {priority}")

        print("=" * 80)

    async def save_quality_report(self, report: DatabaseQualityReport) -> str:
        """Save quality report to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data_quality_report_{timestamp}.json"

        # Convert to serializable format
        serializable_report = {
            "analysis_date": report.analysis_date,
            "total_tables": report.total_tables,
            "total_records": report.total_records,
            "overall_database_score": report.overall_database_score,
            "critical_issues": report.critical_issues,
            "improvement_priorities": report.improvement_priorities,
            "target_achievements": report.target_achievements,
            "table_metrics": {
                name: asdict(metrics) for name, metrics in report.table_metrics.items()
            },
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(serializable_report, f, indent=2, ensure_ascii=False)

        print(f"💾 Quality report saved: {filename}")
        return filename

    async def run_comprehensive_analysis(self) -> DatabaseQualityReport:
        """Run comprehensive quality analysis on all tables"""
        print("🔍 Starting comprehensive data quality analysis...")

        async with aiohttp.ClientSession() as session:
            table_metrics = {}

            # Analyze each table (only accessible ones for now)
            available_tables = [
                "Members (議員)",
                "Bills (法案)",
                "Speeches (発言)",
                "Parties (政党)",
            ]

            for table_name in available_tables:
                if table_name in self.table_configs:
                    try:
                        metrics = await self.analyze_table_quality(session, table_name)
                        if metrics:
                            table_metrics[table_name] = metrics
                    except Exception as e:
                        print(f"❌ Error analyzing {table_name}: {e}")
                        continue

                    # Rate limiting between tables
                    await asyncio.sleep(1)

            # Generate comprehensive report
            report = self.generate_database_report(table_metrics)

            # Print and save report
            self.print_quality_report(report)
            await self.save_quality_report(report)

            return report


async def main():
    """Main entry point"""
    analyzer = ComprehensiveDataQualityAnalyzer()
    report = await analyzer.run_comprehensive_analysis()

    print("✅ Comprehensive data quality analysis completed!")

    # Summary recommendations
    if report.critical_issues:
        print(
            f"\n⚠️ {len(report.critical_issues)} critical issues require immediate attention"
        )
    else:
        print("\n🎉 No critical issues detected - database quality is excellent!")


if __name__ == "__main__":
    asyncio.run(main())
