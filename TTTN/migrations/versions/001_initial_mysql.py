"""Initial, frozen MySQL schema.

This revision deliberately does not import ``Base.metadata``. Alembic history
must remain reproducible when application models gain columns in the future.
"""

from alembic import op
import sqlalchemy as sa


revision = "001_initial_mysql"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "data_sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("language", sa.String(8)),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("crawl_interval_minutes", sa.Integer(), nullable=False),
    )
    op.create_index("ix_data_sources_source_type", "data_sources", ["source_type"])
    op.create_index("ix_data_sources_enabled", "data_sources", ["enabled"])

    op.create_table(
        "news_articles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("url_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tournament_year", sa.Integer()),
        sa.Column("image_url", sa.String(500)),
        sa.Column("language", sa.String(8), nullable=False),
    )
    op.create_index("ix_news_articles_source", "news_articles", ["source"])
    op.create_index("ix_news_articles_title", "news_articles", ["title"])
    op.create_index("ix_news_articles_published_at", "news_articles", ["published_at"])
    op.create_index("ix_news_articles_tournament_year", "news_articles", ["tournament_year"])

    op.create_table(
        "stadiums",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("capacity", sa.Integer()),
        sa.Column("latitude", sa.String(30)),
        sa.Column("longitude", sa.String(30)),
    )
    op.create_index("ix_stadiums_name", "stadiums", ["name"])
    op.create_index("ix_stadiums_city", "stadiums", ["city"])

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fifa_code", sa.String(16), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("confederation", sa.String(20)),
        sa.Column("flag_url", sa.String(500)),
        sa.Column("description", sa.Text()),
    )
    op.create_index("ix_teams_fifa_code", "teams", ["fifa_code"], unique=True)
    op.create_index("ix_teams_name", "teams", ["name"])

    op.create_table(
        "crawl_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("data_sources.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("records_seen", sa.Integer(), nullable=False),
        sa.Column("records_saved", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text()),
    )
    op.create_index("ix_crawl_runs_source_id", "crawl_runs", ["source_id"])
    op.create_index("ix_crawl_runs_status", "crawl_runs", ["status"])

    op.create_table(
        "data_provenance",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("data_sources.id"), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.BigInteger()),
        sa.Column("external_key", sa.String(190), nullable=False),
        sa.Column("source_url", sa.String(500)),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("raw_payload", sa.JSON()),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id", "entity_type", "external_key"),
    )
    op.create_index("ix_data_provenance_source_id", "data_provenance", ["source_id"])
    op.create_index("ix_data_provenance_entity_type", "data_provenance", ["entity_type"])
    op.create_index("ix_data_provenance_entity_id", "data_provenance", ["entity_id"])

    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("external_id", sa.String(100), unique=True),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("birth_date", sa.Date()),
        sa.Column("nationality_team_id", sa.Integer(), sa.ForeignKey("teams.id")),
        sa.Column("position", sa.String(30)),
        sa.Column("height_cm", sa.Integer()),
        sa.Column("photo_url", sa.String(500)),
    )
    op.create_index("ix_players_full_name", "players", ["full_name"])

    op.create_table(
        "tournaments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("host_country", sa.String(120)),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("champion_team_id", sa.Integer(), sa.ForeignKey("teams.id")),
        sa.Column("runner_up_team_id", sa.Integer(), sa.ForeignKey("teams.id")),
        sa.Column("third_team_id", sa.Integer(), sa.ForeignKey("teams.id")),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("overview", sa.Text()),
    )
    op.create_index("ix_tournaments_year", "tournaments", ["year"], unique=True)

    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tournament_id", sa.Integer(), sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(100), nullable=False),
        sa.Column("kickoff_at", sa.DateTime(timezone=True)),
        sa.Column("stage", sa.String(80), nullable=False),
        sa.Column("group_name", sa.String(20)),
        sa.Column("venue", sa.String(150)),
        sa.Column("stadium_id", sa.Integer(), sa.ForeignKey("stadiums.id")),
        sa.Column("home_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("away_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("home_score", sa.Integer()),
        sa.Column("away_score", sa.Integer()),
        sa.Column("home_penalties", sa.Integer()),
        sa.Column("away_penalties", sa.Integer()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attendance", sa.Integer()),
        sa.Column("referee", sa.String(120)),
        sa.Column("source_url", sa.String(500)),
        sa.UniqueConstraint("tournament_id", "external_id"),
    )
    for name, columns in (
        ("ix_matches_tournament_id", ["tournament_id"]),
        ("ix_matches_kickoff_at", ["kickoff_at"]),
        ("ix_matches_stage", ["stage"]),
        ("ix_matches_stadium_id", ["stadium_id"]),
        ("ix_matches_home_team_id", ["home_team_id"]),
        ("ix_matches_away_team_id", ["away_team_id"]),
        ("ix_matches_status", ["status"]),
    ):
        op.create_index(name, "matches", columns)

    op.create_table(
        "squads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tournament_id", sa.Integer(), sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("shirt_number", sa.Integer()),
        sa.Column("position", sa.String(30)),
        sa.Column("is_captain", sa.Boolean(), nullable=False),
        sa.Column("club", sa.String(120)),
        sa.UniqueConstraint("tournament_id", "team_id", "player_id"),
    )
    op.create_index("ix_squads_tournament_id", "squads", ["tournament_id"])
    op.create_index("ix_squads_team_id", "squads", ["team_id"])
    op.create_index("ix_squads_player_id", "squads", ["player_id"])

    op.create_table(
        "standings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tournament_id", sa.Integer(), sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot", sa.String(80), nullable=False),
        sa.Column("group_name", sa.String(20), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("played", sa.Integer(), nullable=False),
        sa.Column("won", sa.Integer(), nullable=False),
        sa.Column("drawn", sa.Integer(), nullable=False),
        sa.Column("lost", sa.Integer(), nullable=False),
        sa.Column("goals_for", sa.Integer(), nullable=False),
        sa.Column("goals_against", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.UniqueConstraint("tournament_id", "snapshot", "group_name", "team_id"),
    )
    op.create_index("ix_standings_tournament_id", "standings", ["tournament_id"])
    op.create_index("ix_standings_snapshot", "standings", ["snapshot"])
    op.create_index("ix_standings_team_id", "standings", ["team_id"])

    op.create_table(
        "tournament_teams",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tournament_id", sa.Integer(), sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("final_position", sa.Integer()),
        sa.Column("qualification_method", sa.String(200)),
        sa.Column("coach", sa.String(120)),
        sa.UniqueConstraint("tournament_id", "team_id"),
    )
    op.create_index("ix_tournament_teams_tournament_id", "tournament_teams", ["tournament_id"])
    op.create_index("ix_tournament_teams_team_id", "tournament_teams", ["team_id"])

    op.create_table(
        "appearances",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("started", sa.Boolean(), nullable=False),
        sa.Column("minutes_played", sa.Integer(), nullable=False),
        sa.UniqueConstraint("match_id", "player_id"),
    )
    op.create_index("ix_appearances_match_id", "appearances", ["match_id"])
    op.create_index("ix_appearances_player_id", "appearances", ["player_id"])
    op.create_index("ix_appearances_team_id", "appearances", ["team_id"])

    op.create_table(
        "match_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id")),
        sa.Column("event_type", sa.String(13), nullable=False),
        sa.Column("minute", sa.Integer()),
        sa.Column("stoppage_minute", sa.Integer()),
    )
    op.create_index("ix_match_events_match_id", "match_events", ["match_id"])
    op.create_index("ix_match_events_team_id", "match_events", ["team_id"])
    op.create_index("ix_match_events_player_id", "match_events", ["player_id"])
    op.create_index("ix_match_events_event_type", "match_events", ["event_type"])
    op.create_index("ix_events_match_type", "match_events", ["match_id", "event_type"])


def downgrade():
    for table in (
        "match_events", "appearances", "tournament_teams", "standings", "squads", "matches",
        "tournaments", "players", "data_provenance", "crawl_runs", "teams", "stadiums",
        "news_articles", "data_sources",
    ):
        op.drop_table(table)
