"""Create concise human-readable and machine-readable summaries from artifacts."""
import json

comp = json.load(open("artifacts/comparison.json"))
out = {"endpoints": {}}
commands = []
for side in ("baseline", "optimized"):
    for entry in comp[side]:
        label = entry["label"]
        ep = label.split("_", 1)[1]
        out["endpoints"].setdefault(ep, {})[side] = {
            "p50_ms": entry["summary"]["p50_ms"],
            "p95_ms": entry["summary"]["p95_ms"],
            "p99_ms": entry["summary"]["p99_ms"],
            "error_rate": entry["summary"]["error_rate"],
            "avg_queries": entry["summary"]["avg_queries"],
        }
        commands.extend(entry.get("commands", []))

open("artifacts/run_output_log.json", "w").write(json.dumps(out, indent=2))
open("artifacts/commands_executed_log.json", "w").write(json.dumps(list(set(commands)), indent=2))
print("wrote artifacts/run_output_log.json and commands_executed_log.json")
