"""Pure transformation and data-quality helpers for crawler payloads."""
from datetime import date
from hashlib import sha256
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


WORLD_CUP_YEARS = {1930, 1934, 1938, *range(1950, 2027, 4)}
EMPTY_VALUES = {"", "na", "n/a", "null", "none", "not applicable", "unknown"}


class DataQualityError(ValueError):
    pass


def clean_text(value, *, nullable: bool = True) -> str | None:
    if value is None:
        return None if nullable else ""
    result = unicodedata.normalize("NFKC", str(value))
    result = re.sub(r"\s+", " ", result).strip()
    if result.casefold() in EMPTY_VALUES:
        return None if nullable else ""
    return result


def person_name(given_name, family_name) -> str:
    parts = [clean_text(given_name), clean_text(family_name)]
    return " ".join(part for part in parts if part) or "Unknown player"


def integer(value, *, default: int | None = None, minimum: int | None = None) -> int | None:
    cleaned = clean_text(value)
    if cleaned is None:
        return default
    try:
        result = int(float(cleaned))
    except (TypeError, ValueError) as exc:
        raise DataQualityError(f"Invalid integer: {value!r}") from exc
    if minimum is not None and result < minimum:
        raise DataQualityError(f"Integer {result} is below {minimum}")
    return result


def boolean(value) -> bool:
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}


def iso_date(value) -> date:
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise DataQualityError(f"Invalid ISO date: {value!r}") from exc


def world_cup_year(tournament_id: str | None = None, match_date=None) -> int:
    match = re.search(r"(19\d{2}|20\d{2})", tournament_id or "")
    year = int(match.group()) if match else iso_date(match_date).year
    if year not in WORLD_CUP_YEARS:
        raise DataQualityError(f"Not a World Cup edition year: {year}")
    return year


def canonical_url(value: str) -> str:
    raw = clean_text(value, nullable=False)
    parts = urlsplit(raw)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise DataQualityError(f"Invalid HTTP URL: {value!r}")
    query = [(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True) if not key.lower().startswith("utm_")]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/") or "/", urlencode(query), ""))


def content_key(*parts) -> str:
    normalized = "|".join(clean_text(part, nullable=False).casefold() for part in parts)
    return sha256(normalized.encode("utf-8")).hexdigest()


def validate_payload(entity_type: str, payload: dict) -> None:
    year = payload.get("year") or payload.get("tournament_year")
    if year is not None and int(year) not in WORLD_CUP_YEARS:
        raise DataQualityError(f"Unsupported World Cup year: {year}")
    if entity_type == "match":
        required = ("external_id", "home_team", "away_team", "date")
        _required(payload, required)
        _required_nested(payload["home_team"], ("name",), "home_team")
        _required_nested(payload["away_team"], ("name",), "away_team")
        if payload["home_team"]["name"].casefold() == payload["away_team"]["name"].casefold():
            raise DataQualityError("Home and away team cannot be identical")
        integer(payload.get("home_score"), minimum=0)
        integer(payload.get("away_score"), minimum=0)
    elif entity_type == "match_event":
        _required(payload, ("external_id", "match_external_id", "team", "event_type"))
        _required_nested(payload["team"], ("name",), "team")
        if payload.get("player"):
            _required_nested(payload["player"], ("external_id", "full_name"), "player")
        minute = integer(payload.get("minute"), default=0, minimum=0)
        if minute is not None and minute > 130:
            raise DataQualityError(f"Invalid event minute: {minute}")
    elif entity_type == "squad":
        _required(payload, ("team", "player", "year"))
        _required_nested(payload["team"], ("name",), "team")
        _required_nested(payload["player"], ("external_id", "full_name"), "player")
    elif entity_type == "appearance":
        _required(payload, ("match_external_id", "team", "player", "year"))
        _required_nested(payload["team"], ("name",), "team")
        _required_nested(payload["player"], ("external_id", "full_name"), "player")
    elif entity_type == "standing":
        _required(payload, ("year", "group", "team", "rank"))
        _required_nested(payload["team"], ("name",), "team")
    elif entity_type == "tournament_standing":
        _required(payload, ("year", "team", "final_position"))
        _required_nested(payload["team"], ("name",), "team")
    elif entity_type == "news":
        _required(payload, ("url", "title", "source"))
        canonical_url(payload["url"])


def _required(payload: dict, keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if payload.get(key) in (None, "", {})]
    if missing:
        raise DataQualityError("Missing required fields: " + ", ".join(missing))


def _required_nested(payload: dict, keys: tuple[str, ...], prefix: str) -> None:
    missing = [f"{prefix}.{key}" for key in keys if payload.get(key) in (None, "", {})]
    if missing:
        raise DataQualityError("Missing required fields: " + ", ".join(missing))
