"""Repeat real frozen batches, including reordered input, in an isolated cache."""
import asyncio
import copy
import json
from pathlib import Path
from unittest.mock import patch
from app import db, graph
from app.news_selection import select

async def main():
    memory, outputs = {}, []
    with patch.object(db,"cached",side_effect=lambda k:copy.deepcopy(memory.get(k))), \
         patch.object(db,"cache_put",side_effect=lambda k,v,ttl:memory.update({k:copy.deepcopy(v)})), \
         patch.object(db,"save_run"):
        for code in ("000660","005930"):
            old = json.loads(Path(f"output/live-batch-{code}.json").read_text(encoding="utf-8"))
            frozen = json.loads(Path(f"tmp/live-batch-bodies-{code}.json").read_text(encoding="utf-8"))
            stock_results = []
            for repeat in range(3):
                articles = copy.deepcopy(frozen["articles"])
                if repeat == 2:
                    # Change batch context without changing any article's contents.
                    articles = articles[:1] + list(reversed(articles[1:]))
                articles, usage, warnings = await select(old["stock"],articles)
                s = {"stock":old["stock"],"articles":articles,"usage":[usage] if usage else [],"news_warnings":warnings}
                s.update(await graph.analyze(s))
                s.update(graph.validate(s))
                if s["validation_errors"]:
                    s.update(graph.correct(s))
                    s.update(await graph.analyze(s))
                    s.update(graph.validate(s))
                s.update(await graph.review(s))
                result = graph.finish(s)["result"]
                stock_results.append(result)
                print(json.dumps({"stock":old["stock"]["name"],"repeat":repeat+1,
                    "calls":len(result["usage"]),"reused":result["reused_finding_count"],
                    "selected":[a["id"] for a in articles if a["analysis_candidate"]],
                    "supplier_selected":next(a["analysis_candidate"] for a in articles if a["id"]=="e1c890a0fe944379"),
                    "warnings":result["warnings"]},ensure_ascii=False),flush=True)
            outputs.append(stock_results)
    Path("output/stability-v8-replay.json").write_text(json.dumps(outputs,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__ == "__main__":
    asyncio.run(main())
