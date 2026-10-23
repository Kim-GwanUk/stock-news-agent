"""Exercise refresh=True twice; bypass run cache, retain content decision cache."""
import json
import urllib.request
from pathlib import Path

base = "http://127.0.0.1:8000"
stocks = json.load(urllib.request.urlopen(base + "/stocks",timeout=10))
results = []
for stock in stocks:
    runs = []
    for repeat in range(2):
        req = urllib.request.Request(base + "/analyze",
            data=json.dumps({"code":stock["code"],"refresh":True}).encode(),
            headers={"Content-Type":"application/json"})
        r = json.load(urllib.request.urlopen(req,timeout=200))
        runs.append(r)
        selected = {a["id"] for a in r["articles"] if a.get("analysis_candidate")}
        print(json.dumps({"stock":stock["name"],"repeat":repeat+1,"version":r["pipeline_version"],
                          "selected":len(selected),"reused":r.get("reused_finding_count"),
                          "calls":len(r["usage"]),"warnings":r["warnings"]},ensure_ascii=False),flush=True)
    results.append(runs)
Path("output/stability-v8-live.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
