import copy,hashlib,json
from pathlib import Path
pool=json.loads(Path('tmp/coverage-v21-pool.json').read_text(encoding='utf-8'))
aa={a['id']:a for row in pool for a in row['articles']}
cases=[
('posco-prs','005490','POSCO홀딩스','54e1cec9ba1df6ba',['판단 보류'],True,'포스코홀딩스 지분매각36434963주·주당55400원·약2조185억원·PRS3년 조건 유지. 자회사3916~4021억원전망을 지주 실적으로 귀속금지. 거래만으로 이익확정 금지.'),
('hana-group-fee','086790','하나금융지주','cfcaa6f10f3a7833',['상승 요인'],True,'그룹 수수료1조4874억 전년37.7%증가, 핵심이익6조2956억13%증가. 하나은행6143억22.4%/하나증권2731억155.7%와 구분. 실제지표와향후시장둔화구분.'),
('hana-investment','086790','하나금융지주','381e576b050967ee',['판단 보류'],True,'하나은행 통한두나무6.55% 1조33억원투자. 공동서비스상용화미확인/규제/두나무순익감소/장외가격이회계손실은아님 유지. 투자액만으로상승금지, 두나무이익은지주이익아님.'),
('soil-new-capacity','010950','S-Oil','bb306a99308fd9bc',['판단 보류'],True,'에쓰오일 연산88만톤 공급예정과 공급과잉 맥락. 한화토탈가동중단을 에쓰오일중단으로귀속금지. 예정생산능력만으로실현이익/매출상승금지.')]

rows=[];labels=[]
for ident,code,name,aid,directions,related,criteria in cases:
    a=copy.deepcopy(aa[aid]);assert not a['prior_url_overlap'] and a['body_status']=='추출됨'
    a['relevant']=True
    rows.append({'name':ident,'stock':{'code':code,'name':name,'market':'KOSPI'},'articles':[a]})
    labels.append({'name':ident,'id':aid,'stock':name,'directions':directions,'related':related,'criteria':criteria,'url':a['url'],'title':a['title']})
Path('tmp/coverage-v21-holdout.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
Path('output/coverage-v21-holdout-labels.json').write_text(json.dumps(labels,ensure_ascii=False,indent=2),encoding='utf-8')
Path('output/coverage-v21-holdout-manifest.json').write_text(json.dumps({'code':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('app').glob('*.py')},'input_sha256':hashlib.sha256(Path('tmp/coverage-v21-holdout.json').read_bytes()).hexdigest(),'label_sha256':hashlib.sha256(Path('output/coverage-v21-holdout-labels.json').read_bytes()).hexdigest(),'unique_sources':len(set(l['url'] for l in labels)),'cases':len(labels),'prior_exact_url_overlap':False,'author':'assistant source-reviewed labels; not independent human ground truth','scope':'sources not used to edit app; frozen before first model evaluation; code must remain unchanged after this file'},indent=2),encoding='utf-8')
