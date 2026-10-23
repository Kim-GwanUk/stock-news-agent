"""Check the morning report's real KRX adapter without changing saved reports."""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.morning_report import krx_index


async def main():
    now = datetime.now(ZoneInfo('Asia/Seoul'))
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        rows = await asyncio.gather(*(
            krx_index(client, market, now.date()) for market in ('KOSPI', 'KOSDAQ')
        ))
    result = {'checked_at': now.isoformat(), 'adapter': 'app.morning_report.krx_index',
              'items': rows, 'app_ui_verified': False}
    destination = ROOT / 'output/market-background-adapter-validation.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if any(row['status'] != 'ok' for row in rows):
        raise SystemExit(1)


if __name__ == '__main__':
    asyncio.run(main())
