"""Conservative candidate ranking, not a claim of business impact."""
import re

ALIASES = {"005930": ["삼성전자"], "000660": ["SK하이닉스", "하이닉스"],
           "005380": ["현대자동차", "현대차"], "018260": ["삼성에스디에스", "삼성SDS"],
           "055550": ["신한지주", "신한금융지주"], "105560": ["KB금융", "KB금융지주"],
           "086790": ["하나금융지주", "하나금융"], "316140": ["우리금융지주", "우리금융"],
           "010950": ["S-Oil", "S-OIL", "에쓰오일", "에스오일"],
           "005490": ["POSCO홀딩스", "포스코홀딩스", "POSCO Holdings"],
           "071050": ["한국금융지주"], "138040": ["메리츠금융지주"]}

# Group labels are search hints, not unconditional legal-entity aliases.
GROUP_NAMES = {"086790": ["하나금융그룹"], "055550": ["신한금융그룹"],
               "105560": ["KB금융그룹"], "316140": ["우리금융그룹"],
               "005490": ["포스코그룹"]}

def normalized(text):
    return re.sub(r"\s+", "", text).casefold()

def visit_without_new_event(article):
    title = normalized(article.get("title", ""))
    if not any(word in title for word in ("방문", "찾은", "찾아", "시찰", "벤치마킹")):
        return False
    body = normalized(article.get("body", ""))
    # Concrete new agreements/operations may coexist with a visit; don't block those.
    return not any(word in body for word in
                   ("계약을체결", "투자를확정했다", "양산을시작했다", "가동을시작했다"))

def rank(stock, article):
    names = [stock["name"], *ALIASES.get(stock["code"], []), *GROUP_NAMES.get(stock["code"], [])]
    title = normalized(article.get("title", ""))
    snippet = normalized(article.get("description", ""))
    in_title = any(normalized(n) in title for n in names)
    in_snippet = any(normalized(n) in snippet for n in names)
    score = 4 if in_title else 1 if in_snippet else 0
    business = any(w in title for w in ["계약", "실적", "매출", "영업이익", "수주", "생산", "공급",
                                        "출하", "증설", "소송", "과징금", "리콜", "금융지원", "상장", "인수"])
    market = any(w in title for w in ["코스피", "코스닥", "거래대금", "거래량", "순매수",
                                     "순매도", "회전율", "주가", "급등", "급락", "시가총액"])
    roundup = market and not business
    if roundup:
        score -= 2
    return {"relevant": in_title or in_snippet, "relevance_score": score,
            "market_roundup": roundup,
            "relevance_note": "제목에 종목 언급" if in_title else "검색 설명에 종목 언급" if in_snippet else "종목 관련성 미확인"}
