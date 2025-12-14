# Objective: docs-audit-fixes

## Type

completable

## Desired State

All agent documentation in `.erk/docs/` and `docs/` accurately reflects the actual codebase implementation:

1. **Class names match reality** - `ErkContext` (not `DotAgentContext`)
2. **CLI commands match reality** - `erk plan create` (not `erk create`)
3. **Config paths match reality** - `.erk/config.toml` (not `erk.toml`)
4. **Directory structures match reality** - `scripts/` (not `kit_cli_commands/`)
5. **Code patterns match recommendations** - `require_cwd(ctx)` (not `Path.cwd()`)
6. **Architectural guidance is consistent** - Protocol vs ABC per AGENTS.md

## Rationale

**Developer Onboarding**: Incorrect documentation causes new developers to write code that doesn't compile or follow wrong patterns.

**Maintainability**: Outdated class names and paths mean examples can't be copy-pasted, increasing friction.

**Consistency**: Contradictory guidance (Protocol vs ABC) causes architectural confusion and inconsistent implementations.

**Trust**: Documentation that doesn't match reality erodes confidence in all documentation.

## Examples

### Before: Outdated Context Class

```python
# From dependency-injection.md (WRONG)
from erk_kits.context import DotAgentContext

ctx = DotAgentContext.for_test(
    github_issues=fake_gh,  # Wrong field name
)
```

### After: Current Context Class

```python
# CORRECT
from erk_shared.context import ErkContext

ctx = ErkContext.for_test(
    issues=fake_gh,  # Correct field name
)
```

### Before: Wrong Directory Path

```markdown
Kit CLI commands live in:
packages/erk-kits/.../kit_cli_commands/erk/
```

### After: Correct Directory Path

```markdown
Kit CLI commands live in:
packages/erk-kits/.../scripts/erk/
```

## Scope

### In Scope

- `.erk/docs/agent/kits/` - Kit development documentation
- `.erk/docs/agent/testing/` - Testing documentation
- `.erk/docs/agent/cli/` - CLI documentation
- `.erk/docs/kits/dignified-python/` - Python style guide
- `docs/user/` - User-facing documentation

### Out of Scope

- Source code changes (docs only)
- Adding new documentation
- Restructuring documentation hierarchy
- Non-agent documentation (public-content, etc.)

## Turn Configuration

### Evaluation Prompt

Search documentation for outdated patterns:

1. `DotAgentContext` - Should be `ErkContext`
2. `erk shell-init` - Should be `erk init --shell`
3. `erk.toml` - Should be `.erk/config.toml`
4. `kit_cli_commands/` - Should be `scripts/`
5. `Path.cwd()` in examples - Should be `require_cwd(ctx)`
6. Top-level plan commands (`erk create`) - Should be `erk plan create`

Report:

- Count of each pattern found
- Files affected
- Recommended batch for next plan (group by related patterns)

### Plan Sizing

Plans should:

1. **Group related files** - All testing docs together, all kit docs together
2. **Verify changes** - Include grep commands to confirm patterns are fixed
3. **Be independently mergeable** - Each plan improves docs without dependencies

Suggested batches:

- **Batch A**: User docs - shell-init, config path
- **Batch B**: Kit docs - DotAgentContext, kit_cli_commands, Path.cwd()
- **Batch C**: Testing docs - DotAgentContext patterns
- **Batch D**: CLI/Architecture docs - command org, Protocol vs ABC
