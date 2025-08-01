#!/usr/bin/env python3
"""
Continuous Quality Monitoring System
継続監視 - 品質劣化防止システムの構築
"""

import asyncio
import json
import os
from datetime import datetime, timedelta

import aiohttp
from dotenv import load_dotenv

load_dotenv("/Users/shogen/seiji-watch/.env.local")


class ContinuousQualityMonitor:
    """Continuous data quality monitoring and degradation prevention system"""

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

        # Quality thresholds and monitoring rules
        self.quality_thresholds = {
            "Members (議員)": {
                "target_completeness": 0.95,
                "critical_threshold": 0.85,
                "warning_threshold": 0.90,
                "max_duplicates": 5,
                "max_invalid_records": 10,
            },
            "Bills (法案)": {
                "target_completeness": 0.90,
                "critical_threshold": 0.70,
                "warning_threshold": 0.80,
                "max_duplicates": 3,
                "max_invalid_records": 20,
            },
            "Speeches (発言)": {
                "target_completeness": 0.85,
                "critical_threshold": 0.65,
                "warning_threshold": 0.75,
                "max_duplicates": 10,
                "max_invalid_records": 15,
            },
            "Parties (政党)": {
                "target_completeness": 0.98,
                "critical_threshold": 0.90,
                "warning_threshold": 0.95,
                "max_duplicates": 0,
                "max_invalid_records": 2,
            },
        }

        # Monitoring schedule
        self.monitoring_schedule = {
            "daily_checks": ["completeness", "duplicates", "recent_changes"],
            "weekly_checks": ["full_quality_analysis", "trend_analysis"],
            "monthly_checks": ["comprehensive_audit", "performance_review"],
        }

    async def get_table_records(
        self,
        session: aiohttp.ClientSession,
        table_name: str,
        modified_since: str | None = None,
    ) -> list[dict]:
        """Fetch records with optional modification date filter"""
        all_records = []
        offset = None

        # Build filter formula for recent changes
        params = {"pageSize": 100}
        if modified_since:
            # Airtable formula to filter by modification date
            filter_formula = f"IS_AFTER({{Updated_At}}, '{modified_since}')"
            params["filterByFormula"] = filter_formula

        while True:
            try:
                if offset:
                    params["offset"] = offset

                async with session.get(
                    f"{self.base_url}/{table_name}", headers=self.headers, params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        records = data.get("records", [])
                        all_records.extend(records)

                        offset = data.get("offset")
                        if not offset:
                            break

                        await asyncio.sleep(0.1)
                    else:
                        print(f"❌ Error fetching {table_name}: {response.status}")
                        return []

            except Exception as e:
                print(f"❌ Error fetching {table_name}: {e}")
                return []

        return all_records

    def calculate_table_quality_metrics(
        self, table_name: str, records: list[dict]
    ) -> dict:
        """Calculate comprehensive quality metrics for a table"""
        if not records:
            return {"error": "No records found"}

        metrics = {
            "table_name": table_name,
            "timestamp": datetime.now().isoformat(),
            "total_records": len(records),
            "completeness": {},
            "uniqueness": {},
            "validity": {},
            "consistency": {},
            "timeliness": {},
            "overall_score": 0.0,
            "quality_grade": "F",
            "alerts": [],
        }

        # Define essential fields per table
        essential_fields = {
            "Members (議員)": ["Name", "House", "Constituency", "Party", "Is_Active"],
            "Bills (法案)": [
                "Title",
                "Bill_Number",
                "Bill_Status",
                "Diet_Session",
                "House",
            ],
            "Speeches (発言)": [
                "Speaker_Name",
                "Speech_Content",
                "Speech_Date",
                "Meeting_Name",
            ],
            "Parties (政党)": ["Name", "Is_Active"],
        }

        fields = essential_fields.get(table_name, [])

        # 1. Completeness Analysis
        completeness_scores = []
        for field in fields:
            filled_count = sum(1 for r in records if r.get("fields", {}).get(field))
            completeness_rate = filled_count / len(records)
            completeness_scores.append(completeness_rate)
            metrics["completeness"][field] = {
                "rate": round(completeness_rate, 3),
                "filled_count": filled_count,
                "empty_count": len(records) - filled_count,
            }

        avg_completeness = (
            sum(completeness_scores) / len(completeness_scores)
            if completeness_scores
            else 0
        )
        metrics["completeness"]["overall"] = round(avg_completeness, 3)

        # 2. Uniqueness Analysis (basic duplicate detection)
        if table_name in ["Members (議員)", "Bills (法案)"]:
            key_field = "Name" if table_name == "Members (議員)" else "Bill_ID"
            values = [r.get("fields", {}).get(key_field) for r in records]
            values = [v for v in values if v]  # Remove None/empty
            unique_values = set(values)

            duplicate_count = len(values) - len(unique_values)
            uniqueness_rate = len(unique_values) / len(values) if values else 1.0

            metrics["uniqueness"] = {
                "rate": round(uniqueness_rate, 3),
                "duplicate_count": duplicate_count,
                "unique_count": len(unique_values),
            }
        else:
            metrics["uniqueness"] = {"rate": 1.0, "duplicate_count": 0}

        # 3. Validity Analysis (basic data format validation)
        invalid_count = 0
        for record in records:
            fields_data = record.get("fields", {})

            # Check for obviously invalid data
            if table_name == "Members (議員)":
                house = fields_data.get("House", "")
                if house not in ["衆議院", "参議院", ""]:
                    invalid_count += 1
            elif table_name == "Bills (法案)":
                status = fields_data.get("Bill_Status", "")
                valid_statuses = ["提出", "審議中", "採決待ち", "成立", "廃案", ""]
                if status not in valid_statuses:
                    invalid_count += 1

        validity_rate = (
            (len(records) - invalid_count) / len(records) if records else 1.0
        )
        metrics["validity"] = {
            "rate": round(validity_rate, 3),
            "invalid_count": invalid_count,
            "valid_count": len(records) - invalid_count,
        }

        # 4. Consistency Analysis (cross-field validation)
        inconsistent_count = 0
        for record in records:
            fields_data = record.get("fields", {})

            # Table-specific consistency checks
            if table_name == "Members (議員)":
                house = fields_data.get("House", "")
                constituency = fields_data.get("Constituency", "")

                # Check house-constituency consistency
                if house == "参議院" and "区" in constituency:
                    inconsistent_count += (
                        1  # 参議院 shouldn't have 区-level constituencies
                    )
                elif house == "衆議院" and constituency in ["比例代表"]:
                    # This could be valid, so don't count as inconsistent
                    pass

        consistency_rate = (
            (len(records) - inconsistent_count) / len(records) if records else 1.0
        )
        metrics["consistency"] = {
            "rate": round(consistency_rate, 3),
            "inconsistent_count": inconsistent_count,
            "consistent_count": len(records) - inconsistent_count,
        }

        # 5. Timeliness Analysis (recent updates)
        recent_threshold = datetime.now() - timedelta(days=30)
        recent_updates = 0

        for record in records:
            updated_at = record.get("fields", {}).get("Updated_At", "")
            if updated_at:
                try:
                    update_time = datetime.fromisoformat(
                        updated_at.replace("Z", "+00:00")
                    )
                    if update_time > recent_threshold:
                        recent_updates += 1
                except Exception:
                    pass

        timeliness_rate = recent_updates / len(records) if records else 0
        metrics["timeliness"] = {
            "rate": round(timeliness_rate, 3),
            "recent_updates": recent_updates,
            "stale_records": len(records) - recent_updates,
        }

        # 6. Overall Quality Score
        weights = {
            "completeness": 0.35,
            "uniqueness": 0.25,
            "validity": 0.20,
            "consistency": 0.15,
            "timeliness": 0.05,
        }

        overall_score = (
            avg_completeness * weights["completeness"]
            + metrics["uniqueness"]["rate"] * weights["uniqueness"]
            + validity_rate * weights["validity"]
            + consistency_rate * weights["consistency"]
            + timeliness_rate * weights["timeliness"]
        )

        metrics["overall_score"] = round(overall_score, 3)

        # 7. Quality Grade
        if overall_score >= 0.95:
            metrics["quality_grade"] = "A+"
        elif overall_score >= 0.90:
            metrics["quality_grade"] = "A"
        elif overall_score >= 0.85:
            metrics["quality_grade"] = "B+"
        elif overall_score >= 0.80:
            metrics["quality_grade"] = "B"
        elif overall_score >= 0.70:
            metrics["quality_grade"] = "C"
        elif overall_score >= 0.60:
            metrics["quality_grade"] = "D"
        else:
            metrics["quality_grade"] = "F"

        # 8. Generate Alerts
        thresholds = self.quality_thresholds.get(table_name, {})

        if avg_completeness < thresholds.get("critical_threshold", 0.7):
            metrics["alerts"].append(
                {
                    "type": "CRITICAL",
                    "metric": "completeness",
                    "current": avg_completeness,
                    "threshold": thresholds["critical_threshold"],
                    "message": f"Completeness below critical threshold ({avg_completeness:.1%} < {thresholds['critical_threshold']:.1%})",
                }
            )
        elif avg_completeness < thresholds.get("warning_threshold", 0.8):
            metrics["alerts"].append(
                {
                    "type": "WARNING",
                    "metric": "completeness",
                    "current": avg_completeness,
                    "threshold": thresholds["warning_threshold"],
                    "message": f"Completeness below warning threshold ({avg_completeness:.1%} < {thresholds['warning_threshold']:.1%})",
                }
            )

        if metrics["uniqueness"]["duplicate_count"] > thresholds.get(
            "max_duplicates", 5
        ):
            metrics["alerts"].append(
                {
                    "type": "WARNING",
                    "metric": "uniqueness",
                    "current": metrics["uniqueness"]["duplicate_count"],
                    "threshold": thresholds["max_duplicates"],
                    "message": f"Too many duplicates ({metrics['uniqueness']['duplicate_count']} > {thresholds['max_duplicates']})",
                }
            )

        if invalid_count > thresholds.get("max_invalid_records", 10):
            metrics["alerts"].append(
                {
                    "type": "WARNING",
                    "metric": "validity",
                    "current": invalid_count,
                    "threshold": thresholds["max_invalid_records"],
                    "message": f"Too many invalid records ({invalid_count} > {thresholds['max_invalid_records']})",
                }
            )

        return metrics

    def analyze_quality_trends(self, historical_reports: list[dict]) -> dict:
        """Analyze quality trends over time"""
        if len(historical_reports) < 2:
            return {"error": "Insufficient historical data for trend analysis"}

        # Sort by timestamp
        sorted_reports = sorted(
            historical_reports, key=lambda x: x.get("timestamp", "")
        )

        trends = {
            "analysis_date": datetime.now().isoformat(),
            "period_analyzed": f"{sorted_reports[0]['timestamp']} to {sorted_reports[-1]['timestamp']}",
            "table_trends": {},
            "overall_trends": {},
            "alerts": [],
        }

        # Analyze trends per table
        for table_name in self.quality_thresholds.keys():
            table_reports = [
                r for r in sorted_reports if r.get("table_name") == table_name
            ]

            if len(table_reports) < 2:
                continue

            first_report = table_reports[0]
            last_report = table_reports[-1]

            # Calculate deltas
            completeness_delta = last_report.get("completeness", {}).get(
                "overall", 0
            ) - first_report.get("completeness", {}).get("overall", 0)

            score_delta = last_report.get("overall_score", 0) - first_report.get(
                "overall_score", 0
            )

            trends["table_trends"][table_name] = {
                "completeness_change": round(completeness_delta, 3),
                "quality_score_change": round(score_delta, 3),
                "trend_direction": (
                    "improving"
                    if score_delta > 0.01
                    else "declining" if score_delta < -0.01 else "stable"
                ),
                "current_grade": last_report.get("quality_grade", "F"),
                "previous_grade": first_report.get("quality_grade", "F"),
            }

            # Generate trend alerts
            if completeness_delta < -0.05:  # 5% decline
                trends["alerts"].append(
                    {
                        "type": "WARNING",
                        "table": table_name,
                        "metric": "completeness_trend",
                        "message": f"{table_name} completeness declining by {completeness_delta:.1%}",
                    }
                )

            if score_delta < -0.1:  # 10% score decline
                trends["alerts"].append(
                    {
                        "type": "CRITICAL",
                        "table": table_name,
                        "metric": "quality_trend",
                        "message": f"{table_name} overall quality declining by {score_delta:.1%}",
                    }
                )

        return trends

    def generate_monitoring_recommendations(
        self, current_metrics: dict, trends: dict
    ) -> list[dict]:
        """Generate actionable monitoring recommendations"""
        recommendations = []

        # Based on current quality state
        for table_name, metrics in current_metrics.items():
            if metrics.get("overall_score", 0) < 0.8:
                recommendations.append(
                    {
                        "priority": "HIGH",
                        "table": table_name,
                        "action": "immediate_quality_review",
                        "description": f"Conduct immediate quality review for {table_name} (score: {metrics.get('overall_score', 0):.1%})",
                        "estimated_effort": "2-4 hours",
                    }
                )

            completeness = metrics.get("completeness", {}).get("overall", 0)
            if completeness < 0.85:
                recommendations.append(
                    {
                        "priority": "MEDIUM",
                        "table": table_name,
                        "action": "completeness_improvement",
                        "description": f"Improve data completeness for {table_name} (current: {completeness:.1%})",
                        "estimated_effort": "4-8 hours",
                    }
                )

            duplicate_count = metrics.get("uniqueness", {}).get("duplicate_count", 0)
            if duplicate_count > 0:
                recommendations.append(
                    {
                        "priority": "MEDIUM",
                        "table": table_name,
                        "action": "duplicate_cleanup",
                        "description": f"Clean up {duplicate_count} duplicate records in {table_name}",
                        "estimated_effort": "1-3 hours",
                    }
                )

        # Based on trends
        for table_name, trend in trends.get("table_trends", {}).items():
            if trend.get("trend_direction") == "declining":
                recommendations.append(
                    {
                        "priority": "HIGH",
                        "table": table_name,
                        "action": "trend_investigation",
                        "description": f"Investigate quality decline in {table_name}",
                        "estimated_effort": "2-6 hours",
                    }
                )

        # Sort by priority
        priority_order = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 3))

        return recommendations

    async def run_daily_monitoring(self):
        """Run daily quality monitoring checks"""
        print("🔍 Starting daily quality monitoring...")

        monitoring_results = {
            "monitoring_date": datetime.now().isoformat(),
            "monitoring_type": "daily",
            "table_metrics": {},
            "system_alerts": [],
            "recommendations": [],
        }

        async with aiohttp.ClientSession() as session:
            # Check each table
            for table_name in self.quality_thresholds.keys():
                print(f"\n📊 Monitoring {table_name}...")

                # Get records (limit to recent changes for daily monitoring)
                (datetime.now() - timedelta(days=1)).isoformat()
                records = await self.get_table_records(session, table_name)

                if records:
                    # Calculate quality metrics
                    metrics = self.calculate_table_quality_metrics(table_name, records)
                    monitoring_results["table_metrics"][table_name] = metrics

                    # Add table alerts to system alerts
                    for alert in metrics.get("alerts", []):
                        alert["table"] = table_name
                        monitoring_results["system_alerts"].append(alert)

                    # Print summary
                    print(
                        f"   📈 Quality Score: {metrics['overall_score']:.1%} (Grade: {metrics['quality_grade']})"
                    )
                    print(f"   📋 Records: {metrics['total_records']}")
                    print(
                        f"   🔍 Completeness: {metrics['completeness']['overall']:.1%}"
                    )
                    print(f"   ⚠️ Alerts: {len(metrics['alerts'])}")
                else:
                    print(f"   ❌ No records found for {table_name}")

        # Generate recommendations
        monitoring_results["recommendations"] = (
            self.generate_monitoring_recommendations(
                monitoring_results["table_metrics"], {}
            )
        )

        # Save monitoring report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"daily_quality_monitoring_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(monitoring_results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Daily monitoring report saved: {filename}")

        # Print summary
        total_alerts = len(monitoring_results["system_alerts"])
        critical_alerts = sum(
            1
            for a in monitoring_results["system_alerts"]
            if a.get("type") == "CRITICAL"
        )

        print(f"\n{'=' * 80}")
        print("📋 DAILY QUALITY MONITORING SUMMARY")
        print(f"{'=' * 80}")
        print(f"📊 Tables Monitored: {len(monitoring_results['table_metrics'])}")
        print(f"🚨 Total Alerts: {total_alerts} (Critical: {critical_alerts})")
        print(f"📝 Recommendations: {len(monitoring_results['recommendations'])}")

        # Show critical alerts
        if critical_alerts > 0:
            print("\n🚨 CRITICAL ALERTS:")
            for alert in monitoring_results["system_alerts"]:
                if alert.get("type") == "CRITICAL":
                    print(
                        f"   ❌ {alert.get('table', 'System')}: {alert.get('message', 'Unknown alert')}"
                    )

        # Show top recommendations
        if monitoring_results["recommendations"]:
            print("\n📝 TOP RECOMMENDATIONS:")
            for rec in monitoring_results["recommendations"][:3]:
                print(f"   🔧 {rec['priority']}: {rec['description']}")

        return monitoring_results

    async def setup_monitoring_schedule(self):
        """Setup continuous monitoring schedule"""
        print("⏰ Setting up continuous quality monitoring schedule...")

        schedule_config = {
            "setup_date": datetime.now().isoformat(),
            "monitoring_intervals": {
                "daily": "24 hours - Completeness, duplicates, recent changes",
                "weekly": "7 days - Full quality analysis, trend analysis",
                "monthly": "30 days - Comprehensive audit, performance review",
            },
            "alert_thresholds": self.quality_thresholds,
            "automation_recommendations": [
                "Integrate with cron job for daily monitoring",
                "Set up email alerts for critical issues",
                "Create dashboard for real-time quality metrics",
                "Implement automated quality reports",
            ],
            "maintenance_tasks": [
                "Weekly trend analysis review",
                "Monthly threshold adjustment",
                "Quarterly monitoring system upgrade",
                "Annual comprehensive audit",
            ],
        }

        filename = f"monitoring_schedule_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(schedule_config, f, indent=2, ensure_ascii=False)

        print(f"💾 Monitoring schedule configuration saved: {filename}")

        return schedule_config


async def main():
    """Main entry point"""
    monitor = ContinuousQualityMonitor()

    # Run daily monitoring
    await monitor.run_daily_monitoring()

    # Setup monitoring schedule
    await monitor.setup_monitoring_schedule()

    print("\n✅ Continuous quality monitoring system established!")
    print("📋 Next: EPIC 13 completion - All tasks completed!")


if __name__ == "__main__":
    asyncio.run(main())
