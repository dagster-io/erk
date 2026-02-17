---
title: Command Rename Checklist
read_when:
  - "renaming an exec script or CLI command"
  - "changing a Click command name"
  - "migrating command references across the codebase"
tripwires:
  - action: "renaming an exec command without updating all 9 reference locations"
    warning: "Follow the 9-place checklist in command-rename-checklist.md to avoid stale references."
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
---

# Command Rename Checklist

When renaming an exec command (e.g., `update-roadmap-step` -> `update-objective-node`), update these 9 locations:

## The 9-Place Checklist

### 1. Script file

Rename the file and update the `@click.command(name=...)` decorator:

```python
# Before: update_roadmap_step.py
@click.command(name="update-roadmap-step")

# After: update_objective_node.py
@click.command(name="update-objective-node")
```

### 2. exec/group.py imports and registration

Update the import and `add_command()` call:

<!-- Source: src/erk/cli/commands/exec/group.py, exec_group.add_command -->

See the import and `add_command()` registration pattern in `src/erk/cli/commands/exec/group.py`.

### 3. Test file

Rename the test file and update all imports and command invocations within tests.

### 4. Skill/command references

Update `.claude/skills/erk-exec/reference.md` and any other skill files that reference the command.

### 5. Slash command templates

Search `.claude/commands/` for references to the old command name and update.

### 6. docs/learned/ references

```bash
grep -r "old-command-name" docs/learned/
```

Update all documentation references.

### 7. CLI help text and descriptions

If the command appears in group help text or other command descriptions, update those references.

### 8. CHANGELOG entry

Add a CHANGELOG entry noting the rename for user awareness.

### 9. Workflow files

Search `.github/workflows/` for references to the old command name.

## Verification

After completing the rename, verify no stale references remain:

```bash
grep -r "old-command-name" --include="*.py" --include="*.md" --include="*.yml" .
```

Any remaining matches should be in historical entries (CHANGELOG, commit messages) or documentation describing the rename itself.

## Example: update-roadmap-step -> update-objective-node

This rename also changed the `--step` parameter to `--node`:

- Script: `update_roadmap_step.py` -> `update_objective_node.py`
- Parameter: `--step` -> `--node`
- All 9 locations updated
- 12 intentional historical references remain in docs/CHANGELOG

## Related Topics

- [CLI Development](../cli/) - Broader CLI patterns and conventions
