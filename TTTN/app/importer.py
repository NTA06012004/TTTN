import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Appearance, EventType, Match, MatchEvent, Player, Squad, Standing, Team, Tournament, TournamentTeam


def import_json(db: Session, path: str | Path) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        teams = {item["code"]: _upsert_team(db, item) for item in data.get("teams", [])}
        tournament_data = data["tournament"]
        tournament = _one(db, Tournament, "year", tournament_data["year"]) or Tournament(year=tournament_data["year"], name=tournament_data["name"])
        tournament.host_country = tournament_data.get("host_country")
        if tournament_data.get("champion_code"):
            tournament.champion = teams[tournament_data["champion_code"]]
        db.add(tournament)
        db.flush()
        for team in teams.values():
            if not db.scalar(select(TournamentTeam).where(TournamentTeam.tournament_id == tournament.id, TournamentTeam.team_id == team.id)):
                db.add(TournamentTeam(tournament_id=tournament.id, team_id=team.id))

        players = {}
        for item in data.get("players", []):
            key = item["external_id"]
            player = _one(db, Player, "external_id", key) or Player(external_id=key, full_name=item["full_name"])
            player.full_name = item["full_name"]
            player.nationality = teams[item["team_code"]]
            player.position = item.get("position")
            db.add(player)
            db.flush()
            players[key] = player
            squad = db.scalar(select(Squad).where(Squad.tournament_id == tournament.id, Squad.team_id == teams[item["team_code"]].id, Squad.player_id == player.id))
            if not squad:
                db.add(Squad(tournament_id=tournament.id, team_id=teams[item["team_code"]].id, player_id=player.id, shirt_number=item.get("shirt_number"), position=item.get("position")))

        for item in data.get("matches", []):
            match = db.scalar(select(Match).where(Match.tournament_id == tournament.id, Match.external_id == item["external_id"]))
            if not match:
                match = Match(tournament_id=tournament.id, external_id=item["external_id"], stage=item["stage"], home_team_id=teams[item["home"]].id, away_team_id=teams[item["away"]].id)
            for field in ("home_score", "away_score", "home_penalties", "away_penalties", "status", "venue"):
                if field in item:
                    setattr(match, field, item[field])
            db.add(match)
            db.flush()
            # Child records are replaced atomically: simple and deterministic for source snapshots.
            for old in db.scalars(select(MatchEvent).where(MatchEvent.match_id == match.id)).all():
                db.delete(old)
            for old in db.scalars(select(Appearance).where(Appearance.match_id == match.id)).all():
                db.delete(old)
            for event in item.get("events", []):
                db.add(MatchEvent(match_id=match.id, team_id=teams[event["team"]].id, player_id=players[event["player"]].id if event.get("player") else None, event_type=EventType(event["type"]), minute=event.get("minute")))
            for app in item.get("appearances", []):
                player = players[app["player"]]
                db.add(Appearance(match_id=match.id, player_id=player.id, team_id=player.nationality_team_id, started=app.get("started", False), minutes_played=app.get("minutes", 0)))

        db.commit()
    except Exception:
        db.rollback()
        raise


def _upsert_team(db: Session, item: dict) -> Team:
    team = _one(db, Team, "fifa_code", item["code"]) or Team(fifa_code=item["code"], name=item["name"])
    team.name, team.confederation = item["name"], item.get("confederation")
    db.add(team)
    db.flush()
    return team


def _one(db: Session, model, field: str, value):
    return db.scalar(select(model).where(getattr(model, field) == value))
