import hashlib, html, itertools, json
from pathlib import Path
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def h(s):return html.escape(str(s))
labels=read('output/final-holdout-labels.json')['labels']
results=read('output/final-holdout-results.json')
controlled={r['result']['stock']['code']:r for r in results if 'result' in r}
replays={r['stock']['code']:r for r in results if 'articles' in r}
manifest=read('output/final-holdout-manifest.json')
assert manifest['code']=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in manifest['code']}
assert manifest['labels_sha256']==hashlib.sha256(Path('output/final-holdout-labels.json').read_bytes()).hexdigest()

def root(a,items):
    seen=set()
    while a.get('duplicate_of') in items and a['id'] not in seen:
        seen.add(a['id']); a=items[a['duplicate_of']]
    return a
notes={
'1aacecd9812826c9':'누락: 대상 기업의 사고 보고 수가 명시돼 있지만 단순 언급으로 분류. 법적 확정 여부 제한을 붙여 다룰 관련 위험 기사다.',
'e604df4aba81f7aa':'제안·미선정·승인 조건은 유지. 다만 수집 본문에 숫자가 빈 문장이 있어 원문 품질은 통과로 볼 수 없다. 어디서 손실됐는지는 추가 확인 필요.',
'4af0447258285598':'수주 증가와 우선협상·향후 목표를 구분해 보존.',
'2b9713365e80651f':'국가별 점유율과 4분기 전망 유지. 통제 묶음에서는 3건을 1건으로 묶었지만 실제 검색 묶음 재생에서는 3건을 별도 선택.',
'33b8c8527cec848a':'7월 일본·1분기 아시아·브라질 사립 시장 범위 유지.',
'97ca0c361b8b184e':'매입 완료와 4분기 목표·환원 방식 미정은 유지. 해석 문구의 “실적 개선”은 목표와 구별해 더 구체화할 여지가 있음.',
'4ffe0a6a21dd75a5':'개발 계획과 2029년 임상 목표 유지. 동일 발표 중복은 통제 묶음에서 놓침.',
'5298b18f9a4ca5c7':'2027년 전임상·2029년 임상 목표 유지. 동일 발표 중복은 통제 묶음에서 놓침.',
'7542387552d4897b':'중대 오류: LG화학 분석에서 OCI의 흑자 전망·증설을 주된 사실로 고르고 상승 판단. LG화학 기소 사실은 보완 문단에 밀림. 원문 일치 검증과 재검토도 통과함.',
'6e1f7bb8b9a02e71':'기소 혐의·거래액/과징금 구별·충당부채 인식 요건 유지. 부과시점 단정 없음.',
'b056714c2ca0f54b':'기소 혐의와 전체 거래 규모 유지. 원문 자체 연도·기간 서술의 정합성은 별도 사실확인 대상이며 이 시험은 보도 사실의 진실성을 인증하지 않음.',
'29594ad0bcb5877c':'회사 평가 및 상업 활용 허용 범위 유지. 매출 확정으로 바꾸지 않음. 통제 묶음에서 중복 미검출.',
'b811d436148bbc30':'오픈소스 공개의 개발 진전 판단. 같은 사건 보도 중복 미검출.',
'b078e23f20575391':'증권사 전망·시장 기대치 대비 하회·전년비 증가가 함께 보존됨. 실제 검색 재생에서는 같은 보고서의 다른 기사가 대표가 됨.',
'06af1b63c8ed85a5':'설명 오류: 분할 후 추진 및 FCF 조건은 원문 그대로 남지만, 주주환원을 자금 조달·투자 재원 확보로 해석. 상승 라벨 일치만으로 성공 처리하면 안 됨.'}
items=[]
for l in labels:
    r=controlled[l['stock_code']]['result']; aa={a['id']:a for a in r['articles']}; a=aa[l['id']]; representative=root(a,aa)
    ff={f['article_id']:f for f in r['findings']}; f=ff[representative['id']]
    replay=replays[l['stock_code']]; ra={a['id']:a for a in replay['articles']}; pa=ra.get(l['id'])
    if not pa: stage='検索上位20件になし' # replaced below for Korean display
    elif not pa.get('body_status'): stage='본문 수집 8건 한도 밖'
    elif pa.get('body_status')!='추출됨':stage='본문 추출 실패/부족'
    elif root(pa,ra).get('analysis_candidate'):stage='분석 대상 또는 대표 기사로 포함'
    else:stage='관련성·사업 사건 판정에서 제외'
    if stage=='検索上位20件になし':stage='기본 검색 상위 20건에 없음'
    items.append({**l,'stock_name':r['stock']['name'],'relation':a.get('relation'),'selected':bool(a.get('analysis_candidate')),'covered':bool(representative.get('analysis_candidate')),'representative':representative['id'],'direction_actual':f['direction'],'reason':f['reason'],'counterpoint':f['counterpoint'],'production_stage':stage,'note':notes.get(l['id'],'대상 기업의 사업 분석에서 제외한 결과가 평가 기준과 일치.'),'locked_quote_match': all(e['quote'] in next(x for x in controlled[l['stock_code']]['extracted'] if x['id']==representative['id']).get('body','') for e in f.get('evidence',[]))})
positive=[i for i in items if i['useful']];negative=[i for i in items if not i['useful']]
strict=[i for i in items if i['selected'] and i['direction']]
dups=[]
for code in controlled:
    group=[i for i in items if i['stock_code']==code and i['useful']]
    for a,b in itertools.combinations(group,2):
        if a['event']==b['event']:
            dups.append({'stock':code,'left':a['id'],'right':b['id'],'grouped':a['representative']==b['representative']})
separate_specs=[('042660','e604df4aba81f7aa','4af0447258285598'),('068270','2b9713365e80651f','33b8c8527cec848a'),('068270','2b9713365e80651f','97ca0c361b8b184e'),('051910','4ffe0a6a21dd75a5','6e1f7bb8b9a02e71'),('035720','29594ad0bcb5877c','b078e23f20575391')]
separate=[]
for code,a,b in separate_specs:
    lookup={i['id']:i for i in items if i['stock_code']==code}
    separate.append({'stock':code,'left':a,'right':b,'separate':lookup[a]['representative']!=lookup[b]['representative']})
summary={'assignments':len(items),'unique_sources':manifest['unique_urls'],'industries':4,'related_covered':[sum(i['covered'] for i in positive),len(positive)],'negative_excluded':[sum(not i['covered'] for i in negative),len(negative)],'strict_direction_selected_only':[sum(i['direction']==i['direction_actual'] for i in strict),len(strict)],'duplicate_pairs':[sum(i['grouped'] for i in dups),len(dups)],'distinct_pairs':[sum(i['separate'] for i in separate),len(separate)],'known_related_production_covered':[sum(i['production_stage']=='분석 대상 또는 대표 기사로 포함' for i in positive),len(positive)],'selected_quote_integrity':[sum(i['locked_quote_match'] for i in items if i['selected']),sum(i['selected'] for i in items)],'production_code_unchanged':True,'overall':'보완 필요 — 최종 통과 아님','excluded_invalid_run':'final-holdout-invalid-harness-results.json: missing collection eligibility flag; excluded in full; labels and app code unchanged'}
Path('output/final-holdout-audit.json').write_text(json.dumps({'summary':summary,'items':items,'duplicate_pairs':dups,'distinct_pairs':separate},ensure_ascii=False,indent=2),encoding='utf-8')
cards=''.join(f'<div class="metric"><b>{h(v[0])} / {h(v[1])}</b><span>{h(k)}</span></div>' for k,v in [('관련 기사 포함',summary['related_covered']),('제외 대조군',summary['negative_excluded']),('선택 후 방향 일치',summary['strict_direction_selected_only']),('동일 사건 중복 쌍',summary['duplicate_pairs']),('별개 사건 분리',summary['distinct_pairs']),('실제 수집 흐름 포함',summary['known_related_production_covered'])])
rows=''.join(f'<tr><td>{h(i["stock_name"])}</td><td><a href="{h(i["url"])}">{h(i["title"])}</a></td><td>{h(i["relation"])}<br>{"대표/분석" if i["selected"] else "중복으로 포함" if i["covered"] else "제외"}</td><td>{h(i["direction_actual"])}<br><small>기준: {h(i["direction"] or "방향 점수 제외")}</small></td><td>{h(i["production_stage"])}</td><td>{h(i["note"])}</td></tr>' for i in items)
details=''.join(f'<details><summary>{h(i["stock_name"])} · {h(i["title"])}</summary><p><b>사전 조건 기준</b> {h(i["conditions"])}</p><p><b>판정 검토</b> {h(i["note"])}</p><p><b>대표 기사 ID</b> {h(i["representative"])}</p><p class="quote">{h(i["reason"])}<br>{h(i["counterpoint"])}</p></details>' for i in items if i['selected'])
page=f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>새 기사 최종 검증 · 보완 필요</title><style>body{{background:#faf9f6;color:#292929;font:15px/1.7 system-ui,sans-serif;max-width:1280px;margin:48px auto;padding:0 24px}}h1,h2{{font-family:Georgia,serif}}h1{{font-size:34px}}small,.muted{{color:#666}}.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.metric,details,.box{{border:1px solid #d5d3ce;padding:20px;background:#fff}}.metric b{{display:block;font-size:28px}}.metric span{{color:#555}}table{{width:100%;border-collapse:collapse;font-size:13px}}td,th{{padding:12px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}}a{{color:inherit}}.scroll{{overflow:auto}}details{{margin:10px 0}}summary{{cursor:pointer;font-weight:600}}.quote{{white-space:pre-wrap;font-size:13px}}@media(max-width:700px){{.metrics{{grid-template-columns:1fr 1fr}}body{{padding:0 16px}}}}</style>
<p class="muted">2026.10.21 · 고정 표본 / 현재 앱 코드 유지 / 운영 이력 변경 없음</p><h1>새 기사로 확인한 결과: 보완 필요</h1><p>조선·바이오·화학·인터넷 4개 업종, 실제 원문 20개를 종목별 21개 사례로 평가했습니다. 기존 평가 자료와 정확히 같은 URL은 제외했습니다. 제목이 다른 동일 사건은 중복 검증용으로 의도적으로 포함했습니다.</p><div class="metrics">{cards}</div>
<h2>가장 중요한 발견</h2><div class="box"><ol><li><b>기업 귀속 오류:</b> LG화학 분석에 OCI의 흑자·증설이 주된 긍정 근거로 사용됐습니다. 원문 인용이 정확해도 대상 기업이 틀리면 오판입니다.</li><li><b>영향 유형 오류:</b> 카카오의 자사주 매입·소각 계획을 자금 조달·투자 재원 확보로 설명했습니다. 상승/하락 라벨만 평가하면 놓치는 오류입니다.</li><li><b>관련 기사 누락:</b> 한화오션 사고 보고 통계를 단순 언급으로 제외했습니다. LG화학 기소 관련 기사는 검색 상위 20건 또는 본문 8건 한도에서 빠졌습니다.</li><li><b>중복 판정이 입력 묶음에 의존:</b> 통제 표본에서는 셀트리온 3건이 묶였지만 실제 검색 묶음에서는 별도로 선택됐습니다. LG화학·카카오는 반대 패턴이었습니다. 같은 사건 식별 기준이 아직 충분히 안정적이지 않습니다.</li><li><b>본문 품질:</b> 한화오션 그리스 제안 기사의 수집 본문은 수량 부분이 빈 문장으로 들어왔습니다. ‘추출됨’ 상태만으로 정상 본문으로 볼 수 없습니다. 원인 위치는 미확정입니다.</li></ol></div>
<h2>조건 보존과 설명 검토</h2><p>선택된 14건의 인용은 수집 본문과 일치했습니다. 수주 확정/우선협상/향후 목표, 임상 예정 연도, 과징금과 거래액 구별, 증권사 전망 및 FCF 조건은 확인한 사례에서 유지됐습니다. 다만 이는 <b>전체 조건의 완전성이나 원문 진실성 검증이 아닙니다.</b> OCI 사실 귀속과 자사주 영향 유형 오류 때문에 설명 전체를 통과 처리하지 않았습니다.</p>
<h2>검증 방법과 범위</h2><ul><li>사전 원문 검토로 기준을 고정한 뒤 선택 → 사실 추출 → 해석 → 검증 → 재검토를 실행했습니다. 모든 평가 기준은 assistant 작성이며 독립 전문가 정답은 아닙니다.</li><li>통제 표본은 모든 본문을 제공해 분석 단계 자체를 검사했습니다. 실제 수집 재생은 당시 저장한 5종목 × 20건 검색 목록에 현재 앱의 제목/설명 선별, 본문 최대8건, 최종 최대5건 로직을 그대로 적용했습니다. 재생 단계는 수집·선별만 확인했으며 모든 결과에 방향 분석을 다시 돌리지는 않았습니다.</li><li>방향 8/9는 엄격한 방향 기준을 미리 정한 사례 중 실제 선택된 대표 기사만의 점수입니다. 누락된 한화오션 위험 기사 1건과 탐색적 사례는 분모에 넣지 않았습니다. 소규모 선택 표본으로 전체 정확도를 주장할 수 없습니다.</li><li>실제 수집 포함 12/17은 이미 알고 있는 관련 기사 17건이 같은 기사 또는 대표 기사로 들어왔는지의 확인입니다. 인터넷 전체 뉴스 재현율이 아닙니다. 2건은 검색에는 있었으나 선별/수집에서 제외, 3건은 해당 기본 검색 목록에 없었습니다.</li><li>중복 3/5는 동일 사건 기사 쌍 기준입니다. 서로 다른 사건의 사전 대조 5쌍은 모두 분리됐습니다. 모든 가능한 기사 조합의 오병합률은 계산하지 않았습니다.</li><li>최초 시험은 평가 도구의 relevant 표시 누락으로 무효 처리했습니다. 평가 도구만 수정하고 동일 기준으로 다시 실행했습니다. 앱 소스 해시 및 평가 기준 해시가 변하지 않았음을 확인했습니다. 무효 결과도 별도 보관했습니다.</li><li>기존 URL 중복은 로컬 과거 평가 자료와 대조했지만 과거에 쓴 모든 사건과의 의미적 독립성을 완전히 증명한 것은 아닙니다. 새 URL/본문 홀드아웃입니다.</li></ul>
<h2>기사별 결과</h2><div class="scroll"><table><thead><tr><th>종목</th><th>원제목 · 출처</th><th>선별</th><th>방향</th><th>실제 수집 흐름</th><th>검토</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>다음 수정 우선순위</h2><ol><li>사실마다 대상 기업/행위 주체를 고정하고, 다른 회사의 실적을 방향 근거로 선택하지 못하게 검증.</li><li>주주환원과 자금 조달을 별도 영향 유형으로 분리하고 해석 문구 검증.</li><li>중복으로 본문 예산을 소모한 뒤 다음 검색 후보를 보충. 다기업 규제/사고 기사에서 대상 기업의 직접 당사자성을 확인.</li><li>사건 식별값(기업·사건·시점·상대방·단계)을 기준으로 중복 처리를 일관되게 적용.</li><li>숫자·문장 손상 탐지와 원문 재확인 경로 마련.</li></ol>
<h2>선택된 기사: 조건과 실제 출력</h2>{details}<p class="muted">검증 자료: final-holdout-manifest.json · final-holdout-labels.json · final-holdout-results.json · final-holdout-audit.json. 이번 요청은 검증으로 마무리하며 운영 코드 수정은 하지 않았습니다.</p></html>'''
Path('output/final-holdout-validation-report.html').write_text(page,encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
