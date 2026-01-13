# API pagination performance test — baseline → optimized

What I changed
- Implemented an in-repo, in-process benchmark that exercises the same handler
  code paths used by an HTTP API (no external server required).
- Introduced a realistic **baseline** implementation that exhibits common
  performance anti-patterns (full-table loads, N+1 queries, redundant work).
- Implemented an **optimized** version that uses LIMIT/OFFSET, single-join
  queries, and avoids N+1.

How to run (single command)
- python run_tests.py

What the runner does
1. Reads `input.json` for workload spec and SLA
2. Seeds a local SQLite DB (>=10k users, follower relationships)
3. Runs the baseline and optimized handlers in-process under concurrent load
4. Emits artifacts to `./artifacts/` including latency distributions,
   query counts, and a comparison JSON

Files you should inspect
- `handlers_baseline.py` — intentionally slow implementation
- `handlers_optimized.py` — optimized implementation and minimal patch
- `run_tests.py` — orchestrates seeding, benchmark, and artifact collection
- `seed_db.py` — fast, idempotent seeding for reproducible runs

Optimization summary (short)
- Fixed N+1 by fetching follower rows with a single JOIN
- Replaced full-table materialization with LIMIT/OFFSET
- Kept semantics (exact total count, stable ordering)

Contact
- GitHub Copilot
