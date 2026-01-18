---
title: CLI Command Patterns
read_when:
  - "implementing CLI commands that accept GitHub identifiers"
  - "setting up implementation artifacts from commands"
  - "handling mutual exclusivity in CLI options"
---

# CLI Command Patterns in Erk

## Issue-to-Object Pattern

When CLI commands need to accept GitHub issue identifiers, follow the **Issue-to-Object** pattern.

### 1. Accept Multiple Input Formats

Use `parse_issue_identifier()` to normalize issue references:

```python
from erk.cli.github_parsing import parse_issue_identifier

@click.option("--for-plan", type=str, default=None)
def command(for_plan: str | None):
    if for_plan is not None:
        issue_number = parse_issue_identifier(for_plan)  # Handles all formats
```

This accepts:

- Plain numbers: `5037`
- P-prefixed: `P5037`
- Full URLs: `https://github.com/dagster-io/erk/issues/5037`

### 2. Fetch from Store and Validate

Fetch objects from the appropriate store and validate required properties:

```python
try:
    plan = ctx.plan_store.get_plan(repo.root, str(issue_number))
except RuntimeError as e:
    raise click.ClickException(str(e)) from e

result = prepare_plan_for_worktree(plan, ctx.time.now())
if isinstance(result, IssueValidationFailed):
    user_output(f"Error: {result.message}")
    raise SystemExit(1) from None
```

**Key:** Always validate that fetched objects have required properties (labels, content, etc.).

### 3. Handle Mutual Exclusivity

When commands accept alternative input methods, validate mutual exclusivity at the start:

```python
if for_plan is not None and branch_name is not None:
    user_output("Error: Cannot specify both BRANCH and --for-plan...")
    raise SystemExit(1) from None

if for_plan is None and branch_name is None:
    user_output("Error: Must provide BRANCH argument or --for-plan option.")
    raise SystemExit(1) from None
```

This prevents confusing error states and makes the API clear to users.

### 4. Assert Non-None After Validation

Use type assertions to help the type checker understand that values are non-None after validation:

```python
# At this point, branch_name is guaranteed to be set
# Type assertion for the type checker
assert branch_name is not None
```

This pattern is necessary because the type checker cannot understand that validation logic narrows types.

## Setting Up Implementation Artifacts

When commands create implementation environments (worktrees, `.impl/` folders), follow this pattern:

### 1. Create the Primary Artifact (Branch/Worktree)

```python
ctx.git.create_branch(repo.root, branch_name, parent_branch)
ctx.branch_manager.track_branch(repo.root, branch_name, parent_branch)
```

### 2. Allocate Resources (Slots)

```python
slot_result = allocate_slot_for_branch(
    ctx,
    repo,
    branch_name,
    force=force,
    reuse_inactive_slots=True,
    cleanup_artifacts=True,
)
```

### 3. Create Implementation Folder

```python
impl_path = create_impl_folder(
    slot_result.worktree_path,
    plan_content,
    overwrite=True,
)

save_issue_reference(
    impl_path,
    issue_number,
    issue_url,
    issue_title,
)
```

### 4. Generate Activation Script

```python
script_path = write_worktree_activate_script(
    worktree_path=slot_result.worktree_path,
    post_create_commands=None,
)

# Print for user copy-paste
user_output("\nTo activate the worktree environment:")
user_output(f"  source {script_path}")
```

**Critical:** Always print the activation script path - users need this to manually set up their environment.

## Error Handling Pattern

```python
try:
    plan = ctx.plan_store.get_plan(repo.root, str(issue_number))
except RuntimeError as e:
    raise click.ClickException(str(e)) from e
```

Use `click.ClickException` to wrap store/gateway errors so they are displayed properly to the user.

## Related Topics

- [GitHub URL Parsing Architecture](github-parsing.md) - Two-layer parsing architecture
- [Optional Arguments](../cli/optional-arguments.md) - Pattern for inferring CLI arguments
- [Branch Create --for-plan](../cli/branch-create-for-plan.md) - Command reference
