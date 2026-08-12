"""End-to-end orchestration for all World Cup ETL sources."""
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.crawlers.fjelstul import FJELSTUL_ADAPTERS
from app.crawlers.historical import WikipediaEditionCrawler
from app.crawlers.news import VietnameseNewsCrawler
from app.crawlers.pipeline import run_adapter
from app.seed import EDITIONS


@dataclass
class EtlSummary:
    runs: list = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def records_seen(self):
        return sum(run.records_seen for run in self.runs)

    @property
    def records_saved(self):
        return sum(run.records_saved for run in self.runs)

    @property
    def records_rejected(self):
        return sum(run.records_rejected for run in self.runs)


def run_worldcup_etl(db: Session, *, year: int | None, include_news: bool = True, include_wikipedia: bool = True) -> EtlSummary:
    summary = EtlSummary()
    adapters = list(FJELSTUL_ADAPTERS)
    if include_wikipedia:
        adapters.append(WikipediaEditionCrawler())
    for adapter in adapters:
        _run(summary, db, adapter, year)

    if include_news:
        news = VietnameseNewsCrawler()
        years = [year] if year else [item[0] for item in EDITIONS]
        for edition_year in years:
            _run(summary, db, news, edition_year)
    return summary


def _run(summary: EtlSummary, db: Session, adapter, year):
    try:
        summary.runs.append(run_adapter(db, adapter, year))
    except Exception as exc:
        summary.errors.append(f"{adapter.code} ({year or 'all'}): {exc}")

