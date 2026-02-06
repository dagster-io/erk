---
title: Parameter Threading Pattern
read_when:
  - adding parameters to multi-layer commands (skill → command → exec)
  - working with slash commands that call erk exec
  - understanding parameter flow through command layers
tripwires:
  - action: "adding a parameter to an erk exec script without updating the calling slash command"
    warning: "3-layer parameter threading: When adding a parameter, update all three layers: skill SKILL.md argument-hint, slash command .md, and erk exec script. Verify all invocations thread the parameter through."
last_audited: "2026-02-05"
audit_result: edited
---

# Parameter Threading Pattern

Many erk commands have a 3-layer architecture where parameters must be threaded through multiple invocation layers:

1. **Skill layer** (`.claude/skills/*/SKILL.md`) - Defines available parameters in `argument-hint` frontmatter
2. **Command layer** (`.claude/commands/*.md`) - Calls erk exec scripts with parameters
3. **Exec script layer** (`src/erk/cli/commands/exec/scripts/*.py`) - Implements the logic with Click options

When adding a parameter, all three layers must be updated consistently.

## Canonical Example: `--pr <number>`

The `--pr` parameter in pr-feedback-classifier demonstrates the pattern. See `.claude/skills/pr-feedback-classifier/SKILL.md` for the complete example showing all three layers.

**Layer 1 (argument-hint)**: A single-line string in SKILL.md frontmatter:

```yaml
argument-hint: "[--pr <number>] [--include-resolved]"
```

**Layer 2 (command body)**: The skill body conditionally threads `--pr` from `$ARGUMENTS` to `erk exec` invocations.

**Layer 3 (exec script)**: Click options on the Python command accept and use the parameter via `@click.pass_context` with `@click.option("--pr", type=int, default=None)`.

## Verification Checklist

For the step-by-step checklist when adding parameters, see [parameter-addition-checklist.md](../cli/parameter-addition-checklist.md).

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

## Related Documentation

- `.claude/skills/pr-feedback-classifier/SKILL.md` - Canonical example
- [parameter-addition-checklist.md](../cli/parameter-addition-checklist.md) - Detailed step-by-step checklist
