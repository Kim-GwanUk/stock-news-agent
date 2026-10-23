import copy,hashlib,json
from pathlib import Path
pool=json.loads(Path('tmp/context-v20-pool.json').read_text(encoding='utf-8'))
aa={a['id']:a for row in pool for a in row['articles']}
cases=[
('hana-forecast','086790','하나금융지주','ae8f29c151c5f53c',['상승 요인'],True,'IBK 추정3분기순익1조2000억원 전년+6%. 확정실적 아님. CET1 13%초과분 주주환원,13.6%추정. 배당/매입 확대는 기대.'),
('hana-group-alias','086790','하나금융지주','a1259c3ffcec5fa3',['상승 요인'],True,'하나금융그룹 순익컨센서스1조2262억+8.3%, 자사주2500~3800억원 예상. 그룹별칭 및 전망 상태 보존. 하나증권155.7%증가를 지주 실적으로 쓰지 않기.'),
('hyundai-mixed','005380','현대차','9fe3753ec49546ba',['판단 보류','상승 요인'],True,'판매10.9%증가는 상승근거 가능하나 점유율13.0→11.8 하락 보존. 그룹155억달러7년투자 계획만으로 상승 금지.2028년 확장 예정,그룹금액을 현대차단독으로 치환 금지.'),
('soil-investment','010950','S-Oil','4b0aa588ca7c999f',['판단 보류'],True,'에쓰오일/S-OIL 별칭 연결.9.3조투자,2027년초상업가동예정/현재시운전. 공급과잉/회사수익전망미공개. 투자만으로 상승 금지; 증권사3조6500억전망을 확정성과로 바꾸면 실패.')]

rows=[];labels=[]
for ident,code,name,aid,directions,related,criteria in cases:
    a=copy.deepcopy(aa[aid]);assert not a['prior_url_overlap'] and a['body_status']=='추출됨'
    a['relevant']=True
    rows.append({'name':ident,'stock':{'code':code,'name':name,'market':'KOSPI'},'articles':[a]})
    labels.append({'name':ident,'id':aid,'stock':name,'directions':directions,'related':related,'criteria':criteria,'url':a['url'],'title':a['title']})
Path('tmp/context-v20-holdout.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
Path('output/context-v20-holdout-labels.json').write_text(json.dumps(labels,ensure_ascii=False,indent=2),encoding='utf-8')
Path('output/context-v20-holdout-manifest.json').write_text(json.dumps({'code':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('app').glob('*.py')},'input_sha256':hashlib.sha256(Path('tmp/context-v20-holdout.json').read_bytes()).hexdigest(),'label_sha256':hashlib.sha256(Path('output/context-v20-holdout-labels.json').read_bytes()).hexdigest(),'unique_sources':len(set(l['url'] for l in labels)),'cases':len(labels),'prior_exact_url_overlap':False,'author':'assistant source-reviewed labels; not independent human ground truth','scope':'sources not used to edit app; frozen before first model evaluation; code must remain unchanged after this file'},indent=2),encoding='utf-8')
