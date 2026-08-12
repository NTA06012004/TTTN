import argparse

from sqlalchemy import select

from app.crawlers.fjelstul import FJELSTUL_ADAPTERS
from app.crawlers.historical import ADAPTERS as LEGACY_ADAPTERS
from app.crawlers.news import VietnameseNewsCrawler
from app.crawlers.pipeline import run_adapter
from app.database import Base, SessionLocal, engine
from app.etl import run_worldcup_etl
from app.importer import import_json
from app.seed import seed_editions
from app.models import NewsArticle
from app.news_relevance import is_world_cup_news


def main() -> None:
    parser = argparse.ArgumentParser(description="World Cup data platform")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db")
    news = commands.add_parser("crawl-news")
    news.add_argument("--year", type=int, help="Tìm kho bài báo của một kỳ World Cup")
    commands.add_parser("seed-demo")
    commands.add_parser("seed-editions")
    commands.add_parser("reclassify-news", help="Phân loại lại tin World Cup đang có trong database")

    adapters = {**LEGACY_ADAPTERS, **{adapter.code: adapter for adapter in FJELSTUL_ADAPTERS}}
    crawler = commands.add_parser("crawl-source")
    crawler.add_argument("source", choices=sorted(adapters))
    crawler.add_argument("--year", type=int)

    etl = commands.add_parser("etl", help="Chạy toàn bộ quy trình extract-transform-load")
    scope = etl.add_mutually_exclusive_group(required=True)
    scope.add_argument("--year", type=int)
    scope.add_argument("--all-years", action="store_true")
    etl.add_argument("--skip-news", action="store_true")
    etl.add_argument("--skip-wikipedia", action="store_true")

    importer = commands.add_parser("import-json")
    importer.add_argument("path")
    args = parser.parse_args()

    if args.command == "init-db":
        Base.metadata.create_all(engine)
        print("Database initialized")
        return

    with SessionLocal() as db:
        if args.command == "crawl-news":
            run = run_adapter(db, VietnameseNewsCrawler(), args.year)
            print(f"News ETL {run.status}: seen={run.records_seen}, saved={run.records_saved}, rejected={run.records_rejected}")
        elif args.command == "crawl-source":
            run = run_adapter(db, adapters[args.source], args.year)
            print(f"Crawl {run.status}: seen={run.records_seen}, saved={run.records_saved}, rejected={run.records_rejected}")
        elif args.command == "etl":
            summary = run_worldcup_etl(
                db, year=None if args.all_years else args.year,
                include_news=not args.skip_news, include_wikipedia=not args.skip_wikipedia,
            )
            print(f"ETL complete: runs={len(summary.runs)}, seen={summary.records_seen}, saved={summary.records_saved}, rejected={summary.records_rejected}, errors={len(summary.errors)}")
            for error in summary.errors:
                print(f"ERROR: {error}")
            if summary.errors:
                raise SystemExit(1)
        elif args.command == "seed-editions":
            seed_editions(db)
            print("Seeded 23 World Cup editions (1930-2026)")
        elif args.command == "reclassify-news":
            articles = db.scalars(select(NewsArticle)).all()
            relevant = 0
            for article in articles:
                article.is_world_cup = is_world_cup_news(article.title, article.summary)
                relevant += int(article.is_world_cup)
            db.commit()
            print(f"Reclassified {len(articles)} articles: relevant={relevant}, excluded={len(articles) - relevant}")
        else:
            path = "data/example_world_cup.json" if args.command == "seed-demo" else args.path
            import_json(db, path)
            print(f"Imported {path}")


if __name__ == "__main__":
    main()
