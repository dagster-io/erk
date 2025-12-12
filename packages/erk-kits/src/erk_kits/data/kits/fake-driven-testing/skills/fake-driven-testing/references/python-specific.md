# Python-Specific Testing Patterns

**Read this when**: Working with pytest, Python mocking, type hints in tests, or testing Python frameworks.

## pytest Fixtures and Dependency Injection

### Basic Fixtures

```python
import pytest
from pathlib import Path
from typing import Any

@pytest.fixture
def database() -> DatabaseAdapter:
    """Provide a fake database for testing."""
    return FakeDatabaseAdapter(
        initial_data={"users": [{"id": 1, "name": "Test User"}]}
    )

@pytest.fixture
def api_client() -> ApiClient:
    """Provide a fake API client for testing."""
    return FakeApiClient(
        responses={
            "/users": [{"id": 1, "name": "Alice"}],
            "/orders": [],
        }
    )

@pytest.fixture
def service(database: DatabaseAdapter, api_client: ApiClient) -> UserService:
    """Provide a service with injected dependencies."""
    return UserService(database=database, api_client=api_client)

def test_user_service(service: UserService) -> None:
    """Test with fixtures providing dependencies."""
    user = service.get_user(1)
    assert user.name == "Test User"
```

### Fixture Scopes

```python
@pytest.fixture(scope="session")
def shared_resource() -> Resource:
    """Session-scoped fixture, created once per test session."""
    resource = expensive_setup()
    yield resource
    resource.cleanup()

@pytest.fixture(scope="module")
def module_database() -> Database:
    """Module-scoped fixture, created once per module."""
    return setup_test_database()

@pytest.fixture(scope="function")  # Default scope
def transaction(module_database: Database) -> Transaction:
    """Function-scoped fixture, created for each test."""
    txn = module_database.begin()
    yield txn
    txn.rollback()
```

### Parametrized Fixtures

```python
@pytest.fixture(params=["sqlite", "postgres", "mysql"])
def database_type(request) -> str:
    """Parametrized fixture runs tests with each parameter."""
    return request.param

@pytest.fixture
def database(database_type: str) -> DatabaseAdapter:
    """Create database based on parametrized type."""
    integration classes = {
        "sqlite": SqliteAdapter,
        "postgres": PostgresAdapter,
        "mysql": MySqlAdapter,
    }
    return integration classes[database_type]()

def test_database_operations(database: DatabaseAdapter) -> None:
    """This test runs 3 times, once for each database type."""
    database.insert("users", {"name": "Test"})
    assert database.count("users") == 1
```

## pytest Parametrization

### Basic Parametrization

```python
@pytest.mark.parametrize("input_val,expected", [
    ("valid", True),
    ("", False),
    (None, False),
    ("with spaces", True),
    ("with-dashes", True),
    ("with_underscores", True),
])
def test_validation(input_val: str | None, expected: bool) -> None:
    """Test multiple cases with parametrization."""
    assert is_valid_username(input_val) == expected
```

### Multiple Parameters

```python
@pytest.mark.parametrize("x", [1, 2])
@pytest.mark.parametrize("y", [10, 20])
def test_multiplication(x: int, y: int) -> None:
    """Creates 4 test cases: (1,10), (1,20), (2,10), (2,20)."""
    result = multiply(x, y)
    assert result == x * y
```

### Parametrize with IDs

```python
@pytest.mark.parametrize(
    "config,expected",
    [
        ({"debug": True}, "DEBUG"),
        ({"debug": False}, "INFO"),
        ({}, "WARNING"),
    ],
    ids=["debug_on", "debug_off", "no_config"]
)
def test_log_level(config: dict, expected: str) -> None:
    """Test with descriptive IDs for better test output."""
    assert get_log_level(config) == expected
```

## Python Mocking Patterns

### Using unittest.mock

```python
from unittest.mock import Mock, patch, MagicMock, PropertyMock
import requests

def test_with_mock() -> None:
    """Basic mocking with unittest.mock."""
    # Create a mock
    mock_response = Mock()
    mock_response.json.return_value = {"status": "ok"}
    mock_response.status_code = 200

    # Patch the requests module
    with patch("requests.get", return_value=mock_response):
        result = fetch_data("https://api.example.com")
        assert result["status"] == "ok"

def test_mock_property() -> None:
    """Mock a property."""
    mock_obj = Mock()
    type(mock_obj).name = PropertyMock(return_value="test_name")
    assert mock_obj.name == "test_name"

def test_magic_mock() -> None:
    """MagicMock supports magic methods."""
    mock = MagicMock()
    mock.__len__.return_value = 5
    assert len(mock) == 5
```

### Using pytest-mock

```python
import pytest

def test_with_pytest_mock(mocker) -> None:
    """Using pytest-mock plugin for cleaner mocking."""
    # Mock a function
    mock_get = mocker.patch("requests.get")
    mock_get.return_value.json.return_value = {"data": "test"}

    # Mock an object
    mock_service = mocker.Mock(spec=UserService)
    mock_service.get_user.return_value = User(id=1, name="Alice")

    # Spy on a method (calls original but tracks calls)
    spy = mocker.spy(UserService, "validate_email")

    service = UserService()
    service.validate_email("test@example.com")

    spy.assert_called_once_with("test@example.com")
```

### Mocking What You Own (Best Practice)

```python
# ❌ WRONG: Mocking third-party library directly
@patch("requests.Session")
def test_bad_mock(mock_session):
    # Fragile - couples to library internals
    mock_session.return_value.get.return_value.json.return_value = {}

# ✅ CORRECT: Create your own integration class
class HttpClient(ABC):
    """Your own abstraction over HTTP."""
    @abstractmethod
    def get(self, url: str) -> dict:
        """Get JSON from URL."""

class RealHttpClient(HttpClient):
    """Real implementation using requests."""
    def get(self, url: str) -> dict:
        return requests.get(url).json()

class FakeHttpClient(HttpClient):
    """Fake for testing."""
    def __init__(self, responses: dict[str, dict]) -> None:
        self.responses = responses

    def get(self, url: str) -> dict:
        return self.responses.get(url, {})

# Test using your fake
def test_with_fake():
    client = FakeHttpClient(responses={
        "https://api.example.com": {"data": "test"}
    })
    service = DataService(http_client=client)
    result = service.fetch_data()
    assert result == {"data": "test"}
```

## Common pytest Fixtures

### Built-in Fixtures

| Fixture             | Purpose                           | Example                                     |
| ------------------- | --------------------------------- | ------------------------------------------- |
| `tmp_path`          | Temporary directory (Path object) | `def test_foo(tmp_path: Path):`             |
| `tmp_path_factory`  | Session-scoped temp dirs          | `tmp_path_factory.mktemp("data")`           |
| `monkeypatch`       | Monkey-patch objects              | `monkeypatch.setattr(module, "func", mock)` |
| `capsys`            | Capture stdout/stderr             | `out, err = capsys.readouterr()`            |
| `caplog`            | Capture log messages              | `assert "ERROR" in caplog.text`             |
| `capfd`             | Capture file descriptors          | `out, err = capfd.readouterr()`             |
| `recwarn`           | Record warnings                   | `assert len(recwarn) == 1`                  |
| `doctest_namespace` | Doctest namespace                 | For doctest configuration                   |

### Using tmp_path

```python
def test_file_operations(tmp_path: Path) -> None:
    """Test with temporary directory."""
    # tmp_path is unique to this test
    config_file = tmp_path / "config.json"
    config_file.write_text('{"debug": true}')

    config = load_config(config_file)
    assert config["debug"] is True

    # Cleanup happens automatically

def test_with_subdirs(tmp_path: Path) -> None:
    """Create complex directory structures."""
    project = tmp_path / "my_project"
    src = project / "src"
    src.mkdir(parents=True)

    (src / "main.py").write_text("print('hello')")

    assert count_python_files(project) == 1
```

### Using monkeypatch

```python
def test_environment_variables(monkeypatch) -> None:
    """Test with modified environment."""
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.delenv("DEBUG", raising=False)

    config = load_config_from_env()
    assert config.api_key == "test_key"
    assert config.debug is False

def test_patch_function(monkeypatch) -> None:
    """Patch a function."""
    def mock_fetch(url: str) -> dict:
        return {"mocked": True}

    monkeypatch.setattr("myapp.api.fetch_data", mock_fetch)

    result = process_api_data()
    assert result["mocked"] is True

def test_patch_datetime(monkeypatch) -> None:
    """Mock datetime.now()."""
    import datetime
    fixed_time = datetime.datetime(2024, 1, 1, 12, 0)

    class MockDatetime(datetime.datetime):
        @classmethod
        def now(cls):
            return fixed_time

    monkeypatch.setattr("datetime.datetime", MockDatetime)

    timestamp = get_current_timestamp()
    assert timestamp == "2024-01-01 12:00:00"
```

## Testing CLI Applications with Click

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
    """Test Click CLI command."""
    runner = CliRunner()

    # Test with arguments
    result = runner.invoke(greet, ["Alice"])
    assert result.exit_code == 0
    assert "Hello, Alice!" in result.output

    # Test with options
    result = runner.invoke(greet, ["Bob", "--greeting", "Hi"])
    assert result.exit_code == 0
    assert "Hi, Bob!" in result.output

    # Test error cases
    result = runner.invoke(greet, [])
    assert result.exit_code != 0
    assert "Error" in result.output

def test_cli_with_input() -> None:
    """Test CLI with user input."""
    @click.command()
    def confirm():
        if click.confirm("Continue?"):
            click.echo("Continuing...")

    runner = CliRunner()

    # Simulate user input
    result = runner.invoke(confirm, input="y\n")
    assert "Continuing..." in result.output

    result = runner.invoke(confirm, input="n\n")
    assert "Continuing..." not in result.output

def test_cli_with_files(tmp_path: Path) -> None:
    """Test CLI that creates files."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(init_project, ["my_project"])

        assert result.exit_code == 0
        assert Path("my_project").exists()
        assert Path("my_project/config.yaml").exists()
```

## Testing Web Frameworks

### Flask Testing

```python
import pytest
from flask import Flask
from flask.testing import FlaskClient

@pytest.fixture
def app() -> Flask:
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/users/<int:user_id>")
    def get_user(user_id):
        return {"id": user_id, "name": "Test User"}

    return app

@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Flask test client."""
    return app.test_client()

def test_flask_endpoint(client: FlaskClient) -> None:
    """Test Flask endpoint."""
    response = client.get("/users/1")
    assert response.status_code == 200
    assert response.json["id"] == 1
    assert response.json["name"] == "Test User"

def test_flask_post(client: FlaskClient) -> None:
    """Test POST request."""
    response = client.post(
        "/users",
        json={"name": "Alice"},
        headers={"Authorization": "Bearer token"}
    )
    assert response.status_code == 201
```

### FastAPI Testing

```python
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI app for testing."""
    app = FastAPI()

    @app.get("/users/{user_id}")
    async def get_user(user_id: int):
        return {"id": user_id, "name": "Test User"}

    return app

@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """FastAPI test client."""
    return TestClient(app)

def test_fastapi_endpoint(client: TestClient) -> None:
    """Test FastAPI endpoint."""
    response = client.get("/users/1")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "Test User"}

@pytest.mark.asyncio
async def test_async_endpoint() -> None:
    """Test async endpoint directly."""
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/users/1")
        assert response.status_code == 200
```

### Django Testing

```python
import pytest
from django.test import TestCase, Client
from django.contrib.auth.models import User

# Using Django's TestCase
class UserViewTest(TestCase):
    """Django TestCase with database transactions."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass"
        )

    def test_user_profile(self):
        """Test user profile view."""
        self.client.login(username="testuser", password="testpass")
        response = self.client.get("/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "testuser")

# Using pytest-django
@pytest.mark.django_db
def test_user_creation():
    """Test with pytest-django."""
    user = User.objects.create_user(
        username="alice",
        email="alice@example.com"
    )
    assert user.username == "alice"
    assert User.objects.count() == 1

@pytest.fixture
def logged_in_client(client, django_user_model):
    """Fixture for logged-in client."""
    user = django_user_model.objects.create_user(
        username="testuser",
        password="testpass"
    )
    client.force_login(user)
    return client

def test_authenticated_view(logged_in_client):
    """Test view requiring authentication."""
    response = logged_in_client.get("/dashboard/")
    assert response.status_code == 200
```

## Type Hints in Tests

### Basic Type Hints

```python
from typing import Any, Protocol
from collections.abc import Generator, Sequence

def test_with_type_hints() -> None:
    """Tests should have return type None."""
    result: int = calculate_sum([1, 2, 3])
    assert result == 6

@pytest.fixture
def user_data() -> dict[str, Any]:
    """Fixtures should have explicit return types."""
    return {"id": 1, "name": "Alice", "active": True}

@pytest.fixture
def database() -> Generator[Database, None, None]:
    """Generator fixtures with cleanup."""
    db = Database()
    db.connect()
    yield db
    db.close()
```

### Protocol Types for Test Doubles

```python
class DatabaseProtocol(Protocol):
    """Protocol for database operations."""

    def query(self, sql: str) -> list[dict[str, Any]]: ...
    def execute(self, sql: str) -> None: ...

class FakeDatabase:
    """Fake implementation of DatabaseProtocol."""

    def __init__(self) -> None:
        self.data: list[dict[str, Any]] = []

    def query(self, sql: str) -> list[dict[str, Any]]:
        return self.data

    def execute(self, sql: str) -> None:
        pass

def test_with_protocol(database: DatabaseProtocol) -> None:
    """Test accepts anything matching DatabaseProtocol."""
    result = database.query("SELECT * FROM users")
    assert isinstance(result, list)
```

## Python Testing Commands

### Basic pytest Commands

```bash
# Run all tests
pytest

# Run specific file
pytest tests/test_service.py

# Run specific test
pytest tests/test_service.py::test_user_creation

# Run tests matching pattern
pytest -k "test_user"

# Run with verbose output
pytest -v

# Run with extra summary info
pytest -ra  # All except passed
pytest -rf  # Failed
pytest -rs  # Skipped

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Run failed first, then others
pytest --ff
```

### Coverage Commands

```bash
# Run with coverage
pytest --cov=src

# Coverage with missing lines
pytest --cov=src --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Coverage with branch coverage
pytest --cov=src --cov-branch

# Fail if coverage below threshold
pytest --cov=src --cov-fail-under=80
```

### Performance and Debugging

```bash
# Run tests in parallel
pytest -n auto  # Requires pytest-xdist
pytest -n 4     # Use 4 workers

# Profile slow tests
pytest --durations=10  # Show 10 slowest tests

# Run with pdb on failure
pytest --pdb

# Run with pdb at start of test
pytest --trace

# Show local variables on failure
pytest -l

# Disable output capturing
pytest -s

# Run with warnings
pytest -W error  # Treat warnings as errors
```

### Markers and Selection

```bash
# Run only marked tests
pytest -m "slow"
pytest -m "not slow"
pytest -m "unit and not integration"

# Common markers
@pytest.mark.skip(reason="Not implemented")
@pytest.mark.skipif(sys.version_info < (3, 10), reason="Requires Python 3.10+")
@pytest.mark.xfail(reason="Known issue")
@pytest.mark.parametrize("x,y", [(1, 2), (3, 4)])
@pytest.mark.timeout(10)  # Requires pytest-timeout
@pytest.mark.flaky(reruns=3)  # Requires pytest-rerunfailures
```

## Testing Best Practices

### AAA Pattern

```python
def test_with_aaa_pattern() -> None:
    """Arrange, Act, Assert pattern."""
    # Arrange - Set up test data and dependencies
    repository = FakeUserRepository(users=[
        User(id=1, name="Alice", active=True),
        User(id=2, name="Bob", active=False),
    ])
    service = UserService(repository=repository)

    # Act - Perform the action being tested
    active_users = service.get_active_users()

    # Assert - Verify the outcome
    assert len(active_users) == 1
    assert active_users[0].name == "Alice"
```

### Given-When-Then (BDD Style)

```python
def test_with_given_when_then() -> None:
    """Behavior-driven development style."""
    # Given - Initial context
    given_an_empty_shopping_cart = ShoppingCart()
    given_a_product = Product(id=1, name="Book", price=15.99)

    # When - Action occurs
    when_adding_product_to_cart = given_an_empty_shopping_cart.add(given_a_product)

    # Then - Expected outcome
    then_cart_should_contain_one_item = given_an_empty_shopping_cart.count() == 1
    then_total_should_be_correct = given_an_empty_shopping_cart.total() == 15.99

    assert then_cart_should_contain_one_item
    assert then_total_should_be_correct
```

### Test Isolation

```python
# Each test should be independent
class TestUserService:
    """Tests for UserService."""

    def setup_method(self) -> None:
        """Run before each test method."""
        self.repository = FakeUserRepository()
        self.service = UserService(self.repository)

    def teardown_method(self) -> None:
        """Run after each test method."""
        self.repository.clear()

    def test_create_user(self) -> None:
        """Test user creation in isolation."""
        user = self.service.create_user("Alice")
        assert user.id == 1
        assert user.name == "Alice"

    def test_delete_user(self) -> None:
        """Test user deletion in isolation."""
        # This test doesn't depend on test_create_user
        self.repository.add(User(id=1, name="Bob"))
        self.service.delete_user(1)
        assert self.repository.count() == 0
```

## Package Structure for Test Utilities

### Organizing Shared Test Code

```
myproject/
├── src/
│   └── myapp/
│       ├── __init__.py
│       ├── services.py
│       └── models.py
├── tests/
│   ├── conftest.py          # Shared fixtures
│   ├── helpers/             # Test utilities
│   │   ├── __init__.py
│   │   ├── builders.py      # Test data builders
│   │   ├── fakes.py         # Fake implementations
│   │   └── fixtures.py      # Additional fixtures
│   ├── unit/
│   │   ├── test_services.py
│   │   └── test_models.py
│   └── integration/
│       └── test_api.py
```

### conftest.py for Shared Fixtures

```python
# tests/conftest.py
import pytest
from pathlib import Path
from tests.helpers.fakes import FakeDatabase, FakeApiClient
from tests.helpers.builders import UserBuilder, OrderBuilder

@pytest.fixture
def fake_db() -> FakeDatabase:
    """Provide fake database for all tests."""
    return FakeDatabase()

@pytest.fixture
def fake_api() -> FakeApiClient:
    """Provide fake API client for all tests."""
    return FakeApiClient()

@pytest.fixture
def user_builder() -> UserBuilder:
    """Provide user builder for test data."""
    return UserBuilder()

# Automatically available in all test files
```

### Test Data Builders

```python
# tests/helpers/builders.py
from dataclasses import dataclass
from typing import Any

@dataclass
class User:
    id: int
    name: str
    email: str
    active: bool = True

class UserBuilder:
    """Builder for test users."""

    def __init__(self) -> None:
        self._id = 1
        self._name = "Test User"
        self._email = "test@example.com"
        self._active = True

    def with_name(self, name: str) -> "UserBuilder":
        self._name = name
        return self

    def with_email(self, email: str) -> "UserBuilder":
        self._email = email
        return self

    def inactive(self) -> "UserBuilder":
        self._active = False
        return self

    def build(self) -> User:
        user = User(
            id=self._id,
            name=self._name,
            email=self._email,
            active=self._active
        )
        self._id += 1  # Auto-increment for next build
        return user

    def build_many(self, count: int) -> list[User]:
        return [self.build() for _ in range(count)]
```

## Related Documentation

- `testing-strategy.md` - Which layer to test at
- `workflows.md` - Step-by-step testing workflows
- `patterns.md` - General testing patterns
- `anti-patterns.md` - What to avoid in Python tests
- `gateway-architecture.md` - Gateway pattern in Python
