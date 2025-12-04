---
title: Session Log Test Fixtures
read_when:
  - "creating JSONL fixtures for session log tests"
  - "testing session plan extraction"
  - "writing integration tests for session parsing"
---

# Session Log Test Fixtures

Guide for creating realistic JSONL test fixtures that simulate Claude Code session logs.

## Overview

Session log fixtures enable testing of session-scoped features without requiring actual Claude Code sessions. These fixtures simulate the JSONL format used by Claude Code in `~/.claude/projects/`.

## When to Use Fixtures

**Use session log fixtures when testing:**

- Session-scoped plan extraction
- Agent log discovery and correlation
- Session metadata parsing
- Project directory discovery
- Cross-session isolation

**Don't use fixtures for:**

- Testing the JSONL parser itself (use unit tests)
- Real integration with Claude Code (use live sessions)
- Simple business logic (use in-memory fakes)

## Fixture Directory Structure

Organize fixtures to mirror the `~/.claude/projects/` structure:

```
tests/
└── integration/
    └── kits/
        └── erk/
            └── fixtures/
                └── session_logs/          # Base fixture directory
                    ├── project_alpha/     # Scenario: Single session, single slug
                    │   └── session-alpha-001.jsonl
                    ├── project_beta/      # Scenario: Multiple sessions
                    │   ├── session-beta-001.jsonl
                    │   └── session-beta-002.jsonl
                    ├── project_gamma/     # Scenario: Session with multiple slugs
                    │   └── session-gamma-001.jsonl
                    ├── project_delta/     # Scenario: No plans (no slug field)
                    │   └── session-delta-001.jsonl
                    └── project_epsilon/   # Scenario: Session + agent files
                        ├── session-epsilon-001.jsonl
                        └── agent-abc123.jsonl
```

## Creating Minimal Fixtures

### Step 1: Define Your Test Scenario

What behavior are you testing?

**Examples:**

- "Find plan slug created in a specific session"
- "Distinguish between parallel sessions"
- "Ignore agent logs when listing sessions"
- "Handle sessions without plans gracefully"

### Step 2: Create Minimal JSONL Entries

Only include fields required for your test. Omit unnecessary detail.

**Minimal session entry (plan mode):**

```json
{
  "sessionId": "test-session-001",
  "type": "summary",
  "slug": "add-auth-feature",
  "message": { "timestamp": 1700000000.0 }
}
```

**Key fields:**

- `sessionId`: Session identifier (required)
- `type`: Entry type (`user`, `assistant`, `tool_result`, `summary`)
- `slug`: Plan identifier (only in Plan Mode entries)
- `message.timestamp`: Unix timestamp for ordering

### Step 3: Create the Fixture File

**Example: Single session with one plan**

File: `fixtures/session_logs/project_alpha/session-alpha-001.jsonl`

```jsonl
{"sessionId": "session-alpha-001", "type": "user", "message": {"content": [{"type": "text", "text": "Create a plan"}], "timestamp": 1700000000.0}}
{"sessionId": "session-alpha-001", "type": "assistant", "message": {"content": [{"type": "text", "text": "I'll enter plan mode"}], "timestamp": 1700000001.0}}
{"sessionId": "session-alpha-001", "type": "summary", "slug": "add-auth-feature", "message": {"timestamp": 1700000002.0}}
```

**Example: Session without plans**

File: `fixtures/session_logs/project_delta/session-delta-001.jsonl`

```jsonl
{"sessionId": "session-delta-001", "type": "user", "message": {"content": [{"type": "text", "text": "Run tests"}], "timestamp": 1700000000.0}}
{"sessionId": "session-delta-001", "type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "id": "tool1"}], "timestamp": 1700000001.0}}
{"sessionId": "session-delta-001", "type": "tool_result", "message": {"tool_use_id": "tool1", "content": [{"type": "text", "text": "Tests passed"}], "timestamp": 1700000002.0}}
```

### Step 4: Write Tests Using Fixtures

**Pattern: Monkeypatch `Path.home()` to fixture directory**

```python
from pathlib import Path
import pytest

def test_find_plan_slug_in_session(monkeypatch, tmp_path: Path) -> None:
    """Test extracting plan slug from session log."""
    # Setup: Copy fixture to temp directory
    fixture_root = Path(__file__).parent / "fixtures" / "session_logs"
    project_alpha = tmp_path / ".claude" / "projects" / "project_alpha"
    project_alpha.mkdir(parents=True)

    # Copy fixture file
    src = fixture_root / "project_alpha" / "session-alpha-001.jsonl"
    dst = project_alpha / "session-alpha-001.jsonl"
    dst.write_text(src.read_text())

    # Monkeypatch home directory
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Test: Extract slug
    slug = find_plan_for_session("session-alpha-001", project_alpha)

    assert slug == "add-auth-feature"
```

## Fixture Patterns by Scenario

### Scenario 1: Single Session, Single Plan

**Use case:** Basic plan extraction

**Fixture:** `project_alpha/session-alpha-001.jsonl`

```jsonl
{
  "sessionId": "session-alpha-001",
  "type": "summary",
  "slug": "add-feature-x",
  "message": {
    "timestamp": 1700000000
  }
}
```

**Test:**

```python
def test_single_session_single_plan(fixture_dir: Path) -> None:
    project = fixture_dir / "project_alpha"
    slug = find_plan_for_session("session-alpha-001", project)
    assert slug == "add-feature-x"
```

### Scenario 2: Multiple Sessions in Same Project

**Use case:** Parallel session isolation

**Fixtures:**

- `project_beta/session-beta-001.jsonl` (plan: "feature-a")
- `project_beta/session-beta-002.jsonl` (plan: "feature-b")

```jsonl
# session-beta-001.jsonl
{"sessionId": "session-beta-001", "type": "summary", "slug": "feature-a", "message": {"timestamp": 1700000000.0}}

# session-beta-002.jsonl (newer mtime)
{"sessionId": "session-beta-002", "type": "summary", "slug": "feature-b", "message": {"timestamp": 1700000100.0}}
```

**Test:**

```python
def test_parallel_sessions_isolated(fixture_dir: Path) -> None:
    """Verify sessions don't interfere despite different mtimes."""
    project = fixture_dir / "project_beta"

    # Should find correct slug despite session-002 being newer
    slug_001 = find_plan_for_session("session-beta-001", project)
    slug_002 = find_plan_for_session("session-beta-002", project)

    assert slug_001 == "feature-a"
    assert slug_002 == "feature-b"
```

### Scenario 3: Session with Multiple Plans

**Use case:** Handle sessions with plan updates

**Fixture:** `project_gamma/session-gamma-001.jsonl`

```jsonl
{"sessionId": "session-gamma-001", "type": "summary", "slug": "plan-v1", "message": {"timestamp": 1700000000.0}}
{"sessionId": "session-gamma-001", "type": "user", "message": {"content": [{"type": "text", "text": "Update plan"}], "timestamp": 1700000010.0}}
{"sessionId": "session-gamma-001", "type": "summary", "slug": "plan-v2", "message": {"timestamp": 1700000020.0}}
```

**Test:**

```python
def test_session_with_multiple_plans(fixture_dir: Path) -> None:
    """Should return most recent plan slug."""
    project = fixture_dir / "project_gamma"
    slug = find_latest_plan_for_session("session-gamma-001", project)
    assert slug == "plan-v2"  # Most recent
```

### Scenario 4: Agent Logs (Filtering)

**Use case:** Ensure agent logs don't interfere with session listing

**Fixtures:**

- `project_epsilon/session-epsilon-001.jsonl` (main session)
- `project_epsilon/agent-abc123.jsonl` (agent subprocess)

```jsonl
# session-epsilon-001.jsonl
{"sessionId": "session-epsilon-001", "type": "summary", "slug": "main-plan", "message": {"timestamp": 1700000000.0}}

# agent-abc123.jsonl (should be ignored by session listing)
{"sessionId": "session-epsilon-001", "type": "assistant", "message": {"content": [{"type": "tool_use"}], "timestamp": 1700000001.0}}
```

**Test:**

```python
def test_agent_logs_filtered(fixture_dir: Path) -> None:
    """Agent logs should not appear in session listing."""
    project = fixture_dir / "project_epsilon"

    sessions = list_sessions(project)

    assert "session-epsilon-001" in sessions
    assert "agent-abc123" not in sessions  # Filtered out
```

### Scenario 5: Empty/Malformed Sessions

**Use case:** Graceful handling of edge cases

**Fixture:** `project_zeta/session-zeta-001.jsonl`

```jsonl
{"sessionId": "session-zeta-001", "type": "user", "message": {"timestamp": 1700000000.0}}

not-valid-json
{"sessionId": "session-zeta-001", "type": "assistant", "message": {"timestamp": 1700000002.0}}
```

**Test:**

```python
def test_malformed_entries_skipped(fixture_dir: Path) -> None:
    """Should skip malformed JSON lines gracefully."""
    project = fixture_dir / "project_zeta"

    # Should parse valid entries, skip malformed line
    entries = parse_session_log(project / "session-zeta-001.jsonl")

    assert len(entries) == 2  # Only valid entries
```

## Fixture Creation Checklist

Before committing fixtures:

- [ ] **Minimal**: Only include fields required for the test
- [ ] **Realistic**: Match actual JSONL structure from Claude Code
- [ ] **Documented**: Add comment explaining test scenario
- [ ] **Organized**: Place in appropriate scenario directory
- [ ] **Self-contained**: Test should work with fixture alone (no external deps)

## Common Mistakes

### ❌ Including Excessive Detail

```jsonl
# DON'T: Include full conversation history
{"sessionId": "test", "type": "user", "message": {"content": [{"type": "text", "text": "A very long message with lots of detail that isn't relevant to the test..."}], "timestamp": 1700000000.0}}
{"sessionId": "test", "type": "assistant", "message": {"content": [{"type": "text", "text": "Another long response..."}], "timestamp": 1700000001.0}}
```

```jsonl
# DO: Use minimal entries
{"sessionId": "test", "type": "summary", "slug": "my-plan", "message": {"timestamp": 1700000000.0}}
```

### ❌ Hardcoding Real Paths

```python
# DON'T: Use real home directory
fixture_dir = Path("/Users/myname/.claude/projects/test")
```

```python
# DO: Use tmp_path and monkeypatch
def test_with_fixture(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # Now fixtures work in isolated temp directory
```

### ❌ Testing Multiple Concerns in One Fixture

```python
# DON'T: Test plan extraction AND agent filtering in same fixture
def test_everything(fixture_dir: Path) -> None:
    # Tests too many things
    pass
```

```python
# DO: Create separate fixtures for separate concerns
def test_plan_extraction(fixture_dir: Path) -> None:
    # Focused test for one behavior
    pass

def test_agent_filtering(fixture_dir: Path) -> None:
    # Separate test for different behavior
    pass
```

## Advanced: Dynamic Fixture Generation

For complex scenarios, generate fixtures programmatically:

```python
import json
from pathlib import Path

def create_session_fixture(
    session_id: str,
    slugs: list[str],
    output_path: Path
) -> None:
    """Generate session log fixture with specified plan slugs."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        timestamp = 1700000000.0

        for slug in slugs:
            entry = {
                "sessionId": session_id,
                "type": "summary",
                "slug": slug,
                "message": {"timestamp": timestamp}
            }
            f.write(json.dumps(entry) + "\n")
            timestamp += 10.0

# Usage in tests
def test_with_generated_fixture(tmp_path: Path) -> None:
    fixture_path = tmp_path / "session-test.jsonl"
    create_session_fixture("test-001", ["plan-a", "plan-b"], fixture_path)

    # Test using generated fixture
    slugs = extract_all_slugs(fixture_path)
    assert slugs == ["plan-a", "plan-b"]
```

## Related Documentation

- [Session Layout](../sessions/layout.md) - JSONL format specification
- [Parallel Session Awareness](../sessions/parallel-session-awareness.md) - Session-scoped patterns
- [Erk Test Reference](./testing.md) - Erk-specific fakes and test structure

## Summary

**Key principles for session log fixtures:**

1. **Minimal**: Include only what's needed for the test
2. **Isolated**: Use `tmp_path` and `monkeypatch` for isolation
3. **Organized**: Group by scenario in fixture directories
4. **Realistic**: Match actual JSONL structure from Claude Code
5. **Focused**: One fixture per test concern

When in doubt, create a simpler fixture. You can always add complexity later if needed.
