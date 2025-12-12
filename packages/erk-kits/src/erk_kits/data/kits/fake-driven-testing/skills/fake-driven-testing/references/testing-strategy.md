# Testing Strategy by Layer

**Read this when**: You need to decide where to add a test, or understand the five-layer testing approach.

## Overview

This skill uses a **defense-in-depth testing strategy** with five layers for Python applications:

```
┌─────────────────────────────────────────┐
│  Layer 5: Business Logic Integration Tests (5%)  │  ← Smoke tests over real system
├─────────────────────────────────────────┤
│  Layer 4: Business Logic Tests (70%)   │  ← Tests over fakes (MOST TESTS)
├─────────────────────────────────────────┤
│  Layer 3: Pure Unit Tests (10%)        │  ← Zero dependencies, isolated testing
├─────────────────────────────────────────┤
│  Layer 2: Integration Sanity Tests (10%)│  ← Fast validation with mocking
├─────────────────────────────────────────┤
│  Layer 1: Fake Infrastructure Tests (5%)│  ← Verify test doubles work
└─────────────────────────────────────────┘
```

**Philosophy**: Test business logic extensively over fast in-memory fakes. Use real implementations sparingly for integration validation.

**Test distribution guidance**: Aim for 70% Layer 4, 10% Layer 3, 10% Layer 2, 5% Layer 5. Layer 1 tests grow as needed when adding/changing fakes.

## Layer 1: Unit Tests of Fakes

**Purpose**: Verify test infrastructure is reliable.

**Location**: `tests/unit/fakes/test_fake_*.py`

**When to write**: When adding or changing fake implementations.

**Why**: If fakes are broken, all higher-layer tests become unreliable. These tests validate that your test doubles behave correctly.

### Pattern: Test the Fake Itself

```python
def test_fake_database_tracks_queries(tmp_path: Path) -> None:
    """Verify FakeDatabaseAdapter tracks database operations."""
    # Arrange
    fake_db = FakeDatabaseAdapter()

    # Act
    fake_db.execute("INSERT INTO users (name) VALUES ('Alice')")
    result = fake_db.query("SELECT * FROM users WHERE name = 'Alice'")

    # Assert fake tracked the operations
    assert len(fake_db.executed_queries) == 2
    assert fake_db.executed_queries[0].startswith("INSERT")
    assert fake_db.executed_queries[1].startswith("SELECT")

    # Assert fake returns expected data
    assert len(result) == 1
    assert result[0]["name"] == "Alice"
```

### What to Test

- **State mutations**: Verify operations update internal state correctly
- **Mutation tracking**: Verify read-only properties track operations
- **Error simulation**: Verify fakes can inject errors when configured
- **State queries**: Verify read operations return expected data

### Example Tests

- `tests/unit/fakes/test_fake_database.py` - Tests of FakeDatabaseAdapter
- `tests/unit/fakes/test_fake_api_client.py` - Tests of FakeApiClient
- `tests/unit/fakes/test_fake_cache.py` - Tests of FakeCache
- `tests/unit/fakes/test_fake_message_queue.py` - Tests of FakeMessageQueue

## Layer 2: Integration Sanity Tests (with Mocking)

**Purpose**: Quick validation of real implementations without slow I/O. Catch syntax errors and basic issues.

**Location**: `tests/integration/test_real_*.py`

**When to write**: When adding or changing real implementations.

**Why**: Ensures code coverage even when underlying systems (database, network, filesystem) are mocked. Sanity checks prevent deployment of obviously broken code.

### Pattern: Mock External Systems, Verify Calls

```python
def test_real_database_executes_correct_query(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify RealDatabaseAdapter calls correct SQL."""
    # Mock the database connection
    mock_connection = Mock()
    mock_cursor = Mock()
    mock_connection.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [{"id": 1, "name": "Alice"}]

    def mock_connect(**kwargs):
        return mock_connection

    monkeypatch.setattr("psycopg2.connect", mock_connect)

    # Act
    db = RealDatabaseAdapter(connection_string="postgresql://...")
    result = db.query("SELECT * FROM users")

    # Assert correct command was constructed
    mock_cursor.execute.assert_called_once_with("SELECT * FROM users")
    assert result == [{"id": 1, "name": "Alice"}]
```

### What to Test

- **Command construction**: Verify correct SQL/API calls are built
- **Error handling**: Verify exceptions from external systems are handled correctly
- **Parsing logic**: Verify response parsing works correctly (can use mock responses)
- **Edge cases**: Verify handling of unusual inputs or error conditions

### Tools

- `monkeypatch` fixture for mocking database connections, HTTP clients, etc.
- Mock return values to simulate various responses
- Test error paths by raising exceptions from mocks

### Example Tests

- `tests/integration/test_real_database.py` - Tests of RealDatabaseAdapter with mocking
- `tests/integration/test_real_api_client.py` - Tests of RealApiClient with mocked HTTP

## Layer 3: Pure Unit Tests

**Purpose**: Test isolated utilities, helpers, and pure functions with zero dependencies.

**Location**: `tests/unit/`

**When to write**: For utilities, parsers, data transformations, or any code with no external dependencies.

**Why**: These tests run extremely fast and are rock-solid reliable since they have no dependencies. Perfect for foundational building blocks.

### Pattern: No Dependencies, Pure Logic Testing

```python
def test_sanitize_branch_name() -> None:
    """Verify branch name sanitization logic."""
    # No setup needed - pure function
    assert sanitize_branch_name("feat/FOO-123") == "feat-foo-123"
    assert sanitize_branch_name("feature__test") == "feature-test"
    assert sanitize_branch_name("UPPER") == "upper"


def test_parse_git_status() -> None:
    """Verify git status output parsing."""
    output = "## main...origin/main"
    result = parse_git_status(output)

    assert result["branch"] == "main"
    assert result["remote"] == "origin/main"
    assert result["ahead"] == 0
    assert result["behind"] == 0


def test_calculate_percentage() -> None:
    """Verify percentage calculation with edge cases."""
    assert calculate_percentage(50, 100) == 50.0
    assert calculate_percentage(0, 100) == 0.0
    assert calculate_percentage(100, 100) == 100.0

    # Edge case: divide by zero
    assert calculate_percentage(0, 0) == 0.0
```

### Key Characteristics

- **Zero imports of Fake\* classes** - if you import a fake, this is Layer 4, not Layer 3
- **No mocking** - no `mock.patch`, no `monkeypatch`
- **No external state** - no filesystem, database, network, subprocess
- **Pure logic only** - string manipulation, parsing, calculations, data structure operations

### What to Test

- **String utilities**: sanitization, formatting, parsing
- **Parsers**: CLI output parsing, config file parsing, response parsing
- **Calculations**: mathematical operations, business calculations
- **Data structures**: custom lists, trees, graphs (in-memory only)
- **Validators**: input validation logic (without external checks)
- **Transformers**: data transformation, mapping, filtering

### What NOT to Test Here

- ❌ Code that uses fakes → That's Layer 4
- ❌ Code that makes subprocess calls → That's Layer 2 or 5
- ❌ Code that reads/writes files → That's Layer 2 or 5
- ❌ Code that hits databases/APIs → That's Layer 2 or 5

### Performance

Pure unit tests are the **fastest tests possible**. They run in microseconds to milliseconds with zero setup overhead.

### Example Tests

- `tests/unit/test_string_utils.py` - String manipulation utilities
- `tests/unit/test_parsers.py` - CLI output parsers
- `tests/unit/test_validators.py` - Input validation logic
- `tests/unit/test_calculations.py` - Business calculation logic

## Layer 4: Business Logic Tests over Fakes (MAJORITY)

**Purpose**: Test application logic extensively with fast in-memory fakes.

**Location**: `tests/unit/services/`, `tests/unit/`, `tests/commands/`

**When to write**: For EVERY feature and bug fix. This is the default testing layer.

**Why**: Fast, reliable, easy to debug. Tests run in milliseconds, not seconds. This is where most testing happens.

### Pattern: Configure Fakes, Execute Logic, Assert Behavior

```python
def test_user_service_creates_user() -> None:
    """Verify user service creates users correctly."""
    # Arrange: Configure fake with desired state
    fake_db = FakeDatabaseAdapter()
    fake_email = FakeEmailClient(
        should_fail_for=["invalid@example.com"]
    )

    service = UserService(database=fake_db, email_client=fake_email)

    # Act: Execute business logic
    user = service.create_user(
        name="Alice",
        email="alice@example.com"
    )

    # Assert: Check behavior
    assert user.id == 1
    assert user.name == "Alice"
    assert user.email == "alice@example.com"

    # Assert: Check side effects via fake's tracking
    assert len(fake_db.executed_queries) == 1
    assert "INSERT INTO users" in fake_db.executed_queries[0]
    assert len(fake_email.sent_emails) == 1
    assert fake_email.sent_emails[0]["to"] == "alice@example.com"
```

### Key Tools

- **Fake implementations**: `FakeDatabaseAdapter`, `FakeApiClient`, `FakeCache`, etc.
- **Builder patterns**: Create complex test data easily
- **pytest fixtures**: Share common test setup
- **`tmp_path`**: pytest fixture for real directories when needed
- **CliRunner**: For testing Click CLI commands

### What to Test

- **Feature behavior**: Does the feature work as expected?
- **Error handling**: How does code handle error conditions?
- **Edge cases**: Unusual inputs, empty states, boundary conditions
- **Business rules**: Validation, calculations, state transitions
- **Side effects**: Did operations modify state correctly? (Check fake's tracking properties)

### Performance

Tests over fakes run in **milliseconds**. A typical test suite of 100+ tests runs in seconds, enabling rapid iteration.

### Example Tests

- `tests/unit/services/test_user_service.py` - Service layer tests
- `tests/unit/services/test_order_service.py` - Business logic tests
- `tests/unit/models/test_pricing.py` - Domain model tests
- `tests/commands/test_cli.py` - CLI command tests with CliRunner

## Layer 5: Business Logic Integration Tests

**Purpose**: Smoke tests over real system to catch integration issues.

**Location**: `tests/e2e/`

**When to write**: Sparingly, for critical user-facing workflows.

**Why**: Catches issues that mocks miss (actual database behavior, filesystem edge cases, network issues), but slow and potentially brittle.

### Pattern: Real Systems, Actual External Calls

```python
def test_user_registration_e2e(test_database_url: str) -> None:
    """End-to-end test: user registration with real database."""
    # Setup: Use real database (possibly dockerized for tests)
    db = RealDatabaseAdapter(connection_string=test_database_url)

    # Clean slate
    db.execute("DELETE FROM users")

    service = UserService(
        database=db,
        email_client=RealEmailClient(api_key="test_key")
    )

    # Act: Execute real operation
    user = service.register_user(
        name="Alice",
        email="alice@example.com",
        password="secure123"
    )

    # Assert: Verify in real database
    users = db.query("SELECT * FROM users WHERE email = 'alice@example.com'")
    assert len(users) == 1
    assert users[0]["name"] == "Alice"

    # Verify email was actually sent (might check test email service)
    # This depends on your test infrastructure
```

### What to Test

- **Critical workflows**: Core user-facing features (signup, checkout, payment)
- **Integration points**: Where multiple systems interact
- **Real system quirks**: Behavior that's hard to mock accurately
- **Data persistence**: Verify data is actually saved and retrievable

### Characteristics

- **Slow**: Tests take seconds, not milliseconds
- **Brittle**: Can fail due to environment issues (database down, network problems)
- **High value**: Catches real integration bugs that unit tests miss

### When NOT to Use Integration Tests

- ❌ Testing business logic (use Layer 4 instead)
- ❌ Testing error handling (use Layer 4 with fakes configured for errors)
- ❌ Testing calculations or validation (use Layer 3 for pure logic, Layer 4 for logic with dependencies)
- ❌ Rapid iteration during development (use Layer 3 or Layer 4)

Use integration tests as **final validation**, not primary testing strategy.

## Decision Tree: Where Should My Test Go?

```
┌─ I need to test...
│
├─ A NEW FEATURE or BUG FIX WITH EXTERNAL DEPENDENCIES
│  └─> Layer 4: tests/unit/services/ or tests/unit/ (over fakes) ← START HERE FOR BUSINESS LOGIC
│
├─ A PURE UTILITY/HELPER WITH NO DEPENDENCIES
│  └─> Layer 3: tests/unit/ (pure unit tests, no fakes/mocks)
│
├─ A FAKE IMPLEMENTATION (test infrastructure)
│  └─> Layer 1: tests/unit/fakes/test_fake_*.py
│
├─ A REAL ADAPTER IMPLEMENTATION (code coverage with mocks)
│  └─> Layer 2: tests/integration/test_real_*.py
│
└─ CRITICAL USER WORKFLOW (smoke test)
   └─> Layer 5: tests/e2e/ (integration tests, sparingly)
```

**Default**:

- For business logic with dependencies → Layer 4 (tests over fakes)
- For pure utilities with no dependencies → Layer 3 (pure unit tests)

## Test Distribution Example

For a typical feature (e.g., "add payment processing"):

- **1-2 fake tests** (Layer 1): Verify `FakePaymentGateway.charge()` works
- **1-2 sanity tests** (Layer 2): Verify `RealPaymentGateway.charge()` calls correct API
- **2-3 pure unit tests** (Layer 3): Test payment amount formatting, currency conversion logic
  - `format_currency(1234.56, "USD")` → `"$1,234.56"`
  - `convert_currency(100, "USD", "EUR")` → calculation logic
  - `validate_card_number("4111...")` → Luhn algorithm check
- **10-12 business logic tests** (Layer 4): Test payment flow over fakes
  - Successful payment
  - Insufficient funds
  - Invalid card
  - Network timeout
  - Duplicate transaction
  - Refund processing
  - Tax calculation
  - Receipt generation
- **1 integration test** (Layer 5): Smoke test entire payment flow with test payment gateway

**Total**: ~20 tests, with 70% over fakes (Layer 4), 10% pure unit (Layer 3), 10% sanity (Layer 2), 5% integration (Layer 5), 5% fake tests (Layer 1).

## Classifying Existing Tests

**Read this when**: You need to understand which layer an existing test belongs to, or you're auditing test coverage.

### Classification Decision Tree

Use this flowchart to classify existing tests into the correct layer:

```
Does the test use ANY external dependencies? (files, git, network, etc.)
├─ NO → Is it testing a fake implementation itself?
│  ├─ YES → Layer 1: Fake Infrastructure Test
│  └─ NO → Layer 3: Pure Unit Test
└─ YES → Does it use real implementations?
   ├─ NO (uses fakes) → Layer 4: Business Logic Test
   └─ YES → Does it mock the I/O operations?
      ├─ YES → Layer 2: Integration Sanity Test
      └─ NO (real I/O) → Layer 5: Business Logic Integration Test
```

### Quick Classification Guide

**Ask these questions in order:**

1. **Does the test import any Fake\* classes?**
   - YES → Layer 4 (Business Logic Test)
   - NO → Continue to question 2

2. **Does the test use mocking (mock.patch, monkeypatch)?**
   - YES → Layer 2 (Integration Sanity Test)
   - NO → Continue to question 3

3. **Does the test make real external calls (subprocess, filesystem, network)?**
   - YES → Layer 5 (Business Logic Integration Test)
   - NO → Continue to question 4

4. **Is the test testing a Fake implementation itself?**
   - YES → Layer 1 (Fake Infrastructure Test)
   - NO → Layer 3 (Pure Unit Test)

### Common Patterns and Their Layer Assignments

**Layer 1 patterns:**

```python
def test_fake_git_tracks_branches():
    fake = FakeGit()  # Testing the fake itself
    fake.create_branch("feature")
    assert "feature" in fake.branches  # Checking fake's internal state
```

**Layer 2 patterns:**

```python
def test_real_git_create_branch(monkeypatch):
    mock_run = Mock()
    monkeypatch.setattr("subprocess.run", mock_run)

    real_git = RealGit()
    real_git.create_branch("feature")

    # Verifying correct command was called (sanity check)
    mock_run.assert_called_once()
```

**Layer 3 patterns:**

```python
def test_sanitize_branch_name():
    # No imports, no dependencies
    result = sanitize_branch_name("feat/FOO")
    assert result == "feat-foo"
```

**Layer 4 patterns:**

```python
def test_create_worktree_command():
    fake_git = FakeGit()  # Using fake
    result = create_worktree(fake_git, name="feature")
    assert result.success
    assert "feature" in fake_git.worktrees
```

**Layer 5 patterns:**

```python
def test_complete_pr_workflow(tmp_path):
    # Real git operations, real filesystem
    repo = git.Repo.init(tmp_path)
    # ... real git commands ...
    # ... real file operations ...
```

### What to Do If a Test Doesn't Fit Cleanly

**Scenario 1: Test uses both fakes and real I/O**

- **Classification**: Layer 4 (Business Logic Test)
- **Recommendation**: Consider refactoring to isolate the I/O behind an integration interface

**Scenario 2: Test has minimal logic, mostly setup**

- **Classification**: Probably not worth testing separately
- **Recommendation**: Consider if this test adds value or is just testing framework behavior

**Scenario 3: Test mocks at multiple levels**

- **Classification**: Layer 2 (Integration Sanity Test) if mocking real implementation
- **Recommendation**: Simplify mocking strategy if possible

**Scenario 4: Test is very slow but uses fakes**

- **Classification**: Still Layer 4, but investigate performance issue
- **Recommendation**: Profile the test to find the bottleneck

### Migration Guidance

**You don't need to move tests just because of new taxonomy.** The layer classification is primarily for:

1. **Understanding current coverage distribution**
2. **Deciding where NEW tests should go**
3. **Identifying gaps in testing strategy**

**Only refactor tests if:**

- Test is in wrong location AND causing confusion
- Test is slow because it's using wrong layer
- Test is brittle because it's over-mocking or over-integrating

## Related Documentation

- `gateway-architecture.md` - Understanding the gateway layer being tested
- `workflows.md` - Step-by-step guides for adding tests
- `patterns.md` - Common testing patterns (CliRunner, builders, etc.)
- `anti-patterns.md` - What to avoid when writing tests
- `python-specific.md` - pytest fixtures, mocking, and Python tools
