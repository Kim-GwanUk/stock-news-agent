"""Preserve complete financing-condition sentences without inventing missing terms."""
import re


def condition_quotes(body):
    found = []
    for paragraph in [body]:
        for match in re.finditer(r".+?(?:[.!?](?=\s|$)|$)", paragraph, re.S):
            sentence = match.group().strip()
            financing = re.search(r"funds?|funding|loan|financing|지원금|보조금|대출|자금", sentence, re.I | re.S)
            condition = re.search(
                r"(?:distribut|disburs)\w*.{0,100}(?:based on|subject to)"
                r"|(?:subject to|conditional on|contingent on).{0,100}(?:conditions|milestones|completion)"
                r"|(?:conditions|조건).{0,100}(?:before|충족)"
                r"|(?:마일스톤|단계|조건).{0,60}(?:따라|충족).{0,30}지급",
                sentence, re.I | re.S)
            # Never cut away a qualifier merely to fit the evidence field.
            if financing and condition and 10 <= len(sentence) <= 360 and sentence not in found:
                found.append(sentence)
    return found


def condition_limitation(quotes):
    # One complete sentence fits both display and evidence limits. Explicitly partial.
    text = re.sub(r"\s+", " ", quotes[0]).lower()
    summary = ""
    if re.search(r"(?:disburse|distribute) the funds based on .{0,60}completion of project milestones", text):
        summary = "사업 단계(마일스톤) 달성이 지급 조건입니다. "
    elif "final approval of the loan remains subject to completion" in text and "closing conditions" in text:
        summary = "최종 대출 승인에는 종결 조건 충족이 필요합니다. "
    elif ("technical, legal, environmental, and financial conditions" in text
          and "before" in text and "financing documents and funds the loan" in text):
        summary = "최종 금융 문서 체결·집행 전에 기술·법률·환경·재무 조건 충족이 필요합니다. "
    return (summary + "원문에 명시된 지원·지급 조건 중 하나: “" + quotes[0] +
            "” 약정과 실제 집행은 구분하며, 다른 조건·일정은 원문이나 후속 공시를 함께 확인해야 합니다.")
