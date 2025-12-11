"""Test warehouse schema generation stays in sync with models.

This test ensures that the generated warehouse-schemas.json file in the React UI
package is kept in sync with the Python Pydantic models.
"""

import json
from pathlib import Path

from csbot.slackbot.webapp.add_connections.generate_schema import generate_warehouse_schemas


def test_warehouse_schemas_json_is_up_to_date() -> None:
    """Verify that warehouse-schemas.json matches current model definitions."""
    # Generate schemas from current models
    generated_schemas = generate_warehouse_schemas()

    # Load the committed JSON file
    # From: packages/csbot/tests/test_warehouse_schema_generation.py
    # To:   packages/ui/src/warehouse-schemas.json
    test_file_path = Path(__file__).resolve()
    # Navigate: test_warehouse_schema_generation.py -> tests -> csbot -> packages
    packages_dir = test_file_path.parent.parent.parent
    json_path = packages_dir / "ui" / "src" / "warehouse-schemas.json"

    if not json_path.exists():
        # If the file doesn't exist, this is expected on first run
        raise AssertionError(
            f"warehouse-schemas.json not found at {json_path}. "
            f"Run: uv run python -m csbot.slackbot.webapp.add_connections.generate_schema"
        )

    with json_path.open(encoding="utf-8") as f:
        committed_schemas = json.load(f)

    # Compare the schemas
    if generated_schemas != committed_schemas:
        raise AssertionError(
            "warehouse-schemas.json is out of sync with Python models. "
            "Run: uv run python -m csbot.slackbot.webapp.add_connections.generate_schema"
        )


def test_all_warehouse_types_have_required_fields() -> None:
    """Verify that all warehouse types have the expected structure."""
    schemas = generate_warehouse_schemas()

    assert "version" in schemas
    assert "generated_from" in schemas
    assert "warehouses" in schemas

    warehouse_types = ["snowflake", "bigquery", "athena", "redshift", "postgres"]

    for warehouse_type in warehouse_types:
        assert warehouse_type in schemas["warehouses"], f"Missing {warehouse_type}"

        warehouse = schemas["warehouses"][warehouse_type]
        assert "type" in warehouse
        assert "fields" in warehouse
        assert "help_info" in warehouse

        # Check that fields have required metadata
        for field_name, field_info in warehouse["fields"].items():
            assert "name" in field_info
            assert "type" in field_info
            assert "required" in field_info
            assert field_info["name"] == field_name

        # Check help_info structure
        help_info = warehouse["help_info"]
        assert "setup_instructions" in help_info or "network_info" in help_info

        if "network_info" in help_info:
            assert "connection_method" in help_info["network_info"]


def test_schema_permissions_are_included() -> None:
    """Verify that all warehouses include schema permission information."""
    schemas = generate_warehouse_schemas()

    for warehouse_type, warehouse in schemas["warehouses"].items():
        help_info = warehouse["help_info"]

        # All warehouses should have schema permissions for the SchemaDiscovery step except MotherDuck
        if warehouse_type == "motherduck":
            continue
        assert "schema_permissions" in help_info, f"{warehouse_type} missing schema_permissions"

        schema_perms = help_info["schema_permissions"]
        assert "header" in schema_perms
        assert "permissions" in schema_perms
        assert isinstance(schema_perms["permissions"], list)
        assert len(schema_perms["permissions"]) > 0
