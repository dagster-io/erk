# ccsesh - Claude Code Session Inspection Library

## Purpose

ccsesh provides tools for inspecting and working with Claude Code session data. It's designed as both a CLI tool and an embeddable library.

## Architecture

```
src/ccsesh/
├── api/                    # Core domain model and business logic
│   ├── __init__.py         # Public API marker
│   ├── projects.py         # Project-related functions
│   └── sessions.py         # Session-related functions
├── cli/
│   └── __init__.py         # CLI entry point
└── commands/               # CLI display layer (thin wrappers)
    ├── __init__.py
    ├── project.py          # Project CLI commands
    └── session.py          # Session CLI commands
```

### Layer Separation

**API Layer (`api/`)**: Core business logic, embeddable as a library

- No click decorators or CLI concerns
- Functions accept explicit parameters for testability
- Can be imported independently: `from ccsesh.api.sessions import list_sessions`

**Commands Layer (`commands/`)**: CLI display only

- Thin wrappers around API functions
- Handle click decorators, options, output formatting
- No business logic - delegate to API layer

## Usage as a Library

```python
from ccsesh.api.projects import list_projects, encode_path_to_project_id
from ccsesh.api.sessions import resolve_project_dir, list_sessions

# List all projects
projects = list_projects()

# Get sessions for a specific project
project_dir = resolve_project_dir(
    project_id="-Users-alice-code-myapp",
    project_path=None,
    cwd=Path.cwd()
)
if project_dir:
    sessions = list_sessions(project_dir)
```

## Testing

API functions accept optional `projects_dir` parameter for testing without mocking:

```python
def test_example(tmp_path: Path) -> None:
    projects_dir = tmp_path / ".claude" / "projects"
    # Use projects_dir parameter directly - no patching needed
    result = resolve_project_dir("id", None, tmp_path, projects_dir=projects_dir)
```

CLI tests patch `get_projects_dir` since the CLI layer doesn't expose the parameter.

## Claude Code Session Format

Sessions are stored in `~/.claude/projects/<encoded-project-id>/`:

- Project ID: filesystem path with `/` replaced by `-`
- Session files: `<session-id>.jsonl` (exclude `agent-*.jsonl`)
- Sorted by modification time (newest first)
