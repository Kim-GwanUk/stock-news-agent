"""Reproducible counts plus explicitly post-hoc source review."""
import json
from collections import Counter
from html import escape as e
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.news_selection import newest_first

results = []
for prefix in ("latest-v14", "latest-v14-negative"):
    results += json.loads(Path(f"output/{prefix}-results.json").read_text(encoding="utf-8"))

notes = {
    "f68acfe07a3cbf60": "선별 오류: 직원 개인의 외부 강연 참여를 삼성전자 핵심 사건으로 취급했다. 최종 방향은 보류여서 호재로 확대하지는 않았다.",
    "6139bc5ed466c939": "선별 경계: 업종 법안 논의와 개별 기업의 직접 사건을 구별할 필요가 있다. 최종 분석은 기업별 사업 영향 불명확으로 보류했다.",
    "0352da71fc90df29": "선별 경계: 보유 지분·평가액 기사가 사업 영향 분석 자리를 사용했다. 최종 사업 방향 보류는 타당하다.",
    "3ee76eb041af2dc4": "상승 방향의 근거는 있으나 증권사 추정이다. 설명의 '이로 인해'는 계약 확보가 가격 상승을 유발한다는 인과를 추가한다. 영향 '높음'도 추가 검토가 필요하다.",
    "8ef4addd2cc0e6d1": "설명 오류: 원문의 내년 실증 계획을 매출·이익 반영 시점으로 확대했다. 개발 진전에 따른 긍정 가능성과 실적 실현 시점을 구별해야 한다.",
    "227695bed78dd033": "설명 오류: 내년 실증을 근거로 매출·이익 가능 시점을 지정했다. 같은 자율주행 실증 사건의 다른 기사도 함께 선택돼 사건 중복이 남았다.",
    "c1d282bf7a433297": "하락 요인 확인 실패: 본문에 전년 대비 영업이익 감소와 후속 수주 지연이 있지만 최종 인용·분석 검증을 통과하지 못해 보류됐다. 인수 소식도 섞인 복합 기사다. 정확한 실패 단계는 추가 추적이 필요하다.",
    "3c53e05a76b9650b": "방향 분석 미완료: 사업 양수도 계약과 향후 승인 조건이 있는 본문을 확보했으나 최종 보류됐다. 본문을 못 읽은 경우와 분석 검증 실패를 안내에서 구분할 필요가 있다.",
}
summary, cards = [], []
comparison = []
for result in results:
    articles = result["articles"]
    chosen = {a["id"] for a in articles if a.get("analysis_candidate")}
    findings = {f["article_id"]:f for f in result["findings"]}
    counts = Counter(findings[aid]["direction"] for aid in chosen)
    eligible = [a for a in articles if a.get("relation")=="직접 관련" and
                a.get("body_status")=="추출됨" and not a.get("duplicate_of") and not a.get("market_roundup")]
    expected = {a["id"] for a in sorted(eligible, key=newest_first)[:5]}
    assert chosen == expected
    old = {a["id"] for a in sorted(eligible,key=lambda a:(a.get("published",""),a["id"]))[:5]}
    comparison.append({"stock":result["stock"]["name"], "latest_selection_matches":True,
                       "newly_selected":[a["title"] for a in articles if a["id"] in chosen-old],
                       "no_longer_selected":[a["title"] for a in articles if a["id"] in old-chosen]})
    summary.append({"stock":result["stock"]["name"],"search":len(articles),
        "bodies":sum(a.get("body_status")=="추출됨" for a in articles),
        "selected":len(chosen), "directions":dict(counts)})
    items = []
    for a in articles:
        f = findings[a["id"]]
        detail = ""
        if a["id"] in chosen:
            detail = f"<p>{e(f['reason'])}</p><p class='muted'>{e(f['counterpoint'])}</p>"
        if a["id"] in notes:
            detail += f"<p class='issue'>{e(notes[a['id']])}</p>"
        items.append(f"<details {'open' if a['id'] in chosen else ''}><summary>"
            f"{'분석' if a['id'] in chosen else '제외/미확인'} · {e(a['title'])}</summary>"
            f"<p class='muted'>{e(a['published'])} · {e(a.get('relation','미확인'))} · "
            f"{e(a.get('body_status','미확보'))} · {e(f['direction'])}</p>"
            f"<a href='{e(a['url'],quote=True)}'>기사 원문</a>{detail}</details>")
    cards.append(f"<section><h2>{e(result['stock']['name'])}</h2>{''.join(items)}</section>")

record = {"summary":summary,"selection_comparison":comparison,"post_hoc_review_notes":notes,
          "accuracy_not_estimated":True,"selection_assigned_by_actual_pipeline":True,
          "tests_passed":81}
Path("output/latest-v14-review.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
table = "".join(f"<tr><td>{e(r['stock'])}</td><td>{r['search']}</td><td>{r['bodies']}</td>"
                f"<td>{r['selected']}</td><td>{r['directions'].get('상승 요인',0)}</td>"
                f"<td>{r['directions'].get('하락 요인',0)}</td><td>{r['directions'].get('판단 보류',0)}</td></tr>" for r in summary)
changes = "".join(f"<li>{e(c['stock'])}: 새로 포함 — {e(' / '.join(c['newly_selected']) or '변동 없음')}"
                  f"; 분석 한도로 제외 — {e(' / '.join(c['no_longer_selected']) or '변동 없음')}</li>" for c in comparison)
html = """<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>최신순 선택 · 실제 뉴스 전체 흐름 검증 v14</title><style>
body{margin:0;background:#f3f5f2;color:#233a30;font:15px/1.8 'Malgun Gothic',sans-serif}
main{max-width:1100px;margin:auto;padding:40px 24px}h1{font-size:32px;line-height:1.45}
h2{font-size:23px}section{margin-top:36px}a{color:#246c51}table{width:100%;border-collapse:collapse;background:white}
td,th{padding:12px;border-bottom:1px solid #dbe3dc;text-align:left}details{background:white;padding:18px;margin:10px 0;border:1px solid #dbe3dc;border-radius:10px}
summary{cursor:pointer;font-weight:bold}.muted{color:#64756a}.issue,.notice{background:#fff0d7;padding:14px;border-left:3px solid #b5893c}
</style><main><p class="muted">천기누설 · 2026-10-21 · 파이프라인 v14</p>
<h1>최신순 선택은 수정했습니다.<br>전체 뉴스 분석에는 남은 오류가 확인됐습니다.</h1>
<p>중복 묶음 처리 후 최신 발행 시각 순으로 최대 5건을 선택합니다. 시간대가 다른 날짜는 실제 시각으로 비교하며
날짜가 없거나 잘못된 기사는 뒤로 보냅니다. 뉴스·선별 캐시와 분석 이력 버전을 갱신했습니다. 자동 테스트 81개 통과.</p>
<h2>실제 수집부터 분석까지</h2><p>삼성전자·현대차·에코프로비엠을 먼저 평가하고, 하락 요인 사례 확인을 위해 현대로템을 추가했습니다.
종목 등록이나 운영 분석 이력은 바꾸지 않았습니다. 수집·선별·분석 캐시를 모두 끄고 실제 LangGraph를 실행했습니다.
평가 도중 앱의 핵심 코드는 변경하지 않았으며 소스·실행 코드 해시를 보존했습니다.</p>
<table><tr><th>종목</th><th>검색</th><th>본문 확보</th><th>분석 대상</th><th>상승</th><th>하락</th><th>보류</th></tr>""" + table + """</table>
<p>총 80건 중 본문 29건을 확보하고 13건을 분석 대상으로 선정했습니다. 본문 미확보 51건이 모두 무관하다는 뜻은 아닙니다.
추가 검색·본문 수집을 통한 누락률 검증은 이번 범위에 포함하지 않았습니다.</p>
<h2>최신순 수정의 실제 효과</h2><p>이번 결과의 적격 대표 기사 집합에서 최신 5건 선택 여부를 종목별로 대조했습니다.
중복으로 묶인 기사의 대표를 최신 기사로 교체하는 수정은 아니며, 검색 범위 밖의 최신 기사까지 보장하지 않습니다.</p><ul>""" + changes + """</ul>
<h2>원문과 대조해 확인한 남은 문제</h2>
<div class="notice">직원의 외부 강연이 핵심 기업 뉴스로 포함됐습니다. 자율주행 실증 기사에는 원문에 없는 매출·이익 반영 시점이 붙었습니다.
동일 실증 사건의 기사들이 함께 선택됐으며, 현대로템 실적 감소 기사는 최종 보류됐습니다.
에코프로비엠에서는 주가 하락을 기업 악재로 단정하지 않았지만, 사업 뉴스가 없다는 결론까지 내릴 수는 없습니다.</div>
<p>이는 결과를 본 뒤 원문과 대조한 사후 점검입니다. 사전 정답 라벨을 갖춘 독립 평가나 사람이 합의한 정확도 측정이 아닙니다.
상승·하락·보류 건수는 모델 출력 분포이며 정답 개수가 아닙니다. 특히 하락 결과가 0건이므로 악재 분석 성공을 주장하지 않습니다.
각 기사 아래 구체적 실패를 기록했고 이번에는 최신순 선택 이외의 규칙을 추가로 조정하지 않았습니다.</p>
""" + "".join(cards) + "</main></html>"
Path("output/latest-v14-validation-report.html").write_text(html,encoding="utf-8")
print(json.dumps(record,ensure_ascii=False))
