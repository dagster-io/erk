# Gateway Layer Architecture

**Read this when**: You need to understand or modify the gateway layer (the thin wrapper interfaces over external state).

## Overview

**Naming note**: "Gateway" is a common name for this pattern. These classes are also called **adapters**, **providers**, or **ports** in other contexts. The pattern matters more than the name.

## What Are Gateway Classes?

**Gateway classes are thin wrappers around heavyweight external APIs** that:

- Touch external state (filesystem, database, APIs, message queues)
- Could be slow (network calls, disk I/O, subprocess execution)
- Could fail periodically (network issues, rate limits, service outages)
- Are difficult to test directly

## The Four Implementations

Every gateway interface has **four implementations**:

### 1. Abstract Interface (ABC)

Defines the contract all implementations must follow.

**Example**: `DatabaseGateway` (`src/myapp/gateways/database.py`)

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

class DatabaseGateway(ABC):
    """Thin wrapper over database operations."""

    @abstractmethod
    def query(self, sql: str, *, timeout: float | None = None) -> list[dict[str, Any]]:
        """Execute a SELECT query."""

    @abstractmethod
    def execute(self, sql: str) -> None:
        """Execute an INSERT, UPDATE, or DELETE."""

    @abstractmethod
    def transaction(self) -> "TransactionContext":
        """Start a database transaction."""

    # ... more methods
```

**Key characteristics**:

- Uses `ABC` (not `Protocol`)
- All methods are `@abstractmethod`
- Contains ONLY runtime operations (no test setup methods)
- May have concrete helper methods (all implementations inherit)

### 2. Real Implementation

Calls actual external systems (database, filesystem, API).

**Example**: `RealDatabaseGateway` (`src/myapp/gateways/database.py`)

```python
import psycopg2
from contextlib import contextmanager

class RealDatabaseGateway(DatabaseGateway):
    """Real database operations via psycopg2."""

    def __init__(self, connection_string: str) -> None:
        self.connection_string = connection_string

    def query(self, sql: str, *, timeout: float | None = None) -> list[dict[str, Any]]:
        """Execute SELECT query against PostgreSQL."""
        conn = psycopg2.connect(
            self.connection_string,
            options=f"-c statement_timeout={int(timeout * 1000)}" if timeout else ""
        )

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()

    def execute(self, sql: str) -> None:
        """Execute INSERT/UPDATE/DELETE against PostgreSQL."""
        conn = psycopg2.connect(self.connection_string)

        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    @contextmanager
    def transaction(self):
        """Transaction context manager."""
        conn = psycopg2.connect(self.connection_string)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
```

**Key characteristics**:

- Uses real libraries (`psycopg2`, `requests`, `boto3`, etc.)
- Handles connection management
- LBYL: checks conditions before operations
- Lets exceptions bubble up (no try/except for control flow)

### 3. Fake Implementation

In-memory simulation for fast testing.

**Example**: `FakeDatabaseGateway` (`tests/fakes/database.py`)

```python
from typing import Any
from contextlib import contextmanager

class FakeDatabaseGateway(DatabaseGateway):
    """In-memory database simulation for testing."""

    def __init__(
        self,
        *,
        initial_data: dict[str, list[dict]] | None = None,
        should_fail_on: list[str] | None = None,
    ) -> None:
        # Mutable state (private)
        self._tables: dict[str, list[dict]] = initial_data or {}
        self._should_fail_on = should_fail_on or []
        self._in_transaction = False

        # Mutation tracking (private, accessed via properties)
        self._executed_queries: list[str] = []
        self._executed_commands: list[str] = []
        self._transaction_count = 0

    def query(self, sql: str, *, timeout: float | None = None) -> list[dict[str, Any]]:
        """Return in-memory data."""
        # Simulate failure if configured
        if any(pattern in sql for pattern in self._should_fail_on):
            raise RuntimeError(f"Simulated failure for: {sql}")

        # Track operation
        self._executed_queries.append(sql)

        # Parse table name (simplified)
        if "FROM" in sql:
            table = sql.split("FROM")[1].split()[0].strip()
            return self._tables.get(table, []).copy()
        return []

    def execute(self, sql: str) -> None:
        """Update in-memory state."""
        # Track operation
        self._executed_commands.append(sql)

        # Simulate INSERT (simplified parsing)
        if sql.startswith("INSERT INTO"):
            # Extract table and values (simplified)
            parts = sql.split()
            table = parts[2]
            if table not in self._tables:
                self._tables[table] = []
            # Add dummy record
            self._tables[table].append({"id": len(self._tables[table]) + 1})

        # Simulate DELETE (simplified)
        elif sql.startswith("DELETE FROM"):
            parts = sql.split()
            table = parts[2]
            if table in self._tables:
                self._tables[table] = []

    @contextmanager
    def transaction(self):
        """Simulated transaction."""
        self._in_transaction = True
        self._transaction_count += 1
        try:
            yield self
        finally:
            self._in_transaction = False

    @property
    def executed_queries(self) -> list[str]:
        """Read-only access for test assertions."""
        return self._executed_queries.copy()

    @property
    def executed_commands(self) -> list[str]:
        """Read-only access for test assertions."""
        return self._executed_commands.copy()

    @property
    def transaction_count(self) -> int:
        """Read-only access for test assertions."""
        return self._transaction_count
```

**Key characteristics**:

- **Constructor injection**: All initial state via keyword arguments
- **In-memory storage**: Dictionaries, lists for state
- **Mutation tracking**: Read-only properties for assertions
- **Fast**: No I/O, no network calls
- **Simulation**: May mimic real behavior (e.g., checking constraints)

**Mutation tracking pattern**:

```python
# In test:
fake_db = FakeDatabaseGateway()
fake_db.execute("INSERT INTO users VALUES (...)")

# Assert operation was called
assert "INSERT INTO users" in fake_db.executed_commands[0]
```

### 4. Dry-Run Wrapper

Intercepts write operations, delegates reads.

**Example**: `DryRunDatabaseGateway` (`src/myapp/gateways/database.py`)

```python
class DryRunDatabaseGateway(DatabaseGateway):
    """Wrapper that prints instead of executing writes."""

    def __init__(self, gateway: DatabaseGateway) -> None:
        self._gateway = gateway  # Wrap any DatabaseGateway implementation

    def query(self, sql: str, *, timeout: float | None = None) -> list[dict[str, Any]]:
        """Delegate read operation."""
        return self._gateway.query(sql, timeout=timeout)

    def execute(self, sql: str) -> None:
        """Print instead of executing."""
        print(f"[DRY RUN] Would execute: {sql}")
        # Does NOT call self._gateway.execute()

    @contextmanager
    def transaction(self):
        """Print transaction operations."""
        print("[DRY RUN] Would start transaction")
        yield self  # Yield self so operations within use dry-run
        print("[DRY RUN] Would commit transaction")
```

**Key characteristics**:

- **Wrapper pattern**: Accepts any gateway implementation
- **Read operations**: Delegate to wrapped implementation
- **Write operations**: Print `[DRY RUN]` message, don't execute
- **Testing**: Verify operations are intercepted correctly

## Common Gateway Types

### API Client Gateway

```python
class ApiClient(ABC):
    """Gateway for external API calls."""

    @abstractmethod
    def get(self, endpoint: str, *, params: dict | None = None) -> dict:
        """GET request to API."""

    @abstractmethod
    def post(self, endpoint: str, *, json: dict) -> dict:
        """POST request to API."""

class RealApiClient(ApiClient):
    """Real HTTP client using requests."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def get(self, endpoint: str, *, params: dict | None = None) -> dict:
        import requests
        response = requests.get(
            f"{self.base_url}{endpoint}",
            params=params,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

class FakeApiClient(ApiClient):
    """Fake API client for testing."""

    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.requested_endpoints: list[str] = []

    def get(self, endpoint: str, *, params: dict | None = None) -> dict:
        self.requested_endpoints.append(endpoint)
        return self.responses.get(endpoint, {})
```

### File System Gateway

```python
class FileSystemGateway(ABC):
    """Gateway for file system operations."""

    @abstractmethod
    def read_file(self, path: Path) -> str:
        """Read file contents."""

    @abstractmethod
    def write_file(self, path: Path, content: str) -> None:
        """Write file contents."""

    @abstractmethod
    def exists(self, path: Path) -> bool:
        """Check if path exists."""

class RealFileSystemGateway(FileSystemGateway):
    """Real file system operations."""

    def read_file(self, path: Path) -> str:
        if path.exists():
            return path.read_text(encoding="utf-8")
        raise FileNotFoundError(f"File not found: {path}")

    def write_file(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def exists(self, path: Path) -> bool:
        return path.exists()

class FakeFileSystemGateway(FileSystemGateway):
    """In-memory file system for testing."""

    def __init__(self) -> None:
        self._files: dict[str, str] = {}

    def read_file(self, path: Path) -> str:
        key = str(path)
        if key in self._files:
            return self._files[key]
        raise FileNotFoundError(f"File not found: {path}")

    def write_file(self, path: Path, content: str) -> None:
        self._files[str(path)] = content

    def exists(self, path: Path) -> bool:
        return str(path) in self._files
```

### Message Queue Gateway

```python
class MessageQueueGateway(ABC):
    """Gateway for message queue operations."""

    @abstractmethod
    def publish(self, topic: str, message: dict) -> None:
        """Publish message to topic."""

    @abstractmethod
    def subscribe(self, topic: str) -> Generator[dict, None, None]:
        """Subscribe to topic messages."""

class FakeMessageQueue(MessageQueueGateway):
    """In-memory message queue for testing."""

    def __init__(self) -> None:
        self._queues: dict[str, list[dict]] = {}
        self._published_messages: list[tuple[str, dict]] = []

    def publish(self, topic: str, message: dict) -> None:
        if topic not in self._queues:
            self._queues[topic] = []
        self._queues[topic].append(message)
        self._published_messages.append((topic, message))

    def subscribe(self, topic: str) -> Generator[dict, None, None]:
        queue = self._queues.get(topic, [])
        while queue:
            yield queue.pop(0)

    @property
    def published_messages(self) -> list[tuple[str, dict]]:
        """For test assertions."""
        return self._published_messages.copy()
```

## When to Add/Change Gateway Methods

### Adding a Method

**If you need to add a method to a gateway interface:**

1. Add `@abstractmethod` to ABC interface
2. Implement in real class with actual I/O
3. Implement in fake class with in-memory state
4. Add handler in dry-run wrapper
5. Write unit test of fake implementation
6. Write integration test of real implementation

### Changing an Interface

**If you need to change an interface:**

- Update all four implementations above
- Update all tests that use the changed method
- Update any business logic that calls the method

## Design Principles

### Keep Gateways Thin

**Gateways should NOT contain business logic**. Push complexity to the business layer.

```python
# ❌ WRONG: Business logic in gateway class
class RealDatabaseGateway(DatabaseGateway):
    def get_active_users_with_recent_orders(self) -> list[dict]:
        """Complex logic to find users."""
        users = self.query("SELECT * FROM users WHERE active = true")
        result = []
        for user in users:
            orders = self.query(f"SELECT * FROM orders WHERE user_id = {user['id']}")
            if any(o['created_at'] > datetime.now() - timedelta(days=30) for o in orders):
                result.append(user)
        return result

# ✅ CORRECT: Thin gateway, logic in business layer
class RealDatabaseGateway(DatabaseGateway):
    def query(self, sql: str) -> list[dict[str, Any]]:
        """Just wrap database query."""
        conn = psycopg2.connect(self.connection_string)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]

# Business logic layer:
class UserService:
    def get_active_users_with_recent_orders(self) -> list[User]:
        """Complex logic over thin gateway."""
        users = self.database.query("SELECT * FROM users WHERE active = true")
        result = []
        for user in users:
            orders = self.database.query(f"SELECT * FROM orders WHERE user_id = {user['id']}")
            if any(o['created_at'] > datetime.now() - timedelta(days=30) for o in orders):
                result.append(User.from_dict(user))
        return result
```

**Why**: Thin gateways are easier to fake, easier to test, easier to understand.

### Fakes Should Be In-Memory

**Fakes should avoid I/O operations** (except minimal directory creation when testing file operations).

```python
# ❌ WRONG: Fake performs I/O
class FakeFileSystem(FileSystemGateway):
    def read_file(self, path: Path) -> str:
        # Reading real files defeats the purpose of fakes!
        return path.read_text()

# ✅ CORRECT: Fake uses in-memory state
class FakeFileSystem(FileSystemGateway):
    def __init__(self) -> None:
        self._files: dict[str, str] = {}

    def read_file(self, path: Path) -> str:
        key = str(path)
        if key in self._files:
            return self._files[key]
        raise FileNotFoundError(f"File not found: {path}")
```

**Exception**: Fakes may create real directories when necessary for integration, but should not read/write actual files.

## Related Documentation

- `testing-strategy.md` - How to test gateway classes at different layers
- `workflows.md` - Step-by-step guide for adding gateway methods
- `patterns.md` - Constructor injection and mutation tracking patterns
- `anti-patterns.md` - What to avoid in gateway design
