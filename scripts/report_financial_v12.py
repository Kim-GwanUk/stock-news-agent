import json
from collections import defaultdict
from html import escape as e
from pathlib import Path

def read(name):
    return json.loads(Path(f"output/financial-v12-{name}.json").read_text(encoding="utf-8"))
before, after = read("unseen-results"), read("results")
assert len(before) == len(after) == 6
groups = defaultdict(list)
for row in after:
    groups[row["id"]].append(row)
cards = []
for ident, runs in groups.items():
    r = runs[0]
    cards.append(f"<article><div class='meta'>{e(r['date'])}</div><h3><a href='{e(r['url'],quote=True)}'>{e(r['title'])}</a></h3>" +
                 "".join(f"<div class='run'><b>{x['repeat']}회차 · {e(x['final']['direction'])}</b>"
                         f"<p>{e(x['final']['reason'])}</p><p class='meta'>{e(x['final']['counterpoint'])}</p></div>" for x in runs) + "</article>")
html = """<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>새 기사 금액·조건 평가 v12</title><style>
body{margin:0;background:#f3f5f1;color:#263b30;font:16px/1.75 'Malgun Gothic',sans-serif}
main{max-width:1050px;margin:auto;padding:44px 24px}h1{font-size:32px}h2{margin-top:36px}h3{font-size:18px}
article{background:white;padding:24px;border:1px solid #dce4de;border-radius:12px;margin:18px 0}
a{color:#25634b}.meta{font-size:14px;color:#65756b}.run+.run{border-top:1px solid #dce4de;padding-top:18px}
table{width:100%;border-collapse:collapse;background:white}td,th{text-align:left;padding:14px;border-bottom:1px solid #dce4de}
.note{padding:22px;background:#fff1d6;border-left:4px solid #b28a3b}
</style><main><div class="meta">천기누설 · v12 → v12b · 독립 평가와 재검증 구분</div>
<h1>새 기사에서 발견한 누락을<br>실패 기록과 함께 보완했습니다.</h1>
<p>450백만 달러, 500 백만 달러, 6.4십억 달러, 2,500백만 달러 표기를 추가 지원합니다.
같은 값·같은 통화만 인정하고 잘못된 자릿수·통화는 차단합니다. 자동 테스트 74개가 통과했습니다.</p>
<h2>평가 설계</h2><p>숫자 처리를 수정한 후 코드를 고정하고, 수정에 쓰지 않은 실제 문서 3건을 각각 두 번 평가했습니다.
영문 언론 보도 1건과 정부·기업 공식 발표 2건입니다. 과거 2022·2024년 기사이며 최신 뉴스가 아닙니다.
SK하이닉스 기사는 이전과 같은 예비 지원 사건의 새 발행처 기사로, 사건까지 독립적이지는 않습니다.</p>
<p>접근에 실패한 에너지부 원문 2건은 평가에 포함하지 않았습니다. LG 기업 발표로 대체했고,
예비 단계가 명시되지 않은 삼성 행사 발표 대신 조건을 확인할 수 있는 SK 언론 보도를 선택했습니다.
이 선택은 모델 호출 전에 완료했으며, 라벨을 모델 입력에 넣지 않았습니다.</p>
<table><tr><th>구분</th><th>최종 방향 일치</th><th>조건 점검</th></tr>""" + f"""
<tr><td>새 문서 최초 평가 · v12</td><td>{sum(r['match'] for r in before)}/6</td><td>예비 단계·차입 한도 누락 발견</td></tr>
<tr><td>보완 후 같은 문서 재검증 · v12b</td><td>{sum(r['match'] for r in after)}/6</td><td>예비 단계와 주요 최대 금액 유지</td></tr>
""" + """</table><p class="meta">최초 평가와 최종 재검증을 합쳐 ‘독립 평가 100%’라고 부르지 않습니다.
예상 방향은 assistant가 사전에 정한 사업 영향 기준이며 외부 전문가 합의 정답이 아닙니다.</p>
<h2>발견과 개선</h2><ul>
<li>새 SK 기사에서 450백만 달러와 6200억 원을 처리했지만, 단독 preliminary memorandum 표현을 놓쳐 예비 단계가 빠졌습니다. 이 표현도 인식하고 원문 조건을 보존하도록 개선했습니다.</li>
<li>LG 기사에서 ‘차입 가능 한도는 25억 달러’를 확정 금액처럼 썼습니다. 한도는·한도가 등 표현을 인식해 ‘최대 25억 달러’를 유지합니다.</li>
<li>LG 차입 기사의 금리 조건이 공개됐는데도 없다고 쓰는 반대 근거가 나왔습니다. 기존 대출 안내를 차입 표현에도 적용했습니다.</li>
<li>삼성 최종 지원 기사에서 미래 단계별 지급을 이미 받았다고 표현했습니다. 향후 단계별 지급이 있는 원문에서 수령 완료 표현을 검사합니다.</li>
<li>이전 예비 합의를 언급하는 최종 지원 발표를 다시 예비 단계로 바꾸지 않도록 구분합니다.</li></ul>
<h2>최종 결과의 범위와 남은 한계</h2><div class="note">
<p>새 SK 기사는 예비 합의와 최대 4억5000만 달러, 삼성 기사는 최대 47억4500만 달러와 단계별 지급,
LG 기사는 합작법인 주체와 최대 25억 달러 한도를 두 번씩 유지했습니다.
검증에 캐시를 사용하지 않았고 운영 관심종목·분석 이력에 과거 자료를 넣지 않았습니다.</p>
<p>설명 전체가 정확하다는 판정은 아닙니다. 삼성 응답 1회는 단계별 지급을 언급하면서도 집행 조건이
확인되지 않는다고 포괄적으로 적어 표현이 모호했습니다. SK 응답 1회의 비구속 표현은 입력 기사에 명시되지 않았습니다.
보조금과 대출의 금액 연결, 계약 체결과 실제 자금 인출의 구분도 지속적인 의미 검토가 필요합니다.</p>
<p>지원 표기는 명시적 달러·원과 십·백·천+만·억·조 조합에 한정됩니다. 모든 한글 수사·약어·통화를
지원하지 않으며 환율 환산도 수행하지 않습니다. 검색·관련성 선별을 제외한 단일 기사 분석 평가입니다.</p></div>
<h2>최종 응답</h2>""" + "".join(cards) + """
<h2>재현 자료</h2><p>financial-v12-labels.json: 사전 기준·원문 해시.
financial-v12-unseen-results.json 및 unseen-code.json: 최초 독립 평가.
financial-v12-results.json 및 code.json: 보완 후 재검증.
최초 실패 기록을 덮어쓰지 않았습니다.</p></main></html>"""
Path("output/financial-v12-validation-report.html").write_text(html, encoding="utf-8")
print(json.dumps({"unseen_direction_matches":sum(r["match"] for r in before),
                  "retest_direction_matches":sum(r["match"] for r in after), "attempts_each":6}, ensure_ascii=False))
