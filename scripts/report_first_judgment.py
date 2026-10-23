"""Report cold-start direction checks without treating label agreement as accuracy."""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def read(name):
    return json.loads((ROOT / "output" / f"first-judgment-{name}.json").read_text(encoding="utf-8"))

before, after, holdout = (read(name) for name in ("before", "after", "holdout"))
def metrics(rows):
    initial = sum(bool(r["first"]["findings"]) and r["first"]["findings"][0]["direction"] == r["expected"] for r in rows)
    valid = sum(not r["first_errors"] for r in rows)
    final = sum(r["match"] for r in rows)
    return f"{initial}/{len(rows)}", f"{valid}/{len(rows)}", f"{final}/{len(rows)}"

summary = "".join(
    "<tr><td>" + name + "</td>" + "".join(f"<td>{v}</td>" for v in metrics(rows)) + "</tr>"
    for name, rows in [("개선 전 · 개발용 4건", before),
                       ("개선 후 · 같은 4건 × 2회", after), ("미사용 평가 · 별도 4건 × 1회", holdout)]
)
cards = []
for row in after + holdout:
    first = row["first"]["findings"][0] if row["first"]["findings"] else {}
    final = row["final"]
    cards.append(f"""<article>
<div class="meta">{escape(row['date'])} · {'개선용' if row['split'] != 'holdout' else '별도 평가'} · 실행 {row['repeat']}</div>
<h3><a href="{escape(row['url'], quote=True)}">{escape(row['title'])}</a></h3>
<p><b>예상 {escape(row['expected'])}</b> · 최초 {escape(first.get('direction', '없음'))} → 최종 {escape(final['direction'])}</p>
<p class="meta">최초 자동 검사: {escape(' / '.join(row['first_errors']) or '통과')} · 모델 호출 {row['calls']}회</p>
<p>{escape(final['reason'])}</p><p><b>생성된 반대 근거:</b> {escape(final['counterpoint'])}</p>
</article>""")

html = """<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>첫 판단 검증 · v9</title><style>
body{margin:0;background:#f4f5f1;color:#22352d;font:16px/1.75 'Malgun Gothic',sans-serif}
main{max-width:1050px;margin:auto;padding:48px 24px}h1{font-size:34px;letter-spacing:-1.4px}
h2{margin-top:40px;font-size:23px}h3{font-size:18px;margin:8px 0}
article{padding:24px;background:white;border:1px solid #dce3dd;border-radius:12px;margin:16px 0}
.meta{color:#627269;font-size:14px}a{color:#25664c}table{border-collapse:collapse;width:100%;background:white}
th,td{padding:16px;border-bottom:1px solid #dce3dd;text-align:left}.scroll{overflow:auto}
.note{padding:22px;background:#fff3da;border-left:4px solid #b88c38}
</style><main><div class="meta">천기누설 · 평가 v9b · 캐시 없는 첫 판단</div>
<h1>방향은 맞았지만,<br>설명까지 모두 정확하지는 않았습니다.</h1>
<p>이전 평가에 쓰지 않은 실제 기사 8건을 추가했습니다. 실적·보조금·리콜의 호재와 악재 6건,
사회공헌·창립기념식 대조군 2건입니다. 2023~2024년 과거 보도이며 최신 뉴스 피드에는 넣지 않았습니다.</p>
<h2>최초 응답과 최종 결과를 분리한 비교</h2>
<div class="scroll"><table><thead><tr><th>평가</th><th>최초 방향 일치</th><th>최초 인용·수치 검사</th><th>수정·검토 후 방향 일치</th></tr></thead>
<tbody>""" + summary + """</tbody></table></div>
<p class="meta">개선 후 8회는 기사 8종이 아닌 4종의 두 번 실행입니다. 별도 평가 4종은 분석 코드 고정 후 처음 평가했습니다.
최초 검사는 자동 인용·수치 검사이며 사실 정확성 전체를 보장하지 않습니다.</p>
<h2>무엇을 바꿨나</h2>
<p>인용 조각을 문장 경계에 맞춰 나눠 소수점·대출 조건 문장이 끊기는 문제를 줄였습니다.
근거를 먼저 선택하도록 출력 순서를 바꾸고 최대 3개 근거를 사용합니다.
설명은 짧게 작성하고 불필요한 숫자·내부 인용 번호를 반복하지 않도록 조정했습니다.
보조금과 대출, 지원 확정과 매출 발생, 국내 미판매와 전사 영향은 구분하도록 지침을 보강했습니다.</p>
<p>개선 전에도 첫 방향은 4건 모두 맞았습니다. 보조금 사례에서 설명 수치와 선택 인용이 불일치해
최종 판단이 보류됐던 문제를 개선했습니다. 별도 평가의 SK하이닉스 적자 사례는 원문의 2012년과 2022년에서
계산한 ‘10년 만’ 표현이 보수적인 수치 검사에 걸렸고 한 번 수정됐습니다. 첫 방향 오류로 세지 않았습니다.</p>
<h2>남은 설명 품질 문제</h2>
<div class="note"><b>방향 일치율을 정확도 100%로 해석하면 안 됩니다.</b>
<ul><li>보조금 기사: 대출 지원 조건·금액의 확정 여부를 부정확하게 표현하거나 공장 가동 예정 시점과 투자 시점을 섞는 표현이 남았습니다.</li>
<li>리콜 기사: 국내 미판매라는 사실만으로 전사·글로벌 영향이 제한적이라고 추정하는 반대 근거가 남았습니다.</li>
<li>같은 모델의 의미 검토에서도 위 표현이 통과했습니다. 인용의 존재와 문장 의미의 정확성은 별도 문제입니다.</li></ul>
방향은 해당 회사의 사업상 상승·하락 요인입니다. 실제 주가 방향, 영향 규모, 상승 확률을 검증한 결과가 아닙니다.</div>
<h2>평가 조건과 한계</h2>
<p>예상 라벨을 호출 전에 저장했고 모델 입력에 넣지 않았습니다. 분석 결과 캐시는 사용하지 않았으며 운영 분석 이력 저장도
차단했습니다. 개선용 4건으로 반복 수정한 뒤 별도 4건을 평가했습니다. 중간 실패 결과도 파일로 보존했습니다.
원문은 공식 기업 뉴스룸 6건과 언론 보도 2건이며 리콜·보조금은 공식 발표도 대조했습니다.</p>
<p>예상 라벨은 assistant가 지정한 소표본 기준이며 독립 전문가 합의 정답이 아닙니다.
이번에는 원문 확보 이후 개별 기사의 판단을 평가했습니다. 검색·종목 관련성 선별·다기사 일괄 분석 정확도는 이번 지표에 포함하지 않습니다.
실적 기사 비중이 높아 일반화에는 추가 평가가 필요합니다.</p>
<h2>기사별 결과 · 생성된 설명을 그대로 기록</h2>
<p class="meta">아래 설명에는 위에서 지적한 오류가 남아 있습니다. 각 제목에서 원문을 확인할 수 있습니다.</p>
""" + "".join(cards) + """<h2>재현 자료</h2>
<p>first-judgment-labels.json · first-judgment-before.json · first-judgment-intermediate.json ·
first-judgment-after.json · first-judgment-holdout.json 및 단계별 코드 해시 기록.
평가 실행: scripts/audit_first_judgment.py. 이 보고서는 저장된 평가 결과로 생성했습니다.</p></main></html>"""
(ROOT / "output" / "first-judgment-validation-report.html").write_text(html, encoding="utf-8")
print(json.dumps({"before": metrics(before), "after": metrics(after), "holdout": metrics(holdout)}, ensure_ascii=False))
