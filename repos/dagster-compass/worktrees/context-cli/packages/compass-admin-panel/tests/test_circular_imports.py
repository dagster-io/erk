"""Test to detect circular import issues in compass-admin-panel."""

import sys
from importlib import import_module


def test_all_modules_import_cleanly():
    """Test that all compass-admin-panel modules can be imported without circular import errors.

    This test ensures that the module structure is clean and doesn't have
    circular dependencies that could cause import errors.
    """
    # List all modules in the package
    modules = [
        "compass_admin_panel.types",
        "compass_admin_panel.app",
        "compass_admin_panel.api_routes",
        "compass_admin_panel.organizations",
        "compass_admin_panel.tokens",
        "compass_admin_panel.onboarding",
        "compass_admin_panel.analytics",
        "compass_admin_panel.cli",
    ]

    # Clear module cache to force fresh imports
    for module_name in modules:
        if module_name in sys.modules:
            del sys.modules[module_name]

    # Attempt to import each module
    errors = {}
    for module_name in modules:
        try:
            import_module(module_name)
        except ImportError as e:
            errors[module_name] = str(e)

    # Assert no import errors
    if errors:
        error_msg = "Import errors detected (likely circular imports):\n"
        for module, error in errors.items():
            error_msg += f"  {module}: {error}\n"
        raise AssertionError(error_msg)


def test_import_order_independence():
    """Test that modules can be imported in any order.

    Circular imports often manifest as order-dependent import failures.
    This test verifies that import order doesn't matter.
    """
    import importlib

    modules_to_test = [
        "compass_admin_panel.types",
        "compass_admin_panel.app",
        "compass_admin_panel.api_routes",
        "compass_admin_panel.organizations",
    ]

    # Test different import orders
    import_orders = [
        modules_to_test,  # Normal order (types -> app -> api_routes)
        list(reversed(modules_to_test)),  # Reverse order
        [
            "compass_admin_panel.api_routes",
            "compass_admin_panel.types",
            "compass_admin_panel.app",
        ],  # api_routes first
        [
            "compass_admin_panel.app",
            "compass_admin_panel.api_routes",
            "compass_admin_panel.types",
        ],  # app first
    ]

    for order in import_orders:
        # Clear all test modules from cache
        for mod in modules_to_test:
            if mod in sys.modules:
                del sys.modules[mod]

        # Try importing in this order
        try:
            for module_name in order:
                importlib.import_module(module_name)
        except ImportError as e:
            raise AssertionError(
                f"Import order dependency detected. "
                f"Failed importing in order {[m.split('.')[-1] for m in order]}: {e}"
            )


def test_types_module_has_no_internal_dependencies():
    """Ensure types.py doesn't import from other compass_admin_panel modules.

    The types module should only depend on external libraries (csbot, aiohttp, etc.)
    to serve as a dependency-free base for other modules.
    """
    # Clear module cache
    if "compass_admin_panel.types" in sys.modules:
        del sys.modules["compass_admin_panel.types"]

    # Import the types module
    # Get the source code
    import inspect

    import compass_admin_panel.types as types_module

    source = inspect.getsource(types_module)

    # Check for internal imports
    forbidden_patterns = [
        "from compass_admin_panel.app import",
        "from compass_admin_panel.api_routes import",
        "from compass_admin_panel.organizations import",
        "from compass_admin_panel.tokens import",
        "from compass_admin_panel.onboarding import",
        "from compass_admin_panel.analytics import",
    ]

    violations = []
    for pattern in forbidden_patterns:
        if pattern in source:
            violations.append(pattern)

    if violations:
        raise AssertionError(
            f"types.py should not import from other compass_admin_panel modules. "
            f"Found: {violations}. This creates circular dependencies."
        )


def test_admin_panel_context_only_in_types():
    """Ensure AdminPanelContext is only defined in types.py, not app.py.

    This prevents circular imports by having a single source of truth.
    """
    # Import both modules
    from compass_admin_panel import app as app_module
    from compass_admin_panel import types as types_module

    # Check that AdminPanelContext is defined in types
    assert hasattr(types_module, "AdminPanelContext"), (
        "AdminPanelContext should be defined in types.py"
    )

    # Check that it's a dataclass
    from dataclasses import is_dataclass

    assert is_dataclass(types_module.AdminPanelContext), "AdminPanelContext should be a dataclass"

    # Verify app.py imports it, doesn't define it
    import inspect

    app_source = inspect.getsource(app_module)

    # Should have import statement
    assert "from compass_admin_panel.types import AdminPanelContext" in app_source, (
        "app.py should import AdminPanelContext from types.py"
    )

    # Should NOT have @dataclass definition
    assert "@dataclass\nclass AdminPanelContext:" not in app_source, (
        "AdminPanelContext should not be defined in app.py (should be in types.py)"
    )
