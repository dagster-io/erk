---
title: Parameter Threading Pattern
read_when:
  - adding parameters to multi-layer commands (skill → command → exec)
  - working with slash commands that call erk exec
  - understanding parameter flow through command layers
tripwires:
  - action: "adding a parameter to an erk exec script without updating the calling slash command"
    warning: "3-layer parameter threading: When adding a parameter, update all three layers: skill SKILL.md argument-hint, slash command .md, and erk exec script. Verify all invocations thread the parameter through."
---

# Parameter Threading Pattern

Many erk commands have a 3-layer architecture where parameters must be threaded through multiple invocation layers:

1. **Skill layer** (`.claude/skills/*/SKILL.md`) - Defines available parameters in frontmatter
2. **Command layer** (`.claude/commands/*.md`) - Calls erk exec scripts with parameters
3. **Exec script layer** (`src/erk/cli/commands/exec/scripts/*.py`) - Implements the logic

When adding a parameter, all three layers must be updated consistently.

## Canonical Example: `--pr <number>`

The `--pr` parameter in pr-feedback-classifier demonstrates the pattern perfectly.

### Layer 1: Skill (argument-hint)

**File**: `.claude/skills/pr-feedback-classifier/SKILL.md:7-10`

```yaml
---
argument-hint: |
  Optional: --pr <number> to target a specific PR instead of current branch
  Optional: --include-resolved to show resolved comments
---
```

**Purpose**: Tells Claude Code what parameters are available for this skill.

### Layer 2: Command (exec invocations)

**File**: `.claude/skills/pr-feedback-classifier/SKILL.md:26-49`

````markdown
1. **Get current branch and PR info:**
   - **If `--pr <number>` specified in `$ARGUMENTS`**:
     ```bash
     gh pr view <number> --json number,title,url -q '{number: .number, title: .title, url: .url}'
     ```

2. **Fetch all comments:**

   ```bash
   # If --include-resolved in $ARGUMENTS:
   erk exec get-pr-review-comments [--pr <number>] --include-resolved
   # Otherwise:
   erk exec get-pr-review-comments [--pr <number>]

   erk exec get-pr-discussion-comments [--pr <number>]
   ```
````

Note: Pass `--pr <number>` to both exec commands when specified in `$ARGUMENTS`.

````

**Purpose**: Threads `--pr` from `$ARGUMENTS` (where user provides it) to `erk exec` scripts.

**Key pattern**: Conditional invocation based on whether parameter was provided:
- Check `$ARGUMENTS` for the parameter
- Pass it to exec scripts when present
- Document that it must be threaded through

### Layer 3: Exec Scripts (Click parameters)

**Files**:
- `src/erk/cli/commands/exec/scripts/get_pr_review_comments.py`
- `src/erk/cli/commands/exec/scripts/get_pr_discussion_comments.py`

```python
@click.command()
@click.option("--pr", type=int, required=False, help="PR number (default: current branch)")
@click.option("--include-resolved", is_flag=True, help="Include resolved comments")
def get_pr_review_comments(pr: int | None, include_resolved: bool) -> None:
    """Fetch review comments from a PR."""
    # Implementation uses pr parameter
    ...
````

**Purpose**: Actual implementation that accepts and uses the parameter.

## 5-Step Verification Checklist

When adding a new parameter to a multi-layer command:

### Step 1: Update argument-hint

Add parameter to skill frontmatter's `argument-hint` field:

```yaml
---
argument-hint: |
  Optional: --my-param <value> to control behavior
---
```

### Step 2: Update Arguments Section

If the skill has an "Arguments" section in the body, document the parameter there:

```markdown
## Arguments

- `--my-param <value>`: Controls XYZ behavior (optional)
```

### Step 3: Update Command Invocations

Find all `erk exec` calls in the command and add the parameter:

```bash
# Before
erk exec my-script

# After
erk exec my-script [--my-param <value>]
```

Add conditional logic if needed:

````markdown
- **If `--my-param <value>` specified in `$ARGUMENTS`**:
  ```bash
  erk exec my-script --my-param <value>
  ```
````

- **Otherwise**:
  ```bash
  erk exec my-script
  ```

````

### Step 4: Update Exec Script

Add Click option to the script:

```python
@click.command()
@click.option("--my-param", type=str, required=False, help="Controls XYZ")
def my_script(my_param: str | None) -> None:
    """Script description."""
    ...
````

### Step 5: Verify All Invocations

Search for all places that call this command/script:

```bash
# Find all invocations of the skill
grep -r "Skill.*my-skill" .claude/

# Find all invocations of the exec script
grep -r "erk exec my-script" .claude/
grep -r "erk exec my-script" src/
```

Verify each invocation threads the parameter if needed.

## Common Mistakes

### Mistake 1: Updating skill but not exec script

**Symptom**: Command invocations pass `--my-param` but exec script doesn't accept it.

**Error**: `Error: No such option: --my-param`

**Fix**: Add Click option to exec script.

### Mistake 2: Updating exec script but not skill invocations

**Symptom**: Exec script accepts parameter but skill never passes it.

**Result**: Parameter is available but never used, silently ignored.

**Fix**: Update command invocations to thread the parameter through.

### Mistake 3: Forgetting to document in argument-hint

**Symptom**: Parameter works but users don't know it exists.

**Result**: Users don't discover the feature.

**Fix**: Add to `argument-hint` frontmatter.

### Mistake 4: Inconsistent parameter names

**Symptom**: Skill uses `--pr-number`, exec script uses `--pr`.

**Error**: Parameter not recognized.

**Fix**: Use identical parameter names across all layers.

## When Parameter Threading Applies

**Use parameter threading when**:

- Slash command calls `erk exec` scripts
- Skill invokes commands with user-provided arguments
- Parameter needs to flow from user input to implementation

**Don't use parameter threading when**:

- Parameter is internal to a single script
- Command doesn't have multiple layers
- Direct Python function calls (use function parameters instead)

## Historical Example: PR #6634

PR #6634 added `--pr <number>` to pr-feedback-classifier, demonstrating this pattern:

1. **Updated argument-hint** to document the new parameter
2. **Updated skill body** to show conditional invocation based on `--pr` presence
3. **Updated two exec scripts** (`get-pr-review-comments`, `get-pr-discussion-comments`) to accept `--pr`
4. **Verified invocations** across all calling commands

The PR serves as a canonical reference for implementing parameter threading.

## Related Documentation

- `.claude/skills/pr-feedback-classifier/SKILL.md` - Canonical example
- [cli-development.md](../cli/cli-development.md) - CLI command structure
- [parameter-addition-checklist.md](../cli/parameter-addition-checklist.md) - Detailed checklist
