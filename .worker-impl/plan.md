# Plan: `erk plan list` Command

## Summary

Create a streamlined `erk plan list` command that efficiently queries and displays plans with minimal API calls. Shows plan number, title, and state with no filtering options.

## Behavior

- **Default**: Show open plans with `erk-plan` label
- **Columns**: `plan` (number with link), `title`, `state` (open/closed with emoji)
- **No flags**: Zero options - simple, focused command
- **Efficiency**: Single GraphQL API call (skips workflow runs and PR linkages)

## Implementation Steps

### Step 1: Add `list_plans` command to `list_cmd.py`

**File**: `src/erk/cli/commands/plan/list_cmd.py`

Add a new command function after the existing `dash` command:

```python
@click.command("list")
@click.pass_obj
def list_plans(ctx: ErkContext) -> None:
    """List plans with erk-plan label.

    Shows open plans by default with plan number, title, and state.

    Examples:
        erk plan list
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # Fetch only issues - skip workflow runs and PR linkages for efficiency
    try:
        plan_data = ctx.plan_list_service.get_plan_list_data(
            repo_root=repo_root,
            labels=["erk-plan"],
            state="open",
            skip_workflow_runs=True,
            skip_pr_linkages=True,
        )
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    plans = [_issue_to_plan(issue) for issue in plan_data.issues]

    if not plans:
        user_output("No plans found.")
        return

    user_output(f"\nFound {len(plans)} plan(s):\n")

    # Simple table with 3 columns
    table = Table(show_header=True, header_style="bold")
    table.add_column("plan", style="cyan", no_wrap=True)
    table.add_column("title", no_wrap=True)
    table.add_column("state", no_wrap=True)

    for plan in plans:
        # Plan number with clickable link
        id_text = f"#{plan.plan_identifier}"
        colored_id = f"[cyan]{id_text}[/cyan]"
        issue_id = f"[link={plan.url}]{colored_id}[/link]" if plan.url else colored_id

        # Truncate title
        title = plan.title[:47] + "..." if len(plan.title) > 50 else plan.title

        # State with emoji
        state_cell = "🟢 open" if plan.state == PlanState.OPEN else "⚫ closed"

        table.add_row(issue_id, title, state_cell)

    console = Console(stderr=True, width=200, force_terminal=True)
    console.print(table)
    console.print()
```

### Step 2: Register command in plan group

**File**: `src/erk/cli/commands/plan/__init__.py`

Add import and registration:

```python
from erk.cli.commands.plan.list_cmd import list_plans

# Add to existing commands
plan_group.add_command(list_plans, name="list")
```

## Files to Modify

1. `src/erk/cli/commands/plan/list_cmd.py` - Add `list_plans` command
2. `src/erk/cli/commands/plan/__init__.py` - Register command

## Testing

Add test in `tests/commands/plan/test_list.py` following the pattern from `test_get.py`:

- Test with FakePlanStore to verify output format
- Test empty state (no plans)
- Test table output includes expected columns
