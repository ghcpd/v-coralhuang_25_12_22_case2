#!/usr/bin/env python
"""
Comprehensive test runner that seeds database, runs baseline and optimized workloads,
and produces before/after performance comparison artifacts.

Usage:
    python run_tests.py
    OR (explicitly)
    .venv\\Scripts\\python.exe run_tests.py
"""
import json
import subprocess
import sys
from pathlib import Path

def get_python_executable():
    """Get the correct Python executable (venv if available, else system)."""
    script_dir = Path(__file__).parent
    venv_python = script_dir / '.venv' / 'Scripts' / 'python.exe'
    if venv_python.exists():
        return str(venv_python)
    return sys.executable

def main():
    """Execute the complete test suite."""
    script_dir = Path(__file__).parent
    python_exe = get_python_executable()
    
    print("="*80)
    print("PERFORMANCE OPTIMIZATION TEST SUITE")
    print("="*80)
    
    print("\n[1/3] Seeding database with 10k users and 15k follower relationships...")
    result = subprocess.run(
        [python_exe, "seed_db.py"],
        cwd=script_dir,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("FAILED: Database seeding failed!")
        print(result.stderr)
        return 1
    
    print("[OK] Database seeded successfully")
    print(result.stdout)
    
    print("\n[2/3] Running baseline and optimized workload tests...")
    print("(This will execute 300 requests per test at 20 concurrency)")
    print("(Full test: 2000 requests at 50 concurrency)")
    
    result = subprocess.run(
        [python_exe, "run_complete_test.py"],
        cwd=script_dir,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("FAILED: Workload tests failed!")
        print(result.stdout)
        print(result.stderr)
        return 1
    
    print(result.stdout)
    
    print("\n[3/3] Generating final report...")
    
    # Load and display results
    results_dir = script_dir / 'test_results'
    
    with open(results_dir / 'comparison_results.json') as f:
        comparison = json.load(f)
    
    print("\n" + "="*80)
    print("FINAL RESULTS SUMMARY")
    print("="*80)
    
    baseline = comparison['baseline']['latency_ms']
    optimized = comparison['optimized']['latency_ms']
    improvements = comparison['improvements']
    
    print("\nLatency Metrics:")
    print(f"  P50:  {baseline['p50']:.2f}ms -> {optimized['p50']:.2f}ms  (REDUCE {improvements['p50_latency_reduction_percent']:.1f}%)")
    print(f"  P95:  {baseline['p95']:.2f}ms -> {optimized['p95']:.2f}ms  (REDUCE {improvements['p95_latency_reduction_percent']:.1f}%)")
    print(f"  P99:  {baseline['p99']:.2f}ms -> {optimized['p99']:.2f}ms  (REDUCE {improvements['p99_latency_reduction_percent']:.1f}%)")
    print(f"  Mean: {baseline['mean']:.2f}ms -> {optimized['mean']:.2f}ms")
    
    print("\nSLA Compliance:")
    sla = comparison['sla_compliance']
    targets = {'p50': 150, 'p95': 300, 'p99': 500}
    
    for metric, target in targets.items():
        baseline_ok = sla['baseline'].get(f'{metric}_ok', False)
        optimized_ok = sla['optimized'].get(f'{metric}_ok', False)
        status = "[PASS]" if optimized_ok else "[FAIL]"
        print(f"  {metric.upper()}: {status} (target: {target}ms)")
    
    print("\nQuery Efficiency:")
    print(f"  Avg Queries/Request: {comparison['baseline']['query_metrics']['average_per_request']:.2f} -> {comparison['optimized']['query_metrics']['average_per_request']:.2f}")
    
    print("\n" + "="*80)
    print("[OK] TEST COMPLETE - All artifacts saved to: test_results/")
    print("="*80)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
