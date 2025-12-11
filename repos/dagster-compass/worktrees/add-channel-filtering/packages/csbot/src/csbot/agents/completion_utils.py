"""Utility functions that use agent completion capabilities."""

import re

from csbot.agents.messages import AgentTextMessage
from csbot.agents.protocol import AsyncAgent


async def generate_context_summary(
    agent: AsyncAgent, topic: str, incorrect_understanding: str, correct_understanding: str
) -> tuple[str, str]:
    """Generate AI summary and keywords for context."""
    prompt = f"""Given the following context about {topic}, create:
1. A concise 140-character summary that captures the key points
2. A list of relevant search keywords separated by commas

Context:
Incorrect Understanding: {incorrect_understanding}
Correct Understanding: {correct_understanding}

Format your response as:
SUMMARY: <280 char summary>
KEYWORDS: <comma-separated keywords>"""

    system = (
        "You are a helpful assistant that creates concise summaries and relevant "
        "keywords for documentation."
    )

    response = await agent.create_completion(
        model=agent.model,
        system=system,
        messages=[AgentTextMessage(role="user", content=prompt)],
        max_tokens=2048,
    )

    # Parse response
    summary_match = re.search(r"SUMMARY: (.*?)(?:\n|$)", response)
    keywords_match = re.search(r"KEYWORDS: (.*?)(?:\n|$)", response)

    if not summary_match or not keywords_match:
        raise ValueError("Could not parse AI response for summary and keywords")

    summary = summary_match.group(1).strip()
    keywords = keywords_match.group(1).strip()

    return summary, keywords


async def categorize_context(
    agent: AsyncAgent, summary: str, available_categories: list[str]
) -> str:
    """Categorize context into one of available categories."""
    system = (
        "You are a helpful assistant that categorizes context into a single category for storage in a "
        "filesystem. You should return only the category name and nothing else. Do not return a "
        "category name that is not provided to you. Format your response as:\n"
        "CATEGORY: <one of the provided categories>"
    )

    content = f"Context: {summary}\n\nPotential categories: {', '.join(available_categories)}"

    response = await agent.create_completion(
        model=agent.model,
        system=system,
        messages=[AgentTextMessage(role="user", content=content)],
        max_tokens=2048,
    )

    # Parse response
    match = re.search(r"CATEGORY: (.*?)(?:\n|$)", response)
    if match:
        return match.group(1).strip()
    else:
        # Fallback to uncategorized if parsing fails
        return "uncategorized"


async def generate_dataset_summary(agent: AsyncAgent, markdown_report: str) -> str:
    """Generate comprehensive dataset summary from analysis."""
    system = (
        "You are a data analysis expert. Given a table analysis report in markdown format, create a "
        "comprehensive summary that will help an LLM understand the data structure and characteristics "
        "to generate accurate SQL queries. Include:\n\n"
        "1. Overall dataset characteristics:\n"
        "  - Total number of rows\n"
        "  - General data quality observations\n"
        "  - Any notable patterns or distributions\n"
        "  - Table comment if provided\n\n"
        "2. For each column:\n"
        "  - Data type and format\n"
        "  - Null value patterns\n"
        "  - Value distributions or patterns\n"
        "  - Common values (if applicable)\n"
        "  - Column comment if provided\n\n"
        "3. Potential query considerations:\n"
        "  - Which columns might be good for filtering\n"
        "  - Which columns might be good for grouping/aggregation\n"
        "  - Any potential join keys or relationships\n"
        "  - Data quality considerations for queries\n\n"
        "Format the summary in clear sections with markdown headers. Be specific and detailed to "
        'help an LLM understand the data structure. Be sure to include a "Keywords" section for '
        "relevant search keywords to make this documentation easier to find, and a "
        '"table and column docs" section for the table comment and column comments verbatim,'
        " if present."
    )

    return await agent.create_completion(
        model=agent.model,
        system=system,
        messages=[AgentTextMessage(role="user", content=markdown_report)],
        max_tokens=63950,  # max for this model
    )
