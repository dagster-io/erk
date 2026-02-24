"""Rendering metadata types for output models.

These frozen dataclasses describe how to render output model fields
as Rich tables, detail views, or JSON. A generic renderer inspects
these types to produce output without per-command rendering code.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Column:
    """Metadata for a Rich table column."""

    field: str
    header: str
    width: int | None
    style: str | None
    no_wrap: bool
    format_method: str | None
    link_field: str | None


@dataclass(frozen=True)
class DetailField:
    """Metadata for a field in detail view."""

    field: str
    label: str
    format_method: str | None
    style: str | None
    skip_if_none: bool


@dataclass(frozen=True)
class DetailSection:
    """A named section containing DetailFields."""

    title: str | None
    fields: tuple[DetailField, ...]
    skip_if_empty: bool


@dataclass(frozen=True)
class TableMeta:
    """Table rendering metadata with JSON root key and column definitions."""

    json_root: str
    columns: tuple[Column, ...]


@dataclass(frozen=True)
class DetailMeta:
    """Detail rendering metadata with JSON root key and section definitions."""

    json_root: str
    sections: tuple[DetailSection, ...]
