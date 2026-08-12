"""Idempotent ETL loader with provenance, validation and reject handling."""
from datetime import datetime, time, timezone
from hashlib import sha256
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawlers.base import CrawlerAdapter
from app.crawlers.transform import canonical_url, content_key, iso_date, validate_payload
from app.models import (
    Appearance, CrawlRun, DataProvenance, DataSource, EtlReject, EventType, Match, MatchEvent,
    NewsArticle, Player, Squad, Stadium, Standing, Team, Tournament, TournamentTeam,
)


def run_adapter(db: Session, adapter: CrawlerAdapter, year: int | None = None) -> CrawlRun:
    source = db.scalar(select(DataSource).where(DataSource.code == adapter.code))
    if not source:
        source = DataSource(code=adapter.code, name=adapter.name, source_type=adapter.source_type, base_url=adapter.base_url)
        db.add(source)
    else:
        source.name, source.source_type, source.base_url = adapter.name, adapter.source_type, adapter.base_url
    db.commit()

    run = CrawlRun(source_id=source.id, status="running")
    db.add(run)
    db.commit()
    seen = saved = rejected = 0

    try:
        for record in adapter.crawl(year=year):
            seen += 1
            try:
                with db.begin_nested():
                    validate_payload(record.entity_type, record.payload)
                    changed, provenance = _stage(db, source.id, record.entity_type, record.external_key, record.source_url, record.payload)
                    entity_id = _materialize(db, record.entity_type, record.payload)
                    provenance.entity_id = entity_id
                    if changed:
                        saved += 1
            except Exception as exc:
                rejected += 1
                db.add(EtlReject(
                    crawl_run_id=run.id, source_id=source.id, entity_type=record.entity_type,
                    external_key=record.external_key, error_message=str(exc)[:2000], raw_payload=record.payload,
                ))

        run.records_seen, run.records_saved, run.records_rejected = seen, saved, rejected
        run.status = "partial" if rejected else "success"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        return run
    except Exception as exc:
        db.rollback()
        failed_run = db.get(CrawlRun, run.id)
        failed_run.records_seen, failed_run.records_saved, failed_run.records_rejected = seen, saved, rejected
        failed_run.status, failed_run.error_message = "failed", str(exc)[:2000]
        failed_run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise


def _stage(db: Session, source_id: int, entity_type: str, external_key: str, source_url: str, payload: dict):
    packed = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    digest = sha256(packed.encode("utf-8")).hexdigest()
    provenance = db.scalar(select(DataProvenance).where(
        DataProvenance.source_id == source_id,
        DataProvenance.entity_type == entity_type,
        DataProvenance.external_key == external_key,
    ))
    changed = provenance is None or provenance.content_hash != digest
    if not provenance:
        provenance = DataProvenance(source_id=source_id, entity_type=entity_type, external_key=external_key)
    provenance.source_url, provenance.content_hash = source_url, digest
    provenance.raw_payload, provenance.collected_at = payload, datetime.now(timezone.utc)
    db.add(provenance)
    db.flush()
    return changed, provenance


def _materialize(db: Session, entity_type: str, payload: dict) -> int | None:
    handlers = {
        "tournament": _load_tournament, "match": _load_match, "squad": _load_squad,
        "appearance": _load_appearance, "match_event": _load_event, "standing": _load_standing,
        "tournament_standing": _load_tournament_standing, "news": _load_news,
    }
    handler = handlers.get(entity_type)
    return handler(db, payload) if handler else None


def _load_tournament(db: Session, payload: dict) -> int | None:
    tournament = db.scalar(select(Tournament).where(Tournament.year == payload["year"]))
    if tournament:
        tournament.overview = payload.get("overview") or tournament.overview
        db.flush()
        return tournament.id
    return None


def _load_match(db: Session, payload: dict) -> int:
    tournament = _tournament(db, payload["year"])
    home, away = _team(db, payload["home_team"]), _team(db, payload["away_team"])
    match = db.scalar(select(Match).where(Match.tournament_id == tournament.id, Match.external_id == payload["external_id"]))
    if not match:
        match = Match(tournament_id=tournament.id, external_id=payload["external_id"], stage=payload.get("stage") or "Unknown", home_team_id=home.id, away_team_id=away.id)
    played_on = iso_date(payload["date"])
    match_time = time.fromisoformat(payload["time"]) if payload.get("time") else time.min
    match.kickoff_at = datetime.combine(played_on, match_time)
    match.stage, match.group_name = payload.get("stage") or "Unknown", payload.get("group")
    match.home_team_id, match.away_team_id = home.id, away.id
    match.home_score, match.away_score = payload.get("home_score"), payload.get("away_score")
    match.home_penalties, match.away_penalties = payload.get("home_penalties"), payload.get("away_penalties")
    match.status = "finished"
    stadium_data = payload.get("stadium") or {}
    if stadium_data.get("name"):
        stadium = db.scalar(select(Stadium).where(Stadium.name == stadium_data["name"], Stadium.city == stadium_data.get("city")))
        if not stadium:
            stadium = Stadium(name=stadium_data["name"], city=stadium_data.get("city") or "Unknown", country=stadium_data.get("country") or "Unknown")
            db.add(stadium); db.flush()
        match.stadium_id, match.venue = stadium.id, stadium.name
    db.add(match); db.flush()
    for team in (home, away):
        if not db.scalar(select(TournamentTeam).where(TournamentTeam.tournament_id == tournament.id, TournamentTeam.team_id == team.id)):
            db.add(TournamentTeam(tournament_id=tournament.id, team_id=team.id))
    return match.id


def _load_squad(db: Session, payload: dict) -> int:
    tournament = _tournament(db, payload["year"])
    team = _team(db, payload["team"])
    player = _player(db, payload["player"], team)
    squad = db.scalar(select(Squad).where(Squad.tournament_id == tournament.id, Squad.team_id == team.id, Squad.player_id == player.id))
    if not squad:
        squad = Squad(tournament_id=tournament.id, team_id=team.id, player_id=player.id)
    squad.shirt_number, squad.position = payload.get("shirt_number"), payload.get("position")
    db.add(squad); db.flush()
    if not db.scalar(select(TournamentTeam).where(TournamentTeam.tournament_id == tournament.id, TournamentTeam.team_id == team.id)):
        db.add(TournamentTeam(tournament_id=tournament.id, team_id=team.id))
    return squad.id


def _load_appearance(db: Session, payload: dict) -> int:
    tournament = _tournament(db, payload["year"])
    match = _match(db, tournament.id, payload["match_external_id"])
    team = _team(db, payload["team"])
    player = _player(db, payload["player"], team)
    appearance = db.scalar(select(Appearance).where(Appearance.match_id == match.id, Appearance.player_id == player.id))
    if not appearance:
        appearance = Appearance(match_id=match.id, player_id=player.id, team_id=team.id)
    appearance.started, appearance.minutes_played = bool(payload.get("started")), payload.get("minutes") or 0
    db.add(appearance); db.flush()
    return appearance.id


def _load_standing(db: Session, payload: dict) -> int:
    tournament = _tournament(db, payload["year"])
    team = _team(db, payload["team"])
    standing = db.scalar(select(Standing).where(
        Standing.tournament_id == tournament.id, Standing.snapshot == payload.get("snapshot", "final"),
        Standing.group_name == payload["group"], Standing.team_id == team.id,
    ))
    if not standing:
        standing = Standing(
            tournament_id=tournament.id, snapshot=payload.get("snapshot", "final"),
            group_name=payload["group"], team_id=team.id,
        )
    for field in ("rank", "played", "won", "drawn", "lost", "goals_for", "goals_against", "points"):
        setattr(standing, field, payload[field])
    db.add(standing); db.flush()
    return standing.id


def _load_tournament_standing(db: Session, payload: dict) -> int:
    tournament = _tournament(db, payload["year"])
    team = _team(db, payload["team"])
    participation = db.scalar(select(TournamentTeam).where(
        TournamentTeam.tournament_id == tournament.id, TournamentTeam.team_id == team.id,
    ))
    if not participation:
        participation = TournamentTeam(tournament_id=tournament.id, team_id=team.id)
    participation.final_position = payload["final_position"]
    db.add(participation); db.flush()
    return participation.id


def _load_event(db: Session, payload: dict) -> int:
    tournament = _tournament(db, payload["year"])
    match = _match(db, tournament.id, payload["match_external_id"])
    credited_team = _team(db, payload["team"])
    player_team = _team(db, payload.get("player_team") or payload["team"])
    player = _player(db, payload["player"], player_team) if payload.get("player") else None
    event = db.scalar(select(MatchEvent).where(MatchEvent.match_id == match.id, MatchEvent.external_id == payload["external_id"]))
    if not event:
        event = MatchEvent(match_id=match.id, external_id=payload["external_id"], team_id=credited_team.id, event_type=EventType(payload["event_type"]))
    event.team_id, event.player_id = credited_team.id, player.id if player else None
    event.event_type = EventType(payload["event_type"])
    event.minute, event.stoppage_minute = payload.get("minute"), payload.get("stoppage_minute")
    db.add(event); db.flush()
    return event.id


def _load_news(db: Session, payload: dict) -> int:
    from app.news_relevance import is_world_cup_news

    url = canonical_url(payload["url"])
    url_hash = content_key(url)
    article = db.scalar(select(NewsArticle).where(NewsArticle.url_hash == url_hash))
    if not article:
        article = NewsArticle(url=url, url_hash=url_hash, source=payload["source"], title=payload["title"])
    article.source, article.title, article.summary = payload["source"], payload["title"], payload.get("summary")
    article.tournament_year, article.image_url = payload.get("tournament_year"), payload.get("image_url")
    article.is_world_cup = is_world_cup_news(article.title, article.summary)
    article.published_at = datetime.fromisoformat(payload["published_at"]).replace(tzinfo=None) if payload.get("published_at") else None
    db.add(article); db.flush()
    return article.id


def _tournament(db: Session, year: int) -> Tournament:
    tournament = db.scalar(select(Tournament).where(Tournament.year == year))
    if not tournament:
        tournament = Tournament(year=year, name=f"FIFA World Cup {year}")
        db.add(tournament); db.flush()
    return tournament


def _team(db: Session, data: dict) -> Team:
    code, name = data.get("code"), data["name"]
    team = db.scalar(select(Team).where(Team.fifa_code == code)) if code else None
    team = team or db.scalar(select(Team).where(Team.name == name))
    if not team:
        fallback = "EXT-" + content_key(name)[:8].upper()
        team = Team(fifa_code=code or fallback, name=name)
    team.name = name
    db.add(team); db.flush()
    return team


def _player(db: Session, data: dict, nationality: Team) -> Player:
    player = db.scalar(select(Player).where(Player.external_id == data["external_id"]))
    if not player:
        player = Player(external_id=data["external_id"], full_name=data["full_name"])
    player.full_name, player.position, player.nationality_team_id = data["full_name"], data.get("position"), nationality.id
    db.add(player); db.flush()
    return player


def _match(db: Session, tournament_id: int, external_id: str) -> Match:
    match = db.scalar(select(Match).where(Match.tournament_id == tournament_id, Match.external_id == external_id))
    if not match:
        raise ValueError(f"Match must be loaded before dependent records: {external_id}")
    return match
