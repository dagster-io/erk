"""Generate slugs for objective node descriptions via LLM.

Takes JSON on stdin with a list of descriptions, uses NodeSlugGenerator
to produce slugs via LLM with deterministic fallback.

Usage:
    echo '{"descriptions": ["Add user model", "Wire into CLI"]}' | erk exec generate-node-slugs

Output JSON:
    {"success": true, "slugs": ["add-user-model", "wire-cli"]}

Exit Codes:
    0: Success
    1: Invalid input or generation failure
"""

import json
import sys

import click

from erk.core.node_slug_generator import NodeSlugGenerator
from erk_shared.context.helpers import require_prompt_executor


@click.command(name="generate-node-slugs")
@click.pass_context
def generate_node_slugs(ctx: click.Context) -> None:
    """Generate slugs for objective node descriptions from JSON on stdin."""
    stdin_input = sys.stdin.read()

    if not stdin_input.strip():
        click.echo(json.dumps({"success": False, "error": "No input provided on stdin"}))
        raise SystemExit(1)

    try:
        data = json.loads(stdin_input)
    except json.JSONDecodeError as e:
        click.echo(json.dumps({"success": False, "error": f"Invalid JSON: {e}"}))
        raise SystemExit(1) from None

    if not isinstance(data, dict):
        click.echo(json.dumps({"success": False, "error": "Input must be a JSON object"}))
        raise SystemExit(1)

    if "descriptions" not in data:
        click.echo(json.dumps({"success": False, "error": "Missing required field: descriptions"}))
        raise SystemExit(1)

    descriptions = data["descriptions"]
    if not isinstance(descriptions, list):
        click.echo(json.dumps({"success": False, "error": "Field 'descriptions' must be a list"}))
        raise SystemExit(1)

    for i, desc in enumerate(descriptions):
        if not isinstance(desc, str):
            click.echo(json.dumps({"success": False, "error": f"Description {i} must be a string"}))
            raise SystemExit(1)

    executor = require_prompt_executor(ctx)
    generator = NodeSlugGenerator(executor)
    result = generator.generate(descriptions)

    click.echo(json.dumps({"success": result.success, "slugs": result.slugs}))
