---
title: Parameter Threading Pattern
read_when:
  - adding parameters to multi-layer commands (skill → command → exec)
  - working with slash commands that call erk exec
  - debugging "No such option" errors in commands
tripwires:
  - action: "adding a parameter to an erk exec script without updating the calling slash command"
    warning: "3-layer parameter threading: When adding a parameter, update all three layers: skill SKILL.md argument-hint, slash command .md, and erk exec script. Verify all invocations thread the parameter through."
last_audited: "2026-02-08"
audit_result: clean
---

# Parameter Threading Pattern

## Why This Pattern Exists

Many erk commands follow a 3-layer indirection:

1. **Skill layer** (`.claude/skills/*/SKILL.md`) — defines user-facing parameters in frontmatter
2. **Command layer** (`.claude/commands/*.md`) — calls erk exec with parameters from `$ARGUMENTS`
3. **Exec script layer** (`src/erk/cli/commands/exec/scripts/*.py`) — Click options implement the logic

This separation enables Claude Code's skill system (layer 1-2) to invoke Python implementations (layer 3) while maintaining clear boundaries between AI prompt engineering and executable code.

**The cost**: Parameters must be explicitly threaded through all three layers. There's no automatic binding. If you add `--pr` to the exec script but forget to pass it in the command, the parameter exists but is never used.

## The Three-Layer Contract

<!-- Source: .claude/skills/pr-feedback-classifier/SKILL.md, argument-hint frontmatter -->
<!-- Source: src/erk/cli/commands/exec/scripts/get_pr_review_comments.py, Click options -->
<!-- Source: src/erk/cli/commands/exec/scripts/get_pr_discussion_comments.py, Click options -->

See `pr-feedback-classifier` skill for the canonical reference implementation.

### Layer 1: Skill Frontmatter (Discovery)

The `argument-hint` field in `SKILL.md` frontmatter documents available parameters:

```yaml
argument-hint: "[--pr <number>] [--include-resolved]"
```

**Purpose**: Tells Claude Code what parameters exist. This appears in command palette and skill documentation. Users discover features here.

**Format**: Square brackets = optional, angle brackets = value required.

### Layer 2: Command Invocations (Routing)

Command bodies conditionally extract parameters from `$ARGUMENTS` and pass them to `erk exec`:

```bash
# If --include-resolved in $ARGUMENTS:
erk exec get-pr-review-comments [--pr <number>] --include-resolved
# Otherwise:
erk exec get-pr-review-comments [--pr <number>]
```

**Purpose**: Routes user-provided arguments from the Claude Code skill system to the Python implementation. This is where the binding happens — or fails to happen if you forget.

### Layer 3: Exec Script Click Options (Implementation)

Python scripts accept parameters via Click decorators:

```python
@click.option("--pr", type=int, default=None, help="PR number (defaults to current branch's PR)")
@click.option("--include-resolved", is_flag=True, help="Include resolved threads")
```

**Purpose**: Actual implementation that uses the parameter values.

## Common Failure Modes

### Silent Omission: Updating Exec Without Updating Command

**Symptom**: Parameter exists in Click options but is never passed by the command.

**Result**: No error — the parameter silently defaults to `None` or `False`. Feature works locally when testing the exec script directly, but fails when invoked through the skill.

**Why this is insidious**: Tests pass, manual invocation works, but users can't access the feature through the intended interface.

**Example**: Adding `--pr` to `get_pr_review_comments.py` but not updating `.claude/skills/pr-feedback-classifier/SKILL.md` to pass it through. Users invoke `/pr-feedback-classifier --pr 123` but the script never receives the `--pr` argument.

### Loud Failure: Updating Command Without Updating Exec

**Symptom**: Command passes `--my-param` but exec script doesn't accept it.

**Error**: `Error: No such option: --my-param`

**Why this happens**: The command layer blindly passes through what it receives from `$ARGUMENTS`. If the exec script doesn't accept the parameter, Click rejects it.

**Fix is obvious**: Add the Click option. This failure mode is preferable to silent omission because it fails fast.

### Documentation Skew: Forgetting argument-hint

**Symptom**: Parameter works end-to-end but isn't documented in skill frontmatter.

**Result**: Users don't discover the feature. It exists but is invisible in command palette and skill documentation.

**Why this matters**: `argument-hint` is the user-facing API contract. If it's not there, the feature doesn't exist from the user's perspective.

### Name Mismatch: Inconsistent Parameter Names Across Layers

**Symptom**: Skill documents `--pr-number`, command passes `--pr-num`, exec script expects `--pr`.

**Error**: Parameter not recognized at some layer.

**Fix**: Use identical names everywhere. The parameter name is part of the contract.

## Decision Framework: When to Use Parameter Threading

**Use when**:

- Slash command invokes `erk exec` scripts
- Skill needs to accept user-provided arguments
- Parameter must flow from Claude Code UI → bash command → Python implementation

**Don't use when**:

- Parameter is internal to a single Python function (use function parameters)
- Direct Python imports (use function calls, not subprocess)
- Command doesn't have multiple layers (just use Click options directly)

## Verification Strategy

The checklist approach (see `docs/learned/cli/parameter-addition-checklist.md`) is essential because grep alone misses silent omissions. You must verify:

1. **Frontmatter documents it**: `grep -A5 "argument-hint" .claude/skills/{skill-name}/SKILL.md`
2. **Command invocations thread it**: `grep "erk exec {script-name}" .claude/` and verify each invocation
3. **Exec script accepts it**: Check Click options in `src/erk/cli/commands/exec/scripts/{script-name}.py`
4. **All invocation sites updated**: `grep -r "erk exec {script-name}"` across both `.claude/` and `src/`

Step 4 is where most failures occur. A grep finds the exec script and the primary command, but misses secondary invocation sites.

## Related Documentation

- [Parameter Addition Checklist](../cli/parameter-addition-checklist.md) — Step-by-step verification procedure
- `.claude/skills/pr-feedback-classifier/SKILL.md` — Canonical reference implementation with `--pr` and `--include-resolved`
- `src/erk/cli/commands/exec/scripts/get_pr_review_comments.py` — Click option implementation
- `src/erk/cli/commands/exec/scripts/get_pr_discussion_comments.py` — Parallel implementation showing pattern consistency
