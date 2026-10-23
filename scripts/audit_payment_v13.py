"""Unseen-source evaluation; no history/cache writes and no label leakage."""
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
    rows = json.loads(Path("tmp/payment-v13-input.json").read_text(encoding="utf-8"))
    assert all(r["article"]["body_status"] == "추출됨" for r in rows)
    snapshot = {"prompt_version": analysis.PROMPT_VERSION, "cache_enabled": False, "labels_in_input": False,
                "sha256": {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (
                    "app/analysis.py","app/financial_grounding.py","app/payment_conditions.py","app/models.py","app/graph.py")}}
    results = []
    with patch.object(db, "cached", return_value=None), patch.object(db, "cache_put"), patch.object(db, "save_run"):
        for repeat in range(2):
            for row in rows:
                r = await evaluate(row)
                r["repeat"] = repeat+1
                results.append(r)
                print(json.dumps({"id": r["id"], "repeat": repeat+1, "errors": r["first_errors"],
                                  "final": r["final"]}, ensure_ascii=False), flush=True)
                Path("output/payment-v13-results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest for p,digest in snapshot["sha256"].items())
    Path("output/payment-v13-code.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

if __name__ == "__main__":
    asyncio.run(main())
