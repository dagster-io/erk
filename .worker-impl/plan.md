# Extraction Plan: Session Store Testing Patterns

## Objective

Document patterns for using FakeClaudeCodeSessionStore to eliminate mocks in tests, including the mock elimination workflow and DotAgentContext.for_test() parameters.

## Source Information

- **Session ID**: 75565cea-99d5-4670-ad8f-6e6c5a755dfa
- **Branch**: 2639-update-plan-save-to-issue-12-07-1905
- **Key Changes**: Refactored plan_save_to_issue.py to use session_store.get_current_session_id(), eliminating 12 mocks

## Documentation Items

### 1. Session Store Integration Pattern (Category A - Learning Gap)

**Location**: `docs/agent/testing/session-store-testing.md` (new file)
**Action**: Create
**Priority**: High (directly supports mock elimination goal)

**Content**:

```markdown
# Testing with FakeClaudeCodeSessionStore

## When to Use

Use `FakeClaudeCodeSessionStore` when testing code that needs:
- Current session ID lookup
- Session discovery/listing
- Session content reading

## Basic Setup

\`\`\`python
from erk_shared.extraction.claude_code_session_store import (
    FakeClaudeCodeSessionStore,
    FakeProject,
    FakeSessionData,
)

# Empty store - no sessions
fake_store = FakeClaudeCodeSessionStore(current_session_id=None)

# Store with current session ID
fake_store = FakeClaudeCodeSessionStore(current_session_id="my-session-id")

# Store with session data
fake_store = FakeClaudeCodeSessionStore(
    current_session_id="test-session-id",
    projects={
        tmp_path: FakeProject(
            sessions={
                "test-session-id": FakeSessionData(
                    content='{"type": "user", "message": {"content": "Hello"}}\n',
                    size_bytes=2000,
                    modified_at=1234567890.0,
                )
            }
        )
    },
)
\`\`\`

## Injecting via DotAgentContext

\`\`\`python
result = runner.invoke(
    my_command,
    ["--format", "json"],
    obj=DotAgentContext.for_test(
        github_issues=fake_gh,
        git=fake_git,
        session_store=fake_store,
        cwd=tmp_path,
    ),
)
\`\`\`

## Key Methods

- `get_current_session_id()` - Returns configured current session ID
- `find_sessions(project_cwd, min_size=0, limit=10)` - Returns sessions from fake data
- `read_session(project_cwd, session_id)` - Returns session content
- `has_project(project_cwd)` - Checks if project exists
```

### 2. Mock Elimination Workflow (Category B - Teaching Gap)

**Location**: `docs/agent/testing/mock-elimination.md` (new file)
**Action**: Create
**Priority**: Medium (process documentation)

**Content**:

```markdown
# Eliminating Mocks with Fakes

## Overview

When you encounter tests with `unittest.mock.patch()`, consider whether a fake can replace the mock. Fakes are preferred because they:
- Test real behavior, not call signatures
- Don't break when implementation changes
- Are reusable across tests

## Workflow

### Step 1: Identify Mock Targets

Look for patterns like:
\`\`\`python
with patch("module.function", return_value=value):
    ...
\`\`\`

### Step 2: Check for Existing Fakes

Common fakes in this codebase:
- `FakeGit` - Git operations
- `FakeGitHubIssues` - GitHub issue operations
- `FakeClaudeCodeSessionStore` - Session store operations
- `FakeGraphite` - Graphite operations

### Step 3: Refactor Source Code (if needed)

If the mocked function reads from filesystem/external state, consider:
1. Adding a dependency injection point (ABC + fake)
2. Using an existing abstraction (e.g., session_store)

Example: Replace file-based session ID lookup with session_store:

\`\`\`python
# Before: File-based (requires mocking)
effective_session_id = session_id or _get_session_id_from_file()

# After: Dependency injection (uses fake)
effective_session_id = session_id or session_store.get_current_session_id()
\`\`\`

### Step 4: Update Tests

Replace mocks with fake configuration:

\`\`\`python
# Before: Mock
with patch("module._get_session_id_from_file", return_value="session-id"):
    result = runner.invoke(command, obj=ctx)

# After: Fake
fake_store = FakeClaudeCodeSessionStore(current_session_id="session-id")
result = runner.invoke(
    command,
    obj=DotAgentContext.for_test(session_store=fake_store),
)
\`\`\`

### Step 5: Remove Unused Imports

After eliminating all mocks, remove:
\`\`\`python
from unittest.mock import patch  # Remove if no longer used
\`\`\`
```

### 3. DotAgentContext.for_test() Reference (Category A - Learning Gap)

**Location**: `docs/agent/testing/dot-agent-context-testing.md` (new file)
**Action**: Create
**Priority**: Medium (reference documentation)

**Content**:

```markdown
# DotAgentContext.for_test() Reference

## Overview

`DotAgentContext.for_test()` creates a test context with injectable fake dependencies.

## Available Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `github_issues` | `GitHubIssues` | `FakeGitHubIssues()` | GitHub issue operations |
| `git` | `Git` | `FakeGit()` | Git operations |
| `session_store` | `ClaudeCodeSessionStore` | `FakeClaudeCodeSessionStore()` | Session store operations |
| `cwd` | `Path` | `Path.cwd()` | Current working directory |
| `repo_root` | `Path` | `None` | Repository root path |

## Usage Examples

### Minimal (all defaults)
\`\`\`python
obj=DotAgentContext.for_test()
\`\`\`

### With specific fakes
\`\`\`python
obj=DotAgentContext.for_test(
    github_issues=FakeGitHubIssues(),
    git=FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    ),
    session_store=FakeClaudeCodeSessionStore(current_session_id="abc123"),
    cwd=tmp_path,
)
\`\`\`

## Accessing in Commands

Use `require_*` helpers to get dependencies:

\`\`\`python
from dot_agent_kit.context_helpers import (
    require_cwd,
    require_git,
    require_github_issues,
    require_session_store,
)

@click.command()
@click.pass_context
def my_command(ctx: click.Context) -> None:
    github = require_github_issues(ctx)
    git = require_git(ctx)
    session_store = require_session_store(ctx)
    cwd = require_cwd(ctx)
```

## Index Updates

**Location**: `docs/agent/index.md`
**Action**: Update
**Priority**: Low

Add entries for the new documentation files under the Testing section.