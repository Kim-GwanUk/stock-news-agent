import copy,hashlib,json
from pathlib import Path
pool=json.loads(Path('tmp/ownership-v19-new-pool.json').read_text(encoding='utf-8'))
aa={a['id']:a for row in pool for a in row['articles']}
cases=[
('bank-kb','105560','KB금융','f3e5109f51fad952',['상승 요인'],True,'KB 순익1조7723억·전년비5.1% 증가 전망, 컨센서스3.9% 미달. 합산7조2870억 또는 우리금융19% 감소를 KB 자체실적으로 쓰면 실패.'),
('bank-returns','105560','KB금융','d4420ec1257a35bf',['상승 요인'],True,'KB 7000억 하반기 매입소각, 올해 총환원3조7000억. 자금유입으로 해석 금지. 순익1조8434억은 전망. 신한·하나·우리 실적 귀속 금지.'),
('insurance-return','138040','메리츠금융지주','9c5b45719f03e3fd',['상승 요인'],True,'메리츠 최근3년 소각3조7191억, 올해8851억. 미래에셋생명1조246억·삼성화재6894억을 메리츠 금액으로 쓰지 않기. 자금 조달 아님.'),
('insurance-no-return','032830','삼성생명','9c5b45719f03e3fd',['판단 보류'],True,'삼성생명 3년간 소각0주. 타사의 소각을 삼성생명 주주환원 호재로 쓰면 실패. 약속 취소가 아닌 부재 사실만으로 방향 단정 불가.'),
('return-order','138040','메리츠금융지주','6cbe955bb3a3b62f',['상승 요인','판단 보류'],True,'메리츠 매수 신청2만7400주. 체결·소각 완료 아님. 자금조달 아님. 방향보다 신청/체결조건과 기업별수량 보존을 평가.'),
('competitor-contract','011070','LG이노텍','c39545003aa430f6',['판단 보류'],False,'3605억 공급계약과2028년 이익개선은 삼성전기. LG이노텍은 주가 비교뿐이므로 직접사업 분석에서 제외.')]
rows=[];labels=[]
for ident,code,name,aid,directions,related,criteria in cases:
    a=copy.deepcopy(aa[aid]);assert not a['prior_url_overlap'] and a['body_status']=='추출됨'
    a['relevant']=True
    rows.append({'name':ident,'stock':{'code':code,'name':name,'market':'KOSPI'},'articles':[a]})
    labels.append({'name':ident,'id':aid,'stock':name,'directions':directions,'related':related,'criteria':criteria,'url':a['url'],'title':a['title']})
Path('tmp/ownership-v19-holdout.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
Path('output/ownership-v19-holdout-labels.json').write_text(json.dumps(labels,ensure_ascii=False,indent=2),encoding='utf-8')
Path('output/ownership-v19-holdout-manifest.json').write_text(json.dumps({'code':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('app').glob('*.py')},'input_sha256':hashlib.sha256(Path('tmp/ownership-v19-holdout.json').read_bytes()).hexdigest(),'label_sha256':hashlib.sha256(Path('output/ownership-v19-holdout-labels.json').read_bytes()).hexdigest(),'unique_sources':len(set(l['url'] for l in labels)),'cases':len(labels),'prior_exact_url_overlap':False,'author':'assistant source-reviewed labels; not independent human ground truth','scope':'sources not used to edit app; frozen before first model evaluation; code must remain unchanged after this file'},indent=2),encoding='utf-8')
