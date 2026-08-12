"""Add composite indexes for statistics and advanced filters."""
from alembic import op


revision = "003_statistics_indexes"
down_revision = "002_etl_quality_events"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_tournaments_champion_year", "tournaments", ["champion_team_id", "year"])
    op.create_index("ix_squads_player_tournament", "squads", ["player_id", "tournament_id"])
    op.create_index("ix_squads_team_tournament", "squads", ["team_id", "tournament_id"])
    op.create_index("ix_matches_tournament_stage_kickoff", "matches", ["tournament_id", "stage", "kickoff_at"])
    op.create_index("ix_matches_home_tournament", "matches", ["home_team_id", "tournament_id"])
    op.create_index("ix_matches_away_tournament", "matches", ["away_team_id", "tournament_id"])
    op.create_index("ix_appearances_player_match", "appearances", ["player_id", "match_id"])
    op.create_index("ix_appearances_team_match", "appearances", ["team_id", "match_id"])
    op.create_index("ix_events_player_type_match", "match_events", ["player_id", "event_type", "match_id"])
    op.create_index("ix_events_team_type_match", "match_events", ["team_id", "event_type", "match_id"])
    op.create_index("ix_tournament_teams_team_tournament", "tournament_teams", ["team_id", "tournament_id"])


def downgrade():
    op.drop_index("ix_tournament_teams_team_tournament", table_name="tournament_teams")
    op.drop_index("ix_events_team_type_match", table_name="match_events")
    op.drop_index("ix_events_player_type_match", table_name="match_events")
    op.drop_index("ix_appearances_team_match", table_name="appearances")
    op.drop_index("ix_appearances_player_match", table_name="appearances")
    op.drop_index("ix_matches_away_tournament", table_name="matches")
    op.drop_index("ix_matches_home_tournament", table_name="matches")
    op.drop_index("ix_matches_tournament_stage_kickoff", table_name="matches")
    op.drop_index("ix_squads_team_tournament", table_name="squads")
    op.drop_index("ix_squads_player_tournament", table_name="squads")
    op.drop_index("ix_tournaments_champion_year", table_name="tournaments")
