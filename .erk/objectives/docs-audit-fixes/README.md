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

### Execution Model

**One chunk per turn.** Each turn fixes one logical grouping of issues.

### Chunks

Process these chunks in priority order. Each chunk is independently mergeable.

1. **User-facing docs**: `erk shell-init` → `erk init --shell`, `erk.toml` → `.erk/config.toml`
2. **Context class migration**: `DotAgentContext` → `ErkContext`
3. **Kit path migration**: `kit_cli_commands/` → `scripts/`
4. **Dependency injection patterns**: `Path.cwd()` → `require_cwd(ctx)`
5. **CLI command organization**: `erk create` → `erk plan create`

### Evaluation Prompt

Search for each pattern across all documentation. Find the **first chunk with remaining matches**:

```bash
# Chunk 1: User-facing
grep -r "erk shell-init" .erk/docs/ docs/
grep -r "erk\.toml" .erk/docs/ docs/

# Chunk 2: Context class
grep -r "DotAgentContext" .erk/docs/ docs/

# Chunk 3: Kit paths
grep -r "kit_cli_commands" .erk/docs/ docs/

# Chunk 4: Dependency injection
grep -r "Path\.cwd()" .erk/docs/ docs/

# Chunk 5: CLI commands
grep -rE "erk (create|get|implement)[^-]" .erk/docs/ docs/
```

Report:

- **Next chunk**: First chunk (1-5) with matches
- **Files affected**: List files for that chunk only
- **If no matches**: Objective complete

### Plan Sizing

Each plan fixes **exactly one chunk**:

1. Fix all instances of the chunk's patterns across all affected files
2. Run verification grep to confirm zero remaining matches
3. Each plan is independently mergeable
