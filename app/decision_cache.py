"""Content-addressed decisions; prices and collection timestamps are not model inputs."""
import hashlib
import json
from app.config import MODEL

TTL = 7 * 86400

def key(stage, stock, article, version, supplements=()):
    def source(a):
        return {k:a.get(k) for k in ("id","title","body","published","url")}
    payload = {"stage":stage,"stock":{k:stock.get(k) for k in ("code","name","market")},
               "model":MODEL,"version":version,"article":source(article),
               "supplements":sorted((source(a) for a in supplements),key=lambda a:a.get("id") or "")}
    return "decision:" + hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
