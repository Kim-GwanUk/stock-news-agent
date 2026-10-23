"""Run in the backend container after generating a morning report."""
import json
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

db = sqlite3.connect('/app/data/app.sqlite')
db.execute("ATTACH DATABASE '/app/data/before-market-verification.sqlite' AS before")
preserved = {}
for table in ('watchlist', 'runs', 'news_events'):
    missing = db.execute(f'SELECT COUNT(*) FROM (SELECT * FROM before.{table} EXCEPT SELECT * FROM main.{table})').fetchone()[0]
    preserved[table] = {
        'before': db.execute(f'SELECT COUNT(*) FROM before.{table}').fetchone()[0],
        'after': db.execute(f'SELECT COUNT(*) FROM main.{table}').fetchone()[0],
        'original_rows_unchanged': missing == 0,
    }
row = db.execute('SELECT payload FROM cache WHERE key=?', ('morning-report-v1:005930',)).fetchone()
report = json.loads(row[0])
indices = [x for x in report['macro'] if x['name'] in ('KOSPI', 'KOSDAQ')]
assert all(x['original_rows_unchanged'] for x in preserved.values())
assert len(indices) == 2 and all(x['status'] == 'ok' for x in indices)
assert report['report_date'] == datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()
print(json.dumps({'preservation': preserved, 'report_date': report['report_date'],
                  'generated_at': report['generated_at'], 'indices': indices,
                  'warnings': report['warnings'], 'news_counts': report['news_counts']},
                 ensure_ascii=False, indent=2))
