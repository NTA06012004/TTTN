"""Optimized aggregate queries used by both REST and legacy statistics APIs."""
from dataclasses import dataclass

from sqlalchemy import and_, case, desc, func, or_, select, union_all
from sqlalchemy.orm import Session, aliased

from app.models import Appearance, EventType, Match, MatchEvent, Player, Squad, Team, Tournament, TournamentTeam


GOAL_TYPES = (EventType.goal, EventType.penalty_goal, EventType.own_goal)
PLAYER_GOAL_TYPES = (EventType.goal, EventType.penalty_goal)
YELLOW_TYPES = (EventType.yellow_card, EventType.second_yellow)
RED_TYPES = (EventType.red_card,)


@dataclass(frozen=True)
class StatisticsFilters:
    year: int | None = None
    team_id: int | None = None
    player_id: int | None = None
    stage: str | None = None

    def as_dict(self) -> dict:
        return {
            key: value for key, value in {
                "year": self.year, "team_id": self.team_id,
                "player_id": self.player_id, "stage": self.stage,
            }.items() if value is not None
        }


def team_statistics(db: Session, metric: str, limit: int, filters: StatisticsFilters) -> dict:
    if metric == "titles":
        stmt = (
            select(Team.id, Team.name, Team.fifa_code, func.count(Tournament.id).label("value"))
            .join(Tournament, Tournament.champion_team_id == Team.id)
        )
        if filters.year is not None:
            stmt = stmt.where(Tournament.year == filters.year)
        if filters.team_id is not None:
            stmt = stmt.where(Team.id == filters.team_id)
    elif metric == "tournaments":
        stmt = (
            select(Team.id, Team.name, Team.fifa_code, func.count(func.distinct(TournamentTeam.tournament_id)).label("value"))
            .join(TournamentTeam, TournamentTeam.team_id == Team.id)
            .join(Tournament, Tournament.id == TournamentTeam.tournament_id)
        )
        if filters.year is not None:
            stmt = stmt.where(Tournament.year == filters.year)
        if filters.team_id is not None:
            stmt = stmt.where(Team.id == filters.team_id)
    elif metric == "goals":
        stmt = (
            select(Team.id, Team.name, Team.fifa_code, func.count(MatchEvent.id).label("value"))
            .join(MatchEvent, MatchEvent.team_id == Team.id)
            .join(Match, Match.id == MatchEvent.match_id)
            .join(Tournament, Tournament.id == Match.tournament_id)
            .where(MatchEvent.event_type.in_(GOAL_TYPES))
        )
        stmt = _apply_event_filters(stmt, filters)
    elif metric == "wins":
        return _team_wins(db, limit, filters)
    else:
        raise ValueError(f"Unsupported team metric: {metric}")

    rows = db.execute(
        stmt.group_by(Team.id, Team.name, Team.fifa_code)
        .order_by(desc("value"), Team.name)
        .limit(limit)
    ).all()
    data = _rank(rows, lambda row, rank: {
        "rank": rank, "team_id": row.id, "team_name": row.name,
        "fifa_code": row.fifa_code, "metric": metric, "value": row.value,
    })
    return _response(metric, data, filters)


def player_statistics(db: Session, metric: str, limit: int, filters: StatisticsFilters) -> dict:
    if metric == "goals":
        stmt = (
            select(Player.id, Player.full_name.label("name"), func.count(MatchEvent.id).label("value"))
            .join(MatchEvent, MatchEvent.player_id == Player.id)
            .join(Match, Match.id == MatchEvent.match_id)
            .join(Tournament, Tournament.id == Match.tournament_id)
            .where(MatchEvent.event_type.in_(PLAYER_GOAL_TYPES))
        )
        stmt = _apply_event_filters(stmt, filters)
    elif metric == "matches":
        stmt = (
            select(Player.id, Player.full_name.label("name"), func.count(func.distinct(Appearance.match_id)).label("value"))
            .join(Appearance, Appearance.player_id == Player.id)
            .join(Match, Match.id == Appearance.match_id)
            .join(Tournament, Tournament.id == Match.tournament_id)
        )
        stmt = _apply_appearance_filters(stmt, filters)
    elif metric == "tournaments":
        if filters.stage is not None:
            stmt = (
                select(Player.id, Player.full_name.label("name"), func.count(func.distinct(Tournament.id)).label("value"))
                .join(Appearance, Appearance.player_id == Player.id)
                .join(Match, Match.id == Appearance.match_id)
                .join(Tournament, Tournament.id == Match.tournament_id)
            )
            stmt = _apply_appearance_filters(stmt, filters)
        else:
            stmt = (
                select(Player.id, Player.full_name.label("name"), func.count(func.distinct(Squad.tournament_id)).label("value"))
                .join(Squad, Squad.player_id == Player.id)
                .join(Tournament, Tournament.id == Squad.tournament_id)
            )
            if filters.year is not None:
                stmt = stmt.where(Tournament.year == filters.year)
            if filters.team_id is not None:
                stmt = stmt.where(Squad.team_id == filters.team_id)
            if filters.player_id is not None:
                stmt = stmt.where(Player.id == filters.player_id)
    else:
        raise ValueError(f"Unsupported player metric: {metric}")

    rows = db.execute(
        stmt.group_by(Player.id, Player.full_name)
        .order_by(desc("value"), Player.full_name)
        .limit(limit)
    ).all()
    data = _rank(rows, lambda row, rank: {
        "rank": rank, "player_id": row.id, "player_name": row.name,
        "metric": metric, "value": row.value,
    })
    return _response(metric, data, filters)


def match_statistics(
    db: Session, metric: str, limit: int, filters: StatisticsFilters, card_type: str = "all",
) -> dict:
    home, away = aliased(Team), aliased(Team)
    base_columns = (
        Match.id, Tournament.year, Match.stage,
        home.name.label("home"), away.name.label("away"),
        Match.home_score, Match.away_score,
    )
    if metric == "goals":
        value = (func.coalesce(Match.home_score, 0) + func.coalesce(Match.away_score, 0)).label("value")
        stmt = select(*base_columns, value)
    elif metric == "cards":
        yellow_expression = func.sum(case((MatchEvent.event_type.in_(YELLOW_TYPES), 1), else_=0))
        red_expression = func.sum(case((MatchEvent.event_type.in_(RED_TYPES), 1), else_=0))
        yellow = yellow_expression.label("yellow_cards")
        red = red_expression.label("red_cards")
        if card_type == "yellow":
            value = yellow_expression.label("value")
            allowed = YELLOW_TYPES
        elif card_type == "red":
            value = red_expression.label("value")
            allowed = RED_TYPES
        else:
            value = func.count(MatchEvent.id).label("value")
            allowed = (*YELLOW_TYPES, *RED_TYPES)
        stmt = select(*base_columns, value, yellow, red).join(MatchEvent, MatchEvent.match_id == Match.id).where(MatchEvent.event_type.in_(allowed))
    else:
        raise ValueError(f"Unsupported match metric: {metric}")

    stmt = (
        stmt.join(Tournament, Tournament.id == Match.tournament_id)
        .join(home, home.id == Match.home_team_id)
        .join(away, away.id == Match.away_team_id)
    )
    if filters.player_id is not None:
        stmt = stmt.join(Appearance, Appearance.match_id == Match.id).where(Appearance.player_id == filters.player_id)
    stmt = _apply_match_filters(stmt, filters)
    if metric == "cards":
        stmt = stmt.group_by(
            Match.id, Tournament.year, Match.stage, home.name, away.name,
            Match.home_score, Match.away_score,
        )
    rows = db.execute(stmt.order_by(desc("value"), Match.id).limit(limit)).all()
    metric_name = f"{card_type}_cards" if metric == "cards" else "goals"
    data = _rank(rows, lambda row, rank: {
        "rank": rank, "match_id": row.id, "tournament_year": row.year,
        "stage": row.stage, "home_team": row.home, "away_team": row.away,
        "home_score": row.home_score, "away_score": row.away_score,
        "metric": metric_name, "value": row.value,
        "yellow_cards": getattr(row, "yellow_cards", None),
        "red_cards": getattr(row, "red_cards", None),
    })
    return _response(metric_name, data, filters, {"card_type": card_type} if metric == "cards" else None)


def _team_wins(db: Session, limit: int, filters: StatisticsFilters) -> dict:
    home_win = or_(
        Match.home_score > Match.away_score,
        and_(Match.home_score == Match.away_score, func.coalesce(Match.home_penalties, -1) > func.coalesce(Match.away_penalties, -1)),
    )
    away_win = or_(
        Match.away_score > Match.home_score,
        and_(Match.away_score == Match.home_score, func.coalesce(Match.away_penalties, -1) > func.coalesce(Match.home_penalties, -1)),
    )
    home_stmt = select(Match.home_team_id.label("team_id"), Match.id.label("match_id")).join(Tournament).where(Match.status == "finished", home_win)
    away_stmt = select(Match.away_team_id.label("team_id"), Match.id.label("match_id")).join(Tournament).where(Match.status == "finished", away_win)
    for stmt_name, stmt in (("home", home_stmt), ("away", away_stmt)):
        if filters.year is not None:
            stmt = stmt.where(Tournament.year == filters.year)
        if filters.team_id is not None:
            column = Match.home_team_id if stmt_name == "home" else Match.away_team_id
            stmt = stmt.where(column == filters.team_id)
        if filters.stage is not None:
            stmt = stmt.where(func.lower(Match.stage) == filters.stage.strip().casefold())
        if stmt_name == "home":
            home_stmt = stmt
        else:
            away_stmt = stmt
    winners = union_all(home_stmt, away_stmt).subquery()
    rows = db.execute(
        select(Team.id, Team.name, Team.fifa_code, func.count(winners.c.match_id).label("value"))
        .join(winners, winners.c.team_id == Team.id)
        .group_by(Team.id, Team.name, Team.fifa_code)
        .order_by(desc("value"), Team.name)
        .limit(limit)
    ).all()
    data = _rank(rows, lambda row, rank: {
        "rank": rank, "team_id": row.id, "team_name": row.name,
        "fifa_code": row.fifa_code, "metric": "wins", "value": row.value,
    })
    return _response("wins", data, filters)


def _apply_match_filters(stmt, filters: StatisticsFilters):
    if filters.year is not None:
        stmt = stmt.where(Tournament.year == filters.year)
    if filters.team_id is not None:
        stmt = stmt.where(or_(Match.home_team_id == filters.team_id, Match.away_team_id == filters.team_id))
    if filters.stage is not None:
        stmt = stmt.where(func.lower(Match.stage) == filters.stage.strip().casefold())
    return stmt


def _apply_event_filters(stmt, filters: StatisticsFilters):
    stmt = _apply_match_filters(stmt, StatisticsFilters(year=filters.year, stage=filters.stage))
    if filters.team_id is not None:
        stmt = stmt.where(MatchEvent.team_id == filters.team_id)
    if filters.player_id is not None:
        stmt = stmt.where(MatchEvent.player_id == filters.player_id)
    return stmt


def _apply_appearance_filters(stmt, filters: StatisticsFilters):
    stmt = _apply_match_filters(stmt, StatisticsFilters(year=filters.year, stage=filters.stage))
    if filters.team_id is not None:
        stmt = stmt.where(Appearance.team_id == filters.team_id)
    if filters.player_id is not None:
        stmt = stmt.where(Appearance.player_id == filters.player_id)
    return stmt


def _response(metric: str, data: list[dict], filters: StatisticsFilters, extra_filters: dict | None = None) -> dict:
    active_filters = filters.as_dict()
    if extra_filters:
        active_filters.update(extra_filters)
    return {"data": data, "meta": {"metric": metric, "count": len(data), "filters": active_filters}}


def _rank(rows, factory):
    result, previous, rank = [], object(), 0
    for index, row in enumerate(rows, 1):
        if row.value != previous:
            rank = index
            previous = row.value
        result.append(factory(row, rank))
    return result


# Compatibility layer for the original /stats routes.
def most_titles(db: Session, limit: int):
    result = team_statistics(db, "titles", limit, StatisticsFilters())["data"]
    return [{"rank": row["rank"], "team_id": row["team_id"], "team_name": row["team_name"], "titles": row["value"]} for row in result]


def top_players(db: Session, metric: str, limit: int, year: int | None):
    normalized = "matches" if metric == "appearances" else metric
    result = player_statistics(db, normalized, limit, StatisticsFilters(year=year))["data"]
    return [{"rank": row["rank"], "player_id": row["player_id"], "player_name": row["player_name"], "value": row["value"]} for row in result]


def top_matches(db: Session, metric: str, limit: int, year: int | None):
    result = match_statistics(db, metric, limit, StatisticsFilters(year=year))["data"]
    return [{
        "rank": row["rank"], "match_id": row["match_id"], "tournament_year": row["tournament_year"],
        "home_team": row["home_team"], "away_team": row["away_team"], "value": row["value"],
    } for row in result]
