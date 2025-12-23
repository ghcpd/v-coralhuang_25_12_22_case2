Performance optimization exercise — summary

What I implemented
- Baseline (pre-optimization) handlers are intentionally suboptimal and perform N+1 database queries for paginated endpoints.
- Optimized implementation reduces query count by using set-based SQL (JOINs and aggregated counts) and proper indexes.

How to run
1. python seed_db.py          # populate SQLite with >=10k users and follower relationships
2. python run_tests.py        # runs baseline and optimized workloads in-process and writes artifacts to ./artifacts

Files changed/added
- handlers.py        (baseline -> optimized)
- models.py          (sqlite helper + per-request instrumentation)
- seed_db.py         (bulk seeder)
- run_tests.py       (in-process load runner + artifact collection)
- app.py             (minimal app mapping)

Goal
- Reduce latency and DB queries for `/api/users` and `/api/users/{id}/followers` under concurrent in-process load.
