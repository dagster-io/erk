# Extraction Plan: Claude Code Project Directory Semantics

## Objective

Document the Claude Code project directory structure, path encoding scheme, and walk-up directory search pattern for future development and debugging.

## Source Information

- **Session ID**: fe54e4aa-7dbf-455a-b14a-8f5bdb0072b4
- **Context**: Implementation of walk-up directory search for session store

---

## Documentation Items

### Item 1: Claude Code Project Directory Structure (Category B - Teaching Gap)

**Location**: `docs/agent/architecture/` or `docs/agent/sessions/`
**Action**: Create new document
**Priority**: Medium

**Content**:

```markdown
# Claude Code Project Directory Structure

Claude Code stores project-specific data in `~/.claude/projects/` using an encoded directory naming scheme.

## Path Encoding Scheme

Project directories are named by encoding the absolute project path:
- Forward slashes (`/`) are replaced with hyphens (`-`)
- Dots (`.`) are replaced with hyphens (`-`)

**Example**:
- Project at `/Users/dev/myrepo` → `~/.claude/projects/-Users-dev-myrepo`
- Project at `/code/my.project` → `~/.claude/projects/-code-my-project`

## Directory Contents

Each project directory contains:
- `<session-id>.jsonl` - Main session logs (UUID format)
- `agent-<agent-id>.jsonl` - Subagent logs from Task tool invocations

## Walk-Up Directory Search

When looking up a project from a working directory, the session store:
1. Checks if an exact match exists for the current path
2. If not found, walks up to the parent directory
3. Repeats until finding a match or hitting the filesystem root

This enables running erk commands from subdirectories of a Claude project.

**Implementation pattern**:
```python
def _get_project_dir(self, project_cwd: Path) -> Path | None:
    current = project_cwd.resolve()
    while True:
        encoded = str(current).replace("/", "-").replace(".", "-")
        project_dir = projects_dir / encoded
        if project_dir.exists():
            return project_dir
        parent = current.parent
        if parent == current:  # Hit filesystem root
            break
        current = parent
    return None
```
```

### Item 2: Glossary Entry for Project Directory (Category B - Teaching Gap)

**Location**: `docs/agent/glossary.md`
**Action**: Add entry
**Priority**: Low

**Content**:

```markdown
### Claude Code Project Directory

The directory where Claude Code stores session data for a specific project. Located at `~/.claude/projects/<encoded-path>` where the path is encoded by replacing `/` and `.` with `-`. Contains session logs (`.jsonl` files) for all Claude Code sessions started from that project directory.

See: [Claude Code Project Directory Structure](sessions/claude-code-project-structure.md)
```

### Item 3: Index Entry (Category B - Teaching Gap)

**Location**: `docs/agent/index.md`
**Action**: Add entry under Sessions category
**Priority**: Low

**Content**:

Add to sessions section:
```markdown
- **[claude-code-project-structure.md](sessions/claude-code-project-structure.md)** — Read when working with Claude Code session storage, debugging session lookup issues, or implementing features that depend on project directory resolution
```