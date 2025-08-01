#!/usr/bin/env python3
"""
Generate test results summary and analysis from individual test reports.
This script aggregates test case results and creates comprehensive reports.
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


class TestResultsAnalyzer:
    """Analyzes and aggregates external test results."""

    def __init__(self, results_directory: str):
        self.results_dir = Path(results_directory)
        self.logger = self._setup_logging()

        # Test metrics tracking
        self.phase_results = defaultdict(list)
        self.issues_by_severity = Counter()
        self.issues_by_category = Counter()
        self.completion_rates = {}
        self.participant_feedback = defaultdict(list)

    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        return logging.getLogger(__name__)

    def load_test_results(self) -> dict[str, Any]:
        """Load all test result files from the results directory."""
        results = {
            "phase_results": {},
            "issue_reports": [],
            "daily_reports": [],
            "final_evaluations": [],
        }

        if not self.results_dir.exists():
            self.logger.error(f"Results directory not found: {self.results_dir}")
            return results

        # Load phase-specific test results
        for phase_dir in self.results_dir.glob("phase-*"):
            if phase_dir.is_dir():
                phase_name = phase_dir.name
                phase_results = self._load_phase_results(phase_dir)
                results["phase_results"][phase_name] = phase_results

        # Load issue reports
        issue_files = list(self.results_dir.glob("issues/*.json")) + list(
            self.results_dir.glob("issues/*.md")
        )
        for issue_file in issue_files:
            issue_data = self._load_issue_report(issue_file)
            if issue_data:
                results["issue_reports"].append(issue_data)

        # Load daily reports
        daily_files = list(self.results_dir.glob("daily-reports/*.json"))
        for daily_file in daily_files:
            daily_data = self._load_daily_report(daily_file)
            if daily_data:
                results["daily_reports"].append(daily_data)

        self.logger.info(
            f"Loaded results: {len(results['phase_results'])} phases, "
            f"{len(results['issue_reports'])} issues, "
            f"{len(results['daily_reports'])} daily reports"
        )

        return results

    def _load_phase_results(self, phase_dir: Path) -> dict[str, Any]:
        """Load test results for a specific phase."""
        phase_results = {
            "test_cases": [],
            "completion_rate": 0.0,
            "success_criteria": {},
            "participant_feedback": [],
        }

        # Load test case results
        test_case_files = list(phase_dir.glob("test-cases-*.json"))
        for tc_file in test_case_files:
            try:
                with open(tc_file, "r", encoding="utf-8") as f:
                    test_cases = json.load(f)
                    phase_results["test_cases"].extend(test_cases)
            except Exception as e:
                self.logger.error(f"Error loading test cases from {tc_file}: {e}")

        # Calculate completion rate
        if phase_results["test_cases"]:
            completed = sum(
                1 for tc in phase_results["test_cases"] if tc.get("status") == "PASS"
            )
            total = len(phase_results["test_cases"])
            phase_results["completion_rate"] = completed / total * 100

        # Load success criteria evaluation
        criteria_file = phase_dir / "success-criteria.json"
        if criteria_file.exists():
            try:
                with open(criteria_file, "r", encoding="utf-8") as f:
                    phase_results["success_criteria"] = json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading success criteria: {e}")

        return phase_results

    def _load_issue_report(self, issue_file: Path) -> dict[str, Any] | None:
        """Load individual issue report."""
        try:
            if issue_file.suffix == ".json":
                with open(issue_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            elif issue_file.suffix == ".md":
                # Parse markdown issue report
                return self._parse_markdown_issue(issue_file)
        except Exception as e:
            self.logger.error(f"Error loading issue report {issue_file}: {e}")
            return None

    def _parse_markdown_issue(self, md_file: Path) -> dict[str, Any]:
        """Parse markdown issue report to extract structured data."""
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract key information using regex
        issue_data = {
            "file": str(md_file),
            "issue_id": self._extract_field(content, r"Issue ID.*?:(.*?)\\n"),
            "severity": self._extract_field(content, r"重要度.*?:(.*?)\\n"),
            "category": self._extract_field(content, r"カテゴリ.*?:(.*?)\\n"),
            "phase": self._extract_field(content, r"Phase.*?:(.*?)\\n"),
            "reporter": self._extract_field(content, r"発見者.*?:(.*?)\\n"),
            "date": self._extract_field(content, r"報告日.*?:(.*?)\\n"),
        }

        return issue_data

    def _extract_field(self, content: str, pattern: str) -> str:
        """Extract field value using regex pattern."""
        match = re.search(pattern, content, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _load_daily_report(self, daily_file: Path) -> dict[str, Any] | None:
        """Load daily progress report."""
        try:
            with open(daily_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading daily report {daily_file}: {e}")
            return None

    def generate_summary_report(self, results: dict[str, Any]) -> dict[str, Any]:
        """Generate comprehensive summary report."""
        summary = {
            "test_execution_summary": self._analyze_test_execution(results),
            "issue_analysis": self._analyze_issues(results["issue_reports"]),
            "phase_performance": self._analyze_phase_performance(
                results["phase_results"]
            ),
            "participant_feedback": self._analyze_participant_feedback(results),
            "success_criteria_evaluation": self._evaluate_success_criteria(results),
            "recommendations": self._generate_recommendations(results),
            "go_no_go_decision": self._make_go_no_go_decision(results),
        }

        return summary

    def _analyze_test_execution(self, results: dict[str, Any]) -> dict[str, Any]:
        """Analyze overall test execution metrics."""
        total_test_cases = 0
        passed_test_cases = 0
        failed_test_cases = 0

        for phase_name, phase_data in results["phase_results"].items():
            test_cases = phase_data.get("test_cases", [])
            total_test_cases += len(test_cases)
            passed_test_cases += sum(
                1 for tc in test_cases if tc.get("status") == "PASS"
            )
            failed_test_cases += sum(
                1 for tc in test_cases if tc.get("status") == "FAIL"
            )

        return {
            "total_test_cases": total_test_cases,
            "passed_test_cases": passed_test_cases,
            "failed_test_cases": failed_test_cases,
            "pass_rate": (
                (passed_test_cases / total_test_cases * 100)
                if total_test_cases > 0
                else 0
            ),
            "total_issues": len(results["issue_reports"]),
            "testing_duration_days": len(results["daily_reports"]),
            "phases_completed": len(results["phase_results"]),
        }

    def _analyze_issues(self, issue_reports: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze issue distribution and patterns."""
        severity_counts = Counter()
        category_counts = Counter()
        phase_counts = Counter()
        reporter_counts = Counter()

        for issue in issue_reports:
            severity_counts[issue.get("severity", "Unknown")] += 1
            category_counts[issue.get("category", "Unknown")] += 1
            phase_counts[issue.get("phase", "Unknown")] += 1
            reporter_counts[issue.get("reporter", "Unknown")] += 1

        return {
            "total_issues": len(issue_reports),
            "severity_distribution": dict(severity_counts),
            "category_distribution": dict(category_counts),
            "phase_distribution": dict(phase_counts),
            "reporter_distribution": dict(reporter_counts),
            "critical_issues": severity_counts.get("Critical", 0),
            "high_issues": severity_counts.get("High", 0),
        }

    def _analyze_phase_performance(
        self, phase_results: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze performance of each testing phase."""
        phase_analysis = {}

        for phase_name, phase_data in phase_results.items():
            phase_analysis[phase_name] = {
                "completion_rate": phase_data.get("completion_rate", 0),
                "total_test_cases": len(phase_data.get("test_cases", [])),
                "success_criteria_met": self._check_phase_success_criteria(
                    phase_data.get("success_criteria", {})
                ),
                "key_findings": phase_data.get("key_findings", []),
                "recommendations": phase_data.get("recommendations", []),
            }

        return phase_analysis

    def _check_phase_success_criteria(self, criteria: dict[str, Any]) -> bool:
        """Check if phase success criteria are met."""
        if not criteria:
            return False

        # Check each criterion
        for criterion, value in criteria.items():
            if isinstance(value, dict) and "target" in value and "actual" in value:
                if value["actual"] < value["target"]:
                    return False
            elif isinstance(value, bool) and not value:
                return False

        return True

    def _analyze_participant_feedback(self, results: dict[str, Any]) -> dict[str, Any]:
        """Analyze feedback from test participants."""
        feedback_summary = {
            "overall_satisfaction": 0.0,
            "usability_rating": 0.0,
            "accessibility_rating": 0.0,
            "performance_rating": 0.0,
            "common_praise": [],
            "common_complaints": [],
            "improvement_suggestions": [],
        }

        # Analyze daily reports for feedback
        ratings = []
        comments = []

        for daily_report in results.get("daily_reports", []):
            if "participant_feedback" in daily_report:
                feedback = daily_report["participant_feedback"]
                if "satisfaction_rating" in feedback:
                    ratings.append(feedback["satisfaction_rating"])
                if "comments" in feedback:
                    comments.extend(feedback["comments"])

        if ratings:
            feedback_summary["overall_satisfaction"] = sum(ratings) / len(ratings)

        return feedback_summary

    def _evaluate_success_criteria(self, results: dict[str, Any]) -> dict[str, Any]:
        """Evaluate overall success criteria for go/no-go decision."""
        criteria_evaluation = {
            "functional_requirements": self._check_functional_requirements(results),
            "performance_requirements": self._check_performance_requirements(results),
            "accessibility_requirements": self._check_accessibility_requirements(
                results
            ),
            "security_requirements": self._check_security_requirements(results),
            "legal_compliance": self._check_legal_compliance(results),
            "expert_approval": self._check_expert_approval(results),
        }

        return criteria_evaluation

    def _check_functional_requirements(self, results: dict[str, Any]) -> dict[str, Any]:
        """Check functional requirements success criteria."""
        # Analyze Phase 1 results for functional requirements
        phase1_data = results["phase_results"].get("phase-1", {})
        test_cases = phase1_data.get("test_cases", [])

        if not test_cases:
            return {"met": False, "score": 0, "details": "No test cases found"}

        pass_rate = (
            sum(1 for tc in test_cases if tc.get("status") == "PASS")
            / len(test_cases)
            * 100
        )

        return {
            "met": pass_rate >= 95,
            "score": pass_rate,
            "target": 95,
            "details": f"Functional test pass rate: {pass_rate:.1f}%",
        }

    def _check_performance_requirements(
        self, results: dict[str, Any]
    ) -> dict[str, Any]:
        """Check performance requirements success criteria."""
        # Analyze Phase 4 results for performance requirements
        phase4_data = results["phase_results"].get("phase-4", {})
        criteria = phase4_data.get("success_criteria", {})

        mobile_load_time = criteria.get("mobile_load_time", {})
        lighthouse_score = criteria.get("lighthouse_performance", {})

        performance_met = True
        if mobile_load_time.get("actual", 1000) > mobile_load_time.get("target", 200):
            performance_met = False
        if lighthouse_score.get("actual", 0) < lighthouse_score.get("target", 90):
            performance_met = False

        return {
            "met": performance_met,
            "mobile_load_time": mobile_load_time,
            "lighthouse_score": lighthouse_score,
            "details": "Performance criteria evaluation",
        }

    def _check_accessibility_requirements(
        self, results: dict[str, Any]
    ) -> dict[str, Any]:
        """Check accessibility requirements success criteria."""
        # Analyze Phase 3 results for accessibility requirements
        phase3_data = results["phase_results"].get("phase-3", {})
        criteria = phase3_data.get("success_criteria", {})

        wcag_compliance = criteria.get("wcag_aa_compliance", {})
        lighthouse_a11y = criteria.get("lighthouse_accessibility", {})

        return {
            "met": wcag_compliance.get("actual", False)
            and lighthouse_a11y.get("actual", 0) >= 90,
            "wcag_compliance": wcag_compliance,
            "lighthouse_accessibility": lighthouse_a11y,
            "details": "WCAG 2.1 AA compliance and accessibility scoring",
        }

    def _check_security_requirements(self, results: dict[str, Any]) -> dict[str, Any]:
        """Check security requirements success criteria."""
        # Analyze Phase 5 results for security requirements
        phase5_data = results["phase_results"].get("phase-5", {})
        criteria = phase5_data.get("success_criteria", {})

        critical_vulnerabilities = criteria.get("critical_vulnerabilities", {})
        security_headers = criteria.get("security_headers", {})

        return {
            "met": critical_vulnerabilities.get("actual", 1) == 0,
            "critical_vulnerabilities": critical_vulnerabilities,
            "security_headers": security_headers,
            "details": "Security vulnerability and configuration assessment",
        }

    def _check_legal_compliance(self, results: dict[str, Any]) -> dict[str, Any]:
        """Check legal compliance requirements."""
        # Analyze legal compliance issues
        legal_issues = [
            issue
            for issue in results["issue_reports"]
            if issue.get("category") == "Legal Compliance"
        ]

        critical_legal_issues = [
            issue for issue in legal_issues if issue.get("severity") == "Critical"
        ]

        return {
            "met": len(critical_legal_issues) == 0,
            "total_legal_issues": len(legal_issues),
            "critical_legal_issues": len(critical_legal_issues),
            "details": "Election law, copyright, and privacy compliance",
        }

    def _check_expert_approval(self, results: dict[str, Any]) -> dict[str, Any]:
        """Check expert approval from participants."""
        # Analyze final evaluations from experts
        approvals = {}

        for phase_name, phase_data in results["phase_results"].items():
            participant_feedback = phase_data.get("participant_feedback", [])
            for feedback in participant_feedback:
                if feedback.get("final_approval"):
                    expert_type = feedback.get("expert_type", "Unknown")
                    approvals[expert_type] = feedback.get("approval_status", False)

        return {
            "met": all(approvals.values()) if approvals else False,
            "approvals": approvals,
            "details": "Final approval from external experts",
        }

    def _generate_recommendations(
        self, results: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate recommendations based on test results."""
        recommendations = []

        # Analyze critical and high issues for recommendations
        critical_issues = [
            issue
            for issue in results["issue_reports"]
            if issue.get("severity") == "Critical"
        ]

        high_issues = [
            issue
            for issue in results["issue_reports"]
            if issue.get("severity") == "High"
        ]

        if critical_issues:
            recommendations.append(
                {
                    "priority": "Critical",
                    "category": "Bug Fixes",
                    "description": f"Address {len(critical_issues)} critical issues before launch",
                    "estimated_effort": "High",
                    "deadline": "Before MVP launch",
                }
            )

        if high_issues:
            recommendations.append(
                {
                    "priority": "High",
                    "category": "Quality Improvements",
                    "description": f"Resolve {len(high_issues)} high priority issues",
                    "estimated_effort": "Medium",
                    "deadline": "Within 1 week post-launch",
                }
            )

        return recommendations

    def _make_go_no_go_decision(self, results: dict[str, Any]) -> dict[str, Any]:
        """Make final go/no-go decision based on all criteria."""
        success_criteria = self._evaluate_success_criteria(results)
        issue_analysis = self._analyze_issues(results["issue_reports"])

        # Decision logic
        critical_issues = issue_analysis["critical_issues"]
        high_issues = issue_analysis["high_issues"]

        functional_met = success_criteria["functional_requirements"]["met"]
        accessibility_met = success_criteria["accessibility_requirements"]["met"]
        security_met = success_criteria["security_requirements"]["met"]
        legal_met = success_criteria["legal_compliance"]["met"]

        # GO criteria: No critical issues, all major requirements met
        go_decision = (
            critical_issues == 0
            and functional_met
            and accessibility_met
            and security_met
            and legal_met
            and high_issues < 5  # Allow up to 5 high issues
        )

        return {
            "decision": "GO" if go_decision else "NO-GO",
            "confidence": "High" if go_decision else "Low",
            "rationale": self._generate_decision_rationale(
                go_decision, critical_issues, high_issues, success_criteria
            ),
            "conditions": (
                self._generate_launch_conditions(results) if go_decision else []
            ),
            "blocking_issues": (
                self._identify_blocking_issues(results) if not go_decision else []
            ),
        }

    def _generate_decision_rationale(
        self,
        go_decision: bool,
        critical_issues: int,
        high_issues: int,
        success_criteria: dict[str, Any],
    ) -> str:
        """Generate rationale for go/no-go decision."""
        if go_decision:
            return (
                f"Recommendation: GO for MVP launch. "
                f"No critical issues found, {high_issues} high issues within acceptable range. "
                f"All core requirements (functional, accessibility, security, legal) met."
            )
        else:
            blocking_factors = []
            if critical_issues > 0:
                blocking_factors.append(f"{critical_issues} critical issues")
            if not success_criteria["functional_requirements"]["met"]:
                blocking_factors.append("functional requirements not met")
            if not success_criteria["accessibility_requirements"]["met"]:
                blocking_factors.append("accessibility requirements not met")
            if not success_criteria["security_requirements"]["met"]:
                blocking_factors.append("security requirements not met")
            if not success_criteria["legal_compliance"]["met"]:
                blocking_factors.append("legal compliance issues")

            return (
                f"Recommendation: NO-GO for MVP launch. "
                f"Blocking factors: {', '.join(blocking_factors)}. "
                f"These issues must be resolved before launch."
            )

    def _generate_launch_conditions(self, results: dict[str, Any]) -> list[str]:
        """Generate conditions for successful launch."""
        conditions = []

        issue_analysis = self._analyze_issues(results["issue_reports"])
        if issue_analysis["high_issues"] > 0:
            conditions.append(
                f"Monitor and address {issue_analysis['high_issues']} high priority issues post-launch"
            )

        conditions.extend(
            [
                "Maintain monitoring and alerting systems",
                "Prepare incident response procedures",
                "Schedule post-launch accessibility audit",
                "Continue user feedback collection",
            ]
        )

        return conditions

    def _identify_blocking_issues(
        self, results: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify specific issues blocking launch."""
        blocking_issues = []

        for issue in results["issue_reports"]:
            if issue.get("severity") == "Critical":
                blocking_issues.append(
                    {
                        "issue_id": issue.get("issue_id"),
                        "category": issue.get("category"),
                        "description": issue.get("summary", "Critical issue found"),
                        "phase": issue.get("phase"),
                    }
                )

        return blocking_issues

    def export_results(self, summary: dict[str, Any], output_dir: str):
        """Export results to various formats."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Export JSON summary
        json_file = output_path / "test_results_summary.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
        self.logger.info(f"Exported JSON summary to {json_file}")

        # Export CSV for spreadsheet analysis
        self._export_csv_reports(summary, output_path)

        # Generate visualizations
        self._generate_visualizations(summary, output_path)

        # Generate final report document
        self._generate_final_report(summary, output_path)

    def _export_csv_reports(self, summary: dict[str, Any], output_path: Path):
        """Export data as CSV files for spreadsheet analysis."""
        # Issue summary CSV
        issues_data = []
        for issue in summary.get("issue_analysis", {}).get("issues", []):
            issues_data.append(
                {
                    "Issue ID": issue.get("issue_id"),
                    "Severity": issue.get("severity"),
                    "Category": issue.get("category"),
                    "Phase": issue.get("phase"),
                    "Reporter": issue.get("reporter"),
                    "Status": issue.get("status", "Open"),
                }
            )

        if issues_data:
            issues_df = pd.DataFrame(issues_data)
            issues_df.to_csv(output_path / "issues_summary.csv", index=False)

    def _generate_visualizations(self, summary: dict[str, Any], output_path: Path):
        """Generate charts and visualizations."""
        plt.style.use("seaborn-v0_8")

        # Issue distribution charts
        issue_analysis = summary.get("issue_analysis", {})

        if issue_analysis.get("severity_distribution"):
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

            # Severity distribution
            severities = list(issue_analysis["severity_distribution"].keys())
            counts = list(issue_analysis["severity_distribution"].values())
            ax1.pie(counts, labels=severities, autopct="%1.1f%%")
            ax1.set_title("Issues by Severity")

            # Category distribution
            categories = list(issue_analysis["category_distribution"].keys())
            cat_counts = list(issue_analysis["category_distribution"].values())
            ax2.bar(categories, cat_counts)
            ax2.set_title("Issues by Category")
            ax2.tick_params(axis="x", rotation=45)

            plt.tight_layout()
            plt.savefig(
                output_path / "issue_distribution.png", dpi=300, bbox_inches="tight"
            )
            plt.close()

    def _generate_final_report(self, summary: dict[str, Any], output_path: Path):
        """Generate final markdown report."""
        report_content = f"""# Diet Issue Tracker - External Testing Final Report

**Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

### Go/No-Go Decision: {summary['go_no_go_decision']['decision']}

**Confidence Level**: {summary['go_no_go_decision']['confidence']}

**Rationale**: {summary['go_no_go_decision']['rationale']}

## Test Execution Summary

- **Total Test Cases**: {summary['test_execution_summary']['total_test_cases']}
- **Pass Rate**: {summary['test_execution_summary']['pass_rate']:.1f}%
- **Total Issues Found**: {summary['test_execution_summary']['total_issues']}
- **Testing Duration**: {summary['test_execution_summary']['testing_duration_days']} days
- **Phases Completed**: {summary['test_execution_summary']['phases_completed']}/6

## Issue Analysis

### By Severity
- **Critical**: {summary['issue_analysis']['critical_issues']} issues
- **High**: {summary['issue_analysis']['high_issues']} issues
- **Total**: {summary['issue_analysis']['total_issues']} issues

### By Category
"""

        for category, count in summary["issue_analysis"][
            "category_distribution"
        ].items():
            report_content += f"- **{category}**: {count} issues\\n"

        report_content += f"""

## Success Criteria Evaluation

### Functional Requirements
- **Status**: {'✅ MET' if summary['success_criteria_evaluation']['functional_requirements']['met'] else '❌ NOT MET'}
- **Score**: {summary['success_criteria_evaluation']['functional_requirements']['score']:.1f}%

### Accessibility Requirements  
- **Status**: {'✅ MET' if summary['success_criteria_evaluation']['accessibility_requirements']['met'] else '❌ NOT MET'}

### Security Requirements
- **Status**: {'✅ MET' if summary['success_criteria_evaluation']['security_requirements']['met'] else '❌ NOT MET'}

### Legal Compliance
- **Status**: {'✅ MET' if summary['success_criteria_evaluation']['legal_compliance']['met'] else '❌ NOT MET'}

## Recommendations

"""

        for i, rec in enumerate(summary["recommendations"], 1):
            report_content += f"{i}. **{rec['category']}** ({rec['priority']}): {rec['description']}\\n"

        if summary["go_no_go_decision"]["decision"] == "GO":
            report_content += f"""

## Launch Conditions

"""
            for condition in summary["go_no_go_decision"]["conditions"]:
                report_content += f"- {condition}\\n"
        else:
            report_content += f"""

## Blocking Issues

"""
            for issue in summary["go_no_go_decision"]["blocking_issues"]:
                report_content += f"- **{issue['issue_id']}**: {issue['description']} ({issue['category']})\\n"

        # Write final report
        report_file = output_path / "final_test_report.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        self.logger.info(f"Generated final report: {report_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate test results summary and analysis"
    )
    parser.add_argument(
        "--results-dir", required=True, help="Directory containing test results"
    )
    parser.add_argument(
        "--output-dir", required=True, help="Output directory for reports"
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv", "html", "all"],
        default="all",
        help="Output format",
    )

    args = parser.parse_args()

    # Create analyzer and process results
    analyzer = TestResultsAnalyzer(args.results_dir)
    results = analyzer.load_test_results()

    if not results["phase_results"] and not results["issue_reports"]:
        print("Error: No test results found in the specified directory")
        sys.exit(1)

    # Generate summary analysis
    summary = analyzer.generate_summary_report(results)

    # Export results
    analyzer.export_results(summary, args.output_dir)

    # Print summary to console
    print(f"\\n📊 Test Results Summary")
    print(f"{'='*50}")
    print(f"Go/No-Go Decision: {summary['go_no_go_decision']['decision']}")
    print(f"Total Issues: {summary['issue_analysis']['total_issues']}")
    print(f"Critical Issues: {summary['issue_analysis']['critical_issues']}")
    print(f"Test Pass Rate: {summary['test_execution_summary']['pass_rate']:.1f}%")
    print(f"\\nReports generated in: {args.output_dir}")


if __name__ == "__main__":
    main()
