# Sync wrapper functions for compatibility with existing code
"""Protocol defining the interface all agent implementations must follow."""

import asyncio
import time

from csbot.agents.completion_utils import (
    categorize_context,
    generate_context_summary,
    generate_dataset_summary,
)
from csbot.agents.protocol import AsyncAgent


def sync_generate_context_summary(
    agent: AsyncAgent, topic: str, incorrect_understanding: str, correct_understanding: str
) -> tuple[str, str]:
    """Synchronous wrapper for generate_context_summary."""

    return asyncio.run(
        generate_context_summary(agent, topic, incorrect_understanding, correct_understanding)
    )


def sync_categorize_context(
    agent: AsyncAgent, summary: str, available_categories: list[str]
) -> str:
    """Synchronous wrapper for categorize_context."""

    return asyncio.run(categorize_context(agent, summary, available_categories))


def sync_generate_dataset_summary(agent: AsyncAgent, markdown_report: str) -> str:
    """Synchronous wrapper for generate_dataset_summary."""

    # Create a new event loop in this thread to avoid conflicts
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        summary = loop.run_until_complete(generate_dataset_summary(agent, markdown_report))

        # Give time for Anthropic HTTP connections to properly close
        time.sleep(2)

        return summary
    finally:
        # Don't close the loop immediately - let cleanup finish
        loop.call_later(5, loop.close)
