#!/usr/bin/env python3
"""
Test runner for Policy Issue Extraction System.
Provides different test configurations and reporting options.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(command, description=""):
    """Run a command and return success status."""
    if description:
        print(f"\n{'='*60}")
        print(f"Running: {description}")
        print(f"Command: {command}")
        print(f"{'='*60}")

    result = subprocess.run(command, shell=True, capture_output=False)
    return result.returncode == 0


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run Policy Issue Extraction tests")

    parser.add_argument(
        '--type',
        choices=['unit', 'integration', 'performance', 'all'],
        default='all',
        help='Type of tests to run'
    )

    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Generate coverage report'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )

    parser.add_argument(
        '--parallel',
        type=int,
        default=1,
        help='Number of parallel test workers'
    )

    parser.add_argument(
        '--fast',
        action='store_true',
        help='Skip slow tests'
    )

    parser.add_argument(
        '--specific',
        type=str,
        help='Run specific test file or test function'
    )

    parser.add_argument(
        '--html-report',
        action='store_true',
        help='Generate HTML coverage report'
    )

    parser.add_argument(
        '--junit-xml',
        type=str,
        help='Generate JUnit XML report to specified file'
    )

    args = parser.parse_args()

    # Ensure we're in the correct directory
    test_dir = Path(__file__).parent
    os.chdir(test_dir)

    # Install test dependencies
    print("Installing test dependencies...")
    install_cmd = "pip install pytest pytest-asyncio pytest-cov pytest-xdist pytest-timeout"
    if not run_command(install_cmd, "Installing test dependencies"):
        print("Failed to install dependencies")
        return 1

    # Build base pytest command
    pytest_cmd = ["python", "-m", "pytest"]

    # Add verbosity
    if args.verbose:
        pytest_cmd.append("-v")
    else:
        pytest_cmd.append("-q")

    # Add parallel execution
    if args.parallel > 1:
        pytest_cmd.extend(["-n", str(args.parallel)])

    # Add coverage reporting
    if args.coverage:
        pytest_cmd.extend([
            "--cov=src",
            "--cov-report=term-missing"
        ])

        if args.html_report:
            pytest_cmd.extend(["--cov-report=html:htmlcov"])

    # Add JUnit XML reporting
    if args.junit_xml:
        pytest_cmd.extend(["--junit-xml", args.junit_xml])

    # Add test type filtering
    if args.type == 'unit':
        pytest_cmd.extend(["-m", "unit"])
    elif args.type == 'integration':
        pytest_cmd.extend(["-m", "integration"])
    elif args.type == 'performance':
        pytest_cmd.extend(["-m", "performance"])

    # Skip slow tests if requested
    if args.fast:
        pytest_cmd.extend(["-m", "not slow"])

    # Add specific test file/function
    if args.specific:
        pytest_cmd.append(args.specific)
    else:
        pytest_cmd.append("tests/")

    # Run the tests
    test_command = " ".join(pytest_cmd)
    success = run_command(test_command, f"Running {args.type} tests")

    if success:
        print(f"\n✅ All {args.type} tests passed!")

        if args.coverage and args.html_report:
            print(f"\n📊 Coverage report generated in: {test_dir}/htmlcov/index.html")

        if args.junit_xml:
            print(f"\n📄 JUnit XML report generated: {args.junit_xml}")

    else:
        print(f"\n❌ Some {args.type} tests failed!")
        return 1

    return 0


def run_unit_tests():
    """Run only unit tests."""
    cmd = "python -m pytest tests/test_policy_issue_extractor.py tests/test_airtable_issue_manager.py -v"
    return run_command(cmd, "Unit Tests")


def run_integration_tests():
    """Run only integration tests."""
    cmd = "python -m pytest tests/test_integration_workflow.py -v"
    return run_command(cmd, "Integration Tests")


def run_performance_tests():
    """Run performance tests."""
    cmd = "python -m pytest tests/test_integration_workflow.py::TestPerformanceAndScalability -v"
    return run_command(cmd, "Performance Tests")


def run_quick_tests():
    """Run quick smoke tests."""
    cmd = "python -m pytest tests/test_policy_issue_extractor.py::TestDualLevelIssue -v"
    return run_command(cmd, "Quick Smoke Tests")


def generate_coverage_report():
    """Generate comprehensive coverage report."""
    cmd = (
        "python -m pytest tests/ "
        "--cov=src "
        "--cov-report=html:htmlcov "
        "--cov-report=term-missing "
        "--cov-report=xml:coverage.xml "
        "--cov-fail-under=80"
    )
    return run_command(cmd, "Coverage Report Generation")


def run_test_suite_ci():
    """Run complete test suite for CI/CD."""
    commands = [
        ("python -m pytest tests/test_policy_issue_extractor.py -v",
         "Unit Tests - Policy Extractor"),
        ("python -m pytest tests/test_airtable_issue_manager.py -v",
         "Unit Tests - Airtable Manager"),
        ("python -m pytest tests/test_integration_workflow.py::TestCompleteExtractionWorkflow -v",
         "Integration Tests - Core Workflow"),
        ("python -m pytest tests/test_integration_workflow.py::TestDataConsistency -v",
         "Integration Tests - Data Consistency"),
    ]

    all_success = True
    for cmd, description in commands:
        success = run_command(cmd, description)
        if not success:
            all_success = False

    if all_success:
        print("\n🎉 All CI tests passed!")
        return 0
    else:
        print("\n💥 Some CI tests failed!")
        return 1


if __name__ == "__main__":
    # If run with specific function arguments
    if len(
        sys.argv) > 1 and sys.argv[1] in [
        'unit',
        'integration',
        'performance',
        'quick',
        'coverage',
            'ci']:
        test_type = sys.argv[1]

        if test_type == 'unit':
            exit_code = 0 if run_unit_tests() else 1
        elif test_type == 'integration':
            exit_code = 0 if run_integration_tests() else 1
        elif test_type == 'performance':
            exit_code = 0 if run_performance_tests() else 1
        elif test_type == 'quick':
            exit_code = 0 if run_quick_tests() else 1
        elif test_type == 'coverage':
            exit_code = 0 if generate_coverage_report() else 1
        elif test_type == 'ci':
            exit_code = run_test_suite_ci()

        sys.exit(exit_code)
    else:
        # Run with argument parsing
        sys.exit(main())
