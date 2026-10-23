import json
from collections import defaultdict
from html import escape as e
from pathlib import Path

rows = json.loads(Path("output/financial-v11-results.json").read_text(encoding="utf-8"))
assert len(rows) == 10
groups = defaultdict(list)
for r in rows:
    groups[r["id"]].append(r)
cards = []
for ident, runs in groups.items():
    r = runs[0]
    output = []
    for run in runs:
        f = run["final"]
        output.append(f"<div class='run'><b>{run['repeat']}회차 · {e(f['direction'])}</b>"
                      f"<p>{e(f['reason'])}</p><p class='meta'>{e(f['counterpoint'])}</p>"
                      f"<p class='meta'>최초 검사: {e(' / '.join(run['first_errors']) or '통과')}</p></div>")
    cards.append(f"<article><div class='meta'>{e(r['date'])} · 예상 {e(r['expected'])}</div>"
                 f"<h3><a href='{e(r['url'],quote=True)}'>{e(r['title'])}</a></h3>{''.join(output)}</article>")
english = [r for r in rows if r["id"] in ("v10-sk-preliminary", "v10-samsung-preliminary")]
stats = {"최종 방향 일치": f"{sum(r['match'] for r in rows)}/10",
         "영문 지원 발표 방향 일치": f"{sum(r['match'] for r in english)}/4",
         "최초 자동 검사 통과": f"{sum(not r['first_errors'] for r in rows)}/10",
         "자동 테스트": "66개 통과"}
table = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k,v in stats.items())
html = """<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>금액·지원 조건 재검증 v11</title><style>
body{margin:0;background:#f3f5f1;color:#263e30;font:16px/1.75 'Malgun Gothic',sans-serif}
main{max-width:1000px;margin:auto;padding:44px 24px}h1{font-size:32px}h2{margin-top:36px}
article{background:white;padding:24px;border:1px solid #dde4df;border-radius:12px;margin:18px 0}
h3{font-size:18px}a{color:#25634b}.meta{font-size:14px;color:#637469}
.run+.run{border-top:1px solid #dde4df;padding-top:16px;margin-top:16px}
table{border-collapse:collapse;background:white;width:100%}td,th{text-align:left;padding:14px;border-bottom:1px solid #dde4df}
.note{padding:22px;background:#fff2d8;border-left:4px solid #b18b3c}</style><main>
<div class="meta">천기누설 · v11c · 실제 과거 기사 재검증</div>
<h1>같은 금액은 같게 비교하고,<br>예비 합의와 한도를 보존합니다.</h1>
<p>이전에 평가했던 기사 5건을 각각 두 번, 캐시 없이 다시 분석했습니다.
영문 지원 발표 2건, 같은 SK 예비 합의의 한국어 기사 1건, 최종 지원 확정·리콜 대조 사례 2건입니다.
새 독립 평가 세트가 아닌 회귀 검증입니다.</p><table>""" + table + """</table>
<h2>변경 내용</h2><ul>
<li>달러·원과 금액을 분리해 정확한 값으로 비교합니다. $450 million ↔ 4억5000만 달러,
$6.4 billion ↔ 64억 달러를 인정합니다. 환율 환산·지원액 합산·틀린 자릿수는 인정하지 않습니다.</li>
<li>선택한 인용의 금액·비율이 최대 한도이면 설명의 해당 수치에도 ‘최대’를 보존합니다.
현재 발표가 예비 합의인 경우 예비·비구속 조건을 설명 본문에 보존합니다.</li>
<li>원문에 명시된 조건이 모델 설명에서 누락되면 조건 안내를 보충합니다.
최종 확정·수령 완료라는 모순된 주장은 별도로 거절합니다.</li>
<li>과거 예비 합의를 언급하는 최종 확정 보도를 예비 단계로 잘못 바꾸지 않는 대조 테스트를 포함했습니다.</li></ul>
<h2>검증 해석</h2><div class="note">
<p>처음 수정한 버전은 10회 중 9회 방향 일치였습니다. 나머지 1회는 근거 없는 일자리 수치와
수정 후 비구속 조건 누락으로 보류되어, 조건 보존을 추가했습니다. 다음 평가에서는 세제혜택 비율의 최대 조건 누락을 확인해 비율까지 한도 보존을 확장했습니다. 위 표는 그 후 최종 버전의 결과입니다.
이전 실패 결과도 별도 파일에 보존했습니다.</p>
<p>방향 일치는 전체 설명 정확도나 주가 예측 정확도가 아닙니다. 예비 합의의 사업 영향 수준,
기간·주체·금액 항목의 의미는 여전히 모델 검토가 필요합니다.
금액 비교는 명시된 달러·원 단위만 지원하며 다른 통화·환율·근삿값은 자동 인정하지 않습니다.
최종 평가의 최초 응답 1회는 ‘450백만 달러’라는 미지원 혼합 표기를 사용해 한 번 수정했습니다.
이는 최종 보류로 이어지지 않았지만 모든 숫자 표기를 지원한다는 뜻은 아닙니다.
예비 단계 감지는 기사 앞부분의 명시적 표현을 사용하므로 복잡한 다중 사건에는 한계가 있습니다.</p>
</div><h2>기사별 최종 결과</h2>""" + "".join(cards) + """
<h2>재현 자료</h2><p>output/financial-v11-results.json, financial-v11-code.json,
financial-v11-initial-results.json. 원문·사전 라벨은 이전 평가 자료를 재사용했습니다.
캐시 읽기·쓰기 및 운영 이력 저장을 차단했습니다. 과거 기사는 최신 피드에 추가하지 않았습니다.</p></main></html>"""
Path("output/financial-v11-validation-report.html").write_text(html, encoding="utf-8")
print(json.dumps(stats, ensure_ascii=False))
