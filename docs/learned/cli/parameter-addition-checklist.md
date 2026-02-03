---
title: Parameter Addition Checklist
read_when:
  - adding a parameter to a multi-layer command
  - working with skills that call erk exec scripts
  - debugging parameter not found errors
tripwires:
  - action: "adding a parameter to erk exec without updating calling command"
    warning: "3-layer parameter threading required. Update skill argument-hint, command invocations, AND exec script. See parameter-addition-checklist.md for complete steps."
---

# Parameter Addition Checklist

When adding a parameter to a multi-layer command (skill → command → exec script), follow this 5-step checklist to ensure the parameter is threaded through all layers correctly.

## Checklist

### ✓ Step 1: Update argument-hint in Skill Frontmatter

**File**: `.claude/skills/{skill-name}/SKILL.md`

**Action**: Add parameter documentation to `argument-hint` field

**Example**:

```yaml
---
argument-hint: |
  Optional: --pr <number> to target a specific PR instead of current branch
  Optional: --my-new-param <value> to control behavior
---
```

**Why**: Tells Claude Code what parameters are available for this skill.

### ✓ Step 2: Document in Arguments Section (if exists)

**File**: `.claude/skills/{skill-name}/SKILL.md` or `.claude/commands/{command-name}.md`

**Action**: If the command has an "Arguments" section in the body, add parameter documentation there

**Example**:

```markdown
## Arguments

- `--pr <number>`: Target specific PR (optional, defaults to current branch)
- `--my-new-param <value>`: Controls XYZ behavior (optional)
```

**Why**: Provides detailed parameter documentation for users reading the skill/command.

### ✓ Step 3: Update erk exec Invocations in Command

**File**: `.claude/skills/{skill-name}/SKILL.md` or `.claude/commands/{command-name}.md`

**Action**: Find all `erk exec` calls and add parameter threading

**Pattern**: Check `$ARGUMENTS` and conditionally pass parameter

**Example**:

````markdown
**Fetch review comments:**

```bash
# If --pr specified in $ARGUMENTS, pass it through
if [[ "$ARGUMENTS" == *"--pr"* ]]; then
  erk exec get-pr-review-comments --pr <number>
else
  erk exec get-pr-review-comments
fi
```
````

**Alternative** (simpler, if parameter is always optional):

```bash
# Pass parameter if present, ignored by exec script if not provided
erk exec get-pr-review-comments [--pr <number>]
```

**Why**: Threads the parameter from user input (`$ARGUMENTS`) to the exec script.

### ✓ Step 4: Add Click Option to Exec Script

**File**: `src/erk/cli/commands/exec/scripts/{script_name}.py`

**Action**: Add `@click.option` decorator

**Example**:

```python
@click.command()
@click.option("--pr", type=int, required=False, help="PR number (default: current branch)")
@click.option("--my-new-param", type=str, required=False, help="Controls XYZ behavior")
def my_script(pr: int | None, my_new_param: str | None) -> None:
    """Script description."""
    # Use parameters in implementation
    if pr:
        # Target specific PR
        ...
    if my_new_param:
        # Apply custom behavior
        ...
```

**Why**: Makes the exec script accept the parameter.

**Important**: Use identical parameter names across all layers (e.g., `--pr` everywhere, not `--pr-number` in one place and `--pr` in another).

### ✓ Step 5: Verify All Invocations

**Action**: Search for all places that invoke this command/script and verify parameter threading

**Commands**:

```bash
# Find skill invocations
grep -r "Skill.*{skill-name}" .claude/

# Find command invocations
grep -r "/{command-name}" .claude/

# Find exec script invocations
grep -r "erk exec {script-name}" .claude/
grep -r "erk exec {script-name}" src/
```

**Verification**: For each invocation, check if it should thread the new parameter. Update if needed.

**Why**: Prevents parameter from being silently dropped in some call paths.

## Example: Adding --pr to pr-feedback-classifier

This is the canonical reference implementation from PR #6634.

### Step 1: Updated argument-hint

```yaml
---
argument-hint: |
  Optional: --pr <number> to target a specific PR instead of current branch
  Optional: --include-resolved to show resolved comments
---
```

### Step 2: Documented in Arguments section

```markdown
## Arguments

- `--pr <number>`: Target a specific PR by number (optional, defaults to current branch)
- `--include-resolved`: Include resolved review comments in output (optional)
```

### Step 3: Updated exec invocations

```bash
# Get PR info
if [[ "$ARGUMENTS" == *"--pr"* ]]; then
  gh pr view <number> --json number,title,url
else
  gh pr view --json number,title,url
fi

# Fetch comments
erk exec get-pr-review-comments [--pr <number>] [--include-resolved]
erk exec get-pr-discussion-comments [--pr <number>]
```

### Step 4: Added Click options

```python
# get_pr_review_comments.py
@click.option("--pr", type=int, required=False, help="PR number (default: current branch)")
def get_pr_review_comments(pr: int | None, include_resolved: bool) -> None:
    ...

# get_pr_discussion_comments.py
@click.option("--pr", type=int, required=False, help="PR number (default: current branch)")
def get_pr_discussion_comments(pr: int | None) -> None:
    ...
```

### Step 5: Verified invocations

Searched for all invocations of `get-pr-review-comments` and `get-pr-discussion-comments` to ensure `--pr` threading was complete.

## Common Mistakes

### Mistake 1: Forgetting Step 5 (verification)

**Symptom**: Parameter works in one code path but not another.

**Fix**: Search for all invocations and update each one.

### Mistake 2: Inconsistent parameter names

**Symptom**: `Error: No such option: --pr-number` when script expects `--pr`.

**Fix**: Use identical names in argument-hint, command invocations, and Click options.

### Mistake 3: Not documenting in argument-hint

**Symptom**: Users don't know the parameter exists.

**Fix**: Always update argument-hint frontmatter.

### Mistake 4: Forgetting Click option

**Symptom**: `Error: No such option: --my-param` when running exec script.

**Fix**: Add `@click.option` to exec script.

## Related Documentation

- [parameter-threading-pattern.md](../architecture/parameter-threading-pattern.md) - Detailed threading pattern explanation
- `.claude/skills/pr-feedback-classifier/SKILL.md` - Reference implementation
- [cli-development.md](cli-development.md) - CLI command structure
