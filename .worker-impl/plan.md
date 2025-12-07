# Extraction Plan: Dead Code Discovery and Kit Artifact Lifecycle

## Objective

Add documentation for systematic dead code discovery after file deletions and kit artifact lifecycle management, plus update planning workflow documentation.

## Source Information

- **Session ID**: e59a46a0-6bdd-46d2-aa55-91d3f31548a5
- **Context**: Session involved deleting 5 unused slash commands and their associated kit CLI commands, then performing deep analysis to find orphaned references

## Documentation Items

### Item 1: Dead Code Discovery Pattern (Category A - Learning)

**Location**: `docs/agent/architecture/dead-code-discovery.md`
**Action**: Create new document
**Priority**: High - This pattern saved significant debugging time in the session

**Content**:

```markdown
---
title: Dead Code Discovery Pattern
read_when:
  - "deleting files or commands"
  - "removing features"
  - "cleaning up unused code"
---

# Dead Code Discovery Pattern

Systematic approach for identifying orphaned code after file deletions.

## When to Use

After deleting:
- Slash commands (`.claude/commands/`)
- Kit CLI commands (`kit_cli_commands/`)
- Python modules
- Any file that might be referenced elsewhere

## Discovery Checklist

### 1. Search for Import References

```bash
# Search for imports of deleted module
grep -r "from deleted_module import" --include="*.py"
grep -r "import deleted_module" --include="*.py"
```

### 2. Search for String References

Deleted commands and features are often referenced by name in:
- Error messages
- Documentation
- Test assertions
- CLI help text
- Comments

```bash
# Search for command name references
grep -r "deleted-command-name" --include="*.py" --include="*.md"
```

### 3. Check Configuration Files

- `kit.yaml` - Kit CLI command entries and artifact lists
- `dot-agent.toml` - Installed artifact references
- `registry-entry.md` - Kit artifact documentation

### 4. Check Test Files

Tests often have hardcoded references:
- Test fixtures with artifact names
- Assertions checking for specific output
- Mock configurations

### 5. Check Documentation

- `docs/agent/` - Agent documentation
- Kit docs (`packages/.../docs/`)
- README files
- Inline code comments with file paths

## Example: Deleting a Slash Command

When deleting `/erk:example-command`:

1. **Delete the command file**: `.claude/commands/erk/example-command.md`
2. **Delete symlink target** (if kit command): `packages/.../commands/erk/example-command.md`
3. **Search for references**:
   ```bash
   grep -r "example-command" --include="*.py" --include="*.md"
   grep -r "/erk:example-command"
   ```
4. **Update kit.yaml**: Remove from `artifacts.command` list
5. **Update dot-agent.toml**: Remove from `artifacts` array
6. **Update tests**: Fix any assertions expecting the command
7. **Update docs**: Remove references in workflow documentation

## Common Orphan Locations

| Deleted Item | Check These Locations |
|--------------|----------------------|
| Slash command | Error messages, CLI help, workflow docs |
| Kit CLI command | kit.yaml, tests, other CLI commands that call it |
| Python module | Imports, __init__.py, test files |
| Documentation | Index files, cross-references, navigation |

## Verification

After cleanup, run CI to catch remaining references:
```bash
make fast-ci
```

Type checkers and import errors will surface remaining dead imports.
```

### Item 2: Kit Artifact Lifecycle (Category A - Learning)

**Location**: `docs/agent/kits/artifact-lifecycle.md`
**Action**: Create new document
**Priority**: Medium - Prevents incomplete deletions

**Content**:

```markdown
---
title: Kit Artifact Lifecycle
read_when:
  - "adding kit artifacts"
  - "removing kit artifacts"
  - "modifying kit structure"
---

# Kit Artifact Lifecycle

Guide for properly adding and removing kit artifacts.

## Artifact Types

| Type | Location | Registration |
|------|----------|--------------|
| Command | `commands/<kit>/` | `kit.yaml` artifacts.command |
| Skill | `skills/<name>/` | `kit.yaml` artifacts.skill |
| Agent | `agents/<kit>/` | `kit.yaml` artifacts.agent |
| Doc | `docs/<kit>/` | `kit.yaml` artifacts.doc |
| Kit CLI Command | `kit_cli_commands/<kit>/` | `kit.yaml` kit_cli_commands |

## Adding an Artifact

1. **Create the artifact file** in the appropriate location
2. **Register in kit.yaml**:
   ```yaml
   artifacts:
     command:
       - commands/mykit/new-command.md
   ```
3. **Run kit sync**: `dot-agent kit sync`
4. **Verify**: Symlink created in `.claude/commands/`

## Removing an Artifact

### Files to Update

1. **Delete artifact file** from kit source
2. **Delete symlink** in `.claude/` (if exists)
3. **Update kit.yaml**: Remove from artifacts list
4. **Update dot-agent.toml**: Remove from installed artifacts
5. **Delete associated tests**
6. **Update registry-entry.md**: Remove from artifact list

### For Kit CLI Commands

Additional steps:
1. **Delete Python file** from `kit_cli_commands/`
2. **Remove entry** from `kit.yaml` kit_cli_commands list
3. **Delete unit tests** for the command

### Verification Checklist

- [ ] Artifact file deleted
- [ ] Symlink deleted (if applicable)
- [ ] kit.yaml updated
- [ ] dot-agent.toml updated
- [ ] Tests deleted
- [ ] Documentation references removed
- [ ] `make fast-ci` passes
```

### Item 3: Planning Workflow Update (Category B - Teaching)

**Location**: `docs/agent/glossary.md`
**Action**: Update existing entry
**Priority**: Low - Documentation already updated in this session

**Content**:

Add/update glossary entry:

```markdown
### Plan Mode Workflow

The standard workflow for creating implementation plans:

1. **Enter Plan Mode** - Claude enters automatically for complex tasks, or manually via EnterPlanMode tool
2. **Create Plan** - Interactive planning with context extraction
3. **Exit Plan Mode** - Plan saved to `~/.claude/plans/`
4. **Save to GitHub** - Run `/erk:save-plan` to create GitHub issue with `erk-plan` label
5. **Implement** - Run `erk implement <issue-number>` to create worktree and execute plan

**Note**: The previous `/erk:craft-plan` command has been removed. Use Plan Mode + `/erk:save-plan` instead.
```