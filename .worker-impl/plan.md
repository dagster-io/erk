# Documentation Plan: erk learn Command Implementation Learnings

## Raw Materials

Gist with preprocessed session XMLs: https://gist.github.com/schrockn/cc7f0c22322ecc84747b014b8401734d

## Context Gathered

### Key Files Discovered

- `packages/erk-shared/src/erk_shared/sessions/discovery.py` - Session discovery logic with `SessionsForPlan` dataclass, `find_sessions_for_plan()`, `get_readable_sessions()`, and `find_local_sessions_for_project()` functions
- `packages/erk-shared/src/erk_shared/learn/impl_events.py` - Extracts session IDs from GitHub issue comments (`extract_implementation_sessions`, `extract_learn_sessions`)
- `packages/erk-shared/src/erk_shared/learn/tracking.py` - Records learn invocations on plan issues
- `src/erk/cli/commands/learn/learn_cmd.py` - CLI command with optional issue argument and branch inference
- `packages/erk-shared/src/erk_shared/naming.py` - Contains `extract_leading_issue_number()` for branch name parsing

### Patterns Found

1. **Dual-source discovery pattern**: Check authoritative source (GitHub issue metadata) first, then fallback to local filesystem scan. Used for session discovery.

2. **Parameter threading pattern**: When adding a parameter to a widely-used function, you must update: the function signature, all callers, all test files that call it.

3. **Optional CLI argument with inference**: Make argument `required=False`, then infer from context (branch name, .impl/ folder, etc.)

### Existing Documentation Checked

- `docs/learned/architecture/metadata-blocks.md` - Already documents metadata block system (created during this implementation)
- `docs/learned/cli/` - Has CLI patterns but not optional argument inference
- `docs/learned/architecture/` - Has gateway patterns but not session discovery

## Documentation Items

### Item 1: Session Discovery Architecture

**Location:** `docs/learned/architecture/session-discovery.md`
**Action:** Create

**Draft Content:**

````markdown
---
title: Session Discovery Architecture
read_when:
  - "finding Claude Code sessions for a plan"
  - "implementing session lookup from GitHub issues"
  - "understanding dual-source discovery patterns"
---

# Session Discovery Architecture

Erk discovers Claude Code sessions associated with plans through a dual-source approach.

## Core Data Structure

```python
@dataclass(frozen=True)
class SessionsForPlan:
    planning_session_id: str | None  # From created_from_session in plan-header
    implementation_session_ids: list[str]  # From impl-started/ended comments
    learn_session_ids: list[str]  # From learn-invoked comments
```
````

## Discovery Sources

### Primary: GitHub Issue Metadata

Sessions are tracked in the plan issue:

- `created_from_session` field in plan-header → planning session
- `last_local_impl_session` field in plan-header → most recent impl
- `impl-started`/`impl-ended` comments → all implementation sessions
- `learn-invoked` comments → previous learn sessions

### Fallback: Local Filesystem

When GitHub has no tracked sessions (older issues), scan ~/.claude/projects/ for sessions where gitBranch matches P{issue}-\*.

## Key Functions

- `find_sessions_for_plan()` - Extracts sessions from GitHub issue
- `get_readable_sessions()` - Filters to sessions that exist on disk
- `find_local_sessions_for_project()` - Scans local sessions by branch pattern

````

---

### Item 2: CLI Optional Arguments with Inference

**Location:** `docs/learned/cli/optional-arguments.md`
**Action:** Create

**Draft Content:**

```markdown
---
title: CLI Optional Arguments with Inference
read_when:
  - "making a CLI argument optional"
  - "inferring CLI arguments from context"
  - "branch-based argument defaults"
---

# CLI Optional Arguments with Inference

Pattern for making CLI arguments optional by inferring them from context.

## Pattern

```python
@click.command("mycommand")
@click.argument("issue", type=str, required=False)
@click.pass_obj
def mycommand(ctx: ErkContext, issue: str | None) -> None:
    # Priority 1: Explicit argument
    if issue is not None:
        issue_number = _extract_issue_number(issue)
    else:
        # Priority 2: Infer from branch name (P123-...)
        branch = ctx.git.get_current_branch(ctx.cwd)
        issue_number = extract_leading_issue_number(branch)

        if issue_number is None:
            # Priority 3: Check .impl/issue.json
            impl_issue = ctx.cwd / ".impl" / "issue.json"
            if impl_issue.exists():
                data = json.loads(impl_issue.read_text())
                issue_number = data.get("issue_number")
````

## Inference Sources (Priority Order)

1. Explicit CLI argument
2. Branch name pattern (P{number}-...)
3. .impl/issue.json file
4. Error with helpful message

## Helper Function

Use `extract_leading_issue_number()` from `erk_shared.naming`:

```python
from erk_shared.naming import extract_leading_issue_number

branch = "P4655-erk-learn-command-01-11-0748"
issue_num = extract_leading_issue_number(branch)  # Returns 4655
```

````

---

### Item 3: Parameter Threading Pattern

**Location:** `docs/learned/architecture/parameter-threading.md`
**Action:** Create

**Draft Content:**

```markdown
---
title: Parameter Threading Pattern
read_when:
  - "adding a parameter to a function used in many places"
  - "threading a new field through multiple layers"
  - "updating function signatures across codebase"
---

# Parameter Threading Pattern

When adding a new parameter to a function that's called from multiple places, you must systematically update all callers.

## Example: Adding created_from_session to Plan Issues

The `created_from_session` parameter was added to track which session created a plan. This required updates across 5+ files.

### Update Order

1. **Core function** - Add parameter to the function being changed
2. **Intermediate functions** - Add parameter to any wrappers
3. **Callers** - Update all places that call the function
4. **Tests** - Update all test files that call the function

### Finding All Callers

```bash
# Find function definition
rg "def create_plan_issue"

# Find all calls
rg "create_plan_issue\(" --type py
````

### Common Mistake

Forgetting to update test files. Tests that call the modified function will fail with unexpected keyword argument errors.

### Checklist

- [ ] Update function signature with new parameter
- [ ] Update docstring
- [ ] Update all direct callers
- [ ] Update all wrapper functions
- [ ] Update all test files
- [ ] Run full test suite to catch any missed callers

```

```
