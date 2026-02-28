---
name: immutable-entities
description: >
  Use when designing domain objects that wrap external state (GitHub issues, PRs,
  metadata), creating entity store patterns, or adding methods to dataclasses.
  Ensures objects are immutable snapshots without gateway references, with mutations
  as standalone functions.
---

# Immutable Entities

## Mental Model

**Remove time from identity.** An entity object IS the state at one moment. It does not track changes, subscribe to updates, or hold connections to where the data came from. When you need to mutate, a standalone function takes the old snapshot plus gateways, executes I/O, and returns a new snapshot representing the next moment.

This separation makes objects trivially testable (construct with literals), safely cacheable (`@cached_property` works because data never changes), and composable (pass snapshots freely without dragging gateway dependencies along).

## Core Rules

1. **Objects are read-only snapshots.** Use `@dataclass(frozen=True)` or an effectively immutable class (private backing fields, no setters). Once constructed, the object never changes.

2. **No gateway references on entities.** Entities hold only data. Gateway objects (`GitHub`, `GitHubIssues`, file-system `Path`) are never stored as fields — they are passed to standalone functions that need them.

3. **Mutations are standalone functions.** Signature: `(snapshot, ..., *, gateways) -> new_snapshot`. The function takes the old snapshot as the first positional argument, gateways as keyword-only arguments, executes the I/O, and returns a fresh snapshot.

4. **Cheap reconstruction / time-stepping.** Creating a new snapshot with updated data is a simple constructor call — not a re-fetch. The mutation function constructs the return value from known data, not by re-reading from the source.

5. **`@cached_property` is safe** because data never changes. Use it for expensive parsing or derived computations that should run at most once.

6. **Network calls never inside objects.** No method or property on an entity may perform I/O. All I/O lives in factory classmethods or standalone functions.

7. **Factory classmethods for construction requiring I/O.** `@classmethod create()` takes gateways, fetches data, and returns a frozen instance. The regular `__init__` takes only pure data.

## Canonical Examples

All examples from `packages/erk-shared/src/erk_shared/entity_store/`.

### Frozen Dataclass with Read Methods — `EntityState`

Read operations are methods on the dataclass. Write operations are standalone functions.

```python
# state.py

@dataclass(frozen=True)
class EntityState:
    """KV metadata snapshot stored in the entity body."""

    number: int
    kind: EntityKind
    body: str

    def get(self, key: str) -> dict[str, Any] | None:
        """Get a metadata block by key. Returns None if not found."""
        block = find_metadata_block(self.body, key)
        if block is None:
            return None
        return block.data

    def has(self, key: str) -> bool:
        """Check if a metadata block exists in the body."""
        return find_metadata_block(self.body, key) is not None
```

### Standalone Mutation Function — `entity_state_set()`

Takes old snapshot + gateways in, returns new snapshot out.

```python
# state.py

def entity_state_set(
    state: EntityState,
    key: str,
    data: dict[str, Any],
    *,
    schema: MetadataBlockSchema,
    github: GitHub,
    github_issues: GitHubIssues,
    repo_root: Path,
) -> EntityState:
    """Set an entire metadata block. Creates or replaces. Returns new state."""
    block = create_metadata_block(key, data, schema=schema)
    rendered = render_metadata_block(block)
    body = state.body

    existing = find_metadata_block(body, key)
    if existing is not None:
        new_body = replace_metadata_block_in_body(body, key, rendered)
    else:
        new_body = (body.rstrip() + "\n\n" + rendered) if body.strip() else rendered

    push_entity_body(
        number=state.number,
        kind=state.kind,
        body=new_body,
        github=github,
        github_issues=github_issues,
        repo_root=repo_root,
    )
    return EntityState(number=state.number, kind=state.kind, body=new_body)
```

### Effectively Immutable Class with `@cached_property` — `EntityLog`

Not a `@dataclass` because `cached_property` is incompatible with `frozen=True` (slots block attribute setting). Uses private backing fields instead.

```python
# log.py

class EntityLog:
    """Immutable append-only log stored as comments."""

    def __init__(self, *, comment_bodies: list[str]) -> None:
        self._comment_bodies = comment_bodies

    def entries(self, key: str) -> list[LogEntry]:
        """Get all log entries with a given key, in chronological order."""
        return [entry for entry in self.all_entries if entry.key == key]

    def latest(self, key: str) -> LogEntry | None:
        """Get the most recent entry with a given key."""
        matching = self.entries(key)
        if not matching:
            return None
        return matching[-1]

    @cached_property
    def all_entries(self) -> list[LogEntry]:
        """Parse all comments once on first access, then memoize."""
        entries: list[LogEntry] = []
        for index, comment_body in enumerate(self._comment_bodies):
            result = parse_metadata_blocks(comment_body)
            for block in result.blocks:
                entries.append(
                    LogEntry(key=block.key, data=block.data, comment_id=index)
                )
        return entries
```

### Factory Classmethod — `GitHubEntity.create()`

`__init__` takes only pure data. `create()` does all I/O and returns a frozen instance.

```python
# entity.py

@dataclass(frozen=True)
class GitHubEntity:
    """A GitHub issue or PR with structured metadata and event log."""

    number: int
    kind: EntityKind
    state: EntityState
    log: EntityLog

    @classmethod
    def create(
        cls,
        *,
        number: int,
        kind: EntityKind,
        github: GitHub,
        github_issues: GitHubIssues,
        repo_root: Path,
    ) -> "GitHubEntity":
        """Build a GitHubEntity by fetching state body and comment bodies."""
        body = fetch_entity_body(
            number=number, kind=kind,
            github=github, github_issues=github_issues, repo_root=repo_root,
        )
        state = EntityState(number=number, kind=kind, body=body)
        comment_bodies = github_issues.get_issue_comments(repo_root, number)
        log = EntityLog(comment_bodies=comment_bodies)
        return cls(number=number, kind=kind, state=state, log=log)
```

## Anti-Patterns

### Gateway field on a dataclass

```python
# BAD: entity holds a gateway reference
@dataclass(frozen=True)
class Issue:
    number: int
    github: GitHub  # Drags dependency everywhere the object goes

# GOOD: entity holds only data
@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    body: str
```

### Network call in a property/method

```python
# BAD: I/O hidden inside a property
class Issue:
    @property
    def comments(self) -> list[str]:
        return self.github.get_comments(self.number)  # Network call!

# GOOD: data provided at construction time
@dataclass(frozen=True)
class Issue:
    number: int
    comment_bodies: list[str]  # Already fetched
```

### Mutation method on a read-only object

```python
# BAD: mutation lives on the entity
@dataclass(frozen=True)
class EntityState:
    body: str

    def set_metadata(self, key: str, data: dict, *, github: GitHub) -> "EntityState":
        ...  # Gateway passed into the object's method

# GOOD: mutation is a standalone function
def entity_state_set(
    state: EntityState,
    key: str,
    data: dict[str, Any],
    *,
    github: GitHub,
    github_issues: GitHubIssues,
    repo_root: Path,
) -> EntityState:
    ...  # Entity is just an argument, not the owner
```

### Returning `self` from a mutation

```python
# BAD: pretends to be immutable but mutates in place
def update(self, body: str) -> "EntityState":
    object.__setattr__(self, "body", body)  # Bypasses frozen!
    return self

# GOOD: returns a genuinely new object
def entity_state_set(...) -> EntityState:
    ...
    return EntityState(number=state.number, kind=state.kind, body=new_body)
```

### Re-fetching data inside a read method

```python
# BAD: read method performs I/O to get fresh data
class EntityState:
    def get(self, key: str, *, github: GitHub) -> dict | None:
        fresh_body = github.get_issue_body(self.number)  # Re-fetch!
        return find_metadata_block(fresh_body, key)

# GOOD: read method uses the snapshot's data
@dataclass(frozen=True)
class EntityState:
    body: str

    def get(self, key: str) -> dict[str, Any] | None:
        block = find_metadata_block(self.body, key)  # Uses snapshot data
        if block is None:
            return None
        return block.data
```
