import csv
from datetime import date
from io import StringIO

from app.config import get_settings
from app.crawlers.base import CrawlerAdapter, SourceRecord
from app.crawlers.http import crawler_session


class InternationalResultsCrawler(CrawlerAdapter):
    """Các trận World Cup từ bộ dữ liệu quốc tế mở của martj42.

    Dataset bao phủ từ 1872 và được lọc chính xác tournament='FIFA World Cup'.
    Adapter chỉ chuẩn hóa; pipeline chịu trách nhiệm map tên đội và upsert.
    """

    code = "international_results"
    name = "International football results"
    source_type = "historical_matches"
    base_url = "https://raw.githubusercontent.com/martj42/international_results/master/data/results.csv"

    def crawl(self, *, year: int | None = None):
        settings = get_settings()
        response = crawler_session().get(self.base_url, timeout=settings.request_timeout_seconds)
        response.raise_for_status()
        for row in csv.DictReader(StringIO(response.text)):
            if row.get("tournament") != "FIFA World Cup":
                continue
            played_on = date.fromisoformat(row["date"])
            if year and played_on.year != year:
                continue
            key = f'{row["date"]}:{row["home_team"]}:{row["away_team"]}'
            yield SourceRecord("match", key, self.base_url, {
                "external_id": key,
                "year": played_on.year,
                "date": row["date"],
                "stage": "Unknown",
                "home_team": {"name": row["home_team"]},
                "away_team": {"name": row["away_team"]},
                "home_score": int(row["home_score"]),
                "away_score": int(row["away_score"]),
                "stadium": {
                    "name": None,
                    "city": row.get("city"),
                    "country": row.get("country"),
                },
                "neutral": row.get("neutral") == "TRUE",
            })


class WikipediaEditionCrawler(CrawlerAdapter):
    """Metadata/đội hình theo từng kỳ qua MediaWiki API (nguồn có attribution)."""

    code = "wikipedia_editions"
    name = "Wikipedia World Cup editions"
    source_type = "encyclopedia"
    base_url = "https://en.wikipedia.org/w/api.php"

    def crawl(self, *, year: int | None = None):
        years = [year] if year else list(range(1930, 2027, 4))
        settings = get_settings()
        for edition in years:
            if edition in (1942, 1946):
                continue
            title = f"{edition} FIFA World Cup"
            response = crawler_session().get(self.base_url, params={"action": "query", "prop": "extracts|info", "exintro": 1, "explaintext": 1, "inprop": "url", "titles": title, "format": "json", "formatversion": 2}, timeout=settings.request_timeout_seconds)
            response.raise_for_status()
            page = response.json()["query"]["pages"][0]
            if "missing" not in page:
                yield SourceRecord("tournament", str(edition), page.get("fullurl", ""), {"year": edition, "title": page.get("title"), "overview": page.get("extract")})


ADAPTERS = {adapter.code: adapter for adapter in (InternationalResultsCrawler(), WikipediaEditionCrawler())}
