"""Classify news articles by World Cup relevance."""

from alembic import op
import sqlalchemy as sa


revision = "004_world_cup_news_relevance"
down_revision = "003_statistics_indexes"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "news_articles",
        sa.Column("is_world_cup", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_news_articles_is_world_cup", "news_articles", ["is_world_cup"])


def downgrade():
    op.drop_index("ix_news_articles_is_world_cup", table_name="news_articles")
    op.drop_column("news_articles", "is_world_cup")
