# Testing Patterns

**Read this when**: You need to implement a specific pattern (constructor injection, mutation tracking, CliRunner, builders, etc.).

## Overview

This document covers common patterns used throughout Python test suites. Each pattern includes examples and explanations.

## Constructor Injection for Fakes

**Pattern**: Pass all initial state via constructor keyword arguments.

### Implementation

```python
from typing import Any
from pathlib import Path

class FakeDatabaseAdapter(DatabaseAdapter):
    def __init__(
        self,
        *,
        initial_data: dict[str, list[dict]] | None = None,
        users: list[dict] | None = None,
        orders: list[dict] | None = None,
        should_fail_on: list[str] | None = None,
    ) -> None:
        # Initialize mutable state from constructor
        self._tables = initial_data or {}
        if users:
            self._tables["users"] = users
        if orders:
            self._tables["orders"] = orders

        self._should_fail_on = should_fail_on or []

        # Initialize mutation tracking
        self._executed_queries: list[str] = []
        self._executed_commands: list[str] = []
        self._transaction_count = 0
```

### Usage in Tests

```python
# ✅ CORRECT: Constructor injection
def test_with_constructor_injection(tmp_path: Path) -> None:
    # Configure fake with initial state
    fake_db = FakeDatabaseAdapter(
        users=[
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
        ],
        orders=[
            {"id": 1, "user_id": 1, "total": 100.00},
        ]
    )

    # Fake is fully configured, ready to use
    users = fake_db.query("SELECT * FROM users")
    assert len(users) == 2
```

### Anti-Pattern

```python
# ❌ WRONG: Mutation after construction
def test_with_mutation() -> None:
    fake_db = FakeDatabaseAdapter()

    # Don't mutate private state directly!
    fake_db._tables["users"] = [...]  # Bypasses encapsulation
    fake_db._executed_queries = []  # Fragile, couples to implementation
```

### Why Constructor Injection?

**Benefits**:

- **Declarative**: Test setup is explicit and readable
- **Encapsulation**: Doesn't expose private implementation details
- **Maintainable**: Changes to fake internals don't break tests
- **Clear intent**: Constructor signature documents what can be configured

**Rule**: If tests need to set up state, add a constructor parameter. Don't mutate private fields.

---

## Mutation Tracking Properties

**Pattern**: Track operations in private lists/dicts, expose via read-only properties.

### Implementation

```python
class FakeApiClient(ApiClient):
    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        self._responses = responses or {}

        # Private mutation tracking
        self._requested_endpoints: list[str] = []
        self._posted_data: list[tuple[str, dict]] = []
        self._request_count = 0

    def get(self, endpoint: str) -> dict:
        """GET request."""
        # Track mutation
        self._requested_endpoints.append(endpoint)
        self._request_count += 1

        # Return configured response
        return self._responses.get(endpoint, {})

    def post(self, endpoint: str, *, json: dict) -> dict:
        """POST request."""
        # Track mutation
        self._posted_data.append((endpoint, json))
        self._request_count += 1

        # Return configured response
        return self._responses.get(endpoint, {})

    @property
    def requested_endpoints(self) -> list[str]:
        """Read-only access for test assertions."""
        return self._requested_endpoints.copy()  # Return copy to prevent tampering

    @property
    def posted_data(self) -> list[tuple[str, dict]]:
        """Read-only access for test assertions."""
        return self._posted_data.copy()

    @property
    def request_count(self) -> int:
        """Read-only access for test assertions."""
        return self._request_count
```

### Usage in Tests

```python
def test_mutation_tracking() -> None:
    fake_api = FakeApiClient(
        responses={
            "/users": [{"id": 1, "name": "Alice"}],
            "/users/1": {"id": 1, "name": "Alice"},
        }
    )

    # Perform operations
    users = fake_api.get("/users")
    user = fake_api.get("/users/1")
    fake_api.post("/users", json={"name": "Bob"})

    # Assert mutations were tracked
    assert fake_api.requested_endpoints == ["/users", "/users/1"]
    assert len(fake_api.posted_data) == 1
    assert fake_api.posted_data[0] == ("/users", {"name": "Bob"})
    assert fake_api.request_count == 3
```

### Why Track Mutations?

**Benefits**:

- **Verification**: Tests can verify operations were called
- **Ordering**: Lists preserve call order for sequential assertions
- **Arguments**: Track arguments passed to operations
- **Debugging**: Easy to see what operations were performed

**Rule**: For every write operation, track the mutation in a read-only property.

---

## Using CliRunner for CLI Tests

**Pattern**: Use Click's `CliRunner` for testing CLI commands, NOT subprocess.

### Basic Usage

```python
from click.testing import CliRunner
import click

@click.command()
@click.argument("name")
@click.option("--greeting", default="Hello")
def greet(name: str, greeting: str) -> None:
    """Greet someone."""
    click.echo(f"{greeting}, {name}!")

def test_cli_command() -> None:
    """Test CLI command with CliRunner."""
    runner = CliRunner()

    # Test with argument
    result = runner.invoke(greet, ["Alice"])

    assert result.exit_code == 0
    assert "Hello, Alice!" in result.output

    # Test with option
    result = runner.invoke(greet, ["Bob", "--greeting", "Hi"])
    assert "Hi, Bob!" in result.output
```

### Separating stdout and stderr (Click 8.2+)

Click 8.2+ automatically separates stdout and stderr. Use `result.stdout` and `result.stderr` for independent access:

```python
@click.command()
def mixed_output() -> None:
    """Command that writes to both stdout and stderr."""
    click.echo("Normal output")           # Goes to stdout
    click.echo("Error message", err=True) # Goes to stderr

def test_separate_stdout_stderr() -> None:
    """Test stdout and stderr are captured separately."""
    runner = CliRunner()
    result = runner.invoke(mixed_output)

    # result.output contains combined stdout+stderr (for backwards compat)
    # result.stdout contains only stdout
    # result.stderr contains only stderr
    assert "Normal output" in result.stdout
    assert "Error message" in result.stderr
    assert "Normal output" not in result.stderr
    assert "Error message" not in result.stdout
```

**IMPORTANT**: Do NOT use `CliRunner(mix_stderr=False)` - this parameter was removed in Click 8.2. Stdout/stderr separation is now automatic.

### With Context Object

```python
class AppContext:
    """Application context passed to commands."""
    def __init__(self, database: DatabaseAdapter, api: ApiClient) -> None:
        self.database = database
        self.api = api

@click.command()
@click.pass_obj
def sync_data(ctx: AppContext) -> None:
    """Sync data from API to database."""
    data = ctx.api.get("/data")
    ctx.database.execute(f"INSERT INTO sync_log VALUES ('{data}')")
    click.echo(f"Synced {len(data)} records")

def test_command_with_context(tmp_path: Path) -> None:
    """Test command that uses context."""
    # Create context with fakes
    fake_db = FakeDatabaseAdapter()
    fake_api = FakeApiClient(responses={"/data": {"records": [1, 2, 3]}})
    ctx = AppContext(database=fake_db, api=fake_api)

    # Invoke command with context
    runner = CliRunner()
    result = runner.invoke(sync_data, obj=ctx)

    # Assert
    assert result.exit_code == 0
    assert "Synced 1 records" in result.output
    assert len(fake_db.executed_commands) == 1
```

### With Isolated Filesystem

```python
@click.command()
@click.argument("project_name")
def init_project(project_name: str) -> None:
    """Initialize a new project."""
    project_dir = Path(project_name)
    project_dir.mkdir()
    (project_dir / "README.md").write_text(f"# {project_name}")
    (project_dir / "config.yaml").write_text("version: 1.0")
    click.echo(f"Created project: {project_name}")

def test_command_creates_files() -> None:
    """Test command that creates files."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Command runs in temporary directory
        result = runner.invoke(init_project, ["my_project"])

        assert result.exit_code == 0
        assert Path("my_project").exists()
        assert Path("my_project/README.md").exists()
        assert Path("my_project/config.yaml").exists()
```

### Capturing Exceptions

```python
def test_command_error() -> None:
    """Test command that raises an exception."""
    @click.command()
    def buggy_cmd():
        raise ValueError("Something went wrong!")

    runner = CliRunner()

    # CliRunner catches exceptions and sets exit_code
    result = runner.invoke(buggy_cmd, catch_exceptions=True)

    assert result.exit_code != 0
    assert "ValueError" in result.output
```

### Why CliRunner (NOT subprocess)?

**Performance**:

- CliRunner: **milliseconds** per test
- Subprocess: **seconds** per test
- **~100x faster** with CliRunner

**Better debugging**:

- Direct access to exceptions
- No shell interpretation issues
- Easier to debug with breakpoints

**Rule**: Always use `CliRunner` for CLI tests. Only use subprocess for true end-to-end integration tests.

---

## Builder Patterns for Complex Scenarios

**Pattern**: Use builder pattern to construct complex test scenarios declaratively.

### Implementation

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class User:
    id: int
    name: str
    email: str
    balance: float = 100.0

@dataclass
class Product:
    id: int
    name: str
    price: float
    stock: int = 100

class TestScenarioBuilder:
    """Builder for complex test scenarios."""

    def __init__(self) -> None:
        self.users: list[dict] = []
        self.products: list[dict] = []
        self.orders: list[dict] = []
        self.api_responses: dict[str, Any] = {}
        self.config: dict[str, Any] = {}

    def with_user(
        self,
        name: str = "Test User",
        email: str | None = None,
        balance: float = 100.0
    ) -> "TestScenarioBuilder":
        """Add a user to the scenario."""
        user_id = len(self.users) + 1
        if email is None:
            email = f"{name.lower().replace(' ', '.')}@example.com"

        self.users.append({
            "id": user_id,
            "name": name,
            "email": email,
            "balance": balance
        })
        return self

    def with_product(
        self,
        name: str = "Test Product",
        price: float = 10.0,
        stock: int = 100
    ) -> "TestScenarioBuilder":
        """Add a product to the scenario."""
        product_id = len(self.products) + 1
        self.products.append({
            "id": product_id,
            "name": name,
            "price": price,
            "stock": stock
        })
        return self

    def with_order(
        self,
        user_id: int,
        product_ids: list[int] | None = None,
        status: str = "pending"
    ) -> "TestScenarioBuilder":
        """Add an order to the scenario."""
        order_id = len(self.orders) + 1
        self.orders.append({
            "id": order_id,
            "user_id": user_id,
            "product_ids": product_ids or [1],
            "status": status
        })
        return self

    def with_api_response(self, endpoint: str, response: Any) -> "TestScenarioBuilder":
        """Configure API response."""
        self.api_responses[endpoint] = response
        return self

    def with_config(self, **kwargs) -> "TestScenarioBuilder":
        """Set configuration values."""
        self.config.update(kwargs)
        return self

    def build(self) -> tuple[FakeDatabaseAdapter, FakeApiClient, dict]:
        """Build configured test environment."""
        fake_db = FakeDatabaseAdapter(
            users=self.users,
            products=self.products,
            orders=self.orders
        )
        fake_api = FakeApiClient(responses=self.api_responses)

        return fake_db, fake_api, self.config
```

### Usage in Tests

```python
def test_complex_e_commerce_scenario() -> None:
    """Test with multiple users, products, and orders."""
    # Fluent, readable test setup
    fake_db, fake_api, config = (
        TestScenarioBuilder()
        .with_user(name="Alice", balance=500)
        .with_user(name="Bob", balance=100)
        .with_product(name="Laptop", price=1000, stock=5)
        .with_product(name="Mouse", price=25, stock=50)
        .with_order(user_id=1, product_ids=[1, 2])
        .with_order(user_id=2, product_ids=[2])
        .with_api_response("/tax", {"rate": 0.08})
        .with_api_response("/shipping", {"cost": 10.00})
        .with_config(enable_discounts=True, discount_rate=0.1)
        .build()
    )

    service = OrderService(database=fake_db, api_client=fake_api, config=config)

    # Test complex business logic
    result = service.calculate_order_total(order_id=1)

    assert result.subtotal == 1025.00
    assert result.tax == 82.00
    assert result.shipping == 10.00
    assert result.discount == 102.50  # 10% discount
    assert result.total == 1014.50
```

### When to Use Builders

**Use builders when**:

- Setting up complex multi-component scenarios
- Same scenario reused across multiple tests
- Test setup obscures test intent
- Many optional configurations

**Don't use builders when**:

- Simple single-component setup
- Setup is only used once
- Constructor injection is sufficient

### Benefits

**Readability**: Fluent API makes test intent clear
**Reusability**: Share builder across test suite
**Maintainability**: Changes to setup logic in one place
**Flexibility**: Mix and match components as needed

---

## Simulated Environment Pattern

**Pattern**: Create isolated test environments with proper setup and cleanup.

### Implementation

```python
from contextlib import contextmanager
from dataclasses import dataclass

@dataclass
class TestEnvironment:
    """Container for test environment resources."""
    base_path: Path
    config_path: Path
    data_path: Path
    database: FakeDatabaseAdapter
    api_client: FakeApiClient

@contextmanager
def simulated_environment(tmp_path: Path):
    """Create isolated test environment with proper cleanup."""
    # Setup test environment structure
    base_path = tmp_path / "test_env"
    base_path.mkdir()

    config_path = base_path / "config"
    config_path.mkdir()

    data_path = base_path / "data"
    data_path.mkdir()

    # Create default configuration
    (config_path / "app.yaml").write_text("""
    database:
      host: localhost
      port: 5432
    api:
      base_url: https://api.example.com
      timeout: 30
    """)

    # Initialize test doubles
    fake_db = FakeDatabaseAdapter(
        users=[{"id": 1, "name": "Test User"}]
    )
    fake_api = FakeApiClient(
        responses={"/health": {"status": "ok"}}
    )

    env = TestEnvironment(
        base_path=base_path,
        config_path=config_path,
        data_path=data_path,
        database=fake_db,
        api_client=fake_api
    )

    try:
        yield env
    finally:
        # Cleanup happens automatically with tmp_path
        # But we could add explicit cleanup here if needed
        pass
```

### Usage

```python
def test_with_simulated_environment(tmp_path: Path) -> None:
    """Test in isolated environment."""
    with simulated_environment(tmp_path) as env:
        # Use the environment
        service = DataService(
            database=env.database,
            api_client=env.api_client,
            config_dir=env.config_path
        )

        # Perform operations
        service.process_data()

        # Assert using environment's test doubles
        assert len(env.database.executed_queries) > 0
        assert env.api_client.request_count > 0

        # Can also use the filesystem
        output_file = env.data_path / "output.json"
        assert output_file.exists()
```

### Why Simulated Environments?

**Benefits**:

- **Isolation**: Each test runs in clean environment
- **Safety**: No risk of polluting real filesystem
- **Cleanup**: Automatic cleanup after test
- **Realistic**: Tests can create real files/directories when needed

**Rule**: Use simulated environments for integration tests that need filesystem isolation.

---

## Error Injection Pattern

**Pattern**: Configure fakes to raise errors for testing error handling.

### Implementation

```python
from typing import Any

class FakePaymentGateway(PaymentGateway):
    def __init__(
        self,
        *,
        approved_cards: list[str] | None = None,
        declined_cards: list[str] | None = None,
        network_error_on: list[str] | None = None,
        rate_limit_after: int | None = None,
    ) -> None:
        self._approved_cards = approved_cards or []
        self._declined_cards = declined_cards or []
        self._network_error_on = network_error_on or []
        self._rate_limit_after = rate_limit_after
        self._request_count = 0
        self._processed_transactions: list[dict] = []

    def charge(self, card_number: str, amount: float) -> str:
        """Process payment with error injection."""
        self._request_count += 1

        # Inject rate limit error
        if self._rate_limit_after and self._request_count > self._rate_limit_after:
            raise RateLimitError("Too many requests")

        # Inject network error
        if card_number in self._network_error_on:
            raise NetworkError("Connection timeout")

        # Simulate declined card
        if card_number in self._declined_cards:
            raise PaymentDeclined(f"Card {card_number[-4:]} declined")

        # Simulate approved card
        if card_number in self._approved_cards:
            transaction_id = f"txn_{self._request_count:04d}"
            self._processed_transactions.append({
                "id": transaction_id,
                "card": card_number,
                "amount": amount,
                "status": "approved"
            })
            return transaction_id

        # Default behavior
        raise ValueError(f"Unknown card: {card_number}")

    @property
    def processed_transactions(self) -> list[dict]:
        """For test assertions."""
        return self._processed_transactions.copy()
```

### Usage in Tests

```python
def test_handles_payment_declined() -> None:
    """Test error handling when payment is declined."""
    # Configure fake to decline specific card
    payment_gateway = FakePaymentGateway(
        approved_cards=["4111111111111111"],
        declined_cards=["4000000000000002"]
    )

    service = PaymentService(payment_gateway=payment_gateway)

    # Test declined card
    result = service.process_payment("4000000000000002", 100.00)

    assert result.status == "failed"
    assert "declined" in result.error_message.lower()
    assert len(payment_gateway.processed_transactions) == 0

def test_handles_network_errors() -> None:
    """Test handling of network errors."""
    payment_gateway = FakePaymentGateway(
        network_error_on=["4242424242424242"]
    )

    service = PaymentService(payment_gateway=payment_gateway)

    # Should retry on network error
    result = service.process_payment_with_retry("4242424242424242", 50.00)

    assert result.status == "failed"
    assert result.retry_count == 3

def test_handles_rate_limiting() -> None:
    """Test rate limit handling."""
    payment_gateway = FakePaymentGateway(
        approved_cards=["4111111111111111"],
        rate_limit_after=5
    )

    service = PaymentService(payment_gateway=payment_gateway)

    # Process 5 successful payments
    for i in range(5):
        result = service.process_payment("4111111111111111", 10.00)
        assert result.status == "success"

    # 6th payment should hit rate limit
    result = service.process_payment("4111111111111111", 10.00)
    assert result.status == "failed"
    assert "rate limit" in result.error_message.lower()
```

### Benefits

**Fast**: No need for real system to fail
**Reliable**: Errors are deterministic, not flaky
**Complete**: Test all error paths, even rare ones
**Safe**: No risk of corrupting real state

**Rule**: Add error injection parameters for operations that can fail.

---

## Dry-Run Testing Pattern

**Pattern**: Verify operations are intercepted, not executed.

### Implementation

```python
def test_data_migration_dry_run(tmp_path: Path, capsys) -> None:
    """Verify --dry-run doesn't modify data."""
    # Arrange: Set up fake with initial data
    fake_db = FakeDatabaseAdapter(
        users=[
            {"id": 1, "name": "Alice", "old_field": "value1"},
            {"id": 2, "name": "Bob", "old_field": "value2"},
        ]
    )

    service = DataMigrationService(database=fake_db)

    # Act: Run migration with dry-run flag
    service.migrate_schema(dry_run=True)

    # Assert: Operation was NOT executed
    assert len(fake_db.executed_commands) == 0  # No writes
    assert len(fake_db.executed_queries) == 1   # Only read queries

    # Assert: Dry-run messages were printed
    captured = capsys.readouterr()
    assert "[DRY RUN]" in captured.out
    assert "Would migrate 2 users" in captured.out
    assert "Would drop column: old_field" in captured.out

    # Assert: Data unchanged
    users = fake_db.query("SELECT * FROM users")
    assert all("old_field" in user for user in users)
```

### Pattern

1. **Arrange**: Set up fake with initial state
2. **Act**: Execute operation with `dry_run=True`
3. **Assert**:
   - Mutation tracking shows operations NOT executed
   - Output contains `[DRY RUN]` messages
   - State unchanged (operations didn't happen)

### CLI Command with Dry-Run

```python
@click.command()
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.pass_obj
def cleanup_data(ctx: AppContext, dry_run: bool) -> None:
    """Clean up old data."""
    if dry_run:
        # Wrap database with dry-run integration class
        ctx.database = DryRunDatabaseAdapter(ctx.database)

    old_records = ctx.database.query("SELECT * FROM logs WHERE age > 30")
    click.echo(f"Found {len(old_records)} old records")

    for record in old_records:
        ctx.database.execute(f"DELETE FROM logs WHERE id = {record['id']}")

    if not dry_run:
        click.echo("✓ Cleanup complete")

def test_cleanup_dry_run() -> None:
    """Test cleanup command with dry-run."""
    fake_db = FakeDatabaseAdapter(
        logs=[
            {"id": 1, "age": 45, "message": "old"},
            {"id": 2, "age": 10, "message": "new"},
        ]
    )
    ctx = AppContext(database=fake_db, api=FakeApiClient())

    runner = CliRunner()
    result = runner.invoke(cleanup_data, ["--dry-run"], obj=ctx)

    # Verify no deletions
    assert len(fake_db.executed_commands) == 0
    assert "[DRY RUN]" in result.output
    assert "Would execute: DELETE" in result.output
```

### Benefits

**Verifies**:

- Dry-run wrapper correctly intercepts operations
- Messages accurately describe what would happen
- No side effects occur in dry-run mode

---

## Related Documentation

- `workflows.md` - Step-by-step guides for using these patterns
- `testing-strategy.md` - Which layer to test at
- `integration-architecture.md` - Understanding fakes and integration layer
- `anti-patterns.md` - What to avoid
- `python-specific.md` - Python-specific testing patterns
