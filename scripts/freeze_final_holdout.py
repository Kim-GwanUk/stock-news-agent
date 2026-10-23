import copy, hashlib, json
from pathlib import Path

def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
pool=read('tmp/final-holdout-pool.json')
extra=read('tmp/final-holdout-extra.json')
kakao=read('tmp/final-holdout-kakao.json')
index={a['id']:a for g in pool+extra+kakao for a in g['articles']}
# Labels written from source bodies before any selection/direction output is run.
# id, useful business item, strict direction (None = exploratory), event, required qualifications
specs=[
('042660','한화오션','조선',[
('1aacecd9812826c9',True,'하락 요인','safety','21개월 누적 보고 3건·사망 3명. 법적 확정 중대재해 건수와 같지 않음. 최근 새 사고나 확정 처벌로 표현 금지.'),
('e604df4aba81f7aa',True,None,'greece','제안 단계, 최종 기종 미선정. 무기체계·수출 승인 필요. 원문 추출에서 숫자가 사라져 수량 검증 불가.'),
('4af0447258285598',True,'상승 요인','orders','9월 말 수주 77억1000만 달러, 전년 연간 63억2000만 대비. 태국은 우선협상, 나미비아 30억 달러는 목표. 경쟁사 수주를 귀속시키지 않음.'),
('18c8bec70d15f978',False,None,'visit','학생 견학·취업 멘토링. 사업 계약 없음.'),
('ba7a9bf261c55aba',False,None,'competitor','미쓰비시 사업. 한화오션은 경쟁 배경. 한화오션 신규 수주로 해석 금지.')]),
('068270','셀트리온','바이오',[
('658e7520bf748797',True,'상승 요인','europe','네덜란드 58%는 확보 공급 물량, 스페인 90%는 7월 점유율. 4분기 성장은 전망, 매출 실현 완료 아님.'),
('fdd6a82b298df883',True,'상승 요인','europe','공급·처방 확대가 실제 매출 반영의 전제. 4분기 성장은 계획.'),
('2b9713365e80651f',True,'상승 요인','europe','동일 유럽 채널 확대 발표. 점유율 국가·시장 범위 유지.'),
('33b8c8527cec848a',True,'상승 요인','asia','일본 7월 램시마 48%, 아시아 1분기, 브라질 사립 시장 약60% 등 시점과 범위를 전체 세계 점유율로 바꾸지 않음.'),
('97ca0c361b8b184e',True,'상승 요인','buyback','이번 1000억 매입 완료, 연간 누적4000억. 4분기6000억은 목표. 순이익 약1/3 환원 원칙, 방식은 검토.'),
('ca8f3642945bfa8d',False,None,'other_bio','삼성바이오에피스 소식, 셀트리온 아님.')]),
('051910','LG화학','화학',[
('4ffe0a6a21dd75a5',True,None,'ai_drug','2027년 전임상·2029년 임상 계획. 승인·상업화·매출 확정 아님.'),
('5298b18f9a4ca5c7',True,None,'ai_drug','동일 컨퍼런스 발표. 2027년 전임상·2029년 임상 목표.'),
('7542387552d4897b',True,'하락 요인','oci_indictment','기사 주체는 OCI지만 LG화학도 명시된 기소 당사자. 16조3961억은 6개사 거래액, LG화학 과징금 아님. OCI 흑자를 LG화학 실적으로 해석 금지.'),
('6e1f7bb8b9a02e71',True,'하락 요인','fine_followup','과징금 금액·부과 시점 미정. 충당부채 인식 요건 충족 시 손익 부담 가능. 16조3961억은 거래액. 기소는 유죄 확정 아님.'),
('b056714c2ca0f54b',True,'하락 요인','indictment','6개 법인·37명 기소 혐의. 16조3961억은 전체 담합 관련 거래 규모. 확정 벌금 아님.')]),
('035720','카카오','인터넷',[
('b811d436148bbc30',True,None,'vision','오픈소스 공개. 회사 벤치마크 평가, 상업 활용 허용은 유료 매출 발생 아님.'),
('29594ad0bcb5877c',True,None,'vision','동일 비전 인코더 2종 공개. 성능 주장은 회사 평가 기준.'),
('b078e23f20575391',True,'하락 요인','forecast','증권사 3분기 영업익2246억 전망, 컨센서스10.9% 하회 예상, 전년비0.4% 증가. 확정 실적 아님.'),
('06af1b63c8ed85a5',True,'상승 요인','return','분할 이후3000억 매입·소각 추진. 카카오X 배당·투자차익30%, 카카오AI FCF20~35%, 전년비50% 이상 늘 때 최대40%. 완료 아님.'),
('ca8f3642945bfa8d',False,None,'other_bio','삼성바이오에피스 소식, 카카오 아님.')])]
groups=[]; labels=[]
for code,name,sector,cases in specs:
    articles=[]
    for ident,useful,direction,event,conditions in cases:
        a=copy.deepcopy(index[ident]); assert not a['prior_url_overlap']
        articles.append(a)
        labels.append(dict(stock_code=code,id=ident,title=a['title'],url=a['url'],useful=useful,direction=direction,event=event,conditions=conditions))
    groups.append(dict(name='controlled-'+code,stock=dict(code=code,name=name,market='KOSPI'),sector=sector,articles=articles))
Path('tmp/final-holdout-frozen.json').write_text(json.dumps(groups,ensure_ascii=False,indent=2),encoding='utf-8')
Path('output/final-holdout-labels.json').write_text(json.dumps({'label_author':'assistant source review; not independent human ground truth','labels':labels},ensure_ascii=False,indent=2),encoding='utf-8')
hashes={str(p).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('app').glob('*.py')}
Path('output/final-holdout-manifest.json').write_text(json.dumps({'code':hashes,'inputs_sha256':hashlib.sha256(Path('tmp/final-holdout-frozen.json').read_bytes()).hexdigest(),'labels_sha256':hashlib.sha256(Path('output/final-holdout-labels.json').read_bytes()).hexdigest(),'sample_assignments':len(labels),'unique_urls':len(set(x['url'] for x in labels)),'prior_exact_url_overlap':False,'scope':'new URL/body sample; same-event independence not exhaustively proven; recent news, no claim of statistical population accuracy'},indent=2),encoding='utf-8')
print('frozen',len(labels),'assignments')
