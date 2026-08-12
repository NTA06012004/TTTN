"""Rules for keeping the news catalogue focused on the men's FIFA World Cup."""

from __future__ import annotations

import re
import unicodedata


WORLD_CUP_PATTERN = re.compile(
    r"(?<!\w)(?:fifa\s+)?world[\s-]*cup(?!\w)|c[uú]p\s+th[eế]\s+gi[oớ]i",
    re.IGNORECASE,
)

# These competitions can contain the phrase "World Cup", but are outside the
# scope of this application: the men's senior national-team FIFA World Cup.
EXCLUDED_PATTERN = re.compile(
    r"(?:"
    r"club\s+world\s+cup|world\s+cup\s+(?:club|n[uữ])|"
    r"women(?:'s)?\s+world\s+cup|world\s+cup\s+women|"
    r"futsal|beach\s+soccer|b[oó]ng\s+[dđ][aá]\s+b[aã]i\s+bi[eể]n|"
    r"\bu[\s.-]?(?:17|20)\b|gi[aả]i\s+tr[eẻ]|youth\s+world\s+cup|"
    r"c[aá]c\s+c[aâ]u\s+l[aạ]c\s+b[oộ]|\bclb\b|"
    r"b[oó]ng\s+chuy[eề]n|volleyball|billiards?|bi-a|c[oờ]\s+vua|chess|"
    r"rugby|cricket|b[oó]ng\s+r[oổ]|basketball|esports?|th[eể]\s+d[uụ]c|"
    r"b[aắ]n\s+s[uú]ng|c[aầ]u\s+l[oô]ng|badminton|hockey|tr[uư][oợ]t\s+tuy[eế]t"
    r")",
    re.IGNORECASE,
)


def _normalize(value: str | None) -> str:
    return unicodedata.normalize("NFKC", value or "").casefold()


def is_world_cup_news(title: str | None, summary: str | None = None) -> bool:
    """Return True only for news about the men's senior FIFA World Cup."""

    normalized_title = _normalize(title)
    if WORLD_CUP_PATTERN.search(normalized_title):
        return EXCLUDED_PATTERN.search(normalized_title) is None

    normalized_summary = _normalize(summary)
    return bool(
        WORLD_CUP_PATTERN.search(normalized_summary)
        and EXCLUDED_PATTERN.search(normalized_summary) is None
    )
