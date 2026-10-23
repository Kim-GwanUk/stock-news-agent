import asyncio, json, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import fact_ledger as fl

async def main():
    caches=json.loads(Path('tmp/status-root-input.json').read_text(encoding='utf-8-sig'))
    out=[]
    for filename in ['news-status-validation.json','news-status-hyundai-validation.json']:
        run=json.loads(Path('output',filename).read_text(encoding='utf-8-sig'))
        for f in run['findings']:
            if f.get('processing_status') not in ('사실 추출 실패','분석 응답 실패'): continue
            a=next(a for c in caches for a in c['articles'] if a['id']==f['article_id'])
            row={'stock':run['stock'],'article':a,'previous_status':f['processing_status']}
            original=fl.materialize
            def capture(article,refs,stock=None):
                row['refs']=refs
                return original(article,refs,stock)
            try:
                if f.get('fact_ledger'):
                    a['fact_ledger']=fl.materialize(a,f['fact_ledger']['facts'],run['stock'])
                    finding,usage=await fl.interpret_one(run['stock'],a)
                    row['finding']=finding
                else:
                    with patch.object(fl,'materialize',side_effect=capture):
                        ledger,usage=await fl.extract_one(run['stock'],a)
                        row['ledger']=ledger
            except Exception as exc:
                row['error']=str(exc) if isinstance(exc,ValueError) else type(exc).__name__
            out.append(row)
            print(json.dumps({'title':a['title'],'error':row.get('error'),'status':f['processing_status']},ensure_ascii=False),flush=True)
            Path('tmp/'+(sys.argv[1] if len(sys.argv)>1 else 'status-root-diagnosis')+'.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
asyncio.run(main())
