#!/usr/bin/env python3
"""Generate JSON schema from Pydantic warehouse configuration models.

This script introspects the Pydantic models in models.py and generates a JSON file
containing field definitions and help information for each warehouse type. This ensures
the React frontend stays in sync with the Python backend definitions.

Usage:
    python -m csbot.slackbot.webapp.add_connections.generate_schema

Output:
    packages/ui/src/warehouse-schemas.json
"""

import json
from pathlib import Path
from typing import Any

from csbot.slackbot.webapp.add_connections.models import (
    AthenaWarehouseConfig,
    BigQueryWarehouseConfig,
    DatabricksWarehouseConfig,
    MotherduckWarehouseConfig,
    PostgresWarehouseConfig,
    RedshiftWarehouseConfig,
    SnowflakeWarehouseConfig,
)


def get_json_schema_extra(field_info: Any) -> dict[str, Any]:
    """Extract json_schema_extra from Pydantic field metadata."""
    json_schema_extra = getattr(field_info, "json_schema_extra", None)
    if json_schema_extra and isinstance(json_schema_extra, dict):
        return json_schema_extra
    return {}


def get_field_type(field_info: Any) -> str:
    """Determine the field type for frontend rendering."""
    # Check for union (Snowflake credential field)
    if hasattr(field_info, "discriminator") and field_info.discriminator:
        return "union"

    # Check annotation for basic types
    annotation = getattr(field_info, "annotation", None)
    if annotation:
        # Check for Literal types (enum-like choices)
        import typing

        if hasattr(typing, "get_origin") and hasattr(typing, "Literal"):
            origin = typing.get_origin(annotation)
            if origin is typing.Literal:
                return "string"  # Literal values are strings

        annotation_str = str(annotation)
        if "int" in annotation_str:
            return "integer"
        if "bool" in annotation_str:
            return "boolean"

    # Default to string
    return "string"


def flatten_union(field_name: str, field_info: Any) -> dict[str, Any]:
    """Flatten a union field into conditional fields.

    For example, Snowflake credential union becomes:
    - credential_type (radio field)
    - password (conditional on credential_type === "password")
    - private_key_file (conditional on credential_type === "private_key")
    - key_password (conditional on credential_type === "private_key")
    """
    fields = {}

    # Get the union_field name - the field that determines which variant to use (e.g., "type")
    union_field = field_info.discriminator
    if not union_field:
        return fields

    # Get union options from annotation
    import typing

    annotation = field_info.annotation
    if hasattr(typing, "get_args"):
        union_types = typing.get_args(annotation)
    else:
        return fields

    # Extract union_field values from each union option
    union_options = []
    union_models = {}

    for union_type in union_types:
        if hasattr(union_type, "model_fields"):
            # Get the union_field from the union model (e.g., "type")
            type_field = union_type.model_fields.get(union_field)
            if type_field and hasattr(type_field, "annotation"):
                # Extract the literal value from Literal["password"] or Literal["private_key"]
                annotation = type_field.annotation
                if hasattr(typing, "get_args"):
                    literal_args = typing.get_args(annotation)
                    if literal_args and len(literal_args) > 0:
                        option_value = literal_args[0]
                        union_options.append(option_value)
                        union_models[option_value] = union_type

    if not union_options:
        return fields

    # Create the union_field as a radio button
    union_field_name = f"{field_name}_type"
    fields[union_field_name] = {
        "name": union_field_name,
        "type": "string",
        "required": True,
        "title": "Authentication Method",
        "description": "Choose how to authenticate",
        "widget": "radio",
        "options": union_options,
        "default": union_options[0],
    }

    # Flatten fields from each union option
    for option_value, union_model in union_models.items():
        for sub_field_name, sub_field_info in union_model.model_fields.items():
            # Skip the union_field itself
            if sub_field_name == union_field:
                continue

            # Use the sub_field_name directly (e.g., "password", "private_key_file")
            flattened_name = sub_field_name

            # Build field data
            sub_field_data: dict[str, Any] = {
                "name": flattened_name,
                "type": get_field_type(sub_field_info),
                "required": sub_field_info.is_required(),
                "conditional": {
                    "field": union_field_name,
                    "value": option_value,
                },
            }

            # Add metadata
            if sub_field_info.title:
                sub_field_data["title"] = sub_field_info.title
            if sub_field_info.description:
                sub_field_data["description"] = sub_field_info.description
            if sub_field_info.examples:
                sub_field_data["examples"] = sub_field_info.examples

            # Extract json_schema_extra
            extra = get_json_schema_extra(sub_field_info)
            if "widget" in extra:
                sub_field_data["widget"] = extra["widget"]
            if "rows" in extra:
                sub_field_data["rows"] = extra["rows"]
            if "validator" in extra:
                sub_field_data["validator"] = extra["validator"]
            if "placeholder" in extra:
                sub_field_data["placeholder"] = extra["placeholder"]

            # Add default if not required
            from pydantic_core import PydanticUndefined

            if (
                not sub_field_info.is_required()
                and sub_field_info.default is not None
                and sub_field_info.default is not PydanticUndefined
            ):
                default_val = sub_field_info.default
                if hasattr(default_val, "__dict__"):
                    sub_field_data["default"] = str(default_val)
                else:
                    sub_field_data["default"] = default_val

            fields[flattened_name] = sub_field_data

    return fields


def extract_field_schema(model_class: type) -> dict[str, Any]:
    """Extract field definitions from a Pydantic model."""
    fields = {}
    # Get field order from model_fields
    for field_name, field_info in model_class.model_fields.items():
        # Check if this is a union field - flatten it into conditional fields
        if hasattr(field_info, "discriminator") and field_info.discriminator:
            union_fields = flatten_union(field_name, field_info)
            fields.update(union_fields)
            continue

        # Regular field processing
        field_data: dict[str, Any] = {
            "name": field_name,
            "type": get_field_type(field_info),
            "required": field_info.is_required(),
        }

        # Add metadata from field definition
        if field_info.title:
            field_data["title"] = field_info.title
        if field_info.description:
            field_data["description"] = field_info.description

        # Check for Literal type to extract options
        import typing

        annotation = field_info.annotation
        if hasattr(typing, "get_origin") and hasattr(typing, "Literal"):
            origin = typing.get_origin(annotation)
            if origin is typing.Literal:
                # Extract literal values as options
                literal_values = typing.get_args(annotation)
                if literal_values and len(literal_values) > 0:
                    field_data["options"] = list(literal_values)
                    # Use radio for 2-3 options, select for more
                    field_data["widget"] = "radio" if len(literal_values) <= 3 else "select"
                    # Set first option as default for optional fields
                    if not field_info.is_required():
                        field_data["default"] = literal_values[0]

        # Extract json_schema_extra metadata
        extra = get_json_schema_extra(field_info)

        # Add widget type if specified (password, textarea, radio, select)
        if "widget" in extra:
            field_data["widget"] = extra["widget"]

        # Add options for radio/select fields
        if "options" in extra:
            field_data["options"] = extra["options"]

        # Add validator reference
        if "validator" in extra:
            field_data["validator"] = extra["validator"]

        # Add rows for textarea
        if "rows" in extra:
            field_data["rows"] = extra["rows"]

        # Add placeholder
        if "placeholder" in extra:
            field_data["placeholder"] = extra["placeholder"]

        # Add conditional visibility rules
        if "conditional" in extra:
            field_data["conditional"] = extra["conditional"]

        # Add examples if present
        examples = field_info.examples
        if examples:
            field_data["examples"] = examples

        # Add default value if present and not required
        from pydantic_core import PydanticUndefined

        if (
            not field_info.is_required()
            and field_info.default is not None
            and field_info.default is not PydanticUndefined
        ):
            # Handle default values - convert to JSON-serializable format
            default_val = field_info.default
            if hasattr(default_val, "__dict__"):
                field_data["default"] = str(default_val)
            else:
                field_data["default"] = default_val

        fields[field_name] = field_data

    return fields


def help_info_to_dict(help_info: Any) -> dict[str, Any]:
    """Convert WarehouseHelpInfo dataclass to dictionary."""
    result: dict[str, Any] = {}

    if help_info.setup_instructions:
        result["setup_instructions"] = help_info.setup_instructions

    if help_info.network_info:
        network_data = {
            "connection_method": help_info.network_info.connection_method,
        }
        if help_info.network_info.port:
            network_data["port"] = help_info.network_info.port
        if help_info.network_info.ip_addresses:
            network_data["ip_addresses"] = help_info.network_info.ip_addresses
        if help_info.network_info.additional_info:
            network_data["additional_info"] = help_info.network_info.additional_info
        result["network_info"] = network_data

    if help_info.connection_permissions:
        result["connection_permissions"] = {
            "header": help_info.connection_permissions.header,
            "permissions": help_info.connection_permissions.permissions,
        }

    if help_info.schema_permissions:
        result["schema_permissions"] = {
            "header": help_info.schema_permissions.header,
            "permissions": help_info.schema_permissions.permissions,
        }

    return result


def generate_warehouse_schemas() -> dict[str, Any]:
    """Generate complete schema for all warehouse types."""
    warehouse_configs = {
        "snowflake": SnowflakeWarehouseConfig,
        "bigquery": BigQueryWarehouseConfig,
        "athena": AthenaWarehouseConfig,
        "redshift": RedshiftWarehouseConfig,
        "motherduck": MotherduckWarehouseConfig,
        "postgres": PostgresWarehouseConfig,
        "databricks": DatabricksWarehouseConfig,
    }

    schemas = {}
    for warehouse_type, config_class in warehouse_configs.items():
        # Extract field definitions
        fields = extract_field_schema(config_class)

        # Get help information
        help_info = config_class.get_help_info()
        help_dict = help_info_to_dict(help_info)

        schema: dict[str, Any] = {
            "type": warehouse_type,
            "fields": fields,
            "help_info": help_dict,
        }

        # Extract field groups if defined
        if hasattr(config_class, "get_field_groups"):
            groups = config_class.get_field_groups()  # type: ignore
            if groups:
                schema["groups"] = groups

        schemas[warehouse_type] = schema

    return {
        "version": "1.0",
        "generated_from": "csbot.slackbot.webapp.add_connections.models",
        "warehouses": schemas,
    }


def main() -> None:
    """Generate and save warehouse schemas to JSON file."""
    # Generate schemas
    schemas = generate_warehouse_schemas()

    # Determine output path
    # From: packages/csbot/src/csbot/slackbot/webapp/add_connections/generate_schema.py
    # To:   packages/ui/src/warehouse-schemas.json
    script_path = Path(__file__).resolve()
    # Navigate up to packages/ directory
    # generate_schema.py -> add_connections -> webapp -> slackbot -> csbot -> src -> csbot -> packages
    packages_dir = script_path.parent.parent.parent.parent.parent.parent.parent
    output_path = packages_dir / "ui" / "src" / "warehouse-schemas.json"

    # Create parent directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON file
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(schemas, f, indent=2, sort_keys=False)

    print(f"✅ Generated warehouse schemas: {output_path}")
    print(f"   Included {len(schemas['warehouses'])} warehouse types")


if __name__ == "__main__":
    main()
