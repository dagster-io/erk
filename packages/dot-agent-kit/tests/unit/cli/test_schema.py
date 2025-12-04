"""Tests for schema.py - dataclass JSON schema generation."""

from dataclasses import dataclass
from typing import Literal

import click
import pytest

from dot_agent_kit.cli.schema import (
    SchemaCommand,
    build_epilog,
    format_type,
    generate_schema,
)


# Test dataclasses for schema generation
@dataclass
class SimpleDataclass:
    """Simple dataclass for testing."""

    name: str
    count: int
    active: bool


@dataclass
class OptionalFieldsDataclass:
    """Dataclass with optional fields."""

    required: str
    optional: str | None


@dataclass
class LiteralFieldsDataclass:
    """Dataclass with Literal type fields."""

    status: Literal["success", "error", "pending"]
    code: Literal[200, 404, 500]


@dataclass
class CollectionFieldsDataclass:
    """Dataclass with collection type fields."""

    items: list[str]
    mapping: dict[str, int]
    nested_list: list[list[int]]


@dataclass
class ComplexUnionDataclass:
    """Dataclass with complex union types."""

    value: str | int | float
    nullable_union: int | None
    multi_union: str | int | list[str]


@dataclass
class NoDocstringDataclass:
    """No docstring for this one."""

    field: str


# Remove docstring to test fallback
NoDocstringDataclass.__doc__ = None


class TestFormatType:
    """Tests for format_type function."""

    def test_format_primitive_types(self) -> None:
        """Test formatting of primitive types."""
        assert format_type(bool) == "boolean"
        assert format_type(int) == "integer"
        assert format_type(float) == "number"
        assert format_type(str) == "string"

    def test_format_none_type(self) -> None:
        """Test formatting of None type."""
        assert format_type(type(None)) == "null"

    def test_format_optional_types(self) -> None:
        """Test formatting of optional (X | None) types."""
        assert format_type(str | None) == "string | null"
        assert format_type(int | None) == "integer | null"

    def test_format_union_types(self) -> None:
        """Test formatting of union types (X | Y)."""
        assert format_type(str | int) == "string | integer"
        assert format_type(str | int | float) == "string | integer | number"

    def test_format_literal_types(self) -> None:
        """Test formatting of Literal types."""
        assert format_type(Literal["a", "b"]) == '"a" | "b"'
        assert format_type(Literal["success", "error"]) == '"success" | "error"'
        assert format_type(Literal[200, 404, 500]) == "200 | 404 | 500"

    def test_format_list_types(self) -> None:
        """Test formatting of list types."""
        assert format_type(list[str]) == "list[string]"
        assert format_type(list[int]) == "list[integer]"
        assert format_type(list[str | None]) == "list[string | null]"
        assert format_type(list) == "list"

    def test_format_dict_types(self) -> None:
        """Test formatting of dict types."""
        assert format_type(dict[str, int]) == "dict[string, integer]"
        assert format_type(dict[str, str]) == "dict[string, string]"
        assert format_type(dict[str, str | int]) == "dict[string, string | integer]"
        assert format_type(dict) == "dict"

    def test_format_nested_collections(self) -> None:
        """Test formatting of nested collection types."""
        assert format_type(list[list[str]]) == "list[list[string]]"
        assert format_type(dict[str, list[int]]) == "dict[string, list[integer]]"

    def test_format_complex_unions(self) -> None:
        """Test formatting of complex union combinations."""
        assert format_type(str | int | None) == "string | integer | null"
        assert format_type(list[str] | dict[str, int]) == "list[string] | dict[string, integer]"


class TestGenerateSchema:
    """Tests for generate_schema function."""

    def test_generate_simple_schema(self) -> None:
        """Test schema generation for simple dataclass."""
        schema = generate_schema(SimpleDataclass)

        # Check title from docstring
        assert "Simple dataclass for testing." in schema

        # Check field names and types
        assert "name: string" in schema
        assert "count: integer" in schema
        assert "active: boolean" in schema

    def test_generate_schema_with_optional_fields(self) -> None:
        """Test schema generation with optional fields."""
        schema = generate_schema(OptionalFieldsDataclass)

        assert "Dataclass with optional fields." in schema
        assert "required: string" in schema
        assert "optional: string | null" in schema

    def test_generate_schema_with_literal_fields(self) -> None:
        """Test schema generation with Literal fields."""
        schema = generate_schema(LiteralFieldsDataclass)

        assert "Dataclass with Literal type fields." in schema
        assert 'status: "success" | "error" | "pending"' in schema
        assert "code: 200 | 404 | 500" in schema

    def test_generate_schema_with_collection_fields(self) -> None:
        """Test schema generation with collection fields."""
        schema = generate_schema(CollectionFieldsDataclass)

        assert "Dataclass with collection type fields." in schema
        assert "items: list[string]" in schema
        assert "mapping: dict[string, integer]" in schema
        assert "nested_list: list[list[integer]]" in schema

    def test_generate_schema_with_complex_unions(self) -> None:
        """Test schema generation with complex union types."""
        schema = generate_schema(ComplexUnionDataclass)

        assert "Dataclass with complex union types." in schema
        assert "value: string | integer | number" in schema
        assert "nullable_union: integer | null" in schema
        assert "multi_union: string | integer | list[string]" in schema

    def test_generate_schema_without_docstring(self) -> None:
        """Test schema generation falls back to class name when no docstring."""
        schema = generate_schema(NoDocstringDataclass)

        # Should use class name as title
        assert "NoDocstringDataclass" in schema
        assert "field: string" in schema

    def test_generate_schema_rejects_non_dataclass(self) -> None:
        """Test that generate_schema raises TypeError for non-dataclasses."""

        class NotADataclass:
            """Not a dataclass."""

            field: str

        with pytest.raises(TypeError, match="is not a dataclass"):
            generate_schema(NotADataclass)

    def test_generate_schema_field_order(self) -> None:
        """Test that generated schema preserves field order."""
        schema = generate_schema(SimpleDataclass)
        lines = schema.split("\n")

        # Find field lines (start with 2 spaces, contain colon)
        field_lines = [line for line in lines if line.startswith("  ") and ":" in line]

        # Check order matches dataclass definition
        assert "name" in field_lines[0]
        assert "count" in field_lines[1]
        assert "active" in field_lines[2]


class TestBuildEpilog:
    """Tests for build_epilog function."""

    def test_build_epilog_single_dataclass(self) -> None:
        """Test epilog generation for single dataclass."""
        epilog = build_epilog(SimpleDataclass)

        # Check header
        assert "JSON Output Schema:" in epilog

        # Check schema content
        assert "Simple dataclass for testing." in epilog
        assert "name: string" in epilog
        assert "count: integer" in epilog
        assert "active: boolean" in epilog

    def test_build_epilog_multiple_dataclasses(self) -> None:
        """Test epilog generation for multiple dataclasses."""
        epilog = build_epilog(SimpleDataclass, OptionalFieldsDataclass)

        # Check both schemas are included
        assert "Simple dataclass for testing." in epilog
        assert "Dataclass with optional fields." in epilog

        # Check both have their fields
        assert "name: string" in epilog
        assert "required: string" in epilog
        assert "optional: string | null" in epilog

    def test_build_epilog_formatting(self) -> None:
        """Test that epilog has proper formatting (blank lines between schemas)."""
        epilog = build_epilog(SimpleDataclass, OptionalFieldsDataclass)

        # Should have double newline between schemas
        assert "\n\n" in epilog

        # Should start with header
        assert epilog.startswith("JSON Output Schema:\n\n")


class TestSchemaCommand:
    """Tests for SchemaCommand Click integration."""

    def test_schema_command_preserves_epilog_formatting(self) -> None:
        """Test that SchemaCommand preserves epilog newlines."""

        @click.command(
            name="test-command",
            cls=SchemaCommand,
            epilog=build_epilog(SimpleDataclass),
        )
        def test_command() -> None:
            """Test command with schema."""
            pass

        # Get help text
        ctx = click.Context(test_command)
        help_text = test_command.get_help(ctx)

        # Check that schema appears in help with formatting preserved
        assert "JSON Output Schema:" in help_text
        assert "Simple dataclass for testing." in help_text
        assert "name: string" in help_text

    def test_schema_command_with_multiple_dataclasses(self) -> None:
        """Test SchemaCommand with multiple dataclasses in epilog."""

        @click.command(
            name="test-command",
            cls=SchemaCommand,
            epilog=build_epilog(SimpleDataclass, LiteralFieldsDataclass),
        )
        @click.argument("input_value")
        def test_command(input_value: str) -> None:
            """Test command with multiple schemas."""
            pass

        ctx = click.Context(test_command)
        help_text = test_command.get_help(ctx)

        # Check both schemas appear
        assert "Simple dataclass for testing." in help_text
        assert "Dataclass with Literal type fields." in help_text
        assert "name: string" in help_text
        assert 'status: "success" | "error" | "pending"' in help_text

    def test_schema_command_integration_with_click_decorators(self) -> None:
        """Test that SchemaCommand works with standard Click decorators."""

        @click.command(
            name="integration-test",
            cls=SchemaCommand,
            epilog=build_epilog(SimpleDataclass),
        )
        @click.argument("name")
        @click.option("--verbose", is_flag=True, help="Enable verbose output")
        def integration_command(name: str, verbose: bool) -> None:
            """Integration test command."""
            pass

        ctx = click.Context(integration_command)
        help_text = integration_command.get_help(ctx)

        # Check all parts present
        assert "Integration test command." in help_text
        assert "NAME" in help_text.upper()
        assert "--verbose" in help_text
        assert "JSON Output Schema:" in help_text
        assert "Simple dataclass for testing." in help_text


class TestEndToEndScenarios:
    """End-to-end integration tests for schema system."""

    def test_success_error_pattern(self) -> None:
        """Test common success/error result pattern."""

        @dataclass
        class SuccessResult:
            """Success result with data."""

            success: bool
            data: str
            count: int

        @dataclass
        class ErrorResult:
            """Error result with message."""

            success: bool
            error: Literal["not_found", "invalid_input"]
            message: str

        epilog = build_epilog(SuccessResult, ErrorResult)

        # Verify both schemas are documented
        assert "Success result with data." in epilog
        assert "data: string" in epilog
        assert "count: integer" in epilog

        assert "Error result with message." in epilog
        assert 'error: "not_found" | "invalid_input"' in epilog
        assert "message: string" in epilog

    def test_nested_optional_collections(self) -> None:
        """Test schema generation with complex nested optional collections."""

        @dataclass
        class ComplexResult:
            """Complex result with nested structures."""

            items: list[dict[str, str | None]]
            metadata: dict[str, list[int]] | None

        schema = generate_schema(ComplexResult)

        assert "items: list[dict[string, string | null]]" in schema
        assert "metadata: dict[string, list[integer]] | null" in schema
