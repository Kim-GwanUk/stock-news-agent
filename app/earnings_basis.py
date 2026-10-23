"""Conservative, source-backed comparison axes for earnings headlines."""
import re

EARNINGS_TITLE = re.compile(r"실적|잠정|영업익|순이익|earnings|financial results|quarter.*results", re.I)
METRIC = r"(?:operating profit|net profit|profitability|earnings)"
DOWN = r"(?:declined|decreased|fell|dropped)"
UP = r"(?:increased|grew|rose|improved)"


def comparisons(article):
    if not EARNINGS_TITLE.search(article.get("title", "")):
        return []
    rows = []
    # Only the report's lead, never an arbitrary later business segment.
    paragraphs = [p.strip() for p in article.get("body", "").splitlines() if p.strip()]
    for index, paragraph in enumerate(paragraphs[:6]):
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
            if re.search(r"\b(?:will|expects?|expected|forecast|outlook)\b|전망|예상|예정", sentence, re.I):
                continue
            # Require the metric to be the grammatical subject, not "division X's profit".
            subject = re.match(rf"\s*(?:({METRIC})\b|(?:연결(?: 기준)?\s*)?(?:영업이익|순이익|수익성)(?:은|이|는|가)?)", sentence, re.I)
            if not subject:
                continue
            basis = ("yoy" if re.search(r"year.on.year|year.over.year|from (?:a|the previous) year|전년\s*(?:동기|대비)", sentence, re.I)
                     else "qoq" if re.search(r"quarter.on.quarter|previous quarter|prior quarter|전분기|전\s*분기", sentence, re.I)
                     else None)
            if not basis:
                continue
            down = re.search(rf"\b{DOWN}\b|\bdown\s+[\d.]+|감소|하락|줄었|줄어", sentence, re.I)
            up = re.search(rf"\b{UP}\b|\bup\s+[\d.]+|증가|상승|늘었|늘어", sentence, re.I)
            if bool(down) == bool(up):
                continue
            # Avoid a segment-specific claim even when it begins with "Operating profit".
            if re.search(r"\b(?:division|segment|business unit)\b|사업부|부문", sentence, re.I):
                continue
            rows.append({"paragraph_index":index, "basis":basis,
                         "direction":"down" if down else "up", "quote":sentence.strip()})
    return rows


def resolved_effect(rows):
    # Explicit YoY leads; QoQ is used only if YoY is absent. Conflicts stay mixed.
    chosen = [r for r in rows if r["basis"] == "yoy"] or [r for r in rows if r["basis"] == "qoq"]
    signs = {r["direction"] for r in chosen}
    if signs == {"down"}:
        return "earnings_down"
    if signs == {"up"}:
        return "earnings_up"
    if len(signs) > 1:
        return "unclear"
    return None
