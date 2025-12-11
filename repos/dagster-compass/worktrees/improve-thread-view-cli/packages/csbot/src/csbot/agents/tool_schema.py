"""Shared utilities for building JSON Schemas for tool parameters."""

from __future__ import annotations

import inspect
from typing import Any, get_args, get_origin, get_type_hints


def _is_optional(t: Any) -> tuple[bool, Any]:
    """Return (is_optional, inner_type) for Optional[inner_type]."""
    origin = get_origin(t)
    if origin is None:
        return (False, t)
    args = get_args(t)
    # Optional[T] is Union[T, NoneType]
    if origin is getattr(__import__("typing"), "Union") and type(None) in args:
        inner = [a for a in args if a is not type(None)]  # noqa: E721
        return (True, inner[0] if inner else Any)
    return (False, t)


def build_input_schema_from_function(func) -> dict[str, Any]:
    """Build a minimal JSON schema for a tool function's parameters.

    Aligns with the Anthropic adapter's simple mapping: primitives only.
    - str -> string, int -> integer, float -> number, bool -> boolean
    - list -> array[string], dict -> object
    - Unknown types default to string
    - Required params: those without defaults
    """
    sig = inspect.signature(func)
    hints = get_type_hints(func)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue

        annotated = hints.get(name, str)
        is_opt, inner = _is_optional(annotated)
        t = inner if is_opt else annotated

        if t is str:
            schema = {"type": "string"}
        elif t is int:
            schema = {"type": "integer"}
        elif t is float:
            schema = {"type": "number"}
        elif t is bool:
            schema = {"type": "boolean"}
        elif t is list or get_origin(t) is list:
            schema = {"type": "array", "items": {"type": "string"}}
        elif t is dict or get_origin(t) is dict:
            schema = {"type": "object"}
        else:
            schema = {"type": "string"}

        properties[name] = schema

        if param.default is inspect.Parameter.empty and not is_opt:
            required.append(name)

    return {"type": "object", "properties": properties, "required": required}
