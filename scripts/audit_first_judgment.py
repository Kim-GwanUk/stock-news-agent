"""Cold evaluations: no cache reads/writes and no application history writes."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch
from app import db, analysis
from scripts.audit_direction import evaluate

async def main():
    phase = sys.argv[1]
    rows = json.loads(Path("tmp/first-judgment-input.json").read_text(encoding="utf-8"))
    rows = [r for r in rows if r["split"] == ("holdout" if phase=="holdout" else "dev")]
    results = []
    repeats = 2 if phase == "after" else 1
    with patch.object(db,"cached",return_value=None),patch.object(db,"cache_put"),patch.object(db,"save_run"):
        for repeat in range(repeats):
            sem = asyncio.Semaphore(2)
            async def run(row):
                assert row["article"]["body_status"]=="추출됨"
                async with sem:
                    result = await evaluate(row)
                    result["repeat"] = repeat+1
                    initial = result["first"].get("findings",[])
                    print(json.dumps({"phase":phase,"repeat":repeat+1,"id":result["id"],
                        "first":initial[0]["direction"] if initial else "응답 없음",
                        "final":result["final"]["direction"],"match":result["match"],
                        "errors":result["first_errors"]},ensure_ascii=False),flush=True)
                    return result
            results.extend(await asyncio.gather(*(run(r) for r in rows)))
    Path(f"output/first-judgment-{phase}.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
    Path(f"output/first-judgment-{phase}-code.json").write_text(json.dumps({
        "prompt_version":analysis.PROMPT_VERSION,
        "sha256":{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in
                  ("app/analysis.py","app/models.py","app/graph.py")},
        "cache_enabled":False,"labels_in_model_input":False},indent=2),encoding="utf-8")

if __name__=="__main__":
    asyncio.run(main())
