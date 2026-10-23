"""Read-only KRX index probe; credentials and raw errors are never logged."""
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import config
import httpx

report={'checked_at':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),'apis':[]}
with httpx.Client(timeout=25,trust_env=False) as client:
    for market,path in [('KOSPI','kospi_dd_trd'),('KOSDAQ','kosdaq_dd_trd')]:
        entry={'market':market,'api':path,'attempts':[]}
        if not os.getenv('KRX_API_KEY'):
            entry['status']='missing_key'
        else:
            for offset in range(1,8):
                day=date(2026,10,23)-timedelta(days=offset)
                if day.weekday()>4: continue
                try:
                    response=client.get('https://data-dbg.krx.co.kr/svc/apis/idx/'+path,
                        params={'basDd':day.strftime('%Y%m%d')},headers={'AUTH_KEY':os.environ['KRX_API_KEY']})
                    attempt={'date':day.isoformat(),'http_status':response.status_code}
                    entry['attempts'].append(attempt)
                    if response.status_code!=200:
                        entry['status']='http_error'; break
                    data=response.json()
                    rows=data.get('OutBlock_1',[])
                    attempt['rows']=len(rows)
                    row=next((r for r in rows if r.get('IDX_NM') in (market,'코스피' if market=='KOSPI' else '코스닥')),None)
                    if row:
                        entry.update(status='ok',row=row); break
                    entry['status']='no_matching_data'
                except Exception as exc:
                    entry.update(status='request_failed',error_type=type(exc).__name__); break
        report['apis'].append(entry)
        print(json.dumps(entry,ensure_ascii=False),flush=True)
Path('output/market-index-live-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
