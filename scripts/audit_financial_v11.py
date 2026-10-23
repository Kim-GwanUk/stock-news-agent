"""Replay previously failing actual articles, with no cache or history writes."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import db, analysis
from scripts.audit_direction import evaluate

async def main():
    snapshot = {
        "prompt_version": analysis.PROMPT_VERSION, "cache_enabled": False, "labels_in_input": False,
        "sha256": {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (
            "app/analysis.py", "app/financial_grounding.py", "app/graph.py")},
    }
    rows = []
    for filename in ("tmp/explanation-v10-input.json", "tmp/explanation-v10-korean-input.json",
                     "tmp/first-judgment-input.json"):
        data = json.loads(Path(filename).read_text(encoding="utf-8"))
        rows += [r for r in data if r["article"]["id"] in (
            "v10-sk-preliminary", "v10-samsung-preliminary", "v10-sk-preliminary-ko",
            "new-grant", "new-recall")]
    results = []
    with patch.object(db, "cached", return_value=None), patch.object(db, "cache_put"), patch.object(db, "save_run"):
        for repeat in range(2):
            for row in rows:
                result = await evaluate(row)
                result["repeat"] = repeat+1
                results.append(result)
                print(json.dumps({"id": result["id"], "repeat": repeat+1,
                                  "first_errors": result["first_errors"], "final": result["final"]},
                                 ensure_ascii=False), flush=True)
                Path("output/financial-v11-results.json").write_text(
                    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("output/financial-v11-code.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

if __name__ == "__main__":
    asyncio.run(main())
