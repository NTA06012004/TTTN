from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str


class TeamOut(ORMModel):
    id: int
    fifa_code: str
    name: str
    confederation: str | None


class TournamentOut(ORMModel):
    id: int
    year: int
    name: str
    host_country: str | None
    champion: TeamOut | None
    runner_up: TeamOut | None = None
    logo_url: str | None = None
    overview: str | None = None


class PlayerOut(ORMModel):
    id: int
    full_name: str
    nationality: TeamOut | None


class MatchOut(ORMModel):
    id: int
    kickoff_at: datetime | None
    stage: str
    home_team: TeamOut
    away_team: TeamOut
    home_score: int | None
    away_score: int | None
    status: str
    venue: str | None = None
    attendance: int | None = None
    referee: str | None = None


class MatchEventOut(BaseModel):
    id: int
    event_type: str
    minute: int | None
    stoppage_minute: int | None
    team_id: int
    team_name: str
    player_id: int | None
    player_name: str | None


class MatchDetail(BaseModel):
    match: MatchOut
    events: list[MatchEventOut]


class NewsOut(ORMModel):
    id: int
    source: str
    url: str
    title: str
    summary: str | None
    published_at: datetime | None
    tournament_year: int | None
    image_url: str | None = None


class StandingOut(BaseModel):
    group_name: str
    rank: int
    team_id: int
    team_name: str
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    points: int


class TournamentTeamOut(BaseModel):
    team: TeamOut
    final_position: int | None
    coach: str | None


class TournamentOverview(BaseModel):
    tournament: TournamentOut
    teams_count: int
    matches_count: int
    goals_count: int
    players_count: int
    news_count: int


class SearchResults(BaseModel):
    tournaments: list[TournamentOut]
    teams: list[TeamOut]
    players: list[PlayerOut]
    matches: list[MatchOut] = Field(default_factory=list)
    news: list[NewsOut]


class StatisticsMeta(BaseModel):
    metric: str
    count: int
    filters: dict[str, Any] = Field(default_factory=dict)


class TeamStatistic(BaseModel):
    rank: int
    team_id: int
    team_name: str
    fifa_code: str
    metric: str
    value: int


class PlayerStatistic(BaseModel):
    rank: int
    player_id: int
    player_name: str
    metric: str
    value: int


class MatchStatistic(BaseModel):
    rank: int
    match_id: int
    tournament_year: int
    stage: str
    home_team: str
    away_team: str
    home_score: int | None = None
    away_score: int | None = None
    metric: str
    value: int
    yellow_cards: int | None = None
    red_cards: int | None = None


class TeamStatisticsResponse(BaseModel):
    data: list[TeamStatistic]
    meta: StatisticsMeta


class PlayerStatisticsResponse(BaseModel):
    data: list[PlayerStatistic]
    meta: StatisticsMeta


class MatchStatisticsResponse(BaseModel):
    data: list[MatchStatistic]
    meta: StatisticsMeta


class TournamentStatistic(BaseModel):
    tournament_year: int
    metric: str
    value: int


class TournamentStatisticsResponse(BaseModel):
    data: list[TournamentStatistic]
    meta: StatisticsMeta


class DashboardTotals(BaseModel):
    tournaments: int
    teams: int
    players: int
    matches: int
    goals: int
    news: int


class DashboardStatisticsResponse(BaseModel):
    data: DashboardTotals
    meta: StatisticsMeta


class RankedTeam(BaseModel):
    rank: int
    team_id: int
    team_name: str
    titles: int


class RankedPlayer(BaseModel):
    rank: int
    player_id: int
    player_name: str
    value: int


class RankedMatch(BaseModel):
    rank: int
    match_id: int
    tournament_year: int
    home_team: str
    away_team: str
    value: int


class ImportedTeam(BaseModel):
    code: str = Field(min_length=3, max_length=3)
    name: str
    confederation: str | None = None
