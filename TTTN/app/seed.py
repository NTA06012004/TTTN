from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Team, Tournament, TournamentTeam


# Metadata nền cho toàn bộ 23 kỳ đã hoàn thành từ 1930 đến 2026.
EDITIONS = [
    (1930, "Uruguay", "Uruguay", "Argentina"), (1934, "Italy", "Italy", "Czechoslovakia"),
    (1938, "France", "Italy", "Hungary"), (1950, "Brazil", "Uruguay", "Brazil"),
    (1954, "Switzerland", "West Germany", "Hungary"), (1958, "Sweden", "Brazil", "Sweden"),
    (1962, "Chile", "Brazil", "Czechoslovakia"), (1966, "England", "England", "West Germany"),
    (1970, "Mexico", "Brazil", "Italy"), (1974, "West Germany", "West Germany", "Netherlands"),
    (1978, "Argentina", "Argentina", "Netherlands"), (1982, "Spain", "Italy", "West Germany"),
    (1986, "Mexico", "Argentina", "West Germany"), (1990, "Italy", "West Germany", "Argentina"),
    (1994, "United States", "Brazil", "Italy"), (1998, "France", "France", "Brazil"),
    (2002, "South Korea & Japan", "Brazil", "Germany"), (2006, "Germany", "Italy", "France"),
    (2010, "South Africa", "Spain", "Netherlands"), (2014, "Brazil", "Germany", "Argentina"),
    (2018, "Russia", "France", "Croatia"), (2022, "Qatar", "Argentina", "France"),
    (2026, "Canada, Mexico & United States", "Spain", "Argentina"),
]


def seed_editions(db: Session) -> None:
    try:
        for year, host, champion_name, runner_name in EDITIONS:
            champion, runner = _team(db, champion_name), _team(db, runner_name)
            item = db.scalar(select(Tournament).where(Tournament.year == year))
            if not item:
                item = Tournament(year=year, name=f"FIFA World Cup {year}")
            item.host_country, item.champion, item.runner_up = host, champion, runner
            db.add(item)
            db.flush()
            for team, position in ((champion, 1), (runner, 2)):
                entry = db.scalar(select(TournamentTeam).where(TournamentTeam.tournament_id == item.id, TournamentTeam.team_id == team.id))
                if not entry:
                    entry = TournamentTeam(tournament_id=item.id, team_id=team.id)
                entry.final_position = position
                db.add(entry)
        db.commit()
    except Exception:
        db.rollback(); raise


def _team(db: Session, name: str) -> Team:
    aliases = {"West Germany": "FRG", "United States": "USA", "Czechoslovakia": "TCH", "Netherlands": "NED"}
    code = aliases.get(name, name[:3].upper())
    team = db.scalar(select(Team).where(Team.fifa_code == code))
    if not team:
        team = Team(fifa_code=code, name=name)
        db.add(team); db.flush()
    return team
