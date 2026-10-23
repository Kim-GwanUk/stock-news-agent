import json
import sqlite3
import time
from contextlib import contextmanager
from app.config import DATA

@contextmanager
def connection():
    DATA.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATA / "app.sqlite", timeout=20) as con:
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript("""
        CREATE TABLE IF NOT EXISTS watchlist(
          code TEXT PRIMARY KEY, name TEXT NOT NULL, market TEXT NOT NULL, kind TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS runs(
          id TEXT PRIMARY KEY, code TEXT NOT NULL, created REAL NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS cache(
          key TEXT PRIMARY KEY, expires REAL NOT NULL, payload TEXT NOT NULL);
        """)
        yield con

def stocks():
    with connection() as con:
        return [dict(r) for r in con.execute("SELECT * FROM watchlist ORDER BY name")]

def add_stock(stock):
    with connection() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("INSERT OR REPLACE INTO watchlist VALUES(?,?,?,?)",
                    (stock.code, stock.name, stock.market, stock.kind))

def delete_stock(code):
    with connection() as con:
        con.execute("DELETE FROM watchlist WHERE code=?", (code,))

def import_stocks(stocks):
    """Atomic insert; never change existing entries."""
    with connection() as con:
        con.execute('BEGIN IMMEDIATE')
        existing={r[0] for r in con.execute('SELECT code FROM watchlist')}
        new={s['code']:s for s in stocks if s['code'] not in existing}
        for s in new.values():
            con.execute('INSERT INTO watchlist VALUES(?,?,?,?)',(s['code'],s['name'],s['market'],s['kind']))
        return list(new.values())

def save_run(result):
    with connection() as con:
        con.execute("INSERT INTO runs VALUES(?,?,?,?)",
                    (result["run_id"], result["stock"]["code"], time.time(),
                     json.dumps(result, ensure_ascii=False)))

def history(code, limit=10):
    with connection() as con:
        rows = con.execute("SELECT payload FROM runs WHERE code=? ORDER BY created DESC LIMIT ?",
                           (code, limit))
        return [json.loads(r[0]) for r in rows]

def cached(key):
    with connection() as con:
        row = con.execute("SELECT payload FROM cache WHERE key=? AND expires>?", (key, time.time())).fetchone()
        return json.loads(row[0]) if row else None

def cache_put(key, payload, ttl):
    with connection() as con:
        con.execute("INSERT OR REPLACE INTO cache VALUES(?,?,?)",
                    (key, time.time() + ttl, json.dumps(payload, ensure_ascii=False)))
