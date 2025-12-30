---
name: fake-driven-testing-workflows
description: Step-by-step guidance for specific testing tasks
---

# Testing Workflows

**Read this when**: You're doing a specific task and need step-by-step guidance.

## Overview

This document provides concrete workflows for common testing scenarios in Python projects. Each workflow includes a checklist and code examples.

## Adding a New Feature

**Test-first workflow** (TDD is encouraged):

**Note**: If your feature includes pure utility functions with no dependencies (string manipulation, parsing, calculations), write those as Layer 3 pure unit tests in `tests/unit/test_*.py`. For business logic with dependencies, use Layer 4 tests over fakes as shown below.

### Step 1: Write Test Over Fakes (Layer 4)

**Location**: `tests/unit/services/test_my_feature.py` or `tests/unit/test_my_logic.py`

```python
from pathlib import Path
import pytest

def test_new_payment_feature(tmp_path: Path) -> None:
    """Test new payment processing feature."""
    # Arrange: Configure fake with initial state
    fake_db = FakeDatabaseAdapter(
        users=[{"id": 1, "name": "Alice", "balance": 100}]
    )
    fake_payment = FakePaymentGateway(
        approved_cards=["4111111111111111"],
        declined_cards=["4000000000000002"]
    )

    service = PaymentService(database=fake_db, payment_gateway=fake_payment)

    # Act: Execute the new feature
    result = service.process_payment(
        user_id=1,
        card_number="4111111111111111",
        amount=50.00
    )

    # Assert: Check expected behavior
    assert result.status == "success"
    assert result.transaction_id is not None

    # Assert: Check state mutations (if applicable)
    assert len(fake_payment.processed_transactions) == 1
    assert fake_payment.processed_transactions[0]["amount"] == 50.00

    # Check user balance was updated
    user = fake_db.query("SELECT * FROM users WHERE id = 1")[0]
    assert user["balance"] == 50.00
```

**Key points**:

- Use `FakeDatabaseAdapter`, `FakePaymentGateway`, etc. for speed
- Use pytest fixtures for common setup
- Use `tmp_path` for real directories when needed
- Test runs in milliseconds

### Step 2: Implement Feature

**Location**: `src/myapp/services/` or `src/myapp/core/`

```python
from typing import Any
from dataclasses import dataclass

@dataclass
class PaymentResult:
    status: str
    transaction_id: str | None
    error_message: str | None = None

class PaymentService:
    """Service for processing payments."""

    def __init__(self, database: DatabaseAdapter, payment_gateway: PaymentGateway) -> None:
        self.database = database
        self.payment_gateway = payment_gateway

    def process_payment(
        self,
        user_id: int,
        card_number: str,
        amount: float
    ) -> PaymentResult:
        """Process a payment for a user."""
        # Get user from database
        users = self.database.query(f"SELECT * FROM users WHERE id = {user_id}")
        if not users:
            return PaymentResult(
                status="failed",
                transaction_id=None,
                error_message="User not found"
            )

        user = users[0]

        # Check user has sufficient balance
        if user["balance"] < amount:
            return PaymentResult(
                status="failed",
                transaction_id=None,
                error_message="Insufficient balance"
            )

        # Process payment through gateway
        try:
            transaction_id = self.payment_gateway.charge(
                card_number=card_number,
                amount=amount
            )
        except PaymentDeclined as e:
            return PaymentResult(
                status="failed",
                transaction_id=None,
                error_message=str(e)
            )

        # Update user balance
        new_balance = user["balance"] - amount
        self.database.execute(
            f"UPDATE users SET balance = {new_balance} WHERE id = {user_id}"
        )

        return PaymentResult(
            status="success",
            transaction_id=transaction_id
        )
```

**Design principles**:

- Keep adapter classes thin (thin wrappers)
- Push complexity to business logic layer
- Business logic calls integration class interfaces, not external systems directly

### Step 3: Run Tests

```bash
pytest tests/unit/services/test_payment_service.py -v
```

**Expected outcome**:

- Test should pass (if implementation correct)
- Test should reveal bugs (if implementation has issues)
- Fast feedback loop (milliseconds per test)

### Step 4: Add Integration Test (Optional)

**When to add**: For critical user-facing features only.

**Location**: `tests/e2e/test_payment_e2e.py`

```python
def test_payment_processing_e2e(test_database_url: str) -> None:
    """End-to-end test with real payment gateway (sandbox)."""
    # Setup real database
    db = RealDatabaseAdapter(test_database_url)
    db.execute("DELETE FROM users")
    db.execute("INSERT INTO users VALUES (1, 'Alice', 100)")

    # Use payment gateway sandbox
    payment = RealPaymentGateway(
        api_key="test_api_key",
        sandbox=True
    )

    service = PaymentService(database=db, payment_gateway=payment)

    # Act
    result = service.process_payment(
        user_id=1,
        card_number="4111111111111111",  # Test card
        amount=50.00
    )

    # Assert: Verify real system state
    assert result.status == "success"

    # Check actual database
    users = db.query("SELECT * FROM users WHERE id = 1")
    assert users[0]["balance"] == 50.00
```

---

## Fixing a Bug

### Step 1: Reproduce Bug with Test Over Fakes

**Write a failing test first** to demonstrate the bug:

```python
def test_bug_negative_balance_not_allowed(tmp_path: Path) -> None:
    """Regression test for bug #123: negative balance was allowed."""
    # Arrange: Configure state that triggers bug
    fake_db = FakeDatabaseAdapter(
        users=[{"id": 1, "name": "Alice", "balance": 10}]
    )
    fake_payment = FakePaymentGateway()

    service = PaymentService(database=fake_db, payment_gateway=fake_payment)

    # Act
    result = service.process_payment(
        user_id=1,
        card_number="4111111111111111",
        amount=20.00  # More than balance
    )

    # Assert: This should FAIL initially (demonstrating the bug)
    assert result.status == "failed"  # Bug: currently returns "success"
    assert result.error_message == "Insufficient balance"  # Bug: no error message
    assert fake_db.query("SELECT * FROM users WHERE id = 1")[0]["balance"] == 10  # Bug: balance becomes -10
```

**Key insight**: Test should FAIL initially. This proves you've reproduced the bug.

### Step 2: Fix the Bug

**Location**: `src/myapp/services/payment_service.py`

```python
# Before (buggy):
def process_payment(self, user_id: int, card_number: str, amount: float) -> PaymentResult:
    user = self.get_user(user_id)
    # ❌ Bug: No balance check!
    transaction_id = self.payment_gateway.charge(card_number, amount)
    new_balance = user["balance"] - amount  # Can go negative!
    self.database.execute(f"UPDATE users SET balance = {new_balance} WHERE id = {user_id}")
    return PaymentResult(status="success", transaction_id=transaction_id)

# After (fixed):
def process_payment(self, user_id: int, card_number: str, amount: float) -> PaymentResult:
    user = self.get_user(user_id)

    # ✅ Fix: Check balance first (LBYL)
    if user["balance"] < amount:
        return PaymentResult(
            status="failed",
            transaction_id=None,
            error_message="Insufficient balance"
        )

    transaction_id = self.payment_gateway.charge(card_number, amount)
    new_balance = user["balance"] - amount
    self.database.execute(f"UPDATE users SET balance = {new_balance} WHERE id = {user_id}")
    return PaymentResult(status="success", transaction_id=transaction_id)
```

### Step 3: Run Test

```bash
pytest tests/unit/services/test_bug_negative_balance_not_allowed.py -v
```

**Expected outcome**: Test should now PASS.

### Step 4: Leave Test as Regression Test

**Don't delete the test!** It prevents future regressions.

```python
def test_bug_123_negative_balance_not_allowed(tmp_path: Path) -> None:
    """Regression test for bug #123: negative balance was allowed."""
    # Keep this test to prevent regression
    ...
```

---

## Adding an Integration class Method

**Use this checklist when adding a new method to an integration class interface.**

### Checklist

- [ ] Add `@abstractmethod` to ABC interface (e.g., `DatabaseAdapter`)
- [ ] Implement in real class (e.g., `RealDatabaseAdapter`) with actual I/O
- [ ] Implement in fake class (e.g., `FakeDatabaseAdapter`) with in-memory state
- [ ] Add mutation tracking property to fake if it's a write operation
- [ ] Add handler in dry-run wrapper if applicable
- [ ] Write unit test of fake (`tests/unit/fakes/test_fake_database.py`)
- [ ] Write integration test of real (`tests/integration/test_real_database.py`)
- [ ] Update business logic to call new method
- [ ] Write business logic test over fake

### Example: Adding `DatabaseAdapter.bulk_insert()`

#### 1. Interface (`src/myapp/integration classes/database.py`)

```python
from abc import ABC, abstractmethod
from typing import Any

class DatabaseAdapter(ABC):
    @abstractmethod
    def bulk_insert(self, table: str, records: list[dict[str, Any]]) -> int:
        """Bulk insert records into table. Returns count of inserted records."""
```

#### 2. Real Implementation (`src/myapp/integration classes/database.py`)

```python
import psycopg2

class RealDatabaseAdapter(DatabaseAdapter):
    def __init__(self, connection_string: str) -> None:
        self.connection_string = connection_string

    def bulk_insert(self, table: str, records: list[dict[str, Any]]) -> int:
        """Bulk insert using PostgreSQL COPY or multiple INSERT."""
        if not records:
            return 0

        conn = psycopg2.connect(self.connection_string)
        cursor = conn.cursor()

        try:
            # Build bulk insert SQL
            columns = list(records[0].keys())
            placeholders = [f"%({col})s" for col in columns]
            sql = f"""
                INSERT INTO {table} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            """

            # Execute for all records
            cursor.executemany(sql, records)
            inserted_count = cursor.rowcount
            conn.commit()

            return inserted_count
        finally:
            cursor.close()
            conn.close()
```

#### 3. Fake Implementation (`tests/fakes/database.py`)

```python
class FakeDatabaseAdapter(DatabaseAdapter):
    def __init__(self, **initial_tables: list[dict]) -> None:
        self._tables: dict[str, list[dict]] = initial_tables
        self._executed_queries: list[str] = []
        self._bulk_inserted: list[tuple[str, int]] = []  # Track bulk inserts

    def bulk_insert(self, table: str, records: list[dict[str, Any]]) -> int:
        """Simulate bulk insert in memory."""
        if not records:
            return 0

        # Initialize table if doesn't exist
        if table not in self._tables:
            self._tables[table] = []

        # Add records to in-memory table
        for record in records:
            # Add auto-incrementing ID if not present
            if "id" not in record:
                record["id"] = len(self._tables[table]) + 1
            self._tables[table].append(record.copy())

        # Track mutation
        self._bulk_inserted.append((table, len(records)))

        return len(records)

    @property
    def bulk_inserted(self) -> list[tuple[str, int]]:
        """Read-only access for test assertions."""
        return self._bulk_inserted.copy()
```

#### 4. Dry-Run Wrapper (`src/myapp/integration classes/database.py`)

```python
class DryRunDatabaseAdapter(DatabaseAdapter):
    def __init__(self, adapter: DatabaseAdapter) -> None:
        self._adapter = adapter

    def bulk_insert(self, table: str, records: list[dict[str, Any]]) -> int:
        """Print what would be inserted without executing."""
        print(f"[DRY RUN] Would bulk insert {len(records)} records into {table}")
        return len(records)  # Return expected count without inserting

    def query(self, sql: str) -> list[dict[str, Any]]:
        """Read operations delegate to wrapped integration class."""
        return self._adapter.query(sql)
```

#### 5. Test Fake (`tests/unit/fakes/test_fake_database.py`)

```python
def test_fake_database_bulk_insert() -> None:
    """Test that FakeDatabaseAdapter tracks bulk inserts."""
    fake_db = FakeDatabaseAdapter()

    records = [
        {"name": "Alice", "email": "alice@example.com"},
        {"name": "Bob", "email": "bob@example.com"},
    ]

    count = fake_db.bulk_insert("users", records)

    # Assert mutation was tracked
    assert ("users", 2) in fake_db.bulk_inserted

    # Assert state was updated
    users = fake_db.query("SELECT * FROM users")
    assert len(users) == 2
    assert users[0]["name"] == "Alice"
    assert users[1]["name"] == "Bob"

    # Assert return value
    assert count == 2
```

#### 6. Test Real (`tests/integration/test_real_database.py`)

```python
def test_real_database_bulk_insert(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that RealDatabaseAdapter calls correct SQL."""
    # Mock psycopg2.connect
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.rowcount = 2

    monkeypatch.setattr("psycopg2.connect", lambda **kwargs: mock_conn)

    db = RealDatabaseAdapter("postgresql://test")
    records = [
        {"name": "Alice", "email": "alice@example.com"},
        {"name": "Bob", "email": "bob@example.com"},
    ]

    count = db.bulk_insert("users", records)

    # Assert correct SQL was executed
    mock_cursor.executemany.assert_called_once()
    sql = mock_cursor.executemany.call_args[0][0]
    assert "INSERT INTO users" in sql
    assert count == 2
```

#### 7. Update Business Logic

```python
# src/myapp/services/user_service.py
class UserService:
    def __init__(self, database: DatabaseAdapter) -> None:
        self.database = database

    def import_users(self, csv_file: Path) -> int:
        """Import users from CSV file."""
        import csv

        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            records = list(reader)

        # Use new bulk_insert method
        count = self.database.bulk_insert("users", records)
        return count
```

#### 8. Write Business Logic Test

```python
# tests/unit/services/test_user_service.py
def test_import_users_from_csv(tmp_path: Path) -> None:
    """Test importing users from CSV."""
    # Create test CSV
    csv_file = tmp_path / "users.csv"
    csv_file.write_text("name,email\nAlice,alice@example.com\nBob,bob@example.com")

    fake_db = FakeDatabaseAdapter()
    service = UserService(database=fake_db)

    count = service.import_users(csv_file)

    assert count == 2
    assert ("users", 2) in fake_db.bulk_inserted

    users = fake_db.query("SELECT * FROM users")
    assert len(users) == 2
    assert users[0]["name"] == "Alice"
```

---

## Changing an Interface

**When modifying an existing method signature.**

### Checklist

- [ ] Update ABC interface
- [ ] Update real implementation
- [ ] Update fake implementation
- [ ] Update dry-run wrapper
- [ ] Update all call sites in business logic
- [ ] Update unit tests of fake
- [ ] Update integration tests of real
- [ ] Update business logic tests that use the method

### Example: Adding a Parameter

**Before**:

```python
def query(self, sql: str) -> list[dict[str, Any]]:
    """Execute a query."""
```

**After** (adding `timeout` parameter):

```python
def query(self, sql: str, *, timeout: float | None = None) -> list[dict[str, Any]]:
    """Execute a query with optional timeout."""
```

**Steps**:

1. Update `DatabaseAdapter` (ABC)
2. Update `RealDatabaseAdapter`: Add timeout to connection
3. Update `FakeDatabaseAdapter`: Track timeout in operation history
4. Update `DryRunDatabaseAdapter`: Print timeout if specified
5. Update all call sites: `db.query(sql, timeout=30.0)`
6. Update tests

---

## Managing Dry-Run Features

**Pattern**: Pass dry-run flag down to gateway layer by wrapping with `DryRunGateway`.

### Service Level

**Location**: `src/myapp/services/`

```python
class DataMigrationService:
    """Service for data migration operations."""

    def __init__(self, database: DatabaseAdapter) -> None:
        self.database = database

    def migrate_data(self, *, dry_run: bool = False) -> None:
        """Migrate data with optional dry-run."""
        database = self.database

        # Wrap gateway layer with dry-run wrapper
        if dry_run:
            database = DryRunDatabaseAdapter(database)

        # Business logic uses database normally
        # If dry-run, operations will print instead of executing
        old_records = database.query("SELECT * FROM old_table")

        for record in old_records:
            transformed = self._transform_record(record)
            database.execute(f"INSERT INTO new_table VALUES ({transformed})")

        if not dry_run:
            database.execute("DROP TABLE old_table")
            print(f"✓ Migrated {len(old_records)} records")
```

**Key insight**: Business logic doesn't change. Dry-run wrapping happens at service level.

### Testing Dry-Run

**Pattern**: Verify operations are NOT executed, but messages are printed.

```python
def test_migrate_data_dry_run(capsys) -> None:
    """Verify --dry-run doesn't modify data."""
    fake_db = FakeDatabaseAdapter(
        old_table=[{"id": 1, "data": "test"}]
    )

    service = DataMigrationService(database=fake_db)
    service.migrate_data(dry_run=True)

    # Verify operation was NOT executed
    assert len(fake_db.executed_queries) == 1  # Only the SELECT
    assert "DROP TABLE" not in str(fake_db.executed_queries)

    # Verify dry-run message was printed
    captured = capsys.readouterr()
    assert "[DRY RUN]" in captured.out
    assert "Would insert" in captured.out
```

### Implementing Dry-Run in Wrapper

**Pattern**: Read operations delegate, write operations print.

```python
class DryRunDatabaseAdapter(DatabaseAdapter):
    def __init__(self, adapter: DatabaseAdapter) -> None:
        self._adapter = adapter

    # Read operation: delegate
    def query(self, sql: str, *, timeout: float | None = None) -> list[dict[str, Any]]:
        return self._adapter.query(sql, timeout=timeout)

    # Write operation: print instead of executing
    def execute(self, sql: str) -> None:
        print(f"[DRY RUN] Would execute: {sql}")
        # Does NOT call self._adapter.execute()

    def bulk_insert(self, table: str, records: list[dict[str, Any]]) -> int:
        print(f"[DRY RUN] Would bulk insert {len(records)} records into {table}")
        return len(records)  # Return expected count
```

---

## Testing with Builder Patterns

**Use builder pattern for complex test scenarios.**

### Example: TestDataBuilder

```python
class TestDataBuilder:
    """Builder for complex test scenarios."""

    def __init__(self) -> None:
        self.users: list[dict] = []
        self.orders: list[dict] = []
        self.products: list[dict] = []
        self.api_responses: dict[str, Any] = {}

    def with_user(
        self,
        name: str = "Test User",
        email: str = "test@example.com",
        balance: float = 100.0
    ) -> "TestDataBuilder":
        """Add a user to the scenario."""
        user_id = len(self.users) + 1
        self.users.append({
            "id": user_id,
            "name": name,
            "email": email,
            "balance": balance
        })
        return self

    def with_order(
        self,
        user_id: int,
        total: float = 50.0,
        status: str = "pending"
    ) -> "TestDataBuilder":
        """Add an order to the scenario."""
        order_id = len(self.orders) + 1
        self.orders.append({
            "id": order_id,
            "user_id": user_id,
            "total": total,
            "status": status
        })
        return self

    def with_product(
        self,
        name: str = "Test Product",
        price: float = 10.0,
        stock: int = 100
    ) -> "TestDataBuilder":
        """Add a product to the scenario."""
        product_id = len(self.products) + 1
        self.products.append({
            "id": product_id,
            "name": name,
            "price": price,
            "stock": stock
        })
        return self

    def with_api_response(self, endpoint: str, response: dict) -> "TestDataBuilder":
        """Configure API response."""
        self.api_responses[endpoint] = response
        return self

    def build(self) -> tuple[FakeDatabaseAdapter, FakeApiClient]:
        """Build configured test environment."""
        fake_db = FakeDatabaseAdapter(
            users=self.users,
            orders=self.orders,
            products=self.products
        )
        fake_api = FakeApiClient(responses=self.api_responses)

        return fake_db, fake_api
```

### Usage

```python
def test_complex_order_scenario() -> None:
    """Test with multiple users, orders, and products."""
    # Fluent, readable test setup
    fake_db, fake_api = (
        TestDataBuilder()
        .with_user(name="Alice", balance=200)
        .with_user(name="Bob", balance=50)
        .with_product(name="Widget", price=25, stock=10)
        .with_product(name="Gadget", price=75, stock=5)
        .with_order(user_id=1, total=100, status="completed")
        .with_order(user_id=2, total=25, status="pending")
        .with_api_response("/tax", {"rate": 0.08})
        .build()
    )

    service = OrderService(database=fake_db, api_client=fake_api)

    # Test complex scenario
    result = service.process_pending_orders()

    assert result.processed_count == 1
    assert result.total_revenue == 25.00
```

**Benefits**:

- Readable test setup
- Reusable across tests
- Clear intent (declarative)
- Easy to extend

---

## Related Documentation

- `testing-strategy.md` - Which layer to test at
- `gateway-architecture.md` - Understanding the gateway layer
- `patterns.md` - Common testing patterns (CliRunner, mutation tracking, etc.)
- `anti-patterns.md` - What to avoid
- `python-specific.md` - pytest fixtures and Python tools
