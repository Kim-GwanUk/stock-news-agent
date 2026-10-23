"""Frozen real-article audit. Labels are assistant-authored, not human ground truth.

Uses saved tmp/news-evaluation-input.json and output/news-evaluation-labels.json.
Does not modify the watchlist or production analysis history.
"""
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import graph, analysis

async def main():
    after = "--after" in sys.argv
    inputs = json.loads(Path("tmp/news-evaluation-selected.json" if after else "tmp/news-evaluation-input.json").read_text(encoding="utf-8"))
    labels = json.loads(Path("output/news-evaluation-labels.json").read_text(encoding="utf-8"))
    results = []
    for group in inputs:
        stock = group["stock"]
        mapping = {r["article_id"]: r for r in labels if r["stock_code"] == stock["code"]}
        selected = [a for a in group["articles"] if a["id"] in mapping]
        for offset in range(0, len(selected), 5):
            original = selected[offset:offset+5]
            # Separately probe direction on ALL audited articles, including rejected ones.
            articles = [{**a, "analysis_candidate": True} for a in original]
            state = {"stock": stock, "articles": articles}
            state.update(await graph.analyze(state))
            state.update(graph.validate(state))
            first_errors = state["validation_errors"]
            if first_errors:
                state.update(graph.correct(state))
                state.update(await graph.analyze(state))
                state.update(graph.validate(state))
            state.update(await graph.review(state))
            findings = {f["article_id"]: f for f in state["draft"]["findings"]}
            for a in original:
                finding = findings.get(a["id"], analysis.deferred(a, "분석 응답 없음"))
                errors = analysis.validate({"findings": [finding]}, articles, [])
                if errors:
                    finding = analysis.deferred(a, "인용 검증 실패")
                label = mapping[a["id"]]
                results.append({**label, "stock_name": stock["name"], "title": a["title"], "url": a["url"],
                                "selected_before": a["analysis_candidate"], "finding": finding,
                                "direction_match": finding["direction"] in label["acceptable_directions"],
                                "first_validation_errors": first_errors, "final_validation_errors": errors})
            print(json.dumps({"stock":stock["name"],"evaluated":len(original)},ensure_ascii=False),flush=True)
    Path("output/news-evaluation-after.json" if after else "output/news-evaluation-results.json").write_text(
        json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"sample":len(results),"direction_match":sum(r["direction_match"] for r in results),
                      "selection_match":sum(r["priority"]==r["selected_before"] for r in results)},ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
