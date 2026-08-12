"""Add ETL rejects and idempotent event keys."""
from alembic import op
import sqlalchemy as sa


revision = "002_etl_quality_events"
down_revision = "001_initial_mysql"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("crawl_runs", sa.Column("records_rejected", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("match_events", sa.Column("external_id", sa.String(100), nullable=True))
    op.add_column("match_events", sa.Column("related_player_id", sa.Integer(), nullable=True))
    op.alter_column("match_events", "event_type", existing_type=sa.String(13), type_=sa.String(30), existing_nullable=False)
    op.create_foreign_key("fk_event_related_player", "match_events", "players", ["related_player_id"], ["id"])
    op.create_index("ix_match_events_related_player_id", "match_events", ["related_player_id"])
    op.create_unique_constraint("uq_match_event_external", "match_events", ["match_id", "external_id"])
    op.create_table(
        "etl_rejects",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("crawl_run_id", sa.BigInteger(), sa.ForeignKey("crawl_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("data_sources.id"), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("external_key", sa.String(190)),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("raw_payload", sa.JSON()),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_etl_rejects_crawl_run_id", "etl_rejects", ["crawl_run_id"])
    op.create_index("ix_etl_rejects_source_id", "etl_rejects", ["source_id"])
    op.create_index("ix_etl_rejects_entity_type", "etl_rejects", ["entity_type"])


def downgrade():
    op.drop_table("etl_rejects")
    op.drop_constraint("uq_match_event_external", "match_events", type_="unique")
    op.drop_index("ix_match_events_related_player_id", table_name="match_events")
    op.drop_constraint("fk_event_related_player", "match_events", type_="foreignkey")
    op.alter_column("match_events", "event_type", existing_type=sa.String(30), type_=sa.String(13), existing_nullable=False)
    op.drop_column("match_events", "related_player_id")
    op.drop_column("match_events", "external_id")
    op.drop_column("crawl_runs", "records_rejected")
