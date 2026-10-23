"""Replay frozen failures and preserve every generation/validation/review stage."""
import asyncio
import copy
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import analysis, db, graph
from app.news_selection import select

async def main(phase):
    rows = json.loads(Path("output/latest-v14-results.json").read_text(encoding="utf-8"))
    rows += json.loads(Path("output/latest-v14-negative-results.json").read_text(encoding="utf-8"))
    if len(sys.argv)>2:
        rows = [r for r in rows if r["stock"]["code"] in sys.argv[2:]]
    paths = ["app/analysis.py","app/news_selection.py","app/graph.py","app/financial_grounding.py"]
    digest = {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
    all_results = []
    for row in rows:
        code = row["stock"]["code"]
        prefix = "latest-v14-negative" if code=="064350" else "latest-v14"
        frozen = json.loads(Path(f"tmp/{prefix}-bodies-{code}.json").read_text(encoding="utf-8"))
        trace = []
        original_generate, original_review = analysis.generate, analysis.review
        async def generate(*args, **kwargs):
            result = await original_generate(*args, **kwargs)
            trace.append({"stage":"generate","draft":copy.deepcopy(result[0])})
            return result
        async def review(*args, **kwargs):
            result = await original_review(*args, **kwargs)
            trace.append({"stage":"review","verdicts":copy.deepcopy(result[0])})
            return result
        with patch.object(db,"cached",return_value=None), patch.object(db,"cache_put"), \
             patch.object(db,"save_run"), patch.object(analysis,"generate",side_effect=generate), \
             patch.object(analysis,"review",side_effect=review):
            articles, usage, warnings = await select(row["stock"], frozen["articles"],
                f"tmp/root-v15-{phase}-selection-{code}.json")
            state = {"stock":row["stock"],"articles":articles,"usage":[usage] if usage else [],
                     "news_warnings":warnings}
            state.update(await graph.analyze(state))
            state.update(graph.validate(state))
            trace.append({"stage":"validate","errors":state["validation_errors"],
                "per_article":{f["article_id"]:analysis.validate({"findings":[f]},articles,[])
                               for f in state["draft"]["findings"]}})
            if state["validation_errors"]:
                state.update(graph.correct(state))
                state.update(await graph.analyze(state))
                state.update(graph.validate(state))
                trace.append({"stage":"validate_after_correction","errors":state["validation_errors"],
                    "per_article":{f["article_id"]:analysis.validate({"findings":[f]},articles,[])
                                   for f in state["draft"]["findings"]}})
            state.update(await graph.review(state))
            result = graph.finish(state)["result"]
        all_results.append({"result":result,"trace":trace})
        Path(f"output/root-v15-{phase}.json").write_text(
            json.dumps(all_results,ensure_ascii=False,indent=2),encoding="utf-8")
        ids = {a["id"] for a in result["articles"] if a.get("analysis_candidate")}
        print(json.dumps({"stock":row["stock"]["name"],"selected":len(ids),
            "validation":[t for t in trace if t["stage"].startswith("validate")],
            "findings":[f for f in result["findings"] if f["article_id"] in ids]},
            ensure_ascii=False),flush=True)
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in digest.items())
    Path(f"output/root-v15-{phase}-code.json").write_text(json.dumps(digest,indent=2),encoding="utf-8")

if __name__=="__main__":
    asyncio.run(main(sys.argv[1]))
