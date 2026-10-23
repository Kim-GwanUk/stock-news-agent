"""Conservative, reversible grouping of matching vehicle price announcements."""
import re
from datetime import datetime


def launch_identity(article):
    title = article.get("title", "")
    body = article.get("body", "")
    if re.search(r"리콜|취소|철회|중단|인하|인상|정정|수정|연기|결함|사고|해지", title):
        return None
    if not re.search(r"신형|디\s*올\s*뉴|올\s*뉴", title):
        return None
    if not re.search(r"가솔린|하이브리드|파워트레인|트림", body):
        return None
    names = re.findall(r"[‘'“\"]([^’'”\"]{2,50})[’'”\"]", title)
    names += re.findall(r"신형\s+([가-힣A-Za-z0-9-]+)", title)
    products = set()
    for name in names:
        if re.search(r"신형|디\s*올\s*뉴|올\s*뉴", name):
            name = re.sub(r"디\s*올\s*뉴|올\s*뉴|신형", "", name)
        name = re.sub(r"\s+", "", name)
        if 2 <= len(name) <= 20 and name in re.sub(r"\s+", "", body):
            products.add(name)
    if not products:
        return None
    try:
        day = datetime.fromisoformat(article["published"].replace("Z", "+00:00")).date()
    except (KeyError, ValueError, TypeError, AttributeError):
        return None
    # Only explicit price paragraphs, excluding promotional gift values.
    price_text = " ".join(p for p in body.splitlines()
                          if re.search(r"가격|가솔린|하이브리드", p)
                          and not re.search(r"상품권|경품|추첨", p))
    prices = frozenset(int(v.replace(",", "")) for v in re.findall(r"([\d,]+)\s*만\s*원", price_text))
    if len(prices) < 3:
        return None
    generations = frozenset(re.findall(r"(\d+)세대", title + " " + body[:700]))
    return day, products, prices, generations


def same_product_launch(left, right):
    a, b = launch_identity(left), launch_identity(right)
    return bool(a and b and a[0] == b[0] and a[1] & b[1] and a[2] == b[2]
                and not (a[3] and b[3] and a[3] != b[3]))


def display_articles(result):
    """Enrich copies of saved articles using exact stored quotes; never rewrite history."""
    findings = {f["article_id"]: f for f in result.get("findings", [])}
    articles = [dict(a) for a in result["articles"]]
    representatives = []
    for article in sorted(articles, key=lambda a: (a.get("published", ""), a["id"]), reverse=True):
        if article.get("duplicate_of") or not article.get("analysis_candidate"):
            continue
        finding = findings.get(article["id"], {})
        quotes = finding.get("fact_ledger", {}).get("facts", [])
        enriched = {**article, "body": article.get("body") or "\n".join(f["quote"] for f in quotes)}
        parent = next((p for p in representatives if same_product_launch(p, enriched)), None)
        if parent:
            article["duplicate_of"] = parent["id"]
            article["display_duplicate"] = True
        else:
            representatives.append(enriched)
    return articles
