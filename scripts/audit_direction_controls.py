import asyncio,json
from pathlib import Path
from audit_direction import evaluate
async def main():
    data=json.loads(Path('tmp/news-evaluation-input.json').read_text(encoding='utf-8'))
    expected={'3b6ee9f2b3f3eedc':'판단 보류','3f42d0d59bb3640f':'상승 요인','65d53e8e01353f07':'판단 보류','924dd0e2d8d9e9ac':'판단 보류'}
    results=[]
    seen=set()
    for group in data:
        for a in group['articles']:
            if a['id'] in expected and a['id'] not in seen:
                seen.add(a['id'])
                r=await evaluate({'stock':group['stock'],'article':{**a,'analysis_candidate':True},'expected':expected[a['id']],'split':'prior-regression'})
                results.append(r)
                print(json.dumps({'id':r['id'],'direction':r['final']['direction'],'impact':r['final']['impact'],'match':r['match']},ensure_ascii=False),flush=True)
    Path('output/direction-audit-controls.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
asyncio.run(main())
