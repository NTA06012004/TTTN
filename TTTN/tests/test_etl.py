import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.crawlers.base import CrawlerAdapter, SourceRecord
from app.crawlers.fjelstul import FjelstulGoalsCrawler, FjelstulSubstitutionsCrawler
from app.crawlers.pipeline import run_adapter
from app.crawlers.transform import DataQualityError, canonical_url, clean_text, person_name
from app.database import Base
from app.models import DataProvenance, EtlReject, Match, Tournament
from app.news_relevance import is_world_cup_news


class FakeMatchCrawler(CrawlerAdapter):
    code = "fake_matches"
    name = "Fake matches"
    source_type = "test"
    base_url = "https://example.test/matches"

    def __init__(self, invalid=False):
        self.invalid = invalid

    def crawl(self, *, year=None):
        away = "Argentina" if self.invalid else "France"
        yield SourceRecord("match", "M-2022-test", self.base_url, {
            "external_id": "M-2022-test", "year": 2022, "date": "2022-12-18", "stage": "final",
            "home_team": {"external_id": "T-ARG", "name": "Argentina", "code": "ARG"},
            "away_team": {"external_id": "T-FRA", "name": away, "code": "FRA"},
            "home_score": 3, "away_score": 3,
        })


def test_transform_cleaning():
    assert clean_text("  World\u00a0 Cup  ") == "World Cup"
    assert person_name("Lionel", "Messi") == "Lionel Messi"
    assert canonical_url("HTTPS://Example.COM/news/?utm_source=x&a=1#top") == "https://example.com/news?a=1"


@pytest.mark.parametrize("title", [
    "Lịch thi đấu vòng loại World Cup 2026",
    "Argentina vô địch Cúp thế giới 2022",
    "FIFA World Cup 2030 sẽ diễn ra ở đâu?",
])
def test_world_cup_news_classifier_accepts_relevant_articles(title):
    assert is_world_cup_news(title)


@pytest.mark.parametrize("title", [
    "Kết quả FIFA Club World Cup 2025",
    "Đội tuyển nữ dự Women's World Cup",
    "Việt Nam vào vòng chung kết Futsal World Cup",
    "Khai mạc U-20 World Cup",
    "World Cup bóng chuyền khởi tranh",
    "Tin bóng đá và đội tuyển hôm nay",
])
def test_world_cup_news_classifier_rejects_unrelated_articles(title):
    assert not is_world_cup_news(title)


def test_goal_transform_normalizes_player_and_event():
    row = {
        "goal_id": "G-1", "match_id": "M-1", "team_id": "T-ARG",
        "team_name": " Argentina ", "team_code": "ARG", "player_team_id": "T-ARG",
        "player_team_name": "Argentina", "player_team_code": "ARG", "player_id": "P-10",
        "given_name": " Lionel ", "family_name": "Messi", "position_code": "FW",
        "minute_regulation": "23", "minute_stoppage": "0", "penalty": "1", "own_goal": "0",
    }
    payload = FjelstulGoalsCrawler().transform(row, 2022)
    assert payload["event_type"] == "penalty_goal"
    assert payload["player"]["full_name"] == "Lionel Messi"
    assert payload["team"]["name"] == "Argentina"
    assert payload["minute"] == 23


def test_substitution_rejects_ambiguous_direction():
    with pytest.raises(DataQualityError, match="exactly one"):
        FjelstulSubstitutionsCrawler().transform({"going_off": "0", "coming_on": "0"}, 2022)


def test_etl_is_idempotent(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'etl.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        db.add(Tournament(year=2022, name="World Cup 2022")); db.commit()
        first = run_adapter(db, FakeMatchCrawler(), 2022)
        second = run_adapter(db, FakeMatchCrawler(), 2022)
        assert (first.records_saved, second.records_saved) == (1, 0)
        assert db.scalar(select(func.count()).select_from(Match)) == 1
        assert db.scalar(select(func.count()).select_from(DataProvenance)) == 1


def test_invalid_record_is_quarantined(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'reject.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        db.add(Tournament(year=2022, name="World Cup 2022")); db.commit()
        run = run_adapter(db, FakeMatchCrawler(invalid=True), 2022)
        assert run.status == "partial"
        assert run.records_rejected == 1
        assert db.scalar(select(func.count()).select_from(EtlReject)) == 1
        assert db.scalar(select(func.count()).select_from(Match)) == 0
