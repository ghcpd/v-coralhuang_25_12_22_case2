# API Performance Optimization

## Overview
This project optimizes a paginated REST API implementation for better performance under concurrent load. The API provides endpoints for listing users and retrieving user followers.

## Optimization Applied
- **N+1 Query Elimination**: Replaced inefficient N+1 queries in the `get_user_followers` handler with a single JOIN query.
- **Database Indexes**: Added indexes on `follower_id` and `followee_id` in the `follows` table.

## Results
- **Baseline (before optimization)**: p50=2672ms, p95=5000ms, p99=5000ms, error_rate=50%
- **Optimized (after optimization)**: p50=283ms, p95=284ms, p99=297ms, error_rate=0%

The optimization reduced latency by ~90% and eliminated timeouts.

## How Results Were Obtained
1. Seeded database with 10k users and 10k follows.
2. Ran workload of 200 concurrent requests (100 list_users, 100 followers_page) with concurrency 50.
3. Measured latency percentiles and error rates.
4. Applied optimizations.
5. Re-ran the same workload.

## Files
- `run_tests.py`: Runner script that executes the workload and generates artifacts.
- `handlers.py`: API handlers (optimized version).
- `models.py`: Database models with indexes.
- Artifacts: `raw_latency_distribution.json`, `p50_p95_p99_comparison_before_after.json`, etc.