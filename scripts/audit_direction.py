"""Isolated historical article audit; never writes application runs/watchlist."""
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import analysis, graph

async def evaluate(row):
    article = row["article"]
    state = {"stock":row["stock"], "articles":[article]}
    state.update(await graph.analyze(state))
    first = state["draft"]
    state.update(graph.validate(state))
    first_errors = state["validation_errors"]
    if first_errors:
        state.update(graph.correct(state))
        state.update(await graph.analyze(state))
        state.update(graph.validate(state))
    before_review = state["draft"]
    state.update(await graph.review(state))
    findings = state["draft"]["findings"]
    finding = next((f for f in findings if f["article_id"] == article["id"]), None)
    final_errors = analysis.validate({"findings":[finding]}, [article], []) if finding else ["응답 없음"]
    if final_errors:
        finding = analysis.deferred(article, "인용·구조 검증 실패")
    return {"id":article["id"],"title":article["title"],"url":article["url"],
            "date":article["published"],"expected":row["expected"],"split":row["split"],
            "first":first,"first_errors":first_errors,"before_review":before_review,
            "final_errors":final_errors,"final":finding,
            "match":finding["direction"] == row["expected"],"calls":len(state.get("usage",[])),
            "prompt_version":analysis.PROMPT_VERSION}

async def main():
    phase = sys.argv[1]
    rows = json.loads(Path("tmp/direction-audit-input.json").read_text(encoding="utf-8"))
    if phase == "final":
        rows += json.loads(Path("tmp/direction-audit-holdout.json").read_text(encoding="utf-8"))
    sem = asyncio.Semaphore(2)
    async def bounded(row):
        async with sem:
            result = await evaluate(row)
            if row["split"] == "dev" or phase != "before":
                print(json.dumps({"phase":phase,"id":result["id"],"direction":result["final"]["direction"],
                                  "errors":result["first_errors"]},ensure_ascii=False),flush=True)
            return result
    results = await asyncio.gather(*(bounded(r) for r in rows))
    Path(f"output/direction-audit-{phase}.json").write_text(
        json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__ == "__main__":
    asyncio.run(main())
