"""Tests for schema formatting utilities.

These are Layer 3 pure unit tests - no dependencies, no fakes, no mocks.
Tests the schema formatting functions that convert TypedDict type hints
to human-readable schema documentation for CLI help.
"""

from typing import Literal, TypedDict

import click

from dot_agent_kit.cli.schema_formatting import (
    JSON_OUTPUT_SCHEMA_ATTR,
    format_schema_for_help,
    format_type_for_schema,
    format_typeddict_for_schema,
    get_json_output_schema,
    is_typeddict,
    json_output,
)


class TestFormatTypeForSchema:
    """Tests for format_type_for_schema function."""

    # Basic types

    def test_str_type(self) -> None:
        result = format_type_for_schema(str)
        assert result == "str"

    def test_int_type(self) -> None:
        result = format_type_for_schema(int)
        assert result == "int"

    def test_bool_type(self) -> None:
        result = format_type_for_schema(bool)
        assert result == "bool"

    def test_float_type(self) -> None:
        result = format_type_for_schema(float)
        assert result == "float"

    # Literal types

    def test_literal_single_bool_true(self) -> None:
        result = format_type_for_schema(Literal[True])
        assert result == "true"

    def test_literal_single_bool_false(self) -> None:
        result = format_type_for_schema(Literal[False])
        assert result == "false"

    def test_literal_single_str(self) -> None:
        result = format_type_for_schema(Literal["success"])
        assert result == '"success"'

    def test_literal_single_int(self) -> None:
        result = format_type_for_schema(Literal[42])
        assert result == "42"

    def test_literal_multiple_strings(self) -> None:
        result = format_type_for_schema(Literal["started", "completed", "failed"])
        assert result == '"started" | "completed" | "failed"'

    def test_literal_multiple_bools(self) -> None:
        result = format_type_for_schema(Literal[True, False])
        assert result == "true | false"

    def test_literal_mixed_types(self) -> None:
        result = format_type_for_schema(Literal["auto", 1, 2, True])
        assert result == '"auto" | 1 | 2 | true'

    # Union types

    def test_union_basic_types(self) -> None:
        result = format_type_for_schema(str | int)
        assert result == "str | int"

    def test_union_with_none(self) -> None:
        result = format_type_for_schema(str | None)
        assert result == "str | None"

    def test_union_multiple_types(self) -> None:
        result = format_type_for_schema(str | int | float | None)
        assert result == "str | int | float | None"

    # List types

    def test_list_with_type_parameter(self) -> None:
        result = format_type_for_schema(list[str])
        assert result == "list[str]"

    def test_list_with_int(self) -> None:
        result = format_type_for_schema(list[int])
        assert result == "list[int]"

    def test_list_without_parameter(self) -> None:
        result = format_type_for_schema(list)
        assert result == "list"

    def test_nested_list(self) -> None:
        result = format_type_for_schema(list[list[str]])
        assert result == "list[list[str]]"

    # Dict types

    def test_dict_with_type_parameters(self) -> None:
        result = format_type_for_schema(dict[str, int])
        assert result == "dict[str, int]"

    def test_dict_string_to_string(self) -> None:
        result = format_type_for_schema(dict[str, str])
        assert result == "dict[str, str]"

    def test_dict_without_parameters(self) -> None:
        result = format_type_for_schema(dict)
        assert result == "dict"

    # Complex nested types

    def test_dict_with_union_value(self) -> None:
        result = format_type_for_schema(dict[str, int | str])
        assert result == "dict[str, int | str]"

    def test_list_of_union(self) -> None:
        result = format_type_for_schema(list[str | int])
        assert result == "list[str | int]"

    # Fallback cases

    def test_custom_class_with_name(self) -> None:
        class CustomType:
            pass

        result = format_type_for_schema(CustomType)
        assert result == "CustomType"


class TestIsTypedDict:
    """Tests for is_typeddict function."""

    def test_typeddict_class(self) -> None:
        class MyTypedDict(TypedDict):
            field: str

        assert is_typeddict(MyTypedDict) is True

    def test_regular_class(self) -> None:
        class RegularClass:
            field: str

        assert is_typeddict(RegularClass) is False

    def test_dict_subclass_without_annotations(self) -> None:
        class DictSubclass(dict):
            pass

        # Even dict subclasses without __annotations__ fail the check
        assert is_typeddict(DictSubclass) is False

    def test_non_class_type(self) -> None:
        assert is_typeddict("not a class") is False  # type: ignore[arg-type]

    def test_none_type(self) -> None:
        assert is_typeddict(None) is False  # type: ignore[arg-type]

    def test_built_in_dict(self) -> None:
        assert is_typeddict(dict) is False


class TestFormatTypedDictForSchema:
    """Tests for format_typeddict_for_schema function."""

    def test_simple_typeddict(self) -> None:
        class SimpleResponse(TypedDict):
            message: str
            count: int

        lines = format_typeddict_for_schema(SimpleResponse)
        assert lines == [
            "  SimpleResponse:",
            "    message: str",
            "    count: int",
        ]

    def test_typeddict_with_success_true(self) -> None:
        class SuccessResponse(TypedDict):
            success: Literal[True]
            data: str

        lines = format_typeddict_for_schema(SuccessResponse)
        assert lines == [
            "  SuccessResponse (success=true):",
            "    success: true",
            "    data: str",
        ]

    def test_typeddict_with_success_false(self) -> None:
        class ErrorResponse(TypedDict):
            success: Literal[False]
            error: str

        lines = format_typeddict_for_schema(ErrorResponse)
        assert lines == [
            "  ErrorResponse (success=false):",
            "    success: false",
            "    error: str",
        ]

    def test_typeddict_custom_indent(self) -> None:
        class Response(TypedDict):
            field: str

        lines = format_typeddict_for_schema(Response, indent=4)
        assert lines == [
            "    Response:",
            "      field: str",
        ]

    def test_typeddict_zero_indent(self) -> None:
        class Response(TypedDict):
            field: str

        lines = format_typeddict_for_schema(Response, indent=0)
        assert lines == [
            "Response:",
            "  field: str",
        ]

    def test_typeddict_with_complex_fields(self) -> None:
        class ComplexResponse(TypedDict):
            items: list[str]
            metadata: dict[str, int]
            status: str | None

        lines = format_typeddict_for_schema(ComplexResponse)
        assert lines == [
            "  ComplexResponse:",
            "    items: list[str]",
            "    metadata: dict[str, int]",
            "    status: str | None",
        ]

    def test_typeddict_with_literal_field(self) -> None:
        class StatusResponse(TypedDict):
            status: Literal["pending", "running", "done"]
            value: int

        lines = format_typeddict_for_schema(StatusResponse)
        assert lines == [
            "  StatusResponse:",
            '    status: "pending" | "running" | "done"',
            "    value: int",
        ]


class TestFormatSchemaForHelp:
    """Tests for format_schema_for_help function."""

    def test_single_typeddict(self) -> None:
        class SingleResponse(TypedDict):
            message: str

        result = format_schema_for_help(SingleResponse)
        expected = """
Output Schema:
  SingleResponse:
    message: str"""
        assert result == expected

    def test_union_of_typeddicts(self) -> None:
        class SuccessOutput(TypedDict):
            success: Literal[True]
            result: str

        class ErrorOutput(TypedDict):
            success: Literal[False]
            error: str

        result = format_schema_for_help(SuccessOutput | ErrorOutput)
        expected = """
Output Schema:
  SuccessOutput (success=true):
    success: true
    result: str

  ErrorOutput (success=false):
    success: false
    error: str"""
        assert result == expected

    def test_union_of_three_typeddicts(self) -> None:
        class TypeA(TypedDict):
            type: Literal["a"]

        class TypeB(TypedDict):
            type: Literal["b"]

        class TypeC(TypedDict):
            type: Literal["c"]

        result = format_schema_for_help(TypeA | TypeB | TypeC)
        # Should have blank lines between variants
        assert "TypeA:" in result
        assert "TypeB:" in result
        assert "TypeC:" in result
        # Count blank lines - should be 2 (between A-B and B-C)
        lines = result.split("\n")
        empty_lines_between = sum(
            1
            for i, line in enumerate(lines)
            if line == "" and i > 1  # Skip the first empty line in header
        )
        assert empty_lines_between == 2

    def test_non_typeddict_type(self) -> None:
        # Should return just the header when given a non-TypedDict
        result = format_schema_for_help(str)
        assert result == "\nOutput Schema:"

    def test_header_format(self) -> None:
        class Response(TypedDict):
            field: str

        result = format_schema_for_help(Response)
        # Should start with newline and "Output Schema:"
        assert result.startswith("\nOutput Schema:")


class TestRealWorldSchemas:
    """Tests with real-world-like OUTPUT_SCHEMA patterns."""

    def test_mark_impl_success_error_pattern(self) -> None:
        """Test the pattern used in mark_impl_started.py."""

        class MarkImplSuccess(TypedDict):
            success: Literal[True]
            issue_number: int

        class MarkImplError(TypedDict):
            success: Literal[False]
            error_type: str
            message: str

        OUTPUT_SCHEMA = MarkImplSuccess | MarkImplError

        result = format_schema_for_help(OUTPUT_SCHEMA)

        # Verify structure
        assert "Output Schema:" in result
        assert "MarkImplSuccess (success=true):" in result
        assert "MarkImplError (success=false):" in result
        assert "issue_number: int" in result
        assert "error_type: str" in result
        assert "message: str" in result

    def test_pr_prep_pattern(self) -> None:
        """Test a more complex schema pattern."""

        class PrPrepSuccess(TypedDict):
            success: Literal[True]
            branch_name: str
            commit_sha: str
            files_changed: list[str]

        class PrPrepError(TypedDict):
            success: Literal[False]
            error_type: Literal["no_changes", "git_error", "validation_failed"]
            message: str
            details: dict[str, str] | None

        OUTPUT_SCHEMA = PrPrepSuccess | PrPrepError

        result = format_schema_for_help(OUTPUT_SCHEMA)

        # Verify complex field types are properly formatted
        assert "files_changed: list[str]" in result
        assert 'error_type: "no_changes" | "git_error" | "validation_failed"' in result
        assert "details: dict[str, str] | None" in result


class TestEdgeCases:
    """Edge case tests for robustness."""

    def test_empty_typeddict(self) -> None:
        """TypedDict with no fields."""

        class EmptyResponse(TypedDict):
            pass

        lines = format_typeddict_for_schema(EmptyResponse)
        # Should still have the class name line
        assert lines == ["  EmptyResponse:"]

    def test_typeddict_with_none_type_field(self) -> None:
        class ResponseWithNone(TypedDict):
            maybe: str | None
            always_none: None

        lines = format_typeddict_for_schema(ResponseWithNone)
        assert "    maybe: str | None" in lines
        assert "    always_none: None" in lines

    def test_deeply_nested_type(self) -> None:
        """Test deeply nested generic types."""
        result = format_type_for_schema(dict[str, list[dict[str, int | None]]])
        assert result == "dict[str, list[dict[str, int | None]]]"

    def test_union_preserves_order(self) -> None:
        """Union types should preserve their order in output."""

        class First(TypedDict):
            order: Literal[1]

        class Second(TypedDict):
            order: Literal[2]

        class Third(TypedDict):
            order: Literal[3]

        result = format_schema_for_help(First | Second | Third)
        lines = result.split("\n")

        # Find indices of each class
        first_idx = next(i for i, line in enumerate(lines) if "First:" in line)
        second_idx = next(i for i, line in enumerate(lines) if "Second:" in line)
        third_idx = next(i for i, line in enumerate(lines) if "Third:" in line)

        assert first_idx < second_idx < third_idx


class TestJsonOutputDecorator:
    """Tests for the @json_output decorator."""

    def test_stores_schema_on_command(self) -> None:
        """Decorator stores schema type on command object."""

        class Success(TypedDict):
            success: Literal[True]

        class Error(TypedDict):
            success: Literal[False]

        @json_output(Success | Error)
        @click.command()
        def my_command() -> None:
            pass

        assert hasattr(my_command, JSON_OUTPUT_SCHEMA_ATTR)
        assert getattr(my_command, JSON_OUTPUT_SCHEMA_ATTR) == Success | Error

    def test_appends_schema_to_help(self) -> None:
        """Decorator appends schema documentation to help text."""

        class Success(TypedDict):
            success: Literal[True]
            data: str

        @json_output(Success)
        @click.command()
        def my_command() -> None:
            """My command description."""
            pass

        help_text = my_command.help or ""
        assert "Output Schema:" in help_text
        assert "Success (success=true):" in help_text
        assert "data: str" in help_text

    def test_preserves_original_help(self) -> None:
        """Decorator preserves original help text."""

        class Result(TypedDict):
            value: int

        @json_output(Result)
        @click.command()
        def my_command() -> None:
            """Original help text."""
            pass

        help_text = my_command.help or ""
        assert "Original help text." in help_text
        assert "Output Schema:" in help_text

    def test_handles_empty_help(self) -> None:
        """Decorator works when command has no help text."""

        class Result(TypedDict):
            value: int

        @json_output(Result)
        @click.command()
        def my_command() -> None:
            pass

        help_text = my_command.help or ""
        assert "Output Schema:" in help_text
        assert "value: int" in help_text

    def test_get_json_output_schema_returns_schema(self) -> None:
        """get_json_output_schema retrieves stored schema."""

        class Success(TypedDict):
            ok: Literal[True]

        @json_output(Success)
        @click.command()
        def my_command() -> None:
            pass

        schema = get_json_output_schema(my_command)
        assert schema == Success

    def test_get_json_output_schema_returns_none_for_undecorated(self) -> None:
        """get_json_output_schema returns None for undecorated commands."""

        @click.command()
        def my_command() -> None:
            pass

        schema = get_json_output_schema(my_command)
        assert schema is None

    def test_works_with_click_options(self) -> None:
        """Decorator works with click options."""

        class Result(TypedDict):
            name: str

        @json_output(Result)
        @click.command()
        @click.option("--name", required=True)
        def my_command(name: str) -> None:
            """Command with options."""
            pass

        help_text = my_command.help or ""
        assert "Output Schema:" in help_text
        assert getattr(my_command, JSON_OUTPUT_SCHEMA_ATTR) == Result

    def test_works_with_click_arguments(self) -> None:
        """Decorator works with click arguments."""

        class Result(TypedDict):
            value: int

        @json_output(Result)
        @click.command()
        @click.argument("value", type=int)
        def my_command(value: int) -> None:
            """Command with arguments."""
            pass

        help_text = my_command.help or ""
        assert "Output Schema:" in help_text
        assert getattr(my_command, JSON_OUTPUT_SCHEMA_ATTR) == Result
