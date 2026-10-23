import copy,hashlib,json
from pathlib import Path
pool=json.loads(Path('tmp/context-v20-final-pool.json').read_text(encoding='utf-8'))
aa={a['id']:a for row in pool for a in row['articles']}
cases=[
('dl-earnings','375500','DL이앤씨','edb1358638782082',['하락 요인'],True,'3분기영업익1063억 전년-8.97%,매출1조6466억-13.65% 전망.2조원 프로젝트는 본계약 앞둔 단계. 향후회복으로 현재악화 뒤집지 않기.'),
('posco-approval','005490','POSCO홀딩스','1da31fd7de5a10ae',['판단 보류'],True,'포스코홀딩스 환경승인. FID·원주민권리협의·후속허가 미완료. 총사업비44억호주달러/30억미달러 추산,2031목표. 지주단독지출/가동완료 아님.'),
('soil-historical','010950','S-Oil','42df4afb24b7955b',['판단 보류'],False,'현재 업황 기사. 에쓰오일1575억원 영업손실은2022년 과거 사례. 현재 회사 실적 악재로 귀속하지 말고 업종맥락으로 분류.'),
('hana-index','086790','하나금융지주','caa41aa62e81837d',['판단 보류'],False,'하나금융지주는 지수구성종목 나열. 다른 기업 자사주/상장이슈를 하나 사업근거로 쓰지 않고 제외.')]

rows=[];labels=[]
for ident,code,name,aid,directions,related,criteria in cases:
    a=copy.deepcopy(aa[aid]);assert not a['prior_url_overlap'] and a['body_status']=='추출됨'
    a['relevant']=True
    rows.append({'name':ident,'stock':{'code':code,'name':name,'market':'KOSPI'},'articles':[a]})
    labels.append({'name':ident,'id':aid,'stock':name,'directions':directions,'related':related,'criteria':criteria,'url':a['url'],'title':a['title']})
Path('tmp/context-v20-final-holdout.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
Path('output/context-v20-final-holdout-labels.json').write_text(json.dumps(labels,ensure_ascii=False,indent=2),encoding='utf-8')
Path('output/context-v20-final-holdout-manifest.json').write_text(json.dumps({'code':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('app').glob('*.py')},'input_sha256':hashlib.sha256(Path('tmp/context-v20-final-holdout.json').read_bytes()).hexdigest(),'label_sha256':hashlib.sha256(Path('output/context-v20-final-holdout-labels.json').read_bytes()).hexdigest(),'unique_sources':len(set(l['url'] for l in labels)),'cases':len(labels),'prior_exact_url_overlap':False,'author':'assistant source-reviewed labels; not independent human ground truth','scope':'sources not used to edit app; frozen before first model evaluation; code must remain unchanged after this file'},indent=2),encoding='utf-8')
