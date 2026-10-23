import json
from pathlib import Path
from html import escape as e

def signature(r):
    return {"selection":{a["id"]:(a.get("relation"),bool(a.get("analysis_candidate")),a.get("duplicate_of"))
                         for a in r["articles"]},
            "findings":{f["article_id"]:f for f in r["findings"]}}

rows, summaries = [], []
for kind,name in [("동일 본문 · 순서 변경 포함","replay"),("실제 앱 · 새로 분석 2회","live")]:
    batches = json.loads(Path(f"output/stability-v8-{name}.json").read_text(encoding="utf-8"))
    for runs in batches:
        base = runs[0]
        selected = [a for a in base["articles"] if a.get("analysis_candidate")]
        supplier = [a for a in base["articles"] if a["id"] == "e1c890a0fe944379"]
        stable = all(signature(r)==signature(base) for r in runs[1:])
        assert stable, (name,base["stock"]["name"])
        assert selected, "Empty batches are not evidence of useful stable analysis"
        assert not any(a.get("analysis_candidate") for a in supplier)
        summary = {"kind":kind,"stock":base["stock"]["name"],"repeats":len(runs),
                   "selected":len(selected),"stable":stable,"supplier_present":bool(supplier),
                   "calls":[len(r["usage"]) for r in runs],
                   "reused":[r.get("reused_finding_count",0) for r in runs]}
        summaries.append(summary)
        rows.append(f"<tr><td>{kind}</td><td>{e(summary['stock'])}</td><td>{len(selected)}건</td>"
                    f"<td>{len(runs)}회 동일</td><td>{'제외 확인' if supplier else '이번 검색에 없음'}</td>"
                    f"<td>{' → '.join(map(str,summary['calls']))}</td></tr>")

html = """<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>공급업체 선별과 반복 판단 검증</title><style>
body{margin:0;background:#f5f5ef;color:#243e32;font:16px/1.7 'Malgun Gothic',sans-serif}
main{max-width:1100px;margin:auto;padding:40px 24px}h1{font-size:32px;letter-spacing:-1px}
table{width:100%;border-collapse:collapse;background:white}td,th{padding:14px;text-align:left;border-bottom:1px solid #dce4d8}
th{background:#e7eee5}.scroll{overflow:auto}.note{padding:20px;background:#fff8e9;border-left:3px solid #bd934c}
a{color:#237552}</style><main><p>2026.10.20 · 파이프라인 v8</p>
<h1>공급업체 뉴스는 구분하고,<br>같은 근거의 판단은 유지합니다.</h1>
<h2>공급업체 기사 선별</h2>
<p>기존 고객사·착공식 참석자로만 등장하는 기사와, 대상 기업의 신규 계약·공동투자·공급중단 기사를 구분합니다.
모델의 고객사 역할 판정도 본문 근거가 있어야 적용합니다. 장비기업 자체 증설 기사에 기존 고객사로만 등장하는 경우에는 별도의 보수적 규칙으로 분석 대상에서 제외합니다.
기사 원문은 추가 검색 결과에 남습니다.</p>
<h2>반복 판단 안정화</h2>
<p>종목, 기사 ID·제목·본문·발행일·URL, 모델, 분석 기준, 보완 공시를 기준으로 판단을 저장합니다.
같은 내용은 7일간 재사용하고 내용이나 기준이 바뀌면 다시 분석합니다. 검색 결과의 다른 기사나 나열 순서가 바뀌어도 해당 기사의 판단은 유지합니다.
일시적인 모델 호출·추가 검토 실패 결과는 확정 판단으로 저장하지 않습니다.</p>
<div class="scroll"><table><tr><th>검증 방식</th><th>종목</th><th>분석 대상</th><th>비교 결과</th><th>공급업체 기사</th><th>모델 호출 수</th></tr>
""" + "".join(rows) + """</table></div>
<p>고정 본문은 종목별 3회 평가했고 마지막 실행은 기사 순서를 바꿨습니다.
실제 앱은 종목별로 refresh=true 요청을 2회 보내 실행 결과 캐시를 건너뛰었습니다.
선별 상태와 기사별 방향·영향 수준·설명·인용 전체를 비교했습니다. 자동 테스트 38개 통과.</p>
<div class="note"><b>일관성과 정확성은 별개입니다.</b>
<p>이 결과는 모델을 매번 새로 호출해도 정답이 같다는 뜻이 아닙니다. 처음 검증을 통과한 판단을 재사용하여 제품의 반복 출력을 안정화한 것입니다.
첫 판단이 틀리면 그 오류도 유지될 수 있습니다. 본문·모델·분석 기준 변경이나 7일 경과 후에는 새 판단이 나올 수 있습니다.</p>
<p>첫 중간 평가에서 삼성전자 현장 방문이 고객사 기사로 잘못 분류되는 회귀를 발견해 본문 근거 검사를 추가했습니다.
최종 검증은 분석 대상이 실제로 남아 있는지도 확인했습니다. 공급업체의 모든 관계와 모든 사건을 판별하는 완성된 규칙은 아닙니다.</p></div>
<p>실제 기사 평가에 사용한 원문·기준은 이전 검증 자료와 동일합니다. 소표본 회귀 검증이며 일반적인 정확도 평가가 아닙니다.
원시 결과: stability-v8-replay.json / stability-v8-live.json. 비교 요약: stability-v8-summary.json.</p></main></html>"""
Path("output/stability-v8-validation-report.html").write_text(html,encoding="utf-8")
Path("output/stability-v8-summary.json").write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(summaries,ensure_ascii=False,indent=2))
