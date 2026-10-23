"""Isolated cold audit; no historical articles enter application history."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import analysis, db
from scripts.audit_direction import evaluate


async def main():
    phase = sys.argv[1]
    if phase == "regression":
        rows = json.loads(Path("tmp/first-judgment-input.json").read_text(encoding="utf-8"))
        rows = [r for r in rows if r["article"]["id"] in ("new-recall", "new-grant")]
    else:
        source = "tmp/explanation-v10-korean-input.json" if phase == "korean" else "tmp/explanation-v10-input.json"
        rows = json.loads(Path(source).read_text(encoding="utf-8"))
    results = []
    with patch.object(db, "cached", return_value=None), patch.object(db, "cache_put"), patch.object(db, "save_run"):
        for repeat in range(2):
            for row in rows:
                result = await evaluate(row)
                result["repeat"] = repeat + 1
                results.append(result)
                print(json.dumps({"id": result["id"], "repeat": repeat+1, "match": result["match"],
                                  "first_errors": result["first_errors"], "final": result["final"]},
                                 ensure_ascii=False), flush=True)
                Path(f"output/explanation-v10-{phase}.json").write_text(
                    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(f"output/explanation-v10-{phase}-code.json").write_text(json.dumps({
        "prompt_version": analysis.PROMPT_VERSION, "cache_enabled": False, "labels_in_input": False,
        "sha256": {p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                   for p in ("app/analysis.py", "app/models.py", "app/graph.py")},
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
