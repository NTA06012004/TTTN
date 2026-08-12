from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
import re

import feedparser
from bs4 import BeautifulSoup

from app.config import get_settings
from app.crawlers.base import CrawlerAdapter, SourceRecord
from app.crawlers.http import crawler_session
from app.crawlers.transform import canonical_url, clean_text, content_key
from app.news_relevance import is_world_cup_news


FEEDS = {
    "VnExpress": "https://vnexpress.net/rss/the-thao.rss",
    "Thanh Nien": "https://thanhnien.vn/rss/the-thao.rss",
    "Tuoi Tre": "https://tuoitre.vn/rss/the-thao.rss",
    "VietnamNet": "https://vietnamnet.vn/rss/the-thao.rss",
    "Dan Tri": "https://dantri.com.vn/rss/the-thao.rss",
    "Lao Dong": "https://laodong.vn/rss/the-thao.rss",
}
YEAR = re.compile(r"\b(19[3-9]\d|20\d{2})\b")
ARCHIVE_DOMAINS = ("vnexpress.net", "tuoitre.vn", "thanhnien.vn", "vietnamnet.vn", "dantri.com.vn", "laodong.vn")


@dataclass(frozen=True)
class ArticleItem:
    source: str
    url: str
    title: str
    summary: str | None
    published_at: datetime | None
    tournament_year: int | None
    image_url: str | None = None

    @property
    def url_hash(self) -> str:
        return sha256(self.url.encode("utf-8")).hexdigest()


def crawl_all() -> list[ArticleItem]:
    settings = get_settings()
    session = crawler_session()
    items: list[ArticleItem] = []
    for source, url in FEEDS.items():
        response = session.get(url, timeout=settings.request_timeout_seconds)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        for entry in feed.entries:
            title = str(entry.get("title", "")).strip()
            summary = BeautifulSoup(str(entry.get("summary", "")), "html.parser").get_text(" ", strip=True)
            haystack = f"{title} {summary}"
            if not is_world_cup_news(title, summary):
                continue
            year_match = YEAR.search(haystack)
            media = entry.get("media_content") or []
            image_url = media[0].get("url") if media else None
            items.append(ArticleItem(source, entry.link, title, summary or None, _parse_date(entry.get("published")), int(year_match.group()) if year_match else None, image_url))
    return items


def crawl_archive(year: int) -> list[ArticleItem]:
    """Tìm metadata bài báo cũ theo năm qua Google News RSS.

    URL cuối vẫn dẫn về tòa soạn; hệ thống chỉ lưu tiêu đề/tóm tắt/link và nguồn.
    """
    settings = get_settings()
    query = f'"World Cup {year}" (' + " OR ".join(f"site:{domain}" for domain in ARCHIVE_DOMAINS) + ")"
    response = crawler_session().get("https://news.google.com/rss/search", params={"q": query, "hl": "vi", "gl": "VN", "ceid": "VN:vi"}, timeout=settings.request_timeout_seconds)
    response.raise_for_status()
    results = []
    for entry in feedparser.parse(response.content).entries:
        publisher = entry.get("source", {}).get("title", "Google News")
        summary = BeautifulSoup(str(entry.get("summary", "")), "html.parser").get_text(" ", strip=True)
        title = str(entry.get("title", "")).strip()
        if not is_world_cup_news(title, summary):
            continue
        results.append(ArticleItem(publisher, entry.link, title, summary or None, _parse_date(entry.get("published")), year))
    return results


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        result = parsedate_to_datetime(value)
        return result if result.tzinfo else result.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


class VietnameseNewsCrawler(CrawlerAdapter):
    code = "vietnamese_news"
    name = "Vietnamese World Cup news"
    source_type = "news"
    base_url = "https://news.google.com/rss"

    def crawl(self, *, year: int | None = None):
        items = crawl_archive(year) if year else crawl_all()
        for item in items:
            if not is_world_cup_news(item.title, item.summary):
                continue
            url = canonical_url(item.url)
            payload = {
                "external_id": content_key(url), "url": url, "source": clean_text(item.source, nullable=False),
                "title": clean_text(item.title, nullable=False), "summary": clean_text(item.summary),
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "tournament_year": item.tournament_year, "image_url": item.image_url,
            }
            yield SourceRecord("news", payload["external_id"], url, payload)
