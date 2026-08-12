"""Adapters for the CC-BY-SA Fjelstul World Cup Database."""
import csv
from io import StringIO
from app.config import get_settings
from app.crawlers.base import CrawlerAdapter, SourceRecord
from app.crawlers.http import crawler_session
from app.crawlers.transform import DataQualityError, boolean, clean_text, integer, person_name, world_cup_year


BASE = "https://raw.githubusercontent.com/jfjelstul/worldcup/master/data-csv"


def team(row: dict, prefix: str = "team") -> dict:
    return {
        "external_id": clean_text(row.get(f"{prefix}_id")),
        "name": clean_text(row.get(f"{prefix}_name"), nullable=False),
        "code": clean_text(row.get(f"{prefix}_code"), nullable=False),
    }


def player(row: dict) -> dict:
    return {
        "external_id": clean_text(row.get("player_id"), nullable=False),
        "full_name": person_name(row.get("given_name"), row.get("family_name")),
        "position": clean_text(row.get("position_code") or row.get("position_name")),
    }


class FjelstulCsvCrawler(CrawlerAdapter):
    source_type = "worldcup_structured_csv"
    dataset: str
    entity_type: str

    @property
    def base_url(self):
        return f"{BASE}/{self.dataset}.csv"

    def crawl(self, *, year: int | None = None):
        response = crawler_session().get(self.base_url, timeout=get_settings().request_timeout_seconds)
        response.raise_for_status()
        for row in csv.DictReader(StringIO(response.text)):
            if "Men's World Cup" not in row.get("tournament_name", ""):
                continue
            row_year = world_cup_year(row.get("tournament_id"), row.get("match_date"))
            if year is not None and row_year != year:
                continue
            record = self.transform(row, row_year)
            yield SourceRecord(self.entity_type, record["external_id"], self.base_url, record)

    def transform(self, row: dict, year: int) -> dict:
        raise NotImplementedError


class FjelstulMatchesCrawler(FjelstulCsvCrawler):
    code, name, dataset, entity_type = "fjelstul_matches", "Fjelstul World Cup matches", "matches", "match"

    def transform(self, row, year):
        return {
            "external_id": row["match_id"], "year": year, "date": row["match_date"], "time": clean_text(row.get("match_time")),
            "stage": clean_text(row.get("stage_name"), nullable=False), "group": clean_text(row.get("group_name")),
            "home_team": team(row, "home_team"), "away_team": team(row, "away_team"),
            "home_score": integer(row.get("home_team_score"), default=0, minimum=0),
            "away_score": integer(row.get("away_team_score"), default=0, minimum=0),
            "home_penalties": integer(row.get("home_team_score_penalties"), default=0, minimum=0),
            "away_penalties": integer(row.get("away_team_score_penalties"), default=0, minimum=0),
            "stadium": {"external_id": clean_text(row.get("stadium_id")), "name": clean_text(row.get("stadium_name")), "city": clean_text(row.get("city_name")), "country": clean_text(row.get("country_name"))},
        }


class FjelstulSquadsCrawler(FjelstulCsvCrawler):
    code, name, dataset, entity_type = "fjelstul_squads", "Fjelstul World Cup squads", "squads", "squad"

    def transform(self, row, year):
        return {"external_id": f'{row["tournament_id"]}:{row["team_id"]}:{row["player_id"]}', "year": year, "team": team(row), "player": player(row), "shirt_number": integer(row.get("shirt_number"), default=None, minimum=0), "position": clean_text(row.get("position_code") or row.get("position_name"))}


class FjelstulGroupStandingsCrawler(FjelstulCsvCrawler):
    code, name, dataset, entity_type = "fjelstul_group_standings", "Fjelstul group standings", "group_standings", "standing"

    def transform(self, row, year):
        return {
            "external_id": row["key_id"], "year": year, "snapshot": "final",
            "stage": clean_text(row.get("stage_name")), "group": clean_text(row.get("group_name"), nullable=False),
            "team": team(row), "rank": integer(row.get("position"), minimum=1),
            "played": integer(row.get("played"), default=0, minimum=0),
            "won": integer(row.get("wins"), default=0, minimum=0),
            "drawn": integer(row.get("draws"), default=0, minimum=0),
            "lost": integer(row.get("losses"), default=0, minimum=0),
            "goals_for": integer(row.get("goals_for"), default=0, minimum=0),
            "goals_against": integer(row.get("goals_against"), default=0, minimum=0),
            "points": integer(row.get("points"), default=0, minimum=0),
        }


class FjelstulTournamentStandingsCrawler(FjelstulCsvCrawler):
    code, name, dataset, entity_type = "fjelstul_tournament_standings", "Fjelstul tournament standings", "tournament_standings", "tournament_standing"

    def transform(self, row, year):
        return {
            "external_id": row["key_id"], "year": year, "team": team(row),
            "final_position": integer(row.get("position"), minimum=1),
        }


class FjelstulAppearancesCrawler(FjelstulCsvCrawler):
    code, name, dataset, entity_type = "fjelstul_appearances", "Fjelstul player appearances", "player_appearances", "appearance"

    def transform(self, row, year):
        return {"external_id": f'{row["match_id"]}:{row["player_id"]}', "year": year, "match_external_id": row["match_id"], "team": team(row), "player": player(row), "started": boolean(row.get("starter")), "minutes": 0}


class FjelstulGoalsCrawler(FjelstulCsvCrawler):
    code, name, dataset, entity_type = "fjelstul_goals", "Fjelstul World Cup goals", "goals", "match_event"

    def transform(self, row, year):
        event_type = "own_goal" if boolean(row.get("own_goal")) else "penalty_goal" if boolean(row.get("penalty")) else "goal"
        credited_team = team(row)
        player_team = team(row, "player_team")
        return _event(row, year, row["goal_id"], event_type, credited_team, player_team)


class FjelstulBookingsCrawler(FjelstulCsvCrawler):
    code, name, dataset, entity_type = "fjelstul_bookings", "Fjelstul World Cup bookings", "bookings", "match_event"

    def transform(self, row, year):
        event_type = "second_yellow" if boolean(row.get("second_yellow_card")) else "red_card" if boolean(row.get("red_card")) else "yellow_card"
        return _event(row, year, row["booking_id"], event_type, team(row), team(row))


class FjelstulPenaltyKicksCrawler(FjelstulCsvCrawler):
    code, name, dataset, entity_type = "fjelstul_penalties", "Fjelstul World Cup shootouts", "penalty_kicks", "match_event"

    def transform(self, row, year):
        event_type = "penalty_shootout_goal" if boolean(row.get("converted")) else "penalty_shootout_miss"
        return _event(row, year, row["penalty_kick_id"], event_type, team(row), team(row))


class FjelstulSubstitutionsCrawler(FjelstulCsvCrawler):
    code, name, dataset, entity_type = "fjelstul_substitutions", "Fjelstul substitutions", "substitutions", "match_event"

    def transform(self, row, year):
        going_off, coming_on = boolean(row.get("going_off")), boolean(row.get("coming_on"))
        if going_off == coming_on:
            raise DataQualityError("Substitution must mark exactly one of going_off/coming_on")
        direction = "out" if going_off else "in"
        return _event(row, year, f'{row["substitution_id"]}:{row["player_id"]}:{direction}', f"substitution_{direction}", team(row), team(row))


def _event(row, year, external_id, event_type, credited_team, player_team):
    return {
        "external_id": external_id, "year": year, "match_external_id": row["match_id"],
        "team": credited_team, "player_team": player_team, "player": player(row), "event_type": event_type,
        "minute": integer(row.get("minute_regulation"), default=0, minimum=0),
        "stoppage_minute": integer(row.get("minute_stoppage"), default=0, minimum=0),
    }
FJELSTUL_ADAPTERS = (
    FjelstulMatchesCrawler(), FjelstulGroupStandingsCrawler(), FjelstulTournamentStandingsCrawler(),
    FjelstulSquadsCrawler(), FjelstulAppearancesCrawler(),
    FjelstulGoalsCrawler(), FjelstulBookingsCrawler(), FjelstulPenaltyKicksCrawler(), FjelstulSubstitutionsCrawler(),
)
