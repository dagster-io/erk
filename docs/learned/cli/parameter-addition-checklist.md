---
title: Parameter Addition Checklist
read_when:
  - adding a parameter to a multi-layer command
  - working with skills that call erk exec scripts
  - debugging parameter not found errors
tripwires:
  - action: "adding a parameter to erk exec without updating calling command"
    warning: "3-layer parameter threading required. Update skill argument-hint, command invocations, AND exec script. See parameter-addition-checklist.md for complete steps."
last_audited: "2026-02-05"
audit_result: edited
---

# Parameter Addition Checklist

When adding a parameter to a multi-layer command (skill → command → exec script), follow this 5-step checklist to ensure the parameter is threaded through all layers correctly.

## Checklist

### Step 1: Update argument-hint in Skill Frontmatter

**File**: `.claude/skills/{skill-name}/SKILL.md`

Add parameter documentation to `argument-hint` field. This tells Claude Code what parameters are available.

See `.claude/skills/pr-feedback-classifier/SKILL.md` for the canonical reference format.

### Step 2: Document in Arguments Section (if exists)

**File**: `.claude/skills/{skill-name}/SKILL.md` or `.claude/commands/{command-name}.md`

If the command has an "Arguments" section in the body, add parameter documentation there too.

### Step 3: Update erk exec Invocations in Command

**File**: `.claude/skills/{skill-name}/SKILL.md` or `.claude/commands/{command-name}.md`

Find all `erk exec` calls and add parameter threading. Check `$ARGUMENTS` and conditionally pass the parameter through.

### Step 4: Add Click Option to Exec Script

**File**: `src/erk/cli/commands/exec/scripts/{script_name}.py`

Add `@click.option` decorator. Use identical parameter names across all layers (e.g., `--pr` everywhere, not `--pr-number` in one place and `--pr` in another).

### Step 5: Verify All Invocations

Search for all places that invoke this command/script and verify parameter threading:

```bash
grep -r "erk exec {script-name}" .claude/
grep -r "erk exec {script-name}" src/
```

## Canonical Example

The `--pr` parameter in `pr-feedback-classifier` (PR #6634) threads through all 5 layers:

1. **Skill**: `.claude/skills/pr-feedback-classifier/SKILL.md` — `argument-hint` field
2. **Exec scripts**: `src/erk/cli/commands/exec/scripts/get_pr_review_comments.py` and `get_pr_discussion_comments.py` — `@click.option("--pr", ...)`

## Common Mistakes

| Mistake                          | Symptom                                                         | Fix                                                               |
| -------------------------------- | --------------------------------------------------------------- | ----------------------------------------------------------------- |
| Forgetting Step 5 (verification) | Parameter works in one code path but not another                | Search for all invocations and update each one                    |
| Inconsistent parameter names     | `Error: No such option: --pr-number` when script expects `--pr` | Use identical names in argument-hint, commands, and Click options |
| Not documenting in argument-hint | Users don't know the parameter exists                           | Always update argument-hint frontmatter                           |
| Forgetting Click option          | `Error: No such option: --my-param`                             | Add `@click.option` to exec script                                |

## Related Documentation

- [Parameter Threading Pattern](../architecture/parameter-threading-pattern.md) — Detailed threading pattern explanation
- `.claude/skills/pr-feedback-classifier/SKILL.md` — Reference implementation
