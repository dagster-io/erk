"""Shared serialization for PlanRowData to JSON-compatible dicts.

Used by both the dash-data exec script and the pr list --json command
to ensure consistent output shapes.
"""

import dataclasses
from datetime import datetime
from typing import Any

from erk.tui.data.types import PlanRowData


def serialize_plan_row(row: PlanRowData) -> dict[str, Any]:
    """Convert PlanRowData to JSON-serializable dict.

    Handles datetime fields (to ISO 8601 strings) and tuple fields
    (log_entries, objective_deps_plans) to lists for JSON compatibility.
    """
    data = dataclasses.asdict(row)
    for key in ("last_local_impl_at", "last_remote_impl_at", "updated_at", "created_at"):
        if isinstance(data[key], datetime):
            data[key] = data[key].isoformat()
    # Convert log_entries tuple of tuples to list of lists
    data["log_entries"] = [list(entry) for entry in row.log_entries]
    # Convert objective_deps_plans tuple of tuples to list of lists
    data["objective_deps_plans"] = [list(entry) for entry in row.objective_deps_plans]
    return data
