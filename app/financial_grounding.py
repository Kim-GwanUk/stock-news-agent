"""Exact currency/unit normalization. No exchange-rate conversion or fuzzy matching."""
import re
from decimal import Decimal

NUM = r"\d[\d,]*(?:\.\d+)?"
EN = re.compile(rf"(?P<prefix>US\$|\$|USD\s+|KRW\s+)?(?P<num>{NUM})\s*(?P<scale>trillion|billion|million|thousand)?\s*(?P<suffix>U\.S\.\s*dollars?|dollars?|USD|won|KRW)?", re.I)
KO = re.compile(rf"(?P<value>(?:{NUM}\s*(?:[십백천]\s*)?[조억만]\s*)+(?:{NUM}\s*)?|{NUM})\s*(?P<currency>달러|원)")
SCALES = {"thousand": 1000, "million": 10**6, "billion": 10**9, "trillion": 10**12}


def amounts(text):
    found = []
    for m in KO.finditer(text):
        value, total, last = m["value"].replace(",", ""), Decimal(0), 0
        for part in re.finditer(r"(\d+(?:\.\d+)?)\s*([십백천]\s*)?([조억만])", value):
            total += Decimal(part[1]) * {"":1,"십":10,"백":100,"천":1000}[(part[2] or "").strip()] * {"조":10**12, "억":10**8, "만":10**4}[part[3]]
            last = part.end()
        if value[last:].strip():
            total += Decimal(value[last:].strip())
        found.append((m.start(), m.end(), "USD" if m["currency"] == "달러" else "KRW", total))
    for m in EN.finditer(text):
        if not (m["prefix"] or m["suffix"]) or any(m.start() < b and m.end() > a for a,b,_,_ in found):
            continue
        currency = "KRW" if re.search(r"KRW|won", (m["prefix"] or "") + (m["suffix"] or ""), re.I) else "USD"
        value = Decimal(m["num"].replace(",", "")) * SCALES.get((m["scale"] or "").lower(), 1)
        found.append((m.start(), m.end(), currency, value))
    return sorted(found)


def without_amounts(text):
    for a,b,_,_ in reversed(amounts(text)):
        text = text[:a] + " " + text[b:]
    return text


def numeric_errors(text, quotes):
    source = {(c,v) for _,_,c,v in amounts(quotes)}
    if any((c,v) not in source for _,_,c,v in amounts(text)):
        return ["설명 금액의 통화·값이 선택한 인용과 일치하지 않습니다. 환율 환산·합산 없이 원문의 금액을 보존하세요."]
    # A count/date containing "10" cannot substantiate "10%". Preserve units.
    percentages = lambda s: {Decimal(m.group(1).replace(",", "")) for m in
        re.finditer(r"(\d[\d,]*(?:\.\d+)?)\s*%", s)}
    if not percentages(text).issubset(percentages(quotes)):
        return ["설명 비율(%)이 선택한 인용의 비율과 일치하지 않습니다. 건수·날짜를 비율 근거로 사용하거나 반올림하지 마세요."]
    numbers = lambda s: set(re.findall(r"\d+(?:\.\d+)*", without_amounts(s).replace(",", "")))
    if not numbers(text).issubset(numbers(quotes)):
        return ["설명 또는 반대 근거에 인용으로 확인하지 못한 수치가 있습니다. 해당 근거를 선택하거나 불필요한 수치를 생략하세요."]
    return []


def capped(text, start):
    return bool(re.search(r"(?:최대|한도(?:는|가|인)?|up\s+to(?:\s+a)?)\s*$", text[max(0,start-24):start], re.I))

def quantities(text):
    return amounts(text) + [(m.start(),m.end(),"percent",Decimal(m[1]))
                           for m in re.finditer(r"(\d+(?:\.\d+)?)\s*%", text)]


def preserve_caps(reason, quotes):
    upper = {(c,v) for a,_,c,v in quantities(quotes) if capped(quotes,a)}
    for a,_,c,v in sorted(quantities(reason), reverse=True):
        if (c,v) in upper and not capped(reason,a):
            reason = reason[:a] + "최대 " + reason[a:]
    return reason


def preliminary_status(body):
    # Current announcement lead only: do not classify a final award by historical PMT mentions.
    lead = body[:800]
    preliminary = re.search(r"preliminary\s+(?:memorandum|terms|agreement)|비구속.{0,12}예비|예비거래각서|예비\s*합의", lead, re.I)
    final = re.search(r"최종.{0,12}(확정|계약|체결)|final\s+award|award\s+(?:follows|comes\s+after)\s+the\s+previously", lead, re.I)
    return bool(preliminary and not final), bool(re.search(r"non.binding|비구속", lead, re.I))


def preserve_stage(reason, body):
    preliminary, nonbinding = preliminary_status(body)
    if preliminary and (not re.search(r"예비|잠정", reason) or (nonbinding and "비구속" not in reason)):
        reason = ("이 지원은 비구속적 예비 합의 단계입니다. " if nonbinding else
                  "이 지원은 예비 합의 단계입니다. ") + reason
    return reason


def qualification_errors(reason, body, quotes):
    errors = []
    preliminary, nonbinding = preliminary_status(body)
    if preliminary:
        if not re.search(r"예비|잠정", reason):
            errors.append("현재 지원은 예비 합의 단계입니다. 설명 본문에 '예비 합의'를 명시하고 최종 확정·수령으로 표현하지 마세요.")
        if nonbinding and "비구속" not in reason:
            errors.append("원문의 비구속 조건이 빠졌습니다. 설명 본문에 '비구속적 예비 합의'를 명시하세요.")
        if re.search(r"(?:최종\s*확정|수령\s*완료|입금\s*완료)(?:됐|되었|됨|받|했|함)", reason):
            errors.append("예비 지원을 최종 확정·수령 완료로 표현했습니다. 예비 합의 사실과 향후 지원 가능성만 설명하세요.")
    upper = {(c,v) for a,_,c,v in quantities(quotes) if capped(quotes,a)}
    for a,_,c,v in quantities(reason):
        if (c,v) in upper and not capped(reason,a):
            errors.append("설명 금액의 '최대' 한도가 빠졌습니다. 해당 금액 바로 앞에 '최대'를 명시하거나 금액을 생략하세요.")
    if (re.search(r"will\s+distribute\s+the\s+funds|마일스톤.{0,30}지급", body, re.I)
            and re.search(r"지원(?:금)?을?\s*받았|자금(?:을)?\s*받았|수령(?:을)?\s*완료|입금(?:이)?\s*완료", reason)):
        errors.append("원문은 사업 단계 달성에 따른 향후 지급입니다. 이미 자금을 받았다고 표현하지 말고 지원 결정과 단계별 지급 조건을 구분하세요.")
    return errors
