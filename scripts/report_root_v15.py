"""Report frozen-source regression honestly, including failed reruns."""
import json
from html import escape as e
from pathlib import Path
from collections import Counter

rows = json.loads(Path("output/root-v15-stable.json").read_text(encoding="utf-8"))
parts = []
for row in rows:
    result = row["result"]
    selected = [a for a in result["articles"] if a.get("analysis_candidate")]
    findings = {f["article_id"]: f for f in result["findings"]}
    counts = Counter(findings[a["id"]]["direction"] for a in selected)
    parts.append(f'<h2>{e(result["stock"]["name"])}</h2><p>선별 {len(selected)}건 · {e(str(dict(counts)))}</p>')
    for a in selected:
        f = findings[a["id"]]
        parts.append(f'<article><h3>{e(a["title"])}</h3><b>{e(f["direction"])} · {e(f["impact"])}</b>'
                     f'<p>{e(f["reason"])}</p><p class="muted">{e(f.get("counterpoint",""))}</p></article>')
    duplicates = [a for a in result["articles"] if a.get("duplicate_of")]
    parts.append(f'<p>중복 제외: {len(duplicates)}건</p>')

html = """<!doctype html><html lang="ko"><meta charset="utf-8"><title>뉴스 분석 원인 추적 · v15</title>
<style>body{max-width:1000px;margin:50px auto;padding:0 24px;background:#f6f7f9;color:#202936;font:16px/1.8 system-ui}
article,section{background:white;border:1px solid #dfe3e8;border-radius:12px;padding:20px;margin:16px 0}
h1{font-size:30px}h3{margin-top:0}.muted{color:#606b7a}b{color:#245a84}</style>
<h1>뉴스 분석 원인 추적 · v15</h1>
<p>2026-10-21 · 네 종목의 기존 실제 기사 원문을 고정한 회귀 검증. 새로운 독립 기사 표본의 정확도 평가가 아닙니다.</p>
<section><h2>확인한 개선</h2><ul>
<li>중복 참조 순서와 날짜 정렬 순서가 달라 중복 표시가 무시되던 오류를 수정했습니다.</li>
<li>같은 협약 발표명·발표일을 확인하는 제한적 중복 규칙을 추가했습니다. 현대차 실증 기사 4건이 대표 1건으로 묶였습니다.</li>
<li>직원 개인 강연·단순 사회공헌과 사업 사건을 구분했습니다.</li>
<li>잘못된 기사만 재생성하고 통과한 분석은 보존합니다. 비율은 비율끼리 검증해 10.03%를 10곳으로 뒷받침하는 오류를 막았습니다.</li>
<li>실증 일정에서 실적 발생 시점을 만들어내는 설명을 검증합니다. 실제 실적 악재는 최종 하락 요인으로 유지됐습니다.</li></ul></section>
<section><h2>남은 문제와 근원</h2>
<p>사업 양수도 기사는 최초 금액 오류를 수정하면서 다른 수치를 추가해 재검증에 실패했습니다.
고정된 사실·조건을 먼저 확정하지 않고 자유로운 설명을 다시 생성하는 구조가 원인입니다.</p>
<p>삼성전자 설명은 반대 근거에 증권사 추정을 표시했지만 첫 문장은 계약을 확정처럼 표현합니다.
에코프로비엠의 거래제도 기사도 사업 분석 후보로 들어왔습니다. 두 번째 기사는 증자 사실도 포함하므로 단순 시장 기사와 일괄 제외할 수 없습니다.
모델의 관련성·사업 사건 판단 및 의미 검토가 흔들리는 문제가 남아 있습니다.</p>
<p>다음 구조 개선은 사건별 사실(발생/예정/추정), 주체, 금액, 조건을 원문 위치와 함께 먼저 고정하고 그 범위에서 설명을 작성하는 것입니다.
현재 제한적 중복 규칙은 모든 종류의 계약·실적 기사를 포괄하지 않으며, 아래 결과가 전체 정확도를 뜻하지 않습니다.</p></section>
<section><h2>검증 범위</h2><p>기존 검색 결과 80건·본문 확보 29건을 재사용했습니다.
캐시를 끄고 실제 모델을 호출했으며 관심 종목·분석 이력은 수정하지 않았습니다.
최종 코드 회귀 테스트 91개 통과. before / after / final / checked / stable 실행 결과와 각 단계 오류·원문 인용은 JSON에 보존했습니다.
아래 설명은 실제 모델 출력 그대로이며, 위의 잔여 오류를 포함합니다.</p></section>
"""
Path("output/root-v15-validation-report.html").write_text(html + "".join(parts) + "</html>", encoding="utf-8")
