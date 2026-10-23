import json
from collections import defaultdict
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sets = {key: json.loads((ROOT / f"output/explanation-v10-{key}.json").read_text(encoding="utf-8"))
        for key in ("regression", "holdout", "korean")}
labels = {"regression": "기존 오류 2건 × 2회", "holdout": "새 기사 4건 × 2회",
          "korean": "추가 한국어 보도 1건 × 2회"}

rows = []
for key, data in sets.items():
    first = sum(bool(r["first"]["findings"]) and r["first"]["findings"][0]["direction"] == r["expected"] for r in data)
    valid = sum(not r["first_errors"] for r in data)
    final = sum(r["match"] for r in data)
    rows.append(f"<tr><td>{labels[key]}</td><td>{first}/{len(data)}</td><td>{valid}/{len(data)}</td><td>{final}/{len(data)}</td></tr>")

groups = defaultdict(list)
for key, data in sets.items():
    for row in data:
        groups[(key, row["id"])].append(row)
cards = []
for (key, ident), results in groups.items():
    row = results[0]
    runs = []
    for r in results:
        f = r["final"]
        runs.append(f"""<div class="run"><b>{r['repeat']}회차 · {e(f['direction'])}</b>
<p>{e(f['reason'])}</p><p class="muted">{e(f['counterpoint'])}</p>
<p class="meta">최초 검사: {e(' / '.join(r['first_errors']) or '통과')} · 모델 호출 {r['calls']}회</p></div>""")
    cards.append(f"""<article><div class="meta">{e(row['date'])} · {labels[key]} · 예상 {e(row['expected'])}</div>
<h3><a href="{e(row['url'], quote=True)}">{e(row['title'])}</a></h3>{''.join(runs)}</article>""")

html = """<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>대출 조건·리콜 영향 설명 검증 v10</title><style>
body{margin:0;background:#f4f5f1;color:#25382f;font:16px/1.75 'Malgun Gothic',sans-serif}
main{max-width:1050px;margin:auto;padding:48px 24px}h1{font-size:34px;letter-spacing:-1.4px}
h2{font-size:23px;margin-top:36px}h3{font-size:18px}a{color:#25634c}
article{background:white;border:1px solid #dce3de;border-radius:12px;padding:24px;margin:20px 0}
.run+.run{border-top:1px solid #e4e9e5;margin-top:20px;padding-top:20px}
.meta{font-size:13px;color:#63766b}.muted{color:#4b6555}.note{padding:22px;background:#fff1d6;border-left:4px solid #b58c3f}
table{width:100%;border-collapse:collapse;background:white}th,td{padding:15px;text-align:left;border-bottom:1px solid #dbe1dc}
.scroll{overflow:auto}
</style><main><div class="meta">천기누설 · v10c · 캐시 없는 실제 기사 평가</div>
<h1>조건을 지우지 않고,<br>영향 범위를 확대하지 않도록.</h1>
<p>기존 오류 기사 2건과 새 기사 5건을 각각 두 번 평가했습니다.
새 기사 중 1건은 같은 SK하이닉스 예비 지원 사건의 한국어 보도로, 새 사건 수는 4개입니다.
2016·2022·2024년 과거 보도이며 현재 뉴스 피드와 운영 이력에는 넣지 않았습니다.</p>
<h2>변경 내용</h2><ul>
<li>의미 검토에서 설명과 반대 근거의 사실성을 각각 판단합니다. 방향이 맞더라도 설명 오류가 있으면 승인하지 않습니다.</li>
<li>근거 없는 전사·국내·단기 영향 축소와 대출 지원 계획을 지우는 표현을 자동 검사합니다. 반대 근거의 숫자도 인용 검사 대상입니다.</li>
<li>지침 보강만으로는 같은 오류가 반복됐습니다. 리콜·대출이 등장하는 기사의 반대 근거는 조건을 임의로 생성하는 대신, 범위·집행을 구분하는 고정 안내로 제공합니다. 이는 원문에서 추출한 반대 사실이 아니라 제품의 평가 한계 안내입니다.</li>
<li>영향 수준을 낮출 때 검토 모델의 새 설명을 사용자 설명에 덧붙이지 않습니다.</li></ul>
<h2>방향과 설명 품질을 구분한 결과</h2>
<div class="scroll"><table><tr><th>평가</th><th>최초 방향 일치</th><th>최초 자동 검사</th><th>최종 방향 일치</th></tr>""" + "".join(rows) + """</table></div>
<p class="meta">자동 검사는 인용·수치·일부 표현 규칙입니다. 의미 전체의 정확성 점수가 아닙니다.
예상 방향은 호출 전에 assistant가 정한 사업 영향 기준이며 독립 전문가 합의 정답이 아닙니다.</p>
<h2>원문 대조에서 확인한 점</h2>
<ul><li>기존 리콜·지원 기사: 최종 4회에서 앞서 문제였던 반대 근거의 ‘국내 영향 없음’, ‘대출 조건 전체 미확정’, ‘투자·집행 시점 임의 추정’이 재발하지 않았습니다. 고정 안내의 효과이며 모델 자체의 사실 추론이 완성됐다는 뜻은 아닙니다.</li>
<li>새 세탁기 리콜 2건: 최종 4회 모두 하락 요인. 대상 지역·무료 조치에서 전사 영향 규모를 축소하지 않았습니다.</li>
<li>새 영문 지원 발표 2건: 4회 모두 숫자 검증 실패로 보류. million/billion을 억·천만 단위로 바꾸면 현재의 문자열 수치 검사가 동치를 인식하지 못합니다. 금액 단위 정규화가 남은 과제입니다.</li>
<li>같은 SK 예비 합의의 한국어 보도: 2회 모두 상승 요인. 대출 조건에 대한 임의 단정은 제거됐지만, 첫 응답은 ‘최대’와 ‘예비’라는 조건을 설명에 충분히 보존하지 못했습니다. 전체 설명 정확성 통과로 보지 않습니다.</li></ul>
<div class="note"><b>아직 남은 한계</b><p>설명 본문은 여전히 모델이 작성합니다. 예비 합의의 조건 생략,
원문의 ‘현재’라는 시점 표현, 수리·환급의 세부 대상 조건이 압축되는 문제를 더 점검해야 합니다.
고정 안내는 기사마다 다른 반대 사실을 요약하는 기능을 일부 줄이는 대신 추정 오류를 줄인 선택입니다.
키워드 기반 안내·규칙은 모든 표현을 포괄하지 못합니다.</p>
<p>새 기사 최종 방향 일치는 10회 중 6회이며 나머지 4회는 보류입니다.
이 수치를 전체 정확도나 주가 예측 성공률로 표현하지 않습니다.</p></div>
<h2>검증 범위</h2><p>수정은 기존 2건으로 진행하고 v10c 코드를 고정한 뒤 새 4건을 평가했습니다.
영문 실패 확인 후 코드 변경 없이 같은 사건의 한국어 보도 1건을 추가했습니다.
선별·검색 품질을 포함한 다기사 앱 평가는 아니며, 원문 확보 이후 개별 기사 판단 평가입니다.
결과 캐시 읽기·쓰기와 운영 이력 저장을 차단했습니다. 자동 테스트 49개가 통과했습니다.</p>
<h2>기사별 최종 출력</h2><p class="meta">출력에 남은 표현 한계는 위 평가와 함께 읽어 주세요. 제목에서 원문으로 이동할 수 있습니다.</p>
""" + "".join(cards) + """<h2>재현 자료</h2>
<p>output/explanation-v10-{regression,holdout,korean}.json 및 단계별 코드 해시, 사전 라벨 파일.
지침만 보강한 초기 결과와 규칙만 보강한 중간 결과도 별도 보존했습니다.
평가 실행 파일: scripts/audit_explanation_v10.py.</p></main></html>"""
path = ROOT / "output/explanation-v10-validation-report.html"
path.write_text(html, encoding="utf-8")
print(str(path))
