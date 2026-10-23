"""Keep independent evaluation, later regression, and unresolved errors separate."""
import hashlib
import json
from html import escape as e
from pathlib import Path

def read(name):
    return json.loads(Path("output",name).read_text(encoding="utf-8"))

snapshot = read("locked-v16-pre-holdout2-code.json")
assert snapshot == read("locked-v16-holdout2-code.json")
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in snapshot.items())

notes = {
    "v16-samsung-q2":"전사 전분기 이익 감소를 보존. 하반기 기대와 구분.",
    "v16-hyundai-q3":"전년 대비 이익 감소와 관세 부담 보존.",
    "v16-hyundai-press":"이익 감소·관세 비용과 향후 대응 계획 보존. 추가 비용 사실이 있어 별도 기사 유지.",
    "v16-sdi-conditional":"조건부 지원 문단과 합작법인 주체 보존.",
    "v16-sdi-detail":"미해결: 이번 배치에서는 사실 추출 결과가 없어 보류. 단독 진단 재실행에서는 추출 성공. 첫 실패의 상세 원인은 확정하지 못했고, 추출 응답의 변동성은 남아 있음.",
    "v16-sdi-final":"최종 약정 종결과 지역사회 계획 조건 보존. 조건부 발표와 별도 기사로 유지.",
    "v16-sk-final-loan":"대출 승인과 실제 집행 불확실성 보존. SK온–SK이노베이션 관계는 본문 자체에 명시되지 않아 기업 관계 확인 범위에 한계.",
    "v16-unrelated-sdi":"삼성SDI 기사가 삼성전자 분석 대상으로 들어오지 않음. 세부 관련성 이름은 ‘단순 언급’으로 나와 ‘무관’과 구분이 불완전.",
    "v16-sdi-conditions":"본문 접근 실패. 분석 성공 표본에서 제외.",
    "v16b-kia":"통과: 매출 증가와 전사 이익 감소가 공존하지만, 이익 악화를 하락 요인으로 분류. 수치·감소 원인 보존.",
    "v16b-lges":"통과: 공급계약, 공급 규모·기간, 공장 가동 목표를 보존. 예정 내용을 완료로 바꾸지 않음.",
    "v16b-lge":"미해결: 원문 수익성 하락과 시장 기대 상회는 모두 남았으나 ‘실적 개선’ 경로를 선택해 상승 요인으로 설명. 사전 기준과 불일치. 잠정 표현은 유지했지만 마지막 문단의 상세 실적 추후 발표 안내는 선택하지 않음.",
}

def table(phase, labels_name):
    labels = read(labels_name)
    output = []
    for row in read(f"locked-v16-{phase}-results.json"):
        r = row["result"]
        fs = {f["article_id"]:f for f in r["findings"]}
        for a in r["articles"]:
            f = fs[a["id"]]
            label = labels.get(a["id"], {})
            text = f["reason"] + " " + f["counterpoint"]
            required = label.get("required", [])
            covered = sum(x.lower() in text.lower() for x in required)
            output.append(f'<tr><td>{e(r["stock"]["name"])}<br><a href="{e(a["url"],quote=True)}">{e(a["title"])}</a>'
                          f'<br><small>{e(a.get("published",""))}</small></td>'
                          f'<td>{"선별" if a.get("analysis_candidate") else "제외"}<br>{e(f["direction"])}</td>'
                          f'<td>{covered}/{len(required) if required else "—"}<br>{e(notes.get(a["id"],""))}</td></tr>')
    return '<table><tr><th>대상·원문</th><th>앱 결과</th><th>사전 확인 표현 보존·원문 대조</th></tr>'+"".join(output)+"</table>"

html = """<!doctype html><html lang="ko"><meta charset="utf-8"><title>사실 고정 구조 · v16 검증</title>
<style>body{font:16px/1.8 system-ui;color:#253142;background:#f5f7fa;max-width:1120px;margin:48px auto;padding:0 24px}
h1{font-size:32px}h2{margin-top:32px}section{background:white;border:1px solid #dce2e9;border-radius:14px;padding:24px;margin:22px 0}
table{border-collapse:collapse;width:100%;background:white}td,th{border:1px solid #dce2e9;padding:14px;text-align:left;vertical-align:top}td:first-child{width:38%}
a{color:#175c93}small{color:#687482}.flow{background:#e7edf5;border-radius:8px;padding:18px}.warn{border-left:5px solid #b87518}</style>
<h1>사실 고정 구조 · v16 검증</h1><p>2026-10-21 · 원문 보존과 영향 해석을 분리했습니다. 전체 정확도가 해결됐다는 보고서는 아닙니다.</p>
<section><h2>변경한 흐름</h2><p class="flow">뉴스 선별 → 원문 문단 선택 → 사실·금액·조건 고정 → 영향 경로 선택 → 코드로 설명 조립 → 의미 검토</p>
<p>모델은 사실을 재작성하지 않고 원문 위치만 선택합니다. 코드가 완전한 문단, 원문 금액, 단계 표현을 복원하고 원문·사실 묶음의 해시를 기록합니다.
영향 설명은 허용된 경로의 문장으로 조립합니다. 재시도는 영향 선택만 반복하며 사실을 다시 추출하지 않습니다.
저장한 설명은 같은 사실로 다시 조립한 결과와 일치하는지 검사합니다. 보류되더라도 확보한 사실과 조건을 유지합니다.</p>
<p>‘예정·추정·조건부’ 표시는 원문 어휘 신호이며 확정 여부의 독립적인 진실성 검증이 아닙니다.
조건을 선택한 뒤 바꾸는 문제는 막지만, 처음부터 중요한 문단을 놓치는 문제까지 보장하지는 않습니다.
원문 보존을 우선해 설명이 길어질 수 있고, 영문 출처의 사실 인용은 영문 그대로 남습니다.</p></section>
<section><h2>평가 분리</h2><ol>
<li>기존 실패 기사로 개발: 사업 양수도 금액·승인 조건 및 실제 실적 악재를 재검증. 초기 실패 실행도 보관.</li>
<li>첫 미사용 표본: 8개 URL 중 7개 본문 확보. 삼성전자/삼성SDI 혼동 대조를 추가해 9개 종목–기사 쌍.
조건부 발표와 2주 뒤 최종 약정을 중복으로 처리하는 실패가 발견됨.</li>
<li>발행일을 선별 입력에 추가하고 2일을 넘는 발표 간 모델 중복 참조를 차단. 첫 표본은 이후 회귀 검증으로 분류.</li>
<li>최종 코드 고정 후 미사용 기사 3개를 별도 평가. 코드 해시·원문 해시·사전 기준을 저장하고 기대 결과는 모델에 전달하지 않음.</li></ol>
<p>2024~2025년 실제 보도·공식 발표를 사용했습니다. 현재 투자 판단이나 최신 뉴스 검색 품질을 평가한 것이 아닙니다.
URL 직접 수집 → 본문 관련성 선별 → 사실 추출 → 방향 해석을 평가했으며 검색 API의 누락률은 측정하지 않았습니다.
운영 캐시·관심 종목·분석 이력은 평가 중 수정하지 않았습니다.</p></section>
<section class="warn"><h2>결론과 남은 문제</h2>
<p>새 독립 표본에서 기아 실적 악화와 LG에너지솔루션 공급계약은 사전 방향 기준에 부합했습니다.
LG전자 혼합 실적은 수익성 하락 사실을 보존하면서도 실적 개선으로 해석하여 기준에 맞지 않았습니다.
이는 숫자·조건 재작성 오류와 별개인 비교 기준(전년 대비/시장 기대 대비) 선택 문제입니다.</p>
<p>회귀 검증에서는 본문 확보 7개 중 6개가 방향 분석을 완료했고, 영문 조건부 대출 기사 1개는 사실 추출 실패로 보류됐습니다.
단독 진단에서는 추출이 성공했으므로 해결로 계산하지 않습니다. 원문 문단 선택의 변동성과 조건 누락은 후속 개선 대상입니다.</p>
<p>동일 날짜 안의 단계 변경이나 장기간 뒤 재보도까지 포괄하는 사건 식별은 미완성입니다.
전체 기사에 대한 정확도나 안정성 수치로 일반화할 수 없습니다.</p></section>
<h2>최종 수정에 쓰지 않은 독립 표본 3개</h2>
"""
html += table("holdout2","locked-v16-holdout2-labels.json")
html += "<h2>첫 표본 수정 후 회귀 검증</h2>" + table("regression","locked-v16-holdout-labels.json")
html += """<section><h2>확인 기록</h2><p>로컬·Docker 각각 테스트 105개 통과. 최초 오류와 재시도 결과, 선택한 원문 위치, 고정 사실 해시를 JSON에 보존했습니다.
표의 표현 보존 개수는 사전 지정 문자열 검사이며, 문장 전체의 의미 정확도를 뜻하지 않습니다.</p>
<ul><li><a href="locked-v16-holdout-results.json">첫 미사용 표본 원결과(중복 실패 포함)</a></li>
<li><a href="locked-v16-regression-results.json">수정 후 회귀 결과</a></li>
<li><a href="locked-v16-holdout2-results.json">최종 독립 표본 결과</a></li>
<li><a href="locked-v16-holdout2-labels.json">독립 표본 사전 기준</a></li>
<li><a href="locked-v16-holdout2-code.json">최종 평가 코드 해시</a></li></ul></section></html>"""
Path("output/locked-v16-validation-report.html").write_text(html,encoding="utf-8")
