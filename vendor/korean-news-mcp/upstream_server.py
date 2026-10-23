"""
Korean AI News Hub - MCP Server
================================
한국 뉴스 + 글로벌 AI/테크 뉴스를 AI 에이전트에서 바로 사용할 수 있는 MCP 서버.
API 키 없이 바로 작동합니다.
"""

from dataclasses import dataclass
from urllib.parse import quote_plus

import feedparser
import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP


# --- Data Models ---

@dataclass
class NewsArticle:
    title: str
    link: str
    summary: str
    source: str
    published: str
    category: str


# --- Constants ---

KOREAN_CATEGORIES = {
    "속보": "한국 속보",
    "정치": "한국 정치",
    "경제": "한국 경제 금융",
    "사회": "한국 사회",
    "IT": "한국 IT 기술 AI",
    "세계": "세계 국제 뉴스",
    "연예": "한국 연예 엔터테인먼트",
    "스포츠": "한국 스포츠",
}

TECH_CATEGORIES = {
    "AI": "AI artificial intelligence LLM",
    "Claude": "Claude Anthropic AI",
    "OpenAI": "OpenAI GPT ChatGPT",
    "MCP": "MCP model context protocol AI agent",
    "OpenClaw": "OpenClaw AI agent framework",
    "스타트업": "tech startup funding",
    "개발": "software development programming coding",
    "클라우드": "AWS cloud computing kubernetes",
}


# --- Internal helpers ---

def _build_google_news_url(query: str, lang: str = "ko", country: str = "KR") -> str:
    encoded = quote_plus(query)
    return (
        f"https://news.google.com/rss/search?"
        f"q={encoded}&hl={lang}&gl={country}&ceid={country}:{lang}"
    )


def _build_google_news_top_url(topic: str, lang: str = "ko", country: str = "KR") -> str:
    topic_map = {
        "headlines": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZxYUdjU0FtdHZHZ0pMVWlnQVAB",
        "tech": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtdHZHZ0pMVWlnQVAB",
        "business": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtdHZHZ0pMVWlnQVAB",
        "science": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y1RjU0FtdHZHZ0pMVWlnQVAB",
    }
    topic_id = topic_map.get(topic, topic_map["headlines"])
    return (
        f"https://news.google.com/rss/topics/{topic_id}?"
        f"hl={lang}&gl={country}&ceid={country}:{lang}"
    )


def _parse_feed(url: str, category: str, max_items: int = 10) -> list[NewsArticle]:
    articles = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:max_items]:
            source = ""
            if hasattr(entry, "source") and hasattr(entry.source, "title"):
                source = entry.source.title
            elif " - " in entry.title:
                parts = entry.title.rsplit(" - ", 1)
                source = parts[-1] if len(parts) > 1 else ""

            published = ""
            if hasattr(entry, "published"):
                published = entry.published
            elif hasattr(entry, "updated"):
                published = entry.updated

            summary = ""
            if hasattr(entry, "summary"):
                soup = BeautifulSoup(entry.summary, "html.parser")
                summary = soup.get_text(strip=True)[:300]

            articles.append(NewsArticle(
                title=entry.title,
                link=entry.link,
                summary=summary,
                source=source,
                published=published,
                category=category,
            ))
    except Exception as e:
        articles.append(NewsArticle(
            title=f"[Feed Error] {str(e)}",
            link="",
            summary="",
            source="error",
            published="",
            category=category,
        ))
    return articles


def _format_articles(articles: list[NewsArticle]) -> str:
    if not articles:
        return "No news found."
    lines = []
    for i, a in enumerate(articles, 1):
        lines.append(f"### {i}. {a.title}")
        if a.source:
            lines.append(f"   Source: {a.source}")
        if a.published:
            lines.append(f"   Time: {a.published}")
        if a.summary:
            lines.append(f"   Summary: {a.summary}")
        lines.append(f"   Link: {a.link}")
        lines.append("")
    return "\n".join(lines)


def _get_korean_news(category: str = "속보", count: int = 10) -> list[NewsArticle]:
    query = KOREAN_CATEGORIES.get(category, category)
    url = _build_google_news_url(query, lang="ko", country="KR")
    return _parse_feed(url, category, max_items=count)


def _get_tech_news(topic: str = "AI", count: int = 10) -> list[NewsArticle]:
    query = TECH_CATEGORIES.get(topic, topic)
    url = _build_google_news_url(query, lang="en", country="US")
    return _parse_feed(url, topic, max_items=count)


def _search_news(query: str, lang: str = "ko", count: int = 10) -> list[NewsArticle]:
    country = "KR" if lang == "ko" else "US"
    url = _build_google_news_url(query, lang=lang, country=country)
    return _parse_feed(url, f"Search: {query}", max_items=count)


def _get_trending_news(count: int = 15) -> list[NewsArticle]:
    url = _build_google_news_top_url("headlines", lang="ko", country="KR")
    return _parse_feed(url, "Headlines", max_items=count)


def _get_trending_tech(count: int = 15) -> list[NewsArticle]:
    url = _build_google_news_top_url("tech", lang="en", country="US")
    return _parse_feed(url, "Global Tech", max_items=count)


async def _read_article_content(url: str) -> str:
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=15.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        article = (
            soup.find("article")
            or soup.find("div", class_=lambda c: c and "article" in c.lower() if c else False)
            or soup.find("div", class_=lambda c: c and "content" in c.lower() if c else False)
            or soup.find("div", id=lambda i: i and "content" in i.lower() if i else False)
        )

        if article:
            text = article.get_text(separator="\n", strip=True)
        else:
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)

        if len(text) > 3000:
            text = text[:3000] + "\n\n... (truncated at 3000 chars)"

        return text if text.strip() else "Could not extract article content. Please visit the link directly."

    except Exception as e:
        return f"Failed to read article: {str(e)}\nVisit directly: {url}"


# --- MCP Server ---

mcp = FastMCP("korean-news-hub")


@mcp.tool()
def korean_news(category: str = "속보", count: int = 10) -> str:
    """Get Korean news by category.

    Args:
        category: News category. Options: 속보, 정치, 경제, 사회, IT, 세계, 연예, 스포츠
        count: Number of articles (default 10, max 20)
    """
    count = min(count, 20)
    categories = ", ".join(KOREAN_CATEGORIES.keys())
    articles = _get_korean_news(category, count)
    result = f"## Korean News - {category}\n\n"
    result += _format_articles(articles)
    result += f"\n---\nAvailable categories: {categories}"
    return result


@mcp.tool()
def tech_news(topic: str = "AI", count: int = 10) -> str:
    """Get global AI/tech news by topic.

    Args:
        topic: Tech topic. Options: AI, Claude, OpenAI, MCP, OpenClaw, 스타트업, 개발, 클라우드
        count: Number of articles (default 10, max 20)
    """
    count = min(count, 20)
    topics = ", ".join(TECH_CATEGORIES.keys())
    articles = _get_tech_news(topic, count)
    result = f"## Global Tech News - {topic}\n\n"
    result += _format_articles(articles)
    result += f"\n---\nAvailable topics: {topics}"
    return result


@mcp.tool()
def news_search(query: str, language: str = "ko", count: int = 10) -> str:
    """Search news by keyword.

    Args:
        query: Search keyword (e.g. "Samsung AI", "Claude Code", "MCP server")
        language: "ko" (Korean) or "en" (English)
        count: Number of articles (default 10, max 20)
    """
    count = min(count, 20)
    articles = _search_news(query, lang=language, count=count)
    lang_label = "Korean" if language == "ko" else "English"
    result = f"## News Search: \"{query}\" ({lang_label})\n\n"
    result += _format_articles(articles)
    return result


@mcp.tool()
def trending(scope: str = "korea") -> str:
    """Get current trending/headline news.

    Args:
        scope: "korea" (Korean headlines) or "tech" (global tech trends)
    """
    if scope == "tech":
        articles = _get_trending_tech(15)
        result = "## Global Tech Trends NOW\n\n"
    else:
        articles = _get_trending_news(15)
        result = "## Korean Headlines NOW\n\n"
    result += _format_articles(articles)
    return result


@mcp.tool()
async def read_article(url: str) -> str:
    """Read and extract article content from a URL.

    Args:
        url: The article URL to read
    """
    content = await _read_article_content(url)
    result = f"## Article Content\n\nSource: {url}\n\n---\n\n{content}"
    return result


@mcp.custom_route("/health", ["GET"])
async def health(request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "ok", "service": "korean-news-hub", "tools": 6})


@mcp.tool()
def daily_briefing() -> str:
    """Generate a comprehensive daily news briefing.
    Combines Korean headlines + AI/tech news + Claude/Anthropic news.
    """
    result = "# Daily News Briefing\n\n"

    result += "## Korean Headlines\n\n"
    kr_articles = _get_trending_news(7)
    result += _format_articles(kr_articles)

    result += "\n## AI / Tech News\n\n"
    ai_articles = _get_tech_news("AI", 5)
    result += _format_articles(ai_articles)

    result += "\n## Claude & Anthropic\n\n"
    claude_articles = _get_tech_news("Claude", 3)
    result += _format_articles(claude_articles)

    result += "\n---\nFor more: use korean_news, tech_news, or news_search tools"
    return result


if __name__ == "__main__":
    import os
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run()
    else:
        port = int(os.environ.get("PORT", "8080"))
        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = port
        from mcp.server.transport_security import TransportSecuritySettings
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        )

        mcp.run(transport=transport)
