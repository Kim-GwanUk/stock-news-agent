"""Backup and merge user records; refuses to overwrite conflicting records."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

TABLES = {"watchlist": "code", "runs": "id"}


def inventory(connection):
    result = {}
    for table, key in TABLES.items():
        rows = connection.execute(f"SELECT * FROM {table} ORDER BY {key}").fetchall()
        encoded = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()
        result[table] = {"count": len(rows), "sha256": hashlib.sha256(encoded).hexdigest()}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["backup", "merge", "inspect"])
    parser.add_argument("source")
    parser.add_argument("destination", nargs="?")
    args = parser.parse_args()
    path = Path(args.source).resolve()
    if not path.is_file():
        raise SystemExit("Source database does not exist.")
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as source:
        assert source.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        if args.mode == "inspect":
            print(json.dumps(inventory(source)))
            return
        target = Path(args.destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        if args.mode == "backup" and target.exists():
            raise SystemExit("Backup destination already exists.")
        with sqlite3.connect(target) as destination:
            if args.mode == "backup":
                source.backup(destination)
                # Portable sealed snapshot: no WAL sidecars required on a read-only mount.
                destination.execute("PRAGMA journal_mode=DELETE")
            else:
                destination.execute("BEGIN IMMEDIATE")
                for table, key in TABLES.items():
                    schema = source.execute(
                        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
                    ).fetchone()[0]
                    if not destination.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
                    ).fetchone():
                        destination.execute(schema)
                    columns = [r[1] for r in source.execute(f"PRAGMA table_info({table})")]
                    key_index = columns.index(key)
                    for row in source.execute(f"SELECT * FROM {table}"):
                        existing = destination.execute(
                            f"SELECT * FROM {table} WHERE {key}=?", (row[key_index],)
                        ).fetchone()
                        if existing is not None and existing != row:
                            raise RuntimeError(f"Conflicting {table} record; migration rolled back.")
                        if existing is None:
                            destination.execute(
                                f"INSERT INTO {table} VALUES ({','.join('?' for _ in row)})", row)
            assert destination.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            print(json.dumps({"source": inventory(source), "destination": inventory(destination)}))


if __name__ == "__main__":
    main()
