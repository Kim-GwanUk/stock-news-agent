"""Replay frozen collected articles through selection and multi-article analysis."""
import asyncio
import json
from pathlib import Path
from unittest.mock import patch
from app import graph
from app.news_selection import select

async def main():
    for code in ("000660","005930"):
        old = json.loads(Path(f"output/live-batch-{code}.json").read_text(encoding="utf-8"))
        frozen = json.loads(Path(f"tmp/live-batch-bodies-{code}.json").read_text(encoding="utf-8"))
        articles, usage, warnings = await select(old["stock"], frozen["articles"],
                                                  f"tmp/batch-v7-selection-{code}.json")
        state = {"stock":old["stock"],"articles":articles,"usage":[usage],"news_warnings":warnings}
        state.update(await graph.analyze(state))
        state.update(graph.validate(state))
        if state["validation_errors"]:
            state.update(graph.correct(state))
            state.update(await graph.analyze(state))
            state.update(graph.validate(state))
        before = state["draft"]
        state.update(await graph.review(state))
        with patch.object(graph.db, "save_run"):
            result = graph.finish(state)["result"]
        Path(f"output/batch-v7-replay-{code}.json").write_text(
            json.dumps({"result":result,"before_review":before,"validation_errors":state["validation_errors"]},
                       ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps({"stock":old["stock"]["name"],"warnings":result["warnings"],
              "articles":[{"title":a["title"],"relation":a["relation"],"selected":a["analysis_candidate"],
                           "duplicate_of":a.get("duplicate_of")} for a in articles if a.get("body_status")=="추출됨"],
              "findings":[f for f in result["findings"] if any(a["id"]==f["article_id"] and a["analysis_candidate"] for a in articles)]},
              ensure_ascii=False),flush=True)

if __name__ == "__main__":
    asyncio.run(main())
