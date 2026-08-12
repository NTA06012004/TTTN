from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC value for ORM-side timestamp defaults."""
    return datetime.now(timezone.utc)


class EventType(str, Enum):
    goal = "goal"
    penalty_goal = "penalty_goal"
    own_goal = "own_goal"
    yellow_card = "yellow_card"
    second_yellow = "second_yellow"
    red_card = "red_card"
    penalty_shootout_goal = "penalty_shootout_goal"
    penalty_shootout_miss = "penalty_shootout_miss"
    substitution_in = "substitution_in"
    substitution_out = "substitution_out"


class Tournament(Base):
    __tablename__ = "tournaments"
    __table_args__ = (Index("ix_tournaments_champion_year", "champion_team_id", "year"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    host_country: Mapped[str | None] = mapped_column(String(120))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    champion_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    runner_up_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    third_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    overview: Mapped[str | None] = mapped_column(Text)
    champion: Mapped[Team | None] = relationship(foreign_keys=[champion_team_id])
    runner_up: Mapped[Team | None] = relationship(foreign_keys=[runner_up_team_id])


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    fifa_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    confederation: Mapped[str | None] = mapped_column(String(20))
    flag_url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)


class Player(Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    full_name: Mapped[str] = mapped_column(String(150), index=True)
    birth_date: Mapped[date | None] = mapped_column(Date)
    nationality_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    nationality: Mapped[Team | None] = relationship()
    position: Mapped[str | None] = mapped_column(String(30))
    height_cm: Mapped[int | None] = mapped_column(Integer)
    photo_url: Mapped[str | None] = mapped_column(String(500))


class Squad(Base):
    __tablename__ = "squads"
    __table_args__ = (
        UniqueConstraint("tournament_id", "team_id", "player_id"),
        Index("ix_squads_player_tournament", "player_id", "tournament_id"),
        Index("ix_squads_team_tournament", "team_id", "tournament_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    shirt_number: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[str | None] = mapped_column(String(30))
    is_captain: Mapped[bool] = mapped_column(default=False)
    club: Mapped[str | None] = mapped_column(String(120))


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("tournament_id", "external_id"),
        Index("ix_matches_tournament_stage_kickoff", "tournament_id", "stage", "kickoff_at"),
        Index("ix_matches_home_tournament", "home_team_id", "tournament_id"),
        Index("ix_matches_away_tournament", "away_team_id", "tournament_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str] = mapped_column(String(100))
    kickoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    stage: Mapped[str] = mapped_column(String(80), index=True)
    group_name: Mapped[str | None] = mapped_column(String(20))
    venue: Mapped[str | None] = mapped_column(String(150))
    stadium_id: Mapped[int | None] = mapped_column(ForeignKey("stadiums.id"), index=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    home_penalties: Mapped[int | None] = mapped_column(Integer)
    away_penalties: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="scheduled", index=True)
    attendance: Mapped[int | None] = mapped_column(Integer)
    referee: Mapped[str | None] = mapped_column(String(120))
    source_url: Mapped[str | None] = mapped_column(String(500))
    home_team: Mapped[Team] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped[Team] = relationship(foreign_keys=[away_team_id])
    stadium: Mapped[Stadium | None] = relationship()


class Appearance(Base):
    __tablename__ = "appearances"
    __table_args__ = (
        UniqueConstraint("match_id", "player_id"),
        Index("ix_appearances_player_match", "player_id", "match_id"),
        Index("ix_appearances_team_match", "team_id", "match_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    started: Mapped[bool] = mapped_column(default=False)
    minutes_played: Mapped[int] = mapped_column(Integer, default=0)


class MatchEvent(Base):
    __tablename__ = "match_events"
    __table_args__ = (
        Index("ix_events_match_type", "match_id", "event_type"),
        Index("ix_events_player_type_match", "player_id", "event_type", "match_id"),
        Index("ix_events_team_type_match", "team_id", "event_type", "match_id"),
        UniqueConstraint("match_id", "external_id", name="uq_match_event_external"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(100))
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), index=True)
    related_player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), index=True)
    event_type: Mapped[EventType] = mapped_column(SqlEnum(EventType, native_enum=False, length=30), index=True)
    minute: Mapped[int | None] = mapped_column(Integer)
    stoppage_minute: Mapped[int | None] = mapped_column(Integer)


class Standing(Base):
    __tablename__ = "standings"
    __table_args__ = (UniqueConstraint("tournament_id", "snapshot", "group_name", "team_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), index=True)
    snapshot: Mapped[str] = mapped_column(String(80), index=True)
    group_name: Mapped[str] = mapped_column(String(20))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    played: Mapped[int] = mapped_column(Integer)
    won: Mapped[int] = mapped_column(Integer)
    drawn: Mapped[int] = mapped_column(Integer)
    lost: Mapped[int] = mapped_column(Integer)
    goals_for: Mapped[int] = mapped_column(Integer)
    goals_against: Mapped[int] = mapped_column(Integer)
    points: Mapped[int] = mapped_column(Integer)


class NewsArticle(Base):
    __tablename__ = "news_articles"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(80), index=True)
    url: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(500), index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    tournament_year: Mapped[int | None] = mapped_column(Integer, index=True)
    image_url: Mapped[str | None] = mapped_column(String(500))
    language: Mapped[str] = mapped_column(String(8), default="vi")
    is_world_cup: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class TournamentTeam(Base):
    __tablename__ = "tournament_teams"
    __table_args__ = (
        UniqueConstraint("tournament_id", "team_id"),
        Index("ix_tournament_teams_team_tournament", "team_id", "tournament_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    final_position: Mapped[int | None] = mapped_column(Integer)
    qualification_method: Mapped[str | None] = mapped_column(String(200))
    coach: Mapped[str | None] = mapped_column(String(120))
    team: Mapped[Team] = relationship()


class Stadium(Base):
    __tablename__ = "stadiums"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    city: Mapped[str] = mapped_column(String(100), index=True)
    country: Mapped[str] = mapped_column(String(100))
    capacity: Mapped[int | None] = mapped_column(Integer)
    latitude: Mapped[str | None] = mapped_column(String(30))
    longitude: Mapped[str | None] = mapped_column(String(30))


class DataSource(Base):
    __tablename__ = "data_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    source_type: Mapped[str] = mapped_column(String(30), index=True)
    base_url: Mapped[str] = mapped_column(String(500))
    language: Mapped[str | None] = mapped_column(String(8))
    enabled: Mapped[bool] = mapped_column(default=True, index=True)
    crawl_interval_minutes: Mapped[int] = mapped_column(Integer, default=1440)


class CrawlRun(Base):
    __tablename__ = "crawl_runs"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running", index=True)
    records_seen: Mapped[int] = mapped_column(Integer, default=0)
    records_saved: Mapped[int] = mapped_column(Integer, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)


class DataProvenance(Base):
    __tablename__ = "data_provenance"
    __table_args__ = (UniqueConstraint("source_id", "entity_type", "external_key"),)
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    external_key: Mapped[str] = mapped_column(String(190))
    source_url: Mapped[str | None] = mapped_column(String(500))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    raw_payload: Mapped[dict | None] = mapped_column(JSON)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EtlReject(Base):
    __tablename__ = "etl_rejects"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    crawl_run_id: Mapped[int] = mapped_column(ForeignKey("crawl_runs.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    external_key: Mapped[str | None] = mapped_column(String(190))
    error_message: Mapped[str] = mapped_column(Text)
    raw_payload: Mapped[dict | None] = mapped_column(JSON)
    rejected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
