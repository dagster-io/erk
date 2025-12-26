"""
Helper functions for usage monitoring tests.

This module provides shared utilities for testing bonus answer grants,
consumption tracking, and other usage monitoring functionality.
"""

import asyncio
from datetime import UTC, datetime


async def setup_organization_bonus_answer_grant(
    sql_conn_factory, organization_id: int, answer_count: int
):
    """
    Insert bonus answer grant directly into the database.

    Args:
        sql_conn_factory: Database connection factory
        organization_id: ID of the organization to grant answers to
        answer_count: Number of bonus answers to grant

    Example:
        await setup_organization_bonus_answer_grant(
            sql_conn_factory, org_id=123, answer_count=10
        )
    """

    def _sync_insert():
        with sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO bonus_answer_grants (organization_id, answer_count, reason) VALUES (%s, %s, %s)",
                (organization_id, answer_count, "Test grant"),
            )
            conn.commit()

    await asyncio.to_thread(_sync_insert)


async def setup_bonus_answer_consumption_via_bot(
    sql_conn_factory, bot_id: str, consumed_count: int
):
    """
    Simulate bonus answer consumption by directly updating usage tracking table.

    Args:
        sql_conn_factory: Database connection factory
        bot_id: ID of the bot consuming answers
        consumed_count: Number of bonus answers consumed

    Example:
        await setup_bonus_answer_consumption_via_bot(
            sql_conn_factory, bot_id="test-bot", consumed_count=5
        )
    """

    def _sync_update():
        current_month = datetime.now(UTC).month
        current_year = datetime.now(UTC).year

        with sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            # Check if a usage tracking entry exists
            cursor.execute(
                "SELECT id FROM usage_tracking WHERE bot_id = %s AND month = %s AND year = %s",
                (bot_id, current_month, current_year),
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing record
                cursor.execute(
                    "UPDATE usage_tracking SET bonus_answer_count = %s WHERE bot_id = %s AND month = %s AND year = %s",
                    (consumed_count, bot_id, current_month, current_year),
                )
            else:
                # Insert new record
                cursor.execute(
                    "INSERT INTO usage_tracking (bot_id, month, year, answer_count, bonus_answer_count) VALUES (%s, %s, %s, %s, %s)",
                    (bot_id, current_month, current_year, 0, consumed_count),
                )
            conn.commit()

    await asyncio.to_thread(_sync_update)
