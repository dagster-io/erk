"""Pure formatting functions for Claude CLI output.

These functions are pure (no side effects) and return formatted strings
ready for printing. They can be easily unit tested without mocking.
"""

import json


def format_string_parameter(param_name: str, param_value: str) -> list[str]:
    """Format string parameter (inline or multiline).

    Args:
        param_name: Parameter name to display
        param_value: String value to format

    Returns:
        List of formatted lines ready to print.
        Single-line strings return one line, multiline strings return multiple.
    """
    if "\n" in param_value:
        lines = [f"   {param_name}:"]
        lines.extend(f"      {line}" for line in param_value.split("\n"))
        return lines
    else:
        return [f"   {param_name}: {param_value}"]


def format_complex_parameter(param_name: str, param_value: dict | list) -> list[str]:
    """Format complex parameter (list/dict) as formatted JSON.

    Args:
        param_name: Parameter name to display
        param_value: Dictionary or list to format as JSON

    Returns:
        List of formatted lines with indented JSON.
    """
    json_str = json.dumps(param_value, indent=2, ensure_ascii=False)
    lines = [f"   {param_name}:"]
    lines.extend(f"      {line}" for line in json_str.split("\n"))
    return lines


def format_string_result(result_content: str) -> list[str]:
    """Format string result with indentation.

    Args:
        result_content: String content to format

    Returns:
        List of formatted lines with 3-space indentation.
    """
    return [f"   {line}" for line in result_content.split("\n")]


def format_structured_result(result_content: list) -> list[str]:
    """Format structured result content.

    Extracts text from structured content items and formats with indentation.

    Args:
        result_content: List of result items (dicts with type and content)

    Returns:
        List of formatted lines with 3-space indentation.
    """
    lines = []
    for result_item in result_content:
        if not isinstance(result_item, dict):
            continue

        if result_item.get("type") == "text":
            text = result_item.get("text", "")
            lines.extend(f"   {line}" for line in text.split("\n"))

    return lines
