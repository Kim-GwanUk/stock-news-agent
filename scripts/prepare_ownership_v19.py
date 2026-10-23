import copy, hashlib, json
from pathlib import Path
rows=json.loads(Path('tmp/final-holdout-frozen.json').read_text(encoding='utf-8'))
out=[]
for row in rows:
    selected=[copy.deepcopy(a) for a in row['articles'] if a['id'] in ('7542387552d4897b','06af1b63c8ed85a5')]
    if selected:
        for a in selected:a['relevant']=True
        out.append({'name':'regression-'+row['stock']['code'],'stock':row['stock'],'articles':selected})
Path('tmp/ownership-v19-regression.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
Path('output/ownership-v19-pre-holdout-code.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('app').glob('*.py')},indent=2),encoding='utf-8')
