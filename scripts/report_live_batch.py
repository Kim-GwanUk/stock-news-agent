"""Inspect saved production API runs against the exact collected bodies."""
import json
from collections import Counter
from html import escape as e
from pathlib import Path
from app import analysis

notes = {
    ("005930", "79b8e2feb24a554c"): "선별 오류. 핵심 사건은 SK하이닉스이며 삼성전자는 비교 사례다. 관련성 설명도 직접 관련 없다고 적었는데 선택됐다. 후속 방향 검토가 보류로 차단했다.",
    ("000660", "79b8e2feb24a554c"): "대상 기업 관련성은 적절하다. 다만 하락 근거는 실적 악화보다 예상 수급 위험이다. 자사주 소각과 반대 해석도 있어 사업 영향과 시장 수급을 구분할 필요가 있다.",
    ("000660", "51c6365d8f37007f"): "관련성은 적절하다. 금융지원은 확인되지만 대상 기업의 직접 실적 효과는 미확인이다. 보류는 설명 가능하나 간접 긍정 요인을 별도로 보여주지 못한다.",
    ("000660", "3b6ee9f2b3f3eedc"): "기업 자체 사회공헌이므로 관련 뉴스다. 사업 실적 근거 없이 호재로 올리지 않은 것은 적절하다.",
    ("000660", "00a2ed683b25921b"): "관련성은 적절하다. 상장 조건 미확정에 따른 보류는 가능하지만, 설명의 '구체적 진행 사항이 없다'는 표현은 본문의 프리IPO 진행·계열사 출자 약정을 충분히 반영하지 못한다.",
    ("005930", "924dd0e2d8d9e9ac"): "현장 방문은 관련 뉴스이나 신규 투자 확정이 아니므로 보류가 적절하다. 다른 방문 기사와 동일 사건이다.",
    ("005930", "a888489b7d3f479e"): "방문·행정 준비를 실적 호재로 오인하지 않았다. 동일 사건 중복이 분석 자리를 차지한다.",
    ("005930", "36fc81dc832b0cb8"): "기업별 증권사 전망으로 관련성은 있으나 확정 실적과 구분해야 한다. 동일 기사를 SK하이닉스에서는 시장·업종 맥락으로 제외해 기준이 일관되지 않다.",
    ("000660", "36fc81dc832b0cb8"): "삼성전자와 함께 핵심 분석 대상인데 이 종목에서만 시장·업종 맥락으로 제외됐다. 선별 기준의 일관성을 개선해야 한다.",
}
sections, summaries = [], []
for code in ("000660", "005930"):
    r = json.loads(Path(f"output/live-batch-{code}.json").read_text(encoding="utf-8"))
    cached = json.loads(Path(f"tmp/live-batch-bodies-{code}.json").read_text(encoding="utf-8"))
    selected = [a for a in r["articles"] if a.get("analysis_candidate")]
    findings = {f["article_id"]: f for f in r["findings"]}
    counts = Counter(findings[a["id"]]["direction"] for a in selected)
    errors = analysis.validate({"findings": r["findings"]}, cached["articles"], [])
    quote_count = sum(len(findings[a["id"]]["evidence"]) for a in selected)
    summary = {"stock":r["stock"]["name"],"run_id":r["run_id"],"as_of":r["as_of"],
               "search_results":len(r["articles"]),
               "extracted":sum(a.get("body_status")=="추출됨" for a in cached["articles"]),
               "selected":len(selected),"directions":dict(counts),"validation_errors":errors,
               "quotes":quote_count,"llm_calls":len(r["usage"]),"corrections":r["correction_count"]}
    summaries.append(summary)
    rows = []
    for a in r["articles"]:
        f = findings[a["id"]]
        note = notes.get((code,a["id"]), "본문 확보 범위 내 선별 결과를 확인함." if a.get("body_status")=="추출됨" else "본문 검토 대상이 아니거나 추출 실패. 제외가 정확하다고 판정할 수 없음.")
        rows.append(f"<tr><td><a href='{e(a['url'],quote=True)}'>{e(a['title'])}</a></td>"
                    f"<td>{e(a.get('body_status','미확보'))}<br>{e(a.get('relation',''))}</td>"
                    f"<td>{e(f['direction']) if a.get('analysis_candidate') else '분석 제외'}</td>"
                    f"<td>{e(note)}</td></tr>")
    sections.append(f"<h2>{e(r['stock']['name'])}</h2><p>{e(r['as_of'])} · 검색 20건 · 본문 확보 {summary['extracted']}건 · 선택 4건 · "
                    f"상승 {counts['상승 요인']} / 하락 {counts['하락 요인']} / 보류 {counts['판단 보류']} · 모델 호출 {summary['llm_calls']}회</p>"
                    "<div class='scroll'><table><tr><th>원제목·출처</th><th>본문 / 관련성</th><th>분석 결과</th><th>검토 의견</th></tr>"
                    +"".join(rows)+"</table></div>")
Path("output/live-batch-summary.json").write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding="utf-8")
html = """<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>실제 앱 다기사 분석 점검</title><style>
body{background:#f5f5ef;color:#253c32;font:15px/1.7 'Malgun Gothic',sans-serif;margin:0}
main{max-width:1200px;margin:auto;padding:40px 24px}h1{font-size:32px;letter-spacing:-1px}
table{border-collapse:collapse;width:100%;background:white}td,th{padding:14px;border-bottom:1px solid #dde4da;text-align:left}
th{background:#e7eee5}td:first-child{width:32%}td:nth-child(2),td:nth-child(3){min-width:90px}
a{color:#237552}.scroll{overflow:auto}.note{background:#fff8e9;padding:20px;border-left:3px solid #be9347}h2{margin-top:40px}
</style><main><p>2026.10.20 · 운영 파이프라인 v6</p><h1>실행은 정상, 선별·설명 품질은 보완 필요</h1>
<p>등록된 SK하이닉스와 삼성전자에 앱이 사용하는 실제 /analyze API를 각각 실행했습니다.
각 종목 안에서는 여러 기사를 함께 분석하고, 두 종목은 앱의 동시 실행 제한에 따라 순서대로 처리했습니다.
결과는 실제 분석 이력에 저장됐습니다. 별도 합성 기사나 과거 평가 기사를 넣지 않았습니다.</p>
<div class="note"><b>이번 결과: 선택 8건 중 상승 0 · 하락 1 · 보류 7</b>
<p>삼성전자에 경쟁사 중심 기사가 포함되는 오류 1건, 동일 기사에 대한 종목별 관련성 기준 차이,
같은 현장 방문의 중복 선정을 발견했습니다. 긍정 기사 사례가 나오지 않아 이번 실행만으로 긍정 판단 성능을 검증했다고 할 수 없습니다.</p></div>
<h2>확인한 것</h2><ul><li>검색 결과는 종목별 20건, 합계 40개 기사-종목 쌍입니다. 두 종목에 겹치는 기사가 있어 고유 기사 40건은 아닙니다.</li>
<li>본문 확보는 SK하이닉스 7건, 삼성전자 6건입니다. 각 종목 최대 8건만 본문 수집하므로 미확보 기사의 관련성 누락률은 알 수 없습니다.</li>
<li>선택된 8건의 남아 있는 인용문은 수집 본문과 대조했고 앱의 인용·수치 검증 오류는 없었습니다. 인용 일치가 해석의 정확성을 보장하지는 않습니다.</li>
<li>두 실행 모두 수정 재시도 0회, 모델 호출 각 3회, 반환 경고 없음. 경고가 없어도 의미상 오류는 발생했습니다.</li></ul>
<h2>우선 개선할 부분</h2><ol><li>핵심 사건의 주체와 대상 종목을 대조하고 관련성 분류·설명의 모순을 차단하기.</li>
<li>동일 사건 재보도를 묶어 분석 자리를 확보하고, 본문 미확보와 무관 판정을 구분하기.</li>
<li>확인된 사실·전망·간접 영향·시장 수급을 구분하기. 보류하더라도 이미 확인된 진행 사항을 없다고 설명하지 않기.</li></ol>
""" + "".join(sections) + """<p>검토는 수집된 본문과 모델 결과를 비교한 assistant의 정성 평가입니다.
기사 사실 자체를 공시로 교차 검증하거나 사람 합의 정답·미래 수익률로 평가하지 않았습니다.
이번 턴은 검증이며 분석 로직은 수정하지 않았습니다. 원시 결과: live-batch-000660.json / live-batch-005930.json.</p></main></html>"""
Path("output/live-batch-validation-report.html").write_text(html,encoding="utf-8")
print(json.dumps(summaries,ensure_ascii=False,indent=2))
