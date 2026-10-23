"""Evaluate frozen inputs without cache/history writes; capture extraction and final output."""
import asyncio
import copy
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import graph, db, analysis
from app.news_selection import select

CODE = ["app/fact_ledger.py","app/analysis.py","app/graph.py","app/news_selection.py"]


async def main(path, name):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    hashes = {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in CODE}
    results = []
    with patch.object(db,"cached",return_value=None), patch.object(db,"cache_put"), patch.object(db,"save_run"):
        for row in rows:
            articles = copy.deepcopy(row["articles"])
            articles, usage, warnings = await select(row["stock"],articles)
            s = {"stock":row["stock"],"articles":articles,"usage":[usage],"news_warnings":warnings}
            s.update(await graph.freeze_facts(s))
            frozen = {a["id"]:copy.deepcopy(a.get("fact_ledger")) for a in s["articles"]}
            s.update(await graph.analyze(s))
            first = copy.deepcopy(s["draft"])
            s.update(graph.validate(s))
            errors = list(s["validation_errors"])
            if errors:
                s.update(graph.correct(s))
                s.update(await graph.analyze(s))
                s.update(graph.validate(s))
            before_review = copy.deepcopy(s["draft"])
            s.update(await graph.review(s))
            assert frozen == {a["id"]:a.get("fact_ledger") for a in s["articles"]}
            results.append({"name":row.get("name"), "first":first, "first_errors":errors,
                            "final_errors":s["validation_errors"], "before_review":before_review,
                            "ledgers":frozen, "result":graph.finish(s)["result"]})
            Path(f"output/{name}-results.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
            r = results[-1]["result"]
            chosen = {a["id"] for a in r["articles"] if a.get("analysis_candidate")}
            print(json.dumps({"name":row.get("name"),"stock":r["stock"]["name"],
                "errors":errors, "final_errors":s["validation_errors"],
                "findings":[{"id":f["article_id"],"direction":f["direction"],
                             "locked":f.get("grounding_mode")} for f in r["findings"] if f["article_id"] in chosen]},
                ensure_ascii=False),flush=True)
    assert hashes == {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in CODE}
    Path(f"output/{name}-code.json").write_text(json.dumps(hashes,indent=2),encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1],sys.argv[2]))
