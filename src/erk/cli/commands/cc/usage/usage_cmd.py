"""Main command for displaying Claude Code usage analytics."""

import json
from typing import Any

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from erk.cli.commands.cc.usage.client import AnthropicAdminClient, AnthropicAdminError
from erk.cli.commands.cc.usage.shared import resolve_tokens


def _format_tokens(count: int) -> str:
    """Format token count as human-readable string."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def _format_cost(cost: float) -> str:
    """Format cost as dollar amount."""
    if cost >= 1.0:
        return f"${cost:.2f}"
    if cost >= 0.01:
        return f"${cost:.3f}"
    return f"${cost:.4f}"


def _format_loc(added: int, removed: int) -> str:
    """Format lines of code as +added/-removed."""
    return f"+{added}/-{removed}"


def _render_table(records: list[dict[str, Any]]) -> None:
    """Render usage records as a Rich table to stderr.

    Each user record gets a summary row followed by indented model and tool
    action sub-rows.
    """
    if not records:
        click.echo("No usage records found.", err=True)
        return

    # Sort by date then email
    records.sort(key=lambda r: (r.get("date", ""), r.get("actor", {}).get("email", "")))

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("User", no_wrap=True)
    table.add_column("Date", no_wrap=True)
    table.add_column("Type", no_wrap=True)
    table.add_column("Sessions", no_wrap=True, justify="right")
    table.add_column("LOC", no_wrap=True, justify="right")
    table.add_column("Commits", no_wrap=True, justify="right")
    table.add_column("PRs", no_wrap=True, justify="right")
    table.add_column("Detail", no_wrap=False)

    for record in records:
        actor = record.get("actor", {})
        email = actor.get("email", actor.get("key_name", "unknown"))
        subscription_type = record.get("subscription_type", "")
        date = record.get("date", "")
        sessions = record.get("sessions", 0)
        loc_added = record.get("lines_of_code_added", 0)
        loc_removed = record.get("lines_of_code_removed", 0)
        commits = record.get("commits", 0)
        prs = record.get("pull_requests", 0)

        # Highlight Max subscription users
        is_max = "max" in subscription_type.lower() if subscription_type else False

        user_text = Text(str(email))
        if is_max:
            user_text.stylize("bold magenta")

        type_text = Text(str(subscription_type))
        if is_max:
            type_text.stylize("bold magenta")

        # User summary row
        table.add_row(
            user_text,
            date,
            type_text,
            str(sessions),
            _format_loc(loc_added, loc_removed),
            str(commits),
            str(prs),
            "",
        )

        # Model breakdown sub-rows
        models = record.get("model_usage", [])
        for model in models:
            model_name = model.get("model", "unknown")
            input_tokens = model.get("input_tokens", 0)
            output_tokens = model.get("output_tokens", 0)
            cache_creation = model.get("cache_creation_input_tokens", 0)
            cache_read = model.get("cache_read_input_tokens", 0)
            cache_tokens = cache_creation + cache_read
            cost = model.get("cost_usd", 0.0)

            detail = (
                f"in={_format_tokens(input_tokens)} "
                f"out={_format_tokens(output_tokens)} "
                f"cache={_format_tokens(cache_tokens)} "
                f"cost={_format_cost(cost)}"
            )
            table.add_row(
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                Text(f"  {model_name}: {detail}", style="dim"),
            )

        # Tool action sub-rows
        tool_actions = record.get("tool_actions", [])
        for action in tool_actions:
            tool_name = action.get("tool", "unknown")
            accepted = action.get("accepted", 0)
            rejected = action.get("rejected", 0)
            detail = f"accepted={accepted} rejected={rejected}"
            table.add_row(
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                Text(f"  {tool_name}: {detail}", style="dim"),
            )

    console = Console(stderr=True, force_terminal=True)
    console.print(table)


def _usage_impl(
    *,
    tokens: tuple[str, ...],
    since: str,
    limit: int,
    output_json: bool,
) -> None:
    """Implementation of usage command logic.

    Args:
        tokens: API tokens from CLI option.
        since: Start date in YYYY-MM-DD format.
        limit: Max results per page.
        output_json: Whether to output raw JSON.
    """
    resolved_tokens = resolve_tokens(tokens=tokens)

    all_records: list[dict[str, Any]] = []

    for token in resolved_tokens:
        client = AnthropicAdminClient(token=token)
        try:
            records = client.get_claude_code_usage(
                starting_at=since,
                limit=limit,
            )
            all_records.extend(records)
        except AnthropicAdminError as e:
            click.echo(f"Error fetching usage data: {e}", err=True)
            raise SystemExit(1) from None

    if output_json:
        click.echo(json.dumps(all_records, indent=2))
        return

    _render_table(all_records)


@click.command("usage")
@click.option(
    "--token",
    "tokens",
    multiple=True,
    help="Anthropic Admin API key (repeatable for multi-account).",
)
@click.option(
    "--since",
    required=True,
    help="Start date in YYYY-MM-DD format.",
)
@click.option(
    "--limit",
    default=1000,
    type=int,
    help="Maximum results per API page (max 1000).",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output raw JSON response.",
)
def usage_command(
    tokens: tuple[str, ...],
    since: str,
    limit: int,
    output_json: bool,
) -> None:
    """Show Claude Code usage analytics from Anthropic Admin API.

    Displays per-user daily usage data including sessions, lines of code,
    commits, PRs, model token usage, and tool actions.

    Max subscription users are highlighted.
    """
    _usage_impl(
        tokens=tokens,
        since=since,
        limit=limit,
        output_json=output_json,
    )
