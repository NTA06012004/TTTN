"""Merge identifiers used by the old demo snapshot into canonical dataset IDs."""

from alembic import op
import sqlalchemy as sa


revision = "005_cleanup_demo_duplicates"
down_revision = "004_world_cup_news_relevance"
branch_labels = None
depends_on = None


def _scalar(connection, sql: str, **params):
    return connection.execute(sa.text(sql), params).scalar()


def _merge_player(connection, demo_external_id: str, canonical_external_id: str) -> None:
    demo_id = _scalar(connection, "SELECT id FROM players WHERE external_id = :value", value=demo_external_id)
    canonical_id = _scalar(connection, "SELECT id FROM players WHERE external_id = :value", value=canonical_external_id)
    if not demo_id or not canonical_id or demo_id == canonical_id:
        return

    # Remove only rows that would violate the unique business key after merge;
    # all remaining references are moved to the canonical player.
    for table, key_columns in (
        ("squads", ("tournament_id", "team_id")),
        ("appearances", ("match_id",)),
    ):
        rows = connection.execute(
            sa.text(f"SELECT id, {', '.join(key_columns)} FROM {table} WHERE player_id = :demo_id"),
            {"demo_id": demo_id},
        ).mappings().all()
        for row in rows:
            predicates = " AND ".join(f"{column} = :{column}" for column in key_columns)
            duplicate_id = _scalar(
                connection,
                f"SELECT id FROM {table} WHERE player_id = :canonical_id AND {predicates}",
                canonical_id=canonical_id,
                **{column: row[column] for column in key_columns},
            )
            if duplicate_id:
                connection.execute(sa.text(f"DELETE FROM {table} WHERE id = :row_id"), {"row_id": row["id"]})

        connection.execute(
            sa.text(f"UPDATE {table} SET player_id = :canonical_id WHERE player_id = :demo_id"),
            {"canonical_id": canonical_id, "demo_id": demo_id},
        )

    connection.execute(
        sa.text("UPDATE match_events SET player_id = :canonical_id WHERE player_id = :demo_id"),
        {"canonical_id": canonical_id, "demo_id": demo_id},
    )
    connection.execute(
        sa.text("UPDATE match_events SET related_player_id = :canonical_id WHERE related_player_id = :demo_id"),
        {"canonical_id": canonical_id, "demo_id": demo_id},
    )
    connection.execute(sa.text("DELETE FROM players WHERE id = :demo_id"), {"demo_id": demo_id})


def upgrade():
    connection = op.get_bind()
    demo_match_id = _scalar(connection, "SELECT id FROM matches WHERE external_id = '2022-final'")
    canonical_match_id = _scalar(connection, "SELECT id FROM matches WHERE external_id = 'M-2022-64'")
    if demo_match_id and canonical_match_id and demo_match_id != canonical_match_id:
        connection.execute(sa.text("DELETE FROM match_events WHERE match_id = :match_id"), {"match_id": demo_match_id})
        connection.execute(sa.text("DELETE FROM appearances WHERE match_id = :match_id"), {"match_id": demo_match_id})
        connection.execute(sa.text("DELETE FROM matches WHERE id = :match_id"), {"match_id": demo_match_id})

    _merge_player(connection, "p-messi", "P-14758")
    _merge_player(connection, "p-mbappe", "P-64077")


def downgrade():
    # Cleanup merges data into canonical entities and intentionally does not
    # recreate obsolete demo duplicates on downgrade.
    pass
