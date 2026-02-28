# Entity Store: Generic KV State + Append-Only Log for GitHub Issues/PRs

## Context

The metadata block subsystem (`erk_shared.gateway.github.metadata`) is reliable and well-tested (~370+ tests), but exposes a procedural API of 50+ free functions operating on raw strings. Callers must know:

- Whether a key lives in the issue body (mutable state) or comments (log entries)
- The exact parse/render/replace dance for read-modify-write cycles
- Which `create_*_block()` and `render_*()` functions to compose for event comments

The user wants this to feel like a reusable library with two distinct APIs:

1. **Entity State** — mutable KV metadata on the issue/PR body (plan-header, objective-header, objective-roadmap)
2. **Entity Log** — immutable append-only entries stored as comments (workflow-started, submission-queued, impl-started, plan-body, etc.)

The store should be generic to both issues and PRs, with a namespace of keys per entity.

Note: `PlanBackend` already wraps some of this pattern for plans specifically. The entity store is the generic layer underneath — `PlanBackend` could eventually be refactored to use it.

## API Design

### Module Location

```
packages/erk-shared/src/erk_shared/entity_store/
├── __init__.py            # empty
├── types.py               # LogEntry, EntityKind
├── entity.py              # GitHubEntity (main entry point)
├── state.py               # EntityState (mutable KV on body)
└── log.py                 # EntityLog (immutable append-only)
```

Lives in `erk_shared` (not nested under `gateway/github/`) because it's a higher-level abstraction that composes gateway operations. The metadata parsing internals remain in `gateway/github/metadata/`.

### Types (`types.py`)

```python
from dataclasses import dataclass
from enum import Enum
from typing import Any


class EntityKind(Enum):
    ISSUE = "issue"
    PR = "pr"


@dataclass(frozen=True)
class LogEntry:
    """An immutable log entry extracted from a GitHub comment."""
    key: str
    data: dict[str, Any]
    comment_id: int
```

### GitHubEntity (`entity.py`)

```python
class GitHubEntity:
    """A GitHub issue or PR with structured metadata and event log.

    Provides two APIs:
    - state: mutable KV metadata stored in the entity body
    - log: immutable append-only entries stored as comments
    """

    def __init__(
        self,
        *,
        number: int,
        kind: EntityKind,
        github: GitHub,
        github_issues: GitHubIssues,
        repo_root: Path,
    ) -> None: ...

    @property
    def number(self) -> int: ...

    @property
    def kind(self) -> EntityKind: ...

    @property
    def state(self) -> EntityState: ...

    @property
    def log(self) -> EntityLog: ...
```

Constructor takes both `GitHub` and `GitHubIssues` gateways because:
- Issues use `github_issues.update_issue_body()` for body writes
- PRs use `github.update_pr_body()` for body writes
- Both use `github_issues.add_comment()` / `get_issue_comments()` for comments (PRs are issues on GitHub)

### EntityState (`state.py`)

```python
class EntityState:
    """Mutable KV metadata stored in the entity body.

    Each operation does a full read-modify-write cycle to GitHub.
    Use `update()` to batch multiple field changes in one round-trip.
    """

    def get(self, key: str) -> dict[str, Any] | None:
        """Get a metadata block by key. Returns None if not found."""

    def get_field(self, key: str, field: str) -> Any | None:
        """Get a single field from a metadata block."""

    def has(self, key: str) -> bool:
        """Check if a metadata block exists in the body."""

    def set(
        self,
        key: str,
        data: dict[str, Any],
        *,
        schema: MetadataBlockSchema | None,
    ) -> None:
        """Set an entire metadata block. Creates or replaces."""

    def set_field(self, key: str, field: str, value: Any) -> None:
        """Update a single field in a metadata block (read-modify-write)."""

    def update(self, key: str, fields: dict[str, Any]) -> None:
        """Update multiple fields in one round-trip (read-modify-write)."""
```

Internal implementation:
- `_fetch_body()` → calls gateway to get current body text
- `_push_body(body)` → calls gateway to write updated body
- `get`/`get_field`/`has` → `_fetch_body()` + `find_metadata_block()` from core.py
- `set` → `_fetch_body()` + `render_metadata_block()` + `replace_metadata_block_in_body()` + `_push_body()`
- `set_field`/`update` → `_fetch_body()` + parse + modify dict + render + replace + `_push_body()`
- `_fetch_body()` and `_push_body()` dispatch on `EntityKind` (issue vs PR)

### EntityLog (`log.py`)

```python
class EntityLog:
    """Immutable append-only log stored as comments.

    Each entry is a GitHub comment containing a metadata block.
    Entries are never modified after creation.
    """

    def append(
        self,
        key: str,
        data: dict[str, Any],
        *,
        title: str,
        description: str,
        schema: MetadataBlockSchema | None,
    ) -> int:
        """Append a structured log entry. Returns comment ID."""

    def append_content(
        self,
        key: str,
        content: str,
        *,
        title: str,
    ) -> int:
        """Append a raw markdown content entry (e.g., plan-body, objective-body).
        Returns comment ID."""

    def entries(self, key: str) -> list[LogEntry]:
        """Get all log entries with a given key, in chronological order."""

    def latest(self, key: str) -> LogEntry | None:
        """Get the most recent entry with a given key."""

    def all_entries(self) -> list[LogEntry]:
        """Get all log entries across all keys."""
```

Internal implementation:
- `append` → `create_metadata_block()` + `render_erk_issue_event()` + `github_issues.add_comment()`
- `append_content` → uses content-specific rendering (like `render_plan_body_block` / `render_objective_body_block`) + `github_issues.add_comment()`
- `entries`/`latest`/`all_entries` → `github_issues.get_issue_comments()` + `parse_metadata_blocks()` on each comment

## Implementation Steps

### Step 1: Create module structure and types
- Create `packages/erk-shared/src/erk_shared/entity_store/` directory
- Write `__init__.py` (empty), `types.py` with `EntityKind` and `LogEntry`

### Step 2: Implement EntityState
- Create `state.py` with `EntityState` class
- Implement `_fetch_body()` / `_push_body()` dispatching on EntityKind
- Implement `get`, `get_field`, `has` (read-only operations)
- Implement `set`, `set_field`, `update` (read-modify-write operations)
- Uses existing `find_metadata_block`, `render_metadata_block`, `replace_metadata_block_in_body` from `metadata.core`

### Step 3: Implement EntityLog
- Create `log.py` with `EntityLog` class
- Implement `append` using `create_metadata_block` + `render_erk_issue_event`
- Implement `append_content` for raw markdown blocks
- Implement `entries`, `latest`, `all_entries` using comment parsing

### Step 4: Implement GitHubEntity
- Create `entity.py` with `GitHubEntity` class
- Wire up `state` and `log` properties

### Step 5: Write comprehensive tests
- Test with `FakeGitHub` / `FakeGitHubIssues` (no real API calls)
- Round-trip tests: `state.set()` → `state.get()`
- Multi-key tests: multiple blocks in same body
- Field-level tests: `state.set_field()` → `state.get_field()`
- Log tests: `log.append()` → `log.entries()` → `log.latest()`
- Content log tests: `log.append_content()` for plan-body/objective-body
- Issue vs PR dispatch tests: verify correct gateway methods called
- Error cases: get on nonexistent key returns None, set_field on missing block

### Step 6: Proof-of-concept caller migration
- Migrate `status_history.py` to use `EntityLog.entries()` instead of manual comment parsing
- This is a clean, isolated caller (pure read of log entries) that validates the log API

## Key Files to Modify

**New files:**
- `packages/erk-shared/src/erk_shared/entity_store/__init__.py`
- `packages/erk-shared/src/erk_shared/entity_store/types.py`
- `packages/erk-shared/src/erk_shared/entity_store/state.py`
- `packages/erk-shared/src/erk_shared/entity_store/log.py`
- `packages/erk-shared/src/erk_shared/entity_store/entity.py`
- `tests/unit/entity_store/test_entity_state.py`
- `tests/unit/entity_store/test_entity_log.py`
- `tests/unit/entity_store/test_github_entity.py`

**Existing files reused (not modified):**
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py` — parsing/rendering internals
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/types.py` — MetadataBlock, MetadataBlockSchema
- `packages/erk-shared/src/erk_shared/gateway/github/abc.py` — GitHub gateway ABC
- `packages/erk-shared/src/erk_shared/gateway/github/issues/abc.py` — GitHubIssues ABC

**Modified for proof-of-concept migration (Step 6):**
- `packages/erk-shared/src/erk_shared/gateway/github/status_history.py`

## Design Decisions

1. **No caching.** Every `get`/`set` hits the gateway. Matches current behavior. Caching can be added later if needed.
2. **Gateway-connected, not string-based.** The store owns the read-modify-write cycle. Callers don't touch raw body strings.
3. **Both gateways required.** Constructor takes `GitHub` + `GitHubIssues` because issue body updates go through `GitHubIssues` while PR body updates go through `GitHub`. This matches the existing gateway split.
4. **Schemas remain optional.** `set()` accepts an optional schema for validation, same as today's `create_metadata_block()`. The store doesn't enforce schemas — callers opt in.
5. **Content blocks use `append_content`.** Raw markdown blocks (plan-body, objective-body) get a separate method since they use different rendering than YAML blocks.
6. **No plan-header collapse yet.** The 42 accessor functions in `plan_header.py` can be migrated to use `state.get_field()` / `state.update()` in a follow-up PR. This PR just builds the foundation.

## Future Migration Path

- **Phase 2:** Migrate remaining callers (one PR per domain: objectives, dispatch, exec scripts)
- **Phase 3:** Refactor `PlanBackend` to use `GitHubEntity` internally
- **Phase 4:** Collapse `plan_header.py` — its 42 functions become `entity.state.get_field("plan-header", field)` / `entity.state.update("plan-header", {field: value})`

## Verification

1. Run unit tests: `pytest tests/unit/entity_store/ -v`
2. Run type checker: `ty check packages/erk-shared/src/erk_shared/entity_store/`
3. Run existing metadata tests to confirm no regressions: `pytest tests/unit/gateways/github/metadata_blocks/ -v`
4. Run status_history tests after migration: `pytest tests/shared/github/test_status_history.py -v`
5. Full CI: `make fast-ci`
