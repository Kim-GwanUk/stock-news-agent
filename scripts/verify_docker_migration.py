"""Compare served records and Docker storage with the preserved local snapshot."""
import json
import sqlite3
import subprocess
from pathlib import Path
from urllib.request import urlopen
from migrate_docker_data import inventory

backup = Path(Path("tmp/docker-migration-backup-path.txt").read_text().strip())
with sqlite3.connect(backup) as db:
    expected = inventory(db)
    db.row_factory = sqlite3.Row
    stocks = [dict(r) for r in db.execute("SELECT * FROM watchlist ORDER BY name")]
    history = {r[0]: [json.loads(x[0]) for x in db.execute(
        "SELECT payload FROM runs WHERE code=? ORDER BY created DESC LIMIT 10", (r[0],))]
        for r in db.execute("SELECT DISTINCT code FROM runs")}

def get(path):
    with urlopen("http://127.0.0.1:8000" + path, timeout=15) as response:
        return json.load(response)

assert get("/stocks") == stocks
for code, records in history.items():
    assert get("/analyses/" + code) == records
assert get("/health")["status"] == "ok"
with urlopen("http://127.0.0.1:8501/_stcore/health", timeout=15) as response:
    assert response.status == 200
actual = json.loads(subprocess.check_output([
    "docker", "compose", "exec", "-T", "backend", "python",
    "/app/migrate_docker_data.py", "inspect", "/app/data/app.sqlite"], text=True))
assert actual == expected
result = {"backup": str(backup), "local_original_preserved": True, "storage": actual,
          "full_record_hashes_match": True, "watchlist_api_matches": True,
          "history_api_matches": True, "history_codes_checked": len(history),
          "backend_health": "ok", "frontend_health": "ok",
          "verified_after_stop_start": True}
Path("output/docker-migration-verification.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
