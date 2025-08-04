#!/usr/bin/env python3
"""
Test Runner for 24/7 Trading System

Organizes and runs tests by category:
- Security tests (authentication, validation, rate limiting)
- Central manager tests (orchestration, cross-instance communication)  
- Container tests (agents, trading, market data)

TODO: [TESTING] Add test result reporting and coverage analysis
TODO: [TESTING] Implement parallel test execution for faster CI/CD
TODO: [TESTING] Add test environment setup and teardown automation
"""
import subprocess
import sys
import argparse
from pathlib import Path


def run_security_tests(verbose=False):
    """
    Run security-focused tests
    
    TODO: [SECURITY] Add security-specific test environment setup
    TODO: [SECURITY] Add penetration testing scenarios
    """
    print("🔒 Running Security Tests...")
    cmd = ["python3", "-m", "pytest", "-m", "security"]
    if verbose:
        cmd.extend(["-v", "--tb=long"])
    return subprocess.run(cmd, capture_output=False)


def run_central_manager_tests(verbose=False):
    """
    Run central manager logic tests
    
    TODO: [CENTRAL-MANAGER] Add test data setup for multi-instance scenarios
    TODO: [CENTRAL-MANAGER] Add network simulation for cross-instance testing
    """
    print("🎛️ Running Central Manager Tests...")
    cmd = ["python3", "-m", "pytest", "-m", "central_manager"]
    if verbose:
        cmd.extend(["-v", "--tb=long"])
    return subprocess.run(cmd, capture_output=False)


def run_container_tests(verbose=False):
    """
    Run individual container logic tests
    
    TODO: [CONTAINER] Add GPU environment simulation for testing
    TODO: [CONTAINER] Add market data mocking for deterministic tests
    """
    print("📦 Running Container Logic Tests...")
    cmd = ["python3", "-m", "pytest", "-m", "container"]
    if verbose:
        cmd.extend(["-v", "--tb=long"])
    return subprocess.run(cmd, capture_output=False)


def run_all_tests(verbose=False):
    """
    Run all test categories in sequence
    
    TODO: [TESTING] Add test result aggregation and reporting
    TODO: [TESTING] Add failure analysis and recommendations
    """
    print("🧪 Running Full Test Suite...")
    
    results = []
    
    # Run each test category
    results.append(("Security", run_security_tests(verbose)))
    results.append(("Central Manager", run_central_manager_tests(verbose)))  
    results.append(("Container Logic", run_container_tests(verbose)))
    
    # Report results
    print("\n" + "="*50)
    print("TEST RESULTS SUMMARY")
    print("="*50)
    
    total_passed = 0
    total_failed = 0
    
    for category, result in results:
        status = "✅ PASSED" if result.returncode == 0 else "❌ FAILED"
        print(f"{category:15} {status}")
        
        if result.returncode == 0:
            total_passed += 1
        else:
            total_failed += 1
    
    print(f"\nOverall: {total_passed} categories passed, {total_failed} categories failed")
    
    if total_failed > 0:
        print("\n⚠️  Some test categories failed. Check output above for details.")
        return 1
    else:
        print("\n🎉 All test categories passed!")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Run 24/7 Trading System Tests")
    parser.add_argument(
        "category", 
        choices=["security", "central-manager", "container", "all"],
        help="Test category to run"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Change to project root directory
    project_root = Path(__file__).parent.parent
    import os
    os.chdir(project_root)
    
    if args.category == "security":
        result = run_security_tests(args.verbose)
    elif args.category == "central-manager":
        result = run_central_manager_tests(args.verbose)
    elif args.category == "container":
        result = run_container_tests(args.verbose)
    elif args.category == "all":
        result = type('Result', (), {'returncode': run_all_tests(args.verbose)})()
    
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()