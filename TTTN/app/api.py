from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session, aliased, joinedload

from app.database import get_db
from app.models import Appearance, EventType, Match, MatchEvent, NewsArticle, Player, Squad, Standing, Team, Tournament, TournamentTeam
from app.schemas import (
    DashboardStatisticsResponse, MatchDetail, MatchOut, MatchStatisticsResponse, NewsOut, PlayerOut, PlayerStatisticsResponse,
    RankedMatch, RankedPlayer, RankedTeam, SearchResults, StandingOut, TeamOut,
    TeamStatisticsResponse, TournamentOut, TournamentOverview, TournamentStatistic,
    TournamentStatisticsResponse, TournamentTeamOut,
)
from app.services import StatisticsFilters, match_statistics, most_titles, player_statistics, team_statistics, top_matches, top_players

router = APIRouter(prefix="/api/v1")
Db = Annotated[Session, Depends(get_db)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0, le=10000)]


def _stage_equals(column, stage: str):
    """Compare normalized stage names while preserving their display spelling."""
    return func.lower(column) == stage.strip().casefold()


@router.get("/tournaments", response_model=list[TournamentOut], tags=["Tournaments"], summary="Danh sách các kỳ World Cup")
def tournaments(db: Db):
    return db.scalars(select(Tournament).options(joinedload(Tournament.champion), joinedload(Tournament.runner_up)).order_by(Tournament.year)).all()


def _tournament(db: Session, year: int) -> Tournament:
    item = db.scalar(select(Tournament).options(joinedload(Tournament.champion), joinedload(Tournament.runner_up)).where(Tournament.year == year))
    if not item:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy World Cup {year}")
    return item


@router.get("/tournaments/{year}", response_model=TournamentOut, tags=["Tournaments"], summary="Chi tiết một kỳ World Cup")
def tournament_detail(year: int, db: Db):
    return _tournament(db, year)


@router.get("/tournaments/{year}/overview", response_model=TournamentOverview, tags=["Tournaments"], summary="Tổng quan dữ liệu một kỳ")
def tournament_overview(year: int, db: Db):
    tournament = _tournament(db, year)
    def count(model, condition):
        return db.scalar(select(func.count()).select_from(model).where(condition)) or 0
    return {
        "tournament": tournament,
        "teams_count": count(TournamentTeam, TournamentTeam.tournament_id == tournament.id),
        "matches_count": count(Match, Match.tournament_id == tournament.id),
        "goals_count": db.scalar(select(func.count()).select_from(MatchEvent).join(Match).where(Match.tournament_id == tournament.id, MatchEvent.event_type.in_(["goal", "penalty_goal", "own_goal"]))) or 0,
        "players_count": count(Squad, Squad.tournament_id == tournament.id),
        "news_count": count(NewsArticle, (NewsArticle.tournament_year == year) & NewsArticle.is_world_cup.is_(True)),
    }


@router.get("/tournaments/{year}/teams", response_model=list[TournamentTeamOut], tags=["Tournaments"], summary="Đội tuyển tham dự một kỳ")
def tournament_teams(year: int, db: Db):
    tournament = _tournament(db, year)
    return db.scalars(select(TournamentTeam).options(joinedload(TournamentTeam.team)).where(TournamentTeam.tournament_id == tournament.id).order_by(TournamentTeam.final_position, TournamentTeam.team_id)).all()


@router.get("/tournaments/{year}/standings", response_model=list[StandingOut], tags=["Tournaments"], summary="Bảng xếp hạng theo kỳ")
def tournament_standings(year: int, db: Db, snapshot: str = "final"):
    tournament = _tournament(db, year)
    rows = db.execute(select(Standing, Team.name).join(Team).where(Standing.tournament_id == tournament.id, Standing.snapshot == snapshot).order_by(Standing.group_name, Standing.rank)).all()
    return [{**{k: getattr(s, k) for k in ("group_name", "rank", "team_id", "played", "won", "drawn", "lost", "goals_for", "goals_against", "points")}, "team_name": name} for s, name in rows]


@router.get("/teams", response_model=list[TeamOut], tags=["Teams"], summary="Danh sách và tìm kiếm đội tuyển")
def teams(db: Db, q: str | None = None, limit: Limit = 100, offset: Offset = 0):
    stmt = select(Team).order_by(Team.name)
    if q:
        stmt = stmt.where(or_(Team.name.ilike(f"%{q}%"), Team.fifa_code.ilike(f"%{q}%")))
    return db.scalars(stmt.offset(offset).limit(limit)).all()


@router.get("/teams/{team_id}", response_model=TeamOut, tags=["Teams"], summary="Chi tiết đội tuyển")
def team_detail(team_id: int, db: Db):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Không tìm thấy đội tuyển")
    return team


@router.get("/players", response_model=list[PlayerOut], tags=["Players"], summary="Danh sách và lọc cầu thủ")
def players(
    db: Db, q: str | None = None, tournament_year: int | None = None,
    team_id: int | None = None, stage: str | None = None,
    limit: Limit = 100, offset: Offset = 0,
):
    stmt = select(Player).options(joinedload(Player.nationality)).order_by(Player.full_name)
    if tournament_year or team_id:
        stmt = stmt.join(Squad)
    if tournament_year:
        stmt = stmt.join(Tournament, Tournament.id == Squad.tournament_id).where(Tournament.year == tournament_year)
    if team_id:
        stmt = stmt.where(Squad.team_id == team_id)
    if stage:
        stmt = stmt.join(Appearance, Appearance.player_id == Player.id).join(Match, Match.id == Appearance.match_id).where(_stage_equals(Match.stage, stage))
        if tournament_year or team_id:
            stmt = stmt.where(Match.tournament_id == Squad.tournament_id)
        if team_id:
            stmt = stmt.where(Appearance.team_id == team_id)
    if q:
        stmt = stmt.where(Player.full_name.ilike(f"%{q}%"))
    return db.scalars(stmt.distinct().offset(offset).limit(limit)).all()


@router.get("/players/{player_id}", response_model=PlayerOut, tags=["Players"], summary="Chi tiết cầu thủ")
def player_detail(player_id: int, db: Db):
    player = db.scalar(select(Player).options(joinedload(Player.nationality)).where(Player.id == player_id))
    if not player:
        raise HTTPException(status_code=404, detail="Không tìm thấy cầu thủ")
    return player


@router.get("/matches", response_model=list[MatchOut], tags=["Matches"], summary="Danh sách và lọc trận đấu")
def matches(
    db: Db, tournament_year: int | None = None, year: int | None = None,
    team_id: int | None = None, player_id: int | None = None, stage: str | None = None,
    limit: Limit = 50, offset: Offset = 0,
):
    if year is not None and tournament_year is not None and year != tournament_year:
        raise HTTPException(status_code=422, detail="year và tournament_year không được mâu thuẫn")
    selected_year = year if year is not None else tournament_year
    stmt = select(Match).options(joinedload(Match.home_team), joinedload(Match.away_team)).join(Tournament)
    if selected_year:
        stmt = stmt.where(Tournament.year == selected_year)
    if team_id:
        stmt = stmt.where(or_(Match.home_team_id == team_id, Match.away_team_id == team_id))
    if player_id:
        stmt = stmt.join(Appearance, Appearance.match_id == Match.id).where(Appearance.player_id == player_id)
    if stage:
        stmt = stmt.where(_stage_equals(Match.stage, stage))
    return db.scalars(stmt.distinct().order_by(Match.kickoff_at, Match.id).offset(offset).limit(limit)).all()


@router.get("/matches/stages", response_model=list[str], tags=["Matches"], summary="Danh sách vòng đấu hiện có")
def match_stages(db: Db):
    return db.scalars(select(Match.stage).distinct().order_by(Match.stage)).all()


@router.get("/matches/{match_id}", response_model=MatchDetail, tags=["Matches"], summary="Chi tiết và diễn biến trận đấu")
def match_detail(match_id: int, db: Db):
    match = db.scalar(
        select(Match).options(joinedload(Match.home_team), joinedload(Match.away_team))
        .where(Match.id == match_id)
    )
    if not match:
        raise HTTPException(status_code=404, detail="Không tìm thấy trận đấu")
    event_team, event_player = aliased(Team), aliased(Player)
    rows = db.execute(
        select(MatchEvent, event_team.name, event_player.full_name)
        .join(event_team, event_team.id == MatchEvent.team_id)
        .outerjoin(event_player, event_player.id == MatchEvent.player_id)
        .where(MatchEvent.match_id == match_id)
        .order_by(MatchEvent.minute, MatchEvent.stoppage_minute, MatchEvent.id)
    ).all()
    events = [{
        "id": event.id, "event_type": event.event_type.value,
        "minute": event.minute, "stoppage_minute": event.stoppage_minute,
        "team_id": event.team_id, "team_name": team_name,
        "player_id": event.player_id, "player_name": player_name,
    } for event, team_name, player_name in rows]
    return {"match": match, "events": events}


@router.get("/news", response_model=list[NewsOut], tags=["News"], summary="Danh sách và tìm kiếm tin tức")
def news(db: Db, q: str | None = None, tournament_year: int | None = None, limit: Limit = 20, offset: Offset = 0):
    stmt = select(NewsArticle).where(NewsArticle.is_world_cup.is_(True))
    if q:
        stmt = stmt.where(or_(NewsArticle.title.ilike(f"%{q}%"), NewsArticle.summary.ilike(f"%{q}%")))
    if tournament_year:
        stmt = stmt.where(NewsArticle.tournament_year == tournament_year)
    return db.scalars(stmt.order_by(NewsArticle.published_at.desc()).offset(offset).limit(limit)).all()


@router.get("/news/{article_id}", response_model=NewsOut, tags=["News"], summary="Chi tiết metadata bài viết")
def news_detail(article_id: int, db: Db):
    article = db.get(NewsArticle, article_id)
    if not article or not article.is_world_cup:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
    return article


@router.get("/stats/teams/most-titles", response_model=list[RankedTeam], tags=["Legacy Statistics"], summary="Đội vô địch nhiều nhất (cũ)", deprecated=True)
def titles(db: Db, limit: Limit = 10):
    return most_titles(db, limit)


@router.get("/stats/players/top-scorers", response_model=list[RankedPlayer], tags=["Legacy Statistics"], summary="Cầu thủ ghi bàn nhiều nhất (cũ)", deprecated=True)
def scorers(db: Db, limit: Limit = 10, tournament_year: int | None = None):
    return top_players(db, "goals", limit, tournament_year)


@router.get("/stats/players/most-appearances", response_model=list[RankedPlayer], tags=["Legacy Statistics"], summary="Cầu thủ ra sân nhiều nhất (cũ)", deprecated=True)
def appearances(db: Db, limit: Limit = 10, tournament_year: int | None = None):
    return top_players(db, "appearances", limit, tournament_year)


@router.get("/stats/matches/most-goals", response_model=list[RankedMatch], tags=["Legacy Statistics"], summary="Trận đấu nhiều bàn nhất (cũ)", deprecated=True)
def goals(db: Db, limit: Limit = 10, tournament_year: int | None = None):
    return top_matches(db, "goals", limit, tournament_year)


@router.get("/stats/matches/most-cards", response_model=list[RankedMatch], tags=["Legacy Statistics"], summary="Trận đấu nhiều thẻ nhất (cũ)", deprecated=True)
def cards(db: Db, limit: Limit = 10, tournament_year: int | None = None):
    return top_matches(db, "cards", limit, tournament_year)


def _statistics_filters(
    year: int | None, team_id: int | None = None,
    player_id: int | None = None, stage: str | None = None,
) -> StatisticsFilters:
    return StatisticsFilters(year=year, team_id=team_id, player_id=player_id, stage=stage)


@router.get("/statistics/overview", response_model=DashboardStatisticsResponse, tags=["Statistics"], summary="Các chỉ số tổng quan hệ thống")
def statistics_overview(db: Db):
    def total(model):
        return db.scalar(select(func.count()).select_from(model)) or 0
    goals = db.scalar(
        select(func.count()).select_from(MatchEvent)
        .where(MatchEvent.event_type.in_((EventType.goal, EventType.penalty_goal, EventType.own_goal)))
    ) or 0
    data = {
        "tournaments": total(Tournament), "teams": total(Team), "players": total(Player),
        "matches": total(Match), "goals": goals,
        "news": db.scalar(select(func.count()).select_from(NewsArticle).where(NewsArticle.is_world_cup.is_(True))) or 0,
    }
    return {"data": data, "meta": {"metric": "overview", "count": len(data), "filters": {}}}


@router.get("/statistics/tournaments/goals", response_model=TournamentStatisticsResponse, tags=["Statistics"], summary="Phân bố bàn thắng theo kỳ")
def tournament_goals_statistics(db: Db, year: int | None = None):
    stmt = (
        select(Tournament.year, func.count(MatchEvent.id).label("value"))
        .join(Match, Match.tournament_id == Tournament.id)
        .join(MatchEvent, MatchEvent.match_id == Match.id)
        .where(MatchEvent.event_type.in_((EventType.goal, EventType.penalty_goal, EventType.own_goal)))
    )
    if year is not None:
        stmt = stmt.where(Tournament.year == year)
    rows = db.execute(stmt.group_by(Tournament.year).order_by(Tournament.year)).all()
    data = [{"tournament_year": row.year, "metric": "goals", "value": row.value} for row in rows]
    filters = {"year": year} if year is not None else {}
    return {"data": data, "meta": {"metric": "goals_by_year", "count": len(data), "filters": filters}}


@router.get("/statistics/teams/titles", response_model=TeamStatisticsResponse, tags=["Statistics"], summary="Xếp hạng số lần vô địch")
def team_titles_statistics(db: Db, limit: Limit = 10, year: int | None = None, team_id: int | None = None):
    """Xếp hạng số lần vô địch; có thể giới hạn vào một năm hoặc đội."""
    return team_statistics(db, "titles", limit, _statistics_filters(year, team_id))


@router.get("/statistics/teams/tournaments", response_model=TeamStatisticsResponse, tags=["Statistics"], summary="Xếp hạng số kỳ tham dự của đội")
def team_tournaments_statistics(db: Db, limit: Limit = 10, year: int | None = None, team_id: int | None = None):
    """Xếp hạng số kỳ World Cup mà đội tuyển tham dự."""
    return team_statistics(db, "tournaments", limit, _statistics_filters(year, team_id))


@router.get("/statistics/teams/goals", response_model=TeamStatisticsResponse, tags=["Statistics"], summary="Xếp hạng bàn thắng theo đội")
def team_goals_statistics(
    db: Db, limit: Limit = 10, year: int | None = None, team_id: int | None = None,
    player_id: int | None = None, stage: str | None = None,
):
    """Xếp hạng tổng bàn thắng được ghi nhận cho đội tuyển."""
    return team_statistics(db, "goals", limit, _statistics_filters(year, team_id, player_id, stage))


@router.get("/statistics/teams/wins", response_model=TeamStatisticsResponse, tags=["Statistics"], summary="Xếp hạng số trận thắng theo đội")
def team_wins_statistics(
    db: Db, limit: Limit = 10, year: int | None = None,
    team_id: int | None = None, stage: str | None = None,
):
    """Xếp hạng số trận thắng, bao gồm thắng bằng loạt luân lưu."""
    return team_statistics(db, "wins", limit, _statistics_filters(year, team_id, stage=stage))


@router.get("/statistics/players/goals", response_model=PlayerStatisticsResponse, tags=["Statistics"], summary="Xếp hạng cầu thủ ghi bàn")
def player_goals_statistics(
    db: Db, limit: Limit = 10, year: int | None = None, team_id: int | None = None,
    player_id: int | None = None, stage: str | None = None,
):
    """Xếp hạng cầu thủ ghi nhiều bàn, không tính bàn phản lưới."""
    return player_statistics(db, "goals", limit, _statistics_filters(year, team_id, player_id, stage))


@router.get("/statistics/players/matches", response_model=PlayerStatisticsResponse, tags=["Statistics"], summary="Xếp hạng số trận của cầu thủ")
def player_matches_statistics(
    db: Db, limit: Limit = 10, year: int | None = None, team_id: int | None = None,
    player_id: int | None = None, stage: str | None = None,
):
    """Xếp hạng cầu thủ có nhiều lần ra sân nhất."""
    return player_statistics(db, "matches", limit, _statistics_filters(year, team_id, player_id, stage))


@router.get("/statistics/players/tournaments", response_model=PlayerStatisticsResponse, tags=["Statistics"], summary="Xếp hạng số kỳ tham dự của cầu thủ")
def player_tournaments_statistics(
    db: Db, limit: Limit = 10, year: int | None = None, team_id: int | None = None,
    player_id: int | None = None, stage: str | None = None,
):
    """Xếp hạng số kỳ World Cup trong đội hình hoặc có lượt ra sân."""
    return player_statistics(db, "tournaments", limit, _statistics_filters(year, team_id, player_id, stage))


@router.get("/statistics/matches/goals", response_model=MatchStatisticsResponse, tags=["Statistics"], summary="Xếp hạng trận đấu nhiều bàn")
def match_goals_statistics(
    db: Db, limit: Limit = 10, year: int | None = None, team_id: int | None = None,
    player_id: int | None = None, stage: str | None = None,
):
    """Xếp hạng trận đấu có tổng tỷ số cao nhất."""
    return match_statistics(db, "goals", limit, _statistics_filters(year, team_id, player_id, stage))


@router.get("/statistics/matches/cards", response_model=MatchStatisticsResponse, tags=["Statistics"], summary="Xếp hạng trận đấu nhiều thẻ")
def match_cards_statistics(
    db: Db, limit: Limit = 10, year: int | None = None, team_id: int | None = None,
    player_id: int | None = None, stage: str | None = None,
    card_type: Literal["all", "yellow", "red"] = "all",
):
    """Xếp hạng trận nhiều thẻ; hỗ trợ riêng thẻ vàng hoặc thẻ đỏ."""
    return match_statistics(db, "cards", limit, _statistics_filters(year, team_id, player_id, stage), card_type)


@router.get("/search", response_model=SearchResults, tags=["Search"], summary="Tìm kiếm toàn cục")
def search_everything(
    db: Db, q: Annotated[str, Query(min_length=2, max_length=100)],
    year: int | None = None, team_id: int | None = None,
    player_id: int | None = None, stage: str | None = None,
    limit: Annotated[int, Query(ge=1, le=25)] = 8,
):
    pattern = f"%{q}%"
    home, away = aliased(Team), aliased(Team)
    match_stmt = (
        select(Match).options(joinedload(Match.home_team), joinedload(Match.away_team))
        .join(Tournament, Tournament.id == Match.tournament_id)
        .join(home, home.id == Match.home_team_id)
        .join(away, away.id == Match.away_team_id)
        .where(or_(
            home.name.ilike(pattern), away.name.ilike(pattern), Match.stage.ilike(pattern),
            Match.venue.ilike(pattern), cast(Tournament.year, String).ilike(pattern),
        ))
    )
    if year is not None:
        match_stmt = match_stmt.where(Tournament.year == year)
    if team_id is not None:
        match_stmt = match_stmt.where(or_(Match.home_team_id == team_id, Match.away_team_id == team_id))
    if player_id is not None:
        match_stmt = match_stmt.join(Appearance, Appearance.match_id == Match.id).where(Appearance.player_id == player_id)
    if stage is not None:
        match_stmt = match_stmt.where(_stage_equals(Match.stage, stage))

    tournament_stmt = select(Tournament).options(joinedload(Tournament.champion), joinedload(Tournament.runner_up)).where(
        or_(Tournament.name.ilike(pattern), Tournament.host_country.ilike(pattern))
    )
    if year is not None:
        tournament_stmt = tournament_stmt.where(Tournament.year == year)

    team_stmt = select(Team).where(or_(Team.name.ilike(pattern), Team.fifa_code.ilike(pattern)))
    if team_id is not None:
        team_stmt = team_stmt.where(Team.id == team_id)
    if year is not None:
        team_stmt = team_stmt.join(TournamentTeam, TournamentTeam.team_id == Team.id).join(Tournament).where(Tournament.year == year)

    player_stmt = select(Player).options(joinedload(Player.nationality)).where(Player.full_name.ilike(pattern))
    uses_squad = year is not None or team_id is not None
    if uses_squad:
        player_stmt = player_stmt.join(Squad, Squad.player_id == Player.id)
    if year is not None:
        player_stmt = player_stmt.join(Tournament, Tournament.id == Squad.tournament_id).where(Tournament.year == year)
    if team_id is not None:
        player_stmt = player_stmt.where(Squad.team_id == team_id)
    if player_id is not None:
        player_stmt = player_stmt.where(Player.id == player_id)
    if stage is not None:
        player_stmt = player_stmt.join(Appearance, Appearance.player_id == Player.id).join(Match, Match.id == Appearance.match_id).where(_stage_equals(Match.stage, stage))
        if uses_squad:
            player_stmt = player_stmt.where(Match.tournament_id == Squad.tournament_id)
        if team_id is not None:
            player_stmt = player_stmt.where(Appearance.team_id == team_id)

    news_stmt = select(NewsArticle).where(
        NewsArticle.is_world_cup.is_(True),
        or_(NewsArticle.title.ilike(pattern), NewsArticle.summary.ilike(pattern)),
    )
    if year is not None:
        news_stmt = news_stmt.where(NewsArticle.tournament_year == year)

    return {
        "tournaments": db.scalars(tournament_stmt.limit(limit)).all(),
        "teams": db.scalars(team_stmt.distinct().order_by(Team.name).limit(limit)).all(),
        "players": db.scalars(player_stmt.distinct().order_by(Player.full_name).limit(limit)).all(),
        "matches": db.scalars(match_stmt.distinct().order_by(Match.kickoff_at.desc(), Match.id).limit(limit)).all(),
        "news": db.scalars(news_stmt.order_by(NewsArticle.published_at.desc()).limit(limit)).all(),
    }
