import json
from html import escape
from pathlib import Path
from collections import defaultdict

def read(name):
    return json.loads(Path(f"output/payment-v13-{name}.json").read_text(encoding="utf-8"))

first, final = read("first-results"), read("results")
assert len(first) == len(final) == 6
groups = defaultdict(list)
for row in final:
    groups[row["id"]].append(row)
cards = []
for ident, rows in groups.items():
    item = rows[0]
    cards.append(
        f"<article><small>{escape(item['date'])} · 과거 자료</small>"
        f"<h2><a href='{escape(item['url'], quote=True)}'>{escape(item['title'])}</a></h2>"
        f"<p class='condition'>{escape(item['final']['counterpoint'])}</p>" +
        "".join(f"<p><b>{r['repeat']}회: {escape(r['final']['direction'])}</b><br>"
                f"{escape(r['final']['reason'])}</p>" for r in rows) + "</article>")
assert all("원문에 명시된 지원·지급 조건" in r["final"]["counterpoint"] for r in final)
assert all(not r["final_errors"] for r in final)
html = """<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>지급 조건 검증 v13</title><style>
body{margin:0;background:#f5f6f3;color:#253b32;font:16px/1.8 'Malgun Gothic',sans-serif}
main{max-width:1040px;margin:auto;padding:48px 24px}h1{font-size:34px;line-height:1.4}
h2{font-size:19px}article{background:white;border:1px solid #dce3dd;border-radius:12px;padding:24px;margin:20px 0}
a{color:#21644b}small{color:#65766a}.condition{background:#edf4ee;padding:18px}
.note{background:#fff0d6;padding:20px;border-left:4px solid #b88a38}
table{width:100%;border-collapse:collapse;background:white}th,td{padding:14px;border-bottom:1px solid #dce3dd;text-align:left}
</style><main><small>천기누설 · 2026-10-20 · v13 → v13b</small>
<h1>지급 조건을 모호한 안내 대신<br>확인된 조건과 원문으로 표시합니다.</h1>
<p>사업 단계 달성, 대출 종결 조건, 기술·법률·환경·재무 요건을 짧은 한국어 설명과 원문 문장으로 함께 표시합니다.
문장 중간 줄바꿈을 보존하며, 선택된 조건이 전체 조건이라고 주장하지 않습니다.
추출은 정해진 표현과 360자 이내의 문장을 지원하며 모든 계약 조건을 자동 해석하는 기능은 아닙니다.</p>
<table><tr><th>확인 항목</th><th>결과</th></tr>
<tr><td>새로 수집한 문서</td><td>2024년 정부·기업 공식 발표 3건 × 2회</td></tr>
<tr><td>지급 조건과 원문 유지</td><td>첫 평가 6/6 · 수정 후 재검증 6/6</td></tr>
<tr><td>SK하이닉스 지원 단계</td><td>첫 평가 2/2 오류(최종 지원을 예비로 표시) → 재검증 2/2 수정 확인</td></tr>
<tr><td>수정 후 첫 생성의 수치·인용 검사</td><td>5/6 통과 · 1건 자동 수정 후 통과</td></tr>
<tr><td>최종 방향과 사전 기준의 일치</td><td>6/6 상승 요인 · 방향 정확도 일반화 불가</td></tr>
<tr><td>프로젝트 자동 테스트</td><td>79개 통과</td></tr></table>
<h2>검증 범위와 해석</h2>
<p>첫 모델 평가 전에 기대 방향과 조건을 기록했습니다. 정답 라벨은 모델에 전달하지 않았으며,
평가 실행 중 코드 해시를 고정하고 분석 캐시·운영 이력 저장을 차단했습니다.
SK실트론 자료의 줄바꿈은 수집 점검 단계에서 수정에 사용했으므로 완전히 손대지 않은 평가 자료가 아닙니다.
첫 평가에서 발견한 지원 단계 오류를 수정한 뒤 같은 자료를 다시 평가했으므로 최종 결과는 회귀 검증입니다.</p>
<p>대상 기사의 관련성은 이 실험에서 미리 지정했습니다. 뉴스 검색·관련성 선별의 정확도를 검증한 결과가 아닙니다.
공식 발표 자료이며 독립적인 언론 취재 기사와 구별해야 합니다. 모두 긍정적 자금 지원 사례로 악재 대조군은 없습니다.</p>
<div class="note"><b>남은 표현상의 한계</b><br>
SK실트론의 최종 승인 조건은 조건란에 정확히 나오지만, 본문 설명에는 ‘조건부’가 생략됩니다.
큐셀 2회차의 ‘국내’는 원문의 미국 내 사업을 뜻해 한국 독자에게 모호할 수 있습니다.
조건 보존 성공을 전체 설명의 완전한 정확성으로 간주하지 않습니다.
또한 기사에 여러 기업·여러 자금 항목이 나오면 조건과 주체를 연결하는 추가 검증이 필요합니다.</div>
""" + "".join(cards) + """
<p>첫 실패와 최종 결과, 입력 출처·본문 해시, 실행 코드 해시는 output/payment-v13-*.json에 별도 보존했습니다.</p>
</main></html>"""
Path("output/payment-v13-validation-report.html").write_text(html, encoding="utf-8")
print("output/payment-v13-validation-report.html")
