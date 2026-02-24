"""Generic renderer for output models with Meta inner classes.

Four functions that work with ANY output model having the appropriate Meta:
- render_json_list: Serialize list of entries to JSON
- render_json_detail: Serialize single entry to JSON
- render_table: Render list as Rich Table to stderr
- render_detail: Render single entry as formatted fields to stderr
"""

import json
from dataclasses import asdict
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from erk.cli.output_framework.rendering_types import DetailMeta, DetailSection, TableMeta


def _get_table_meta(entry_type: type) -> TableMeta:
    """Extract TableMeta from an output model's Meta inner class."""
    meta = getattr(entry_type, "Meta", None)
    if meta is None:
        raise ValueError(f"{entry_type.__name__} has no Meta inner class")
    table_meta = getattr(meta, "table", None)
    if table_meta is None:
        raise ValueError(f"{entry_type.__name__}.Meta has no table attribute")
    return table_meta


def _get_detail_meta(entry_type: type) -> DetailMeta:
    """Extract DetailMeta from an output model's Meta inner class."""
    meta = getattr(entry_type, "Meta", None)
    if meta is None:
        raise ValueError(f"{entry_type.__name__} has no Meta inner class")
    detail_meta = getattr(meta, "detail", None)
    if detail_meta is None:
        raise ValueError(f"{entry_type.__name__}.Meta has no detail attribute")
    return detail_meta


def _resolve_field_value(entry: Any, field_path: str) -> Any:
    """Resolve a dotted field path (e.g., 'header.created_by') on an entry."""
    obj = entry
    for part in field_path.split("."):
        if obj is None:
            return None
        obj = getattr(obj, part, None)
    return obj


def render_json_list(entries: list[Any]) -> str:
    """Render a list of output model entries as JSON.

    Uses Meta.table.json_root as the wrapper key.

    Args:
        entries: List of output model instances with Meta.table

    Returns:
        JSON string with structure {"<json_root>": [...], "total_count": N}
    """
    if not entries:
        # Need at least the type to get json_root; use a sensible fallback
        return json.dumps({"items": [], "total_count": 0}, indent=2)

    table_meta = _get_table_meta(type(entries[0]))
    serialized = [asdict(entry) for entry in entries]
    output = {
        table_meta.json_root: serialized,
        "total_count": len(serialized),
    }
    return json.dumps(output, indent=2, default=str)


def render_json_detail(entry: Any) -> str:
    """Render a single output model entry as JSON.

    Uses Meta.detail.json_root as the wrapper key.

    Args:
        entry: Output model instance with Meta.detail

    Returns:
        JSON string with structure {"<json_root>": {...}}
    """
    detail_meta = _get_detail_meta(type(entry))
    serialized = asdict(entry)
    output = {detail_meta.json_root: serialized}
    return json.dumps(output, indent=2, default=str)


def render_table(entries: list[Any]) -> None:
    """Render a list of output model entries as a Rich Table to stderr.

    Reads Meta.table.columns to build columns, calls format_method or raw
    field access, and applies link_field wrapping.

    Args:
        entries: List of output model instances with Meta.table
    """
    if not entries:
        return

    table_meta = _get_table_meta(type(entries[0]))
    table = Table(show_header=True, header_style="bold")

    for col in table_meta.columns:
        table.add_column(
            col.header,
            style=col.style,
            no_wrap=col.no_wrap,
            width=col.width,
        )

    for entry in entries:
        row_values: list[str] = []
        for col in table_meta.columns:
            # Get cell value via format_method or raw field
            if col.format_method is not None:
                method = getattr(entry, col.format_method, None)
                if method is not None:
                    cell_value = method()
                else:
                    cell_value = str(getattr(entry, col.field, "-"))
            else:
                raw = getattr(entry, col.field, None)
                cell_value = str(raw) if raw is not None else "-"

            # Apply link wrapping if link_field is specified
            if col.link_field is not None:
                link_url = getattr(entry, col.link_field, None)
                if link_url is not None:
                    cell_value = f"[link={link_url}]{cell_value}[/link]"

            row_values.append(cell_value)

        table.add_row(*row_values)

    console = Console(stderr=True, width=200, force_terminal=True)
    console.print(table)
    console.print()


def _render_detail_section(entry: Any, section: DetailSection) -> list[str]:
    """Render a single detail section, returning formatted lines.

    Args:
        entry: Output model instance
        section: Section definition with fields

    Returns:
        List of formatted lines (may be empty if skip_if_empty and all None)
    """
    label_width = 12
    field_lines: list[str] = []

    for detail_field in section.fields:
        # Get value: use format_method if specified, else resolve field path
        if detail_field.format_method is not None:
            method = getattr(entry, detail_field.format_method, None)
            if method is not None:
                value = method()
            else:
                value = _resolve_field_value(entry, detail_field.field)
        else:
            value = _resolve_field_value(entry, detail_field.field)

        # Convert to string
        if value is None:
            if detail_field.skip_if_none:
                continue
            display_value = "-"
        else:
            display_value = str(value)

        styled_label = click.style(f"{detail_field.label}:".ljust(label_width), dim=True)
        if detail_field.style is not None:
            display_value = click.style(display_value, bold=(detail_field.style == "bold"))
        field_lines.append(f"{styled_label} {display_value}")

    # Check skip_if_empty
    if section.skip_if_empty and not field_lines:
        return []

    lines: list[str] = []
    if section.title is not None:
        lines.append("")
        title_str = f"\u2500\u2500\u2500 {section.title} \u2500\u2500\u2500"
        lines.append(click.style(title_str, bold=True))
    lines.extend(field_lines)
    return lines


def render_detail(entry: Any) -> None:
    """Render a single output model entry as formatted detail fields to stderr.

    Reads Meta.detail.sections to iterate fields, calls format_method,
    applies skip_if_none/skip_if_empty logic.

    Args:
        entry: Output model instance with Meta.detail
    """
    detail_meta = _get_detail_meta(type(entry))
    all_lines: list[str] = [""]

    for section in detail_meta.sections:
        section_lines = _render_detail_section(entry, section)
        all_lines.extend(section_lines)

    for line in all_lines:
        click.echo(line, err=True)
