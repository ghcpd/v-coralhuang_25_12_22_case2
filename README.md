# API Pagination Performance Tuning (OSWE mini-project)

🔧 Overview

This project implements a small API (in-process invocation only) with two paginated endpoints:

- `GET /api/users` — list users (paginated)
- `GET /api/users/<id>/followers` — list a user's followers (paginated)

The goal is to reproduce a performance problem under concurrent load and then apply a minimal, measured optimization to meet the latency SLAs described in `input.json`.

✅ What you'll find

- `handlers.py` — handler implementations (baseline and optimized modes). Optimized mode batches follower-count queries and follower-user fetches to avoid N+1 queries and redundant per-user queries.
- `models.py`, `db.py` — SQLAlchemy models and DB session management
- `seed_db.py` — seeds the DB with >=10k users and follower relationships
- `run_tests.py` — one-command runner that reads `input.json`, seeds (if required), runs baseline and optimized workloads in-process, collects latency stats and DB query counts, and writes artifacts to `artifacts/`
- `requirements.txt` — Python dependencies

How to run

1. Create a virtualenv and install requirements:

   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt

2. Run the full test sequence (seeding + baseline + optimized):

   python run_tests.py

Artifacts

After a run you'll find artifacts in `artifacts/`: latency distributions, p50/p95/p99 comparisons, query counts, slow query excerpts, and a short optimization summary.

License & Notes

This project is intentionally small and uses SQLite for simplicity. The benchmarking is performed in-process by invoking handler functions directly to match the assignment constraints (no external HTTP server).