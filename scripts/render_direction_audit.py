"""Render saved evaluation results without additional API calls."""
import json
from html import escape
from pathlib import Path

def read(name):
    return json.loads(Path(f"output/direction-audit-{name}.json").read_text(encoding="utf-8"))

final, before, controls = read("final"), read("before"), read("controls")
baseline = {r["id"]: r for r in before}
e = lambda value: escape(str(value), quote=True)
rows = []
for r in final:
    old = baseline.get(r["id"])
    rows.append(f"""<tr><td><a href="{e(r['url'])}">{e(r['title'])}</a>
    <small>{e(r['date'])} · {'최종 별도 표본' if old is None else '개선에 사용한 표본'}</small></td>
    <td>{e(r['expected'])}</td><td>{e(old['final']['direction']) if old else '미평가'}</td>
    <td><b>{e(r['final']['direction'])}</b><small>{e(r['final']['impact'])}</small></td></tr>""")
control_rows = "".join(f"""<tr><td><a href="{e(r['url'])}">{e(r['title'])}</a></td>
    <td>{e(r['expected'])}</td><td>{e(r['final']['direction'])}</td></tr>""" for r in controls)
html = """<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>실제 기사 방향 판단 검증</title>
<style>
body{margin:0;background:#f5f5ef;color:#223c32;font:16px/1.7 'Malgun Gothic',sans-serif}
main{max-width:1120px;margin:auto;padding:48px 28px}h1{font-size:34px;letter-spacing:-1.5px;line-height:1.3}
h2{margin-top:36px;font-size:22px}p{max-width:900px}small{display:block;color:#64766d;font-size:12px}
.metrics{display:flex;gap:16px;flex-wrap:wrap}.metric{background:white;border:1px solid #dce3d9;border-radius:14px;padding:20px;flex:1;min-width:180px}
.metric b{display:block;font-size:30px}table{width:100%;border-collapse:collapse;background:white}
th,td{text-align:left;padding:14px;border-bottom:1px solid #dce3d9}th{background:#e7eee5}
td:not(:first-child){white-space:nowrap}a{color:#237552;text-decoration:none}a:hover{text-decoration:underline}
.note{border-left:3px solid #c69a4b;padding:14px 20px;background:#fffaf0}.scroll{overflow:auto}
footer{margin-top:40px;color:#64766d;font-size:13px}
</style><main><small>품질 점검 · 2026.10.20 · 분석 프롬프트 v6</small>
<h1>명확한 호재·악재는 구분하고,<br>근거가 부족하면 보류합니다.</h1>
<p>삼성전자·SK하이닉스의 실제 과거 실적 발표 및 계약 기사 8건을 발표 당시의 사업 영향 기준으로 평가했습니다.
현재 뉴스 피드와 분석 이력에는 추가하지 않았습니다.</p>
<div class="metrics"><div class="metric">개선에 사용한 6건<b>0 → 5건</b><small>기대 방향 일치 / 나머지 1건 보류</small></div>
<div class="metric">최종 별도 표본 2건<b>2 / 2건</b><small>코드 수정 후 추가 평가</small></div>
<div class="metric">최종 8건 분류<b>상승 4 · 하락 3</b><small>보류 1 · 기대 방향과 반대 0</small></div></div>
<h2>무엇을 개선했나</h2><ul>
<li>모델이 인용문을 다시 쓰지 않고 실제 원문 조각을 선택하도록 변경했습니다. 서버가 원문 그대로 인용을 복원합니다.</li>
<li>기사 하나에는 종합 판단 하나만 생성합니다. 실적 기사는 해당 기간의 전사 손익을 우선하며, 일부 사업의 호조와 미래 전망은 반대 근거로 구분합니다.</li>
<li>방향 근거가 맞고 영향 규모만 불확실하면 보류 대신 영향 수준을 낮출 수 있습니다. 원문·출처·수치 검증은 유지합니다.</li></ul>
<h2>기사별 결과</h2><div class="scroll"><table><thead><tr><th>원문 / 발표일</th><th>평가 기준</th><th>개선 전</th><th>최종 결과</th></tr></thead><tbody>
""" + "".join(rows) + """</tbody></table></div>
<h2>무조건 긍정·부정으로 바뀌지 않는지도 확인</h2>
<p>이전 표본 중 사회공헌·시장 일반론·단순 방문 3건은 보류를 유지했습니다.
협력사 금융지원은 약한 간접 호재를 기대했으나 보류하여 미해결 사례로 남겼습니다. 이 기준 자체도 사람의 검토가 필요합니다.</p>
<div class="scroll"><table><thead><tr><th>기존 대조 기사</th><th>평가 기준</th><th>최종 결과</th></tr></thead><tbody>
""" + control_rows + """</tbody></table></div>
<h2>남은 문제와 해석 범위</h2><div class="note">
<p>삼성전자 2023년 1분기 기사는 설명에 선택한 인용으로 확인되지 않는 수치가 남아 보류했습니다.
첫 수정에서는 같은 기사에 상반된 판단이 생성되거나, 일부 부문의 호조로 전사 실적 악화를 긍정적으로 분류하는 오류도 발견했습니다.
최종 수정에서 기사별 단일 판단과 전사 손익 우선 규칙을 추가했습니다.</p>
<p>처음 분리한 2건도 중간 결과 확인 후 수정에 사용했으므로 최종적으로 기존 6건 모두 개선용 표본입니다.
마지막에 별도로 추가한 SK하이닉스 2024년 2분기·삼성전자 2024년 4분기 2건만 최종 수정에 사용하지 않았습니다.</p></div>
<ul><li>평가 기준은 assistant가 사전에 작성했습니다. 전문가 합의 정답이나 일반적인 정확도 수치가 아닙니다.</li>
<li>표본은 명확한 실적·계약 중심이며 기업 공식 보도자료 7건과 Reuters 배포 기사 1건입니다. 일반 언론 기사 전체를 대표하지 않습니다.</li>
<li>본문을 확보한 기사 하나씩의 분석·수정·검토 경로를 실행했습니다. 검색·관련성 선별·여러 기사 동시 분석을 포함한 전체 서비스 평가는 아닙니다.</li>
<li>상승·하락 요인은 사업에 미치는 방향입니다. 주가 수익률 예측이나 영향 수준의 정확도를 검증한 결과가 아닙니다. 설명의 모든 문장이 검증됐다는 뜻도 아닙니다.</li>
<li>모델 응답은 실행마다 달라질 수 있습니다. 반복 평가와 사람 검수가 필요합니다. 자동 테스트는 27개 통과했습니다.</li></ul>
<footer>재현 자료: direction-audit-before.json / direction-audit-after.json / direction-audit-final.json /
direction-audit-controls.json. 최종 평가 전 코드 해시는 direction-audit-final-code-snapshot.json에 보관했습니다.
이후 운영 캐시 버전만 v6로 올렸습니다.</footer></main></html>"""
Path("output/direction-validation-report.html").write_text(html, encoding="utf-8")
print("output/direction-validation-report.html")
