---
name: fake-driven-testing-anti-patterns
description: Common testing mistakes to avoid
---

# Testing Anti-Patterns

**Read this when**: You're unsure if your approach is correct, or want to avoid common mistakes.

## Overview

This document covers common anti-patterns in Python testing and how to avoid them. Each anti-pattern includes examples of what NOT to do and the correct approach.

## ❌ Testing Speculative Features

**NEVER write tests for code that doesn't exist yet** (unless doing TDD RIGHT NOW).

### Wrong Approach

```python
# ❌ WRONG: Placeholder test for future feature
# def test_feature_we_might_add_later():
#     """TODO: Implement this feature next sprint."""
#     pass

# ❌ WRONG: Test stub for "maybe someday" idea
# def test_hypothetical_feature():
#     """Feature we're considering for Q2."""
#     # Not implemented yet, just a placeholder
#     pass
```

### Correct Approach

```python
# ✅ CORRECT: TDD for feature being implemented NOW
def test_new_feature_im_building_today():
    """Test for feature I'm about to implement."""
    result = process_payment(card="4111111111111111", amount=100.00)
    assert result.status == "success"  # Will implement after this test

# ✅ CORRECT: Test for actively worked bug fix
def test_bug_123_is_fixed():
    """Regression test for bug I'm fixing right now."""
    # Reproducing bug, then will fix it
    ...
```

### Why This Is Wrong

**Problems with speculative tests**:

- **Maintenance burden**: Tests need updating when feature changes
- **False confidence**: Test suite looks comprehensive but validates nothing
- **Wasted effort**: Planned features often change significantly before implementation
- **Stale code**: Commented-out tests clutter codebase

**Rule**: Only write tests for code being **actively implemented or fixed in this work session**.

### TDD Is Explicitly Allowed

**TDD workflow is encouraged**:

1. Write failing test for feature you're about to implement
2. Implement feature
3. Test passes

This is NOT speculative because you're implementing NOW, not "maybe later."

---

## ❌ Wrong Test Categorization (Unit vs Integration)

**CRITICAL: Tests MUST be categorized correctly to maintain CI performance**.

### Test Categorization Rules

🔴 **A test MUST be categorized as an integration test if:**

1. **It invokes a subprocess** - Any test that calls `subprocess.run()`, `subprocess.Popen()`, or similar
2. **It uses `time.sleep()`** - Tests that rely on actual timing delays (must use mocking or DI instead)
3. **It performs extensive real filesystem I/O** - Tests that interact with external filesystem locations, create many files, or depend on actual filesystem behavior (limited file I/O with `isolated_filesystem()` or `tmp_path` in unit tests is acceptable)
4. **It tests subprocess boundaries** - Tests validating that abstraction layers correctly wrap external tools

### Location Rules

- **Unit tests** → `tests/unit/`, `tests/commands/`, `tests/core/`
  - Use fakes (FakeGit, FakeShell, etc.)
  - Use `CliRunner` (NOT subprocess)
  - No `time.sleep()` calls
  - Fast, in-memory execution

- **Integration tests** → `tests/integration/`
  - Use real implementations (RealGit, etc.)
  - May invoke subprocess calls
  - May use `tmp_path` fixture for real directories
  - Slower, tests external tool integration

### Wrong Approach

```python
# ❌ WRONG - Unit test location with subprocess call
# Located in tests/commands/test_sync.py
def test_sync_calls_git() -> None:
    result = subprocess.run(["git", "fetch"], capture_output=True)
    # This MUST be moved to tests/integration/

# ❌ WRONG - Unit test with time.sleep()
# Located in tests/unit/test_retry.py
def test_retry_with_backoff() -> None:
    time.sleep(0.5)  # Actual delay
    # This MUST be moved to tests/integration/ OR use mocking
```

### Correct Approach

```python
# ✅ CORRECT - Integration test with subprocess
# Located in tests/integration/test_real_git.py
def test_real_git_fetch(tmp_path: Path) -> None:
    result = subprocess.run(["git", "fetch"], cwd=tmp_path, capture_output=True)
    assert result.returncode == 0

# ✅ CORRECT - Unit test with mocked sleep
# Located in tests/unit/test_retry.py
def test_retry_with_backoff(monkeypatch) -> None:
    mock_sleep = Mock()
    monkeypatch.setattr("time.sleep", mock_sleep)
    # Test logic without actual delay
```

### Why This Matters

- **CI performance**: Unit tests must remain fast (<2s total) for quick feedback
- **Test reliability**: Subprocess calls can fail due to environment differences
- **Parallel execution**: Tests with subprocesses may have race conditions
- **Resource usage**: Subprocess tests consume more system resources

**Rule**: If unsure, default to integration test. It's safer to categorize a test as integration than to slow down the unit test suite.

---

## ❌ Hardcoded Paths in Tests (CATASTROPHIC)

**NEVER use hardcoded paths in tests**. Always use fixtures.

### Wrong Approach

```python
# ❌ WRONG - CATASTROPHICALLY DANGEROUS
def test_something():
    service = FileService(base_path=Path("/test/default/path"))
    service.process_files()

def test_another_thing():
    db = DatabaseAdapter(data_dir=Path("/var/lib/myapp/test"))
    db.initialize()

def test_with_absolute_path():
    config_path = Path("/Users/someone/test/config.yaml")
    # Code may write files to this path!
    config = load_config(config_path)
```

### Correct Approach

```python
# ✅ CORRECT - Use tmp_path fixture
def test_something(tmp_path: Path):
    service = FileService(base_path=tmp_path)
    service.process_files()

# ✅ CORRECT - Use temporary directory
def test_another_thing(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db = DatabaseAdapter(data_dir=data_dir)
    db.initialize()

# ✅ CORRECT - Create config in tmp_path
def test_with_config(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("debug: true")
    config = load_config(config_path)
```

### Why This Is Catastrophic

**Dangers of hardcoded paths**:

1. **Global config mutation**: Code may write config files at hardcoded paths, polluting real filesystem
2. **False isolation**: Tests appear isolated but share state through hardcoded paths
3. **Security risk**: Creating files at system paths can be exploited
4. **CI/CD failures**: Paths may not exist on CI systems
5. **Permission errors**: Tests may not have write access to hardcoded paths

**Detection**: **If you see `Path("/` in test code, STOP and use fixtures.**

---

## ❌ Not Updating All Layers When Interface Changes

**When changing an integration class interface, you MUST update ALL four implementations.**

### Wrong Approach

```python
# You changed DatabaseAdapter.query() signature:

# 1. DatabaseAdapter (ABC) ✅ Updated
class DatabaseAdapter(ABC):
    @abstractmethod
    def query(self, sql: str, *, timeout: float = 30.0) -> list[dict]:
        ...

# 2. RealDatabaseAdapter ✅ Updated
class RealDatabaseAdapter(DatabaseAdapter):
    def query(self, sql: str, *, timeout: float = 30.0) -> list[dict]:
        # Updated implementation
        ...

# 3. FakeDatabaseAdapter ❌ FORGOT TO UPDATE!
class FakeDatabaseAdapter(DatabaseAdapter):
    def query(self, sql: str) -> list[dict]:
        # Old signature - type error!
        ...

# 4. DryRunDatabaseAdapter ❌ FORGOT TO UPDATE!
class DryRunDatabaseAdapter(DatabaseAdapter):
    def query(self, sql: str) -> list[dict]:
        # Old signature - type error!
        ...

# Result: Type errors, broken tests, runtime failures
```

### Correct Approach

**Use this checklist when changing an interface**:

- [ ] Update ABC interface (e.g., `DatabaseAdapter`)
- [ ] Update real implementation (e.g., `RealDatabaseAdapter`)
- [ ] Update fake implementation (e.g., `FakeDatabaseAdapter`)
- [ ] Update dry-run wrapper (e.g., `DryRunDatabaseAdapter`)
- [ ] Update all call sites in business logic
- [ ] Update unit tests of fake
- [ ] Update integration tests of real
- [ ] Update business logic tests that use the method

**Tool**: Run `mypy` or `ty check` to catch signature mismatches.

### Why This Is Wrong

**Problems**:

- **Type errors**: Implementations don't match interface
- **Runtime errors**: Tests pass locally but fail in production
- **Inconsistent behavior**: Different implementations have different behavior
- **Broken tests**: Tests expect old signature

**Rule**: When changing interface, update ALL implementation layers (ABC, Real, Fake, DryRun) + tests.

---

## ❌ Using subprocess in Unit Tests

**Use test clients and CliRunner for testing, NOT subprocess**.

### Wrong Approach

```python
# ❌ WRONG: Slow, harder to debug
def test_cli_command():
    result = subprocess.run(
        ["python", "-m", "myapp", "process", "--file", "data.csv"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "processed" in result.stdout

# ❌ WRONG: Even worse - shell=True
def test_another_command():
    result = subprocess.run(
        "myapp process --file data.csv",
        shell=True,
        capture_output=True,
    )
    assert result.returncode == 0
```

### Correct Approach

```python
# ✅ CORRECT: Fast, better error messages (for Click CLIs)
from click.testing import CliRunner

def test_cli_command(tmp_path: Path):
    runner = CliRunner()
    data_file = tmp_path / "data.csv"
    data_file.write_text("id,name\n1,Alice")

    result = runner.invoke(process_cmd, ["--file", str(data_file)])

    assert result.exit_code == 0
    assert "processed" in result.output

# ✅ CORRECT: For Flask apps
def test_flask_endpoint(client):
    response = client.post("/process", json={"file": "data.csv"})
    assert response.status_code == 200

# ✅ CORRECT: For FastAPI apps
def test_fastapi_endpoint(client):
    response = client.post("/process", json={"file": "data.csv"})
    assert response.status_code == 200
```

### Why This Is Wrong

**Performance**:

- **Test client/CliRunner**: milliseconds per test (~10ms)
- **subprocess**: seconds per test (~1s)
- **~100x slower** with subprocess

**Debugging**:

- subprocess: Harder to set breakpoints, unclear errors
- Test clients: Direct access to exceptions, clear stack traces

**Reliability**:

- subprocess: Shell interpretation issues, PATH dependencies
- Test clients: Direct Python invocation, no shell quirks

**Rule**: Always use appropriate test clients. Only use subprocess for true end-to-end integration tests (Layer 5).

---

## ❌ Complex Logic in Integration class Classes

**Integration classes should be THIN wrappers**. Push complexity to business logic layer.

### Wrong Approach

```python
# ❌ WRONG: Business logic in adapter class
class RealDatabaseAdapter(DatabaseAdapter):
    def get_premium_users_with_expired_subscriptions(self) -> list[dict]:
        """Complex logic to find specific users."""
        users = self.query("SELECT * FROM users WHERE premium = true")

        # 50 lines of complex business logic...
        result = []
        for user in users:
            subscriptions = self.query(
                f"SELECT * FROM subscriptions WHERE user_id = {user['id']}"
            )

            # Complex date calculations
            for sub in subscriptions:
                end_date = datetime.fromisoformat(sub['end_date'])
                grace_period = timedelta(days=7)
                if end_date + grace_period < datetime.now():
                    # More complex logic...
                    if self._should_include_user(user, sub):
                        result.append(user)

        return result

    def _should_include_user(self, user: dict, sub: dict) -> bool:
        # Even more business logic...
        return True
```

**Problems**:

- Hard to fake (complex logic in fake too)
- Hard to test (need to mock everything)
- Hard to understand (mixed concerns)
- Hard to change (logic tied to database implementation)

### Correct Approach

```python
# ✅ CORRECT: Thin integration class, just wrap database operations
class RealDatabaseAdapter(DatabaseAdapter):
    def query(self, sql: str) -> list[dict[str, Any]]:
        """Just wrap database query - no business logic."""
        conn = psycopg2.connect(self.connection_string)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]

# ✅ CORRECT: Business logic in service layer
class SubscriptionService:
    def __init__(self, database: DatabaseAdapter) -> None:
        self.database = database

    def get_premium_users_with_expired_subscriptions(self) -> list[User]:
        """Complex logic over thin integration class."""
        users = self.database.query("SELECT * FROM users WHERE premium = true")

        # Business logic here - easy to test over fakes!
        result = []
        for user_dict in users:
            user = User.from_dict(user_dict)
            if self._has_expired_subscription(user):
                result.append(user)

        return result

    def _has_expired_subscription(self, user: User) -> bool:
        """Business logic isolated from database."""
        subscriptions = self.database.query(
            f"SELECT * FROM subscriptions WHERE user_id = {user.id}"
        )

        for sub in subscriptions:
            if self._is_expired(sub):
                return True
        return False
```

**Benefits**:

- Easy to fake (thin integration class, simple fake)
- Easy to test (business logic tested over fakes)
- Easy to understand (clear separation of concerns)
- Easy to change (business logic independent of database)

### Rule

**Integration classes should**:

- Wrap external system calls
- Parse responses into domain objects
- Validate basic preconditions (file exists, etc.)

**Integration classes should NOT**:

- Contain business logic
- Make decisions about "what to do"
- Implement algorithms or calculations
- Have complex control flow

**Test**: If you can't easily fake an integration class, it's too complex. Push logic up.

---

## ❌ Fakes with I/O Operations

**Fakes should be in-memory ONLY** (except minimal directory creation).

### Wrong Approach

```python
# ❌ WRONG: Fake performs I/O
class FakeDatabaseAdapter(DatabaseAdapter):
    def __init__(self, db_file: Path) -> None:
        self.db_file = db_file

    def query(self, sql: str) -> list[dict]:
        # Reading/writing real files defeats the purpose!
        import sqlite3
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(sql)
        return cursor.fetchall()

class FakeFileService(FileService):
    def process_file(self, path: Path) -> str:
        # Actually reading files defeats the purpose!
        content = path.read_text()
        return content.upper()
```

**Problems**:

- Slow (I/O operations)
- Requires real filesystem setup
- Defeats purpose of fakes
- Tests become integration tests

### Correct Approach

```python
# ✅ CORRECT: Fake uses in-memory state
class FakeDatabaseAdapter(DatabaseAdapter):
    def __init__(
        self,
        *,
        initial_data: dict[str, list[dict]] | None = None
    ) -> None:
        self._tables = initial_data or {}
        self._executed_queries: list[str] = []

    def query(self, sql: str) -> list[dict]:
        """Return in-memory data."""
        self._executed_queries.append(sql)

        # Simple parsing, return from memory
        if "FROM users" in sql:
            return self._tables.get("users", []).copy()
        return []

class FakeFileService(FileService):
    def __init__(self) -> None:
        self._processed_files: list[str] = []

    def process_file(self, path: Path) -> str:
        """Simulate processing without I/O."""
        self._processed_files.append(str(path))
        return "SIMULATED RESULT"
```

**Benefits**:

- Fast (no I/O)
- Simple test setup (configure via constructor)
- True unit testing
- Reliable (no filesystem quirks)

### Exception: Directory Creation

**Acceptable**: Fakes may create real directories when needed for filesystem integration.

```python
# ✅ ACCEPTABLE: Create directory for integration
class FakeFileManager(FileManager):
    def create_project(self, base_path: Path, name: str) -> Path:
        # Create real directory (acceptable for filesystem integration)
        project_path = base_path / name
        project_path.mkdir(parents=True, exist_ok=True)

        # But don't write actual files - keep data in memory
        self._projects[str(project_path)] = {
            "name": name,
            "created": datetime.now()
        }

        return project_path
```

**Rule**: Fakes may `mkdir()`, but should not read/write files.

---

## ❌ Testing Implementation Details

**Test behavior, not implementation**.

### Wrong Approach

```python
# ❌ WRONG: Testing internal implementation details
def test_service_uses_cache():
    """Test that service uses internal cache."""
    service = UserService(database=fake_db)

    # Checking private implementation details
    assert hasattr(service, "_cache")
    assert isinstance(service._cache, dict)

    service.get_user(1)
    assert 1 in service._cache  # Testing private attribute

def test_service_calls_private_method():
    """Test that service calls private method."""
    service = OrderService(database=fake_db)

    # Mocking private method - fragile!
    service._validate_order = Mock()

    service.process_order(order)
    service._validate_order.assert_called_once()
```

### Correct Approach

```python
# ✅ CORRECT: Testing observable behavior
def test_service_caches_users():
    """Test that service doesn't query database twice for same user."""
    fake_db = FakeDatabaseAdapter()
    service = UserService(database=fake_db)

    # Get same user twice
    user1 = service.get_user(1)
    user2 = service.get_user(1)

    # Assert on observable behavior - only one query
    assert len(fake_db.executed_queries) == 1
    assert user1 == user2

def test_order_validation():
    """Test that invalid orders are rejected."""
    service = OrderService(database=fake_db)

    invalid_order = Order(items=[], total=-50)

    # Test behavior, not how it's implemented
    with pytest.raises(ValueError, match="Invalid order"):
        service.process_order(invalid_order)
```

### Why This Is Wrong

**Problems**:

- Tests break when refactoring
- Couples tests to implementation
- Doesn't verify user-visible behavior
- Makes code harder to change

**Rule**: Test what the code **does**, not **how** it does it.

---

## ❌ Incomplete Test Coverage for Integration class Changes

**When adding/changing integration class method, you must test ALL implementations**.

### Wrong Approach

```python
# Added new method to DatabaseAdapter
# ✅ Implemented in RealDatabaseAdapter
# ✅ Implemented in FakeDatabaseAdapter
# ❌ Forgot to test FakeDatabaseAdapter!
# ❌ Forgot to test RealDatabaseAdapter!

# Result: Untested code, potential bugs
```

### Correct Approach

**Complete testing checklist**:

- [ ] Unit test of fake (`tests/unit/fakes/test_fake_database.py`)
- [ ] Integration test of real with mocking (`tests/integration/test_real_database.py`)
- [ ] Business logic test using fake (`tests/unit/services/test_my_service.py`)
- [ ] (Optional) E2E test with real implementation

**See**: `workflows.md#adding-an-integration class-method` for full checklist.

---

## ❌ Mocking What You Don't Own

**Create your own integration classes instead of mocking third-party libraries directly**.

### Wrong Approach

```python
# ❌ WRONG: Mocking third-party library
@patch("requests.Session")
def test_api_call(mock_session):
    # Fragile - couples to requests internals
    mock_session.return_value.get.return_value.json.return_value = {"data": "test"}

    service = DataService()
    result = service.fetch_data()

@patch("boto3.client")
def test_s3_upload(mock_boto):
    # Fragile - AWS SDK might change
    mock_client = Mock()
    mock_boto.return_value = mock_client
    mock_client.upload_file.return_value = None
```

### Correct Approach

```python
# ✅ CORRECT: Create your own integration class
class StorageAdapter(ABC):
    @abstractmethod
    def upload_file(self, local_path: Path, remote_key: str) -> None:
        """Upload file to storage."""

class S3StorageAdapter(StorageAdapter):
    """Real implementation using boto3."""
    def upload_file(self, local_path: Path, remote_key: str) -> None:
        import boto3
        client = boto3.client("s3")
        client.upload_file(str(local_path), self.bucket, remote_key)

class FakeStorageAdapter(StorageAdapter):
    """Fake for testing."""
    def __init__(self) -> None:
        self.uploaded_files: list[tuple[str, str]] = []

    def upload_file(self, local_path: Path, remote_key: str) -> None:
        self.uploaded_files.append((str(local_path), remote_key))

# Test with your fake
def test_file_upload():
    storage = FakeStorageAdapter()
    service = FileService(storage=storage)

    service.process_and_upload("data.csv")

    assert ("data.csv", "processed/data.csv") in storage.uploaded_files
```

**Benefits**:

- Not coupled to third-party library internals
- Easy to test
- Clear interface
- Can switch libraries without changing tests

---

## Summary of Anti-Patterns

| Anti-Pattern                 | Why It's Wrong                    | Correct Approach            |
| ---------------------------- | --------------------------------- | --------------------------- |
| Testing speculative features | Maintenance burden, no value      | Only test active work       |
| Hardcoded paths              | Catastrophic: pollutes filesystem | Use `tmp_path` fixture      |
| Not updating all layers      | Type errors, broken tests         | Update ABC/Real/Fake/DryRun |
| subprocess in unit tests     | 100x slower, harder to debug      | Use test clients            |
| Complex logic in gateways    | Hard to test, hard to fake        | Keep gateways thin          |
| Fakes with I/O               | Slow, defeats purpose             | In-memory only              |
| Testing implementation       | Breaks on refactoring             | Test behavior               |
| Incomplete gateway tests     | Untested code, potential bugs     | Test all implementations    |
| Mocking third-party libs     | Fragile, coupled to internals     | Create your own gateways    |

## Related Documentation

- `workflows.md` - Step-by-step guides for correct approaches
- `patterns.md` - Common testing patterns to follow
- `testing-strategy.md` - Which layer to test at
- `gateway-architecture.md` - Understanding the gateway layer
- `python-specific.md` - Python testing best practices
