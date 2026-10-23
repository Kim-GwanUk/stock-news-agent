"""Generate actual watchlist previews; record public report data, never credentials."""
import json
import sys
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import db

with httpx.Client(base_url='http://127.0.0.1:8000',timeout=330) as client:
    stocks=client.get('/stocks').json()
    if not stocks:
        for stock in db.stocks():
            r=client.post('/stocks',json={'code':stock['code'],'kind':stock['kind']})
            r.raise_for_status()
        stocks=client.get('/stocks').json()
    reports=[]
    for stock in stocks:
        print('Generating',stock['code'],flush=True)
        response=client.post('/reports/morning/'+stock['code'])
        response.raise_for_status()
        report=response.json()
        reports.append(report)
        (ROOT/'output/morning-live-validation.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'stock':stock['code'],'last':report['prices']['last'].get('date'),
            'news':{k:len(v) for k,v in report['news'].items()},'counts':report['news_counts'],
            'macro':[{k:v for k,v in x.items() if k in ('name','status','date','note')} for x in report['macro']],
            'policy':report.get('policy',{}).get('status'),'warnings':report['warnings']},ensure_ascii=False),flush=True)
