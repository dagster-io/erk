# Plan: Fix Agent Session Slug Lookup for Parallel Planning

## Problem

When parallel Task agents run `/erk:plan-save`, they all save the wrong plan due to a bug in slug lookup:

1. Agent session ID is `agent-<id>` (e.g., `agent-a1b2c3d4`)
2. Slug is logged in `agent-a1b2c3d4.jsonl`
3. `_iter_session_entries` **skips all agent files** (line 324-326 in real.py)
4. `find_plan_for_session()` returns `None` for agent sessions
5. Falls back to mtime-based selection - returns most recent plan from ANY session
6. All parallel agents get the same (wrong) plan

## Solution

Handle agent sessions specially in `extract_slugs_from_session()` - when session_id starts with `agent-`, read the agent file directly instead of using `_iter_session_entries`.

## Implementation

### Step 1: Add `_read_agent_session_entries` helper

**File:** `packages/erk-shared/src/erk_shared/learn/extraction/claude_installation/real.py`

Add new helper method that reads ALL entries from a specific agent file (no sessionId filtering):

```python
def _read_agent_session_entries(self, project_dir: Path, agent_id: str) -> list[dict]:
    """Read all entries from an agent session file."""
    if not agent_id.startswith("agent-"):
        agent_id = f"agent-{agent_id}"

    agent_file = project_dir / f"{agent_id}.jsonl"
    if not agent_file.exists():
        return []

    entries: list[dict] = []
    with open(agent_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            entries.append(entry)
    return entries
```

### Step 2: Modify `extract_slugs_from_session`

**File:** `packages/erk-shared/src/erk_shared/learn/extraction/claude_installation/real.py`

Update to detect agent session IDs and use the new helper:

```python
def extract_slugs_from_session(self, project_cwd: Path, session_id: str) -> list[str]:
    project_dir = self._get_project_dir(project_cwd)
    if project_dir is None:
        return []

    # For agent sessions, read the agent file directly
    if session_id.startswith("agent-"):
        entries = self._read_agent_session_entries(project_dir, session_id)
    else:
        entries = self._iter_session_entries(project_dir, session_id, max_lines=None)

    # Rest of method unchanged...
```

### Step 3: Add integration test

**File:** `tests/integration/test_session_store_integration.py`

```python
class TestExtractSlugsFromAgentSession:
    def test_extracts_slug_from_agent_file(self, mock_claude_home: Path) -> None:
        install_fixture(mock_claude_home, "project_epsilon", "/test/epsilon")
        store = RealClaudeInstallation()
        slugs = store.extract_slugs_from_session(Path("/test/epsilon"), "agent-12345678")
        assert slugs == ["agent-should-be-ignored"]  # slug from fixture
```

### Step 4: Add unit test for fake

**File:** `tests/unit/fakes/test_fake_claude_installation.py`

```python
def test_extract_slugs_from_agent_session() -> None:
    installation = FakeClaudeInstallation.for_test(
        session_slugs={"agent-a1b2c3d4": ["my-agent-plan"]}
    )
    slugs = installation.extract_slugs_from_session(Path("/project"), "agent-a1b2c3d4")
    assert slugs == ["my-agent-plan"]
```

## Files to Modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/learn/extraction/claude_installation/real.py` | Add `_read_agent_session_entries`, modify `extract_slugs_from_session` |
| `tests/integration/test_session_store_integration.py` | Add agent slug extraction tests |
| `tests/unit/fakes/test_fake_claude_installation.py` | Add agent session slug test |

## No Changes Needed

- `abc.py` - Interface unchanged
- `fake.py` - Already supports any session_id key in `session_slugs` dict
- `_iter_session_entries` - Keep unchanged for existing callers

## Verification

1. Run unit tests: `pytest tests/unit/fakes/test_fake_claude_installation.py -v`
2. Run integration tests: `pytest tests/integration/test_session_store_integration.py -v -k "agent"`
3. Manual test: Launch parallel Task agents with plan mode and verify each saves its own plan