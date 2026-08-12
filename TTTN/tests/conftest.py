import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db, make_engine
from app.importer import import_json
from app.main import app
from app.models import NewsArticle


@pytest.fixture
def client(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    with TestingSession() as db:
        import_json(db, "data/example_world_cup.json")
        db.add_all([
            NewsArticle(
                source="Test News", url="https://example.test/world-cup",
                url_hash="relevant-news", title="Lịch thi đấu World Cup 2022",
                tournament_year=2022, is_world_cup=True,
            ),
            NewsArticle(
                source="Test News", url="https://example.test/asean-cup",
                url_hash="excluded-news", title="Tin ASEAN Cup hôm nay",
                tournament_year=2022, is_world_cup=False,
            ),
        ])
        db.commit()

    def override_db():
        with TestingSession() as db:
            yield db
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
