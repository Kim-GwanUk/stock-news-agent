import copy,hashlib,json
from pathlib import Path
pool=json.loads(Path('tmp/ownership-v19-fresh-pool.json').read_text(encoding='utf-8'))
aa={a['id']:a for row in pool for a in row['articles']}
cases=[
('finance-forecast','071050','한국금융지주','48bc804fd95af420',['하락 요인'],True,'한국금융지주 4321억원 순익 전망, 전분기56.6%감소. 미래에셋4088억손실과 업종76.6%감소를 자체실적으로 쓰면 실패. 전망 유지.'),
('shinhan-return','055550','신한지주','10eee63f4b5496d0',['상승 요인'],True,'7000억원 규모 매입 완료, 취득6538515주+기존1주=소각6538516주 예정.11월4일 소각예정이며 관계기관 협의로 변경 가능. 자금조달 아님.'),
('roundup-return','055550','신한지주','ef9cba3d7f79bd82',['상승 요인','판단 보류'],True,'신한 자기주식 취득완료에 따른 소각정정. LS에코에너지·플리토 실적이나 다른 기업 자금조달을 신한 근거로 쓰면 실패.'),
('roundup-earnings','229640','LS에코에너지','ef9cba3d7f79bd82',['상승 요인'],True,'LS에코에너지 매출3515.21억+51%,영업이익221.74억+50.15%,순익140.22억+24.85%. 플리토영업이익217.03%를 귀속하면 실패.'),
('telecom-investment','017670','SK텔레콤','018fddd0786c7961',['판단 보류'],True,'SK텔레콤 2030년까지 AI컴퍼니4억8000만달러 투자약정. SK하이닉스167조/326조현금흐름을 SKT실적 또는 자금유입으로 쓰면 실패. 상장효과는 논평상 우려/가정.')]

rows=[];labels=[]
for ident,code,name,aid,directions,related,criteria in cases:
    a=copy.deepcopy(aa[aid]);assert not a['prior_url_overlap'] and a['body_status']=='추출됨'
    a['relevant']=True
    rows.append({'name':ident,'stock':{'code':code,'name':name,'market':'KOSPI'},'articles':[a]})
    labels.append({'name':ident,'id':aid,'stock':name,'directions':directions,'related':related,'criteria':criteria,'url':a['url'],'title':a['title']})
Path('tmp/ownership-v19-final-holdout.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
Path('output/ownership-v19-final-holdout-labels.json').write_text(json.dumps(labels,ensure_ascii=False,indent=2),encoding='utf-8')
Path('output/ownership-v19-final-holdout-manifest.json').write_text(json.dumps({'code':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('app').glob('*.py')},'input_sha256':hashlib.sha256(Path('tmp/ownership-v19-final-holdout.json').read_bytes()).hexdigest(),'label_sha256':hashlib.sha256(Path('output/ownership-v19-final-holdout-labels.json').read_bytes()).hexdigest(),'unique_sources':len(set(l['url'] for l in labels)),'cases':len(labels),'prior_exact_url_overlap':False,'author':'assistant source-reviewed labels; not independent human ground truth','scope':'sources not used to edit app; frozen before first model evaluation; code must remain unchanged after this file'},indent=2),encoding='utf-8')
