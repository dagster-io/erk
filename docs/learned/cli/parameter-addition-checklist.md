---
audit_result: edited
last_audited: '2026-02-08'
read_when:
- adding a parameter to a multi-layer command
- working with skills that call erk exec scripts
- debugging parameter not found errors
title: Parameter Addition Checklist
tripwires:
- action: adding a parameter to erk exec without updating calling command
  warning: 5-step verification required. Parameter additions must thread through skill
    argument-hint, command invocations, AND exec script. Miss any layer and you get
    silent failures or discovery problems. See parameter-addition-checklist.md.
---

# Parameter Addition Checklist

## Why This Checklist Exists

The 3-layer indirection pattern (skill → command → exec script) creates **mechanical synchronization requirements** that can't be automated. Parameters must be manually threaded through each layer, and missing any step causes one of two failure modes:

1. **Silent omission** — parameter exists but is never passed (most dangerous)
2. **Loud failure** — parameter passed but not accepted (fails fast, easier to debug)

The checklist approach catches both failure modes. Grep alone only catches loud failures.

## The 5-Step Verification Protocol

This is a **verification protocol**, not implementation guidance. For WHY parameters require threading and the failure modes that occur when you skip steps, see [Parameter Threading Pattern](../architecture/parameter-threading-pattern.md).

### Step 1: Update argument-hint in Skill Frontmatter

**Why**: Discovery layer. If not documented here, users can't find the parameter in Claude Code's UI.

<!-- Source: .claude/skills/pr-feedback-classifier/SKILL.md, argument-hint frontmatter -->

Add parameter to `argument-hint` field using format: `[--flag]` for optionals, `--flag <value>` for required values.

**Verification**: `grep -A3 "argument-hint" .claude/skills/{skill-name}/SKILL.md`

### Step 2: Document in Arguments Section (if exists)

**Why**: Human-readable explanation supplements machine-readable frontmatter.

If the skill or command has an "Arguments" section in the markdown body, document parameter behavior there (e.g., "defaults to current branch's PR").

**Skip if**: No existing Arguments section. Don't create one just for this.

### Step 3: Update erk exec Invocations in Command

**Why**: Routing layer. This is where `$ARGUMENTS` from Claude Code gets translated into actual command-line flags for the exec script.

<!-- Source: .claude/skills/pr-feedback-classifier/SKILL.md, erk exec invocation patterns -->

Find all `erk exec {script-name}` calls in the command/skill body. Add parameter threading logic:

```bash
# Example: conditional flag threading
# If --my-flag in $ARGUMENTS:
erk exec my-script [--pr <number>] --my-flag
# Otherwise:
erk exec my-script [--pr <number>]
```

**Verification**: `grep "erk exec {script-name}" .claude/skills/{skill-name}/SKILL.md`

**Common mistake**: Updating the skill but forgetting to pass the parameter in the actual `erk exec` invocation. This causes silent omission — the exec script never receives the parameter but doesn't error either.

### Step 4: Add Click Option to Exec Script

**Why**: Implementation layer. The Python function must accept the parameter.

<!-- Source: src/erk/cli/commands/exec/scripts/get_pr_review_comments.py, @click.option decorators -->
<!-- Source: src/erk/cli/commands/exec/scripts/get_pr_discussion_comments.py, @click.option decorators -->

See Click option patterns in `get_pr_review_comments.py` and `get_pr_discussion_comments.py`.

**Naming constraint**: Use **identical parameter names** across all layers. `--pr` in argument-hint = `--pr` in bash command = `--pr` in Click option. Mismatches cause loud failures.

**Verification**: Check `@click.option` decorators near the function definition.

### Step 5: Verify All Invocation Sites

**Why**: Secondary invocation sites (other commands that call the same exec script) must also thread the new parameter.

Grep across **both** `.claude/` and `src/` to find all invocations:

```bash
grep -r "erk exec {script-name}" .claude/
grep -r "erk exec {script-name}" src/
```

For each match, verify the new parameter is threaded through (or intentionally omitted if that invocation doesn't need it).

**This step catches silent omissions**. If you skip this, the primary command works but secondary code paths fail silently.

## Canonical Reference Implementation

<!-- Source: .claude/skills/pr-feedback-classifier/SKILL.md, full skill implementation -->
<!-- Source: src/erk/cli/commands/exec/scripts/get_pr_review_comments.py, complete parameter threading -->
<!-- Source: src/erk/cli/commands/exec/scripts/get_pr_discussion_comments.py, parallel implementation -->

The `--pr` parameter in `pr-feedback-classifier` skill (PR #6634) demonstrates correct threading:

1. **argument-hint**: `[--pr <number>]` documents optional parameter
2. **Skill body**: "Arguments" section explains default behavior
3. **erk exec calls**: Both `get-pr-review-comments` and `get-pr-discussion-comments` thread `[--pr <number>]`
4. **Click options**: Both scripts accept `@click.option("--pr", type=int, default=None, ...)`
5. **Verification**: No other invocation sites exist (grep confirms)

See the three source files for complete implementation patterns.

## Common Mistakes and Their Symptoms

| Mistake                          | Symptom                                                         | Detection Method                       |
| -------------------------------- | --------------------------------------------------------------- | -------------------------------------- |
| Skip Step 5 (verification)       | Parameter works in primary path but not secondary invocations   | Grep all invocation sites              |
| Inconsistent names across layers | `Error: No such option: --pr-number` when script expects `--pr` | Check all layers use identical names   |
| Skip Step 1 (argument-hint)      | Users can't discover feature in Claude Code UI                  | Check frontmatter documents parameter  |
| Skip Step 3 (command threading)  | Exec script never receives parameter (silent default behavior)  | Grep command for `erk exec` invocation |
| Skip Step 4 (Click option)       | `Error: No such option: --my-param`                             | Fails fast, obvious to fix             |

**Silent omission vs loud failure**: Steps 3-4 omissions create different failure modes. Missing Click option (Step 4) fails loudly. Missing command threading (Step 3) fails silently — the worst kind.

## When This Checklist Applies

**Use when**:

- Adding parameter to command that uses skill → command → exec pattern
- Parameter must be user-accessible through Claude Code UI
- Working with multi-layer indirection (not direct Python calls)

**Don't use when**:

- Parameter is internal to single Python function (use function parameters directly)
- Direct Python imports with function calls (no subprocess boundary)
- Single-layer commands without exec scripts

For single-layer commands, just add the Click option. This checklist is specifically for the 3-layer pattern.

## Related Documentation

- [Parameter Threading Pattern](../architecture/parameter-threading-pattern.md) — WHY threading is required, failure mode analysis, decision framework
- `.claude/skills/pr-feedback-classifier/SKILL.md` — Canonical reference showing all 5 steps implemented correctly
- `src/erk/cli/commands/exec/scripts/get_pr_review_comments.py` — Click option implementation patterns
- `src/erk/cli/commands/exec/scripts/get_pr_discussion_comments.py` — Parallel implementation demonstrating consistency
