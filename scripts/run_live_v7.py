"""Run the actual app API for registered stocks and retain reproducible snapshots."""
import json
import urllib.request
from pathlib import Path
from app import db

base = "http://127.0.0.1:8000"
stocks = json.load(urllib.request.urlopen(base + "/stocks", timeout=10))
for stock in stocks:
    code = stock["code"]
    req = urllib.request.Request(base + "/analyze",
        data=json.dumps({"code":code,"refresh":True}).encode(),
        headers={"Content-Type":"application/json"})
    result = json.load(urllib.request.urlopen(req, timeout=200))
    Path(f"output/live-v7-{code}.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    cache = db.cached("news:v7:" + code)
    if cache:
        Path(f"tmp/live-v7-bodies-{code}.json").write_text(
            json.dumps(cache,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({"stock":stock["name"],"version":result["pipeline_version"],
          "selected":sum(bool(a.get("analysis_candidate")) for a in result["articles"]),
          "duplicates":sum(bool(a.get("duplicate_of")) for a in result["articles"]),
          "warnings":result["warnings"]},ensure_ascii=False),flush=True)
