import asyncio,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import fact_ledger
async def main():
    rows=json.loads(Path('tmp/ownership-v19-regression.json').read_text(encoding='utf-8'))
    for row in rows:
        a=row['articles'][0]
        try:
            l,u=await fact_ledger.extract_one(row['stock'],a)
            a['fact_ledger']=l
            print(row['stock']['name'],'facts',json.dumps([{k:f.get(k) for k in ('id','role','subject','event_kind','target_eligible')} for f in l['facts']],ensure_ascii=False),flush=True)
            f,u=await fact_ledger.interpret_one(row['stock'],a)
            print('OK',f['direction'],f['resolved_effect'],flush=True)
        except ValueError as e:print('VALIDATION',str(e),flush=True)
asyncio.run(main())
