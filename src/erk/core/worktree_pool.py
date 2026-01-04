"""Worktree pool state management.

Provides dataclasses and persistence functions for managing a pool of
pre-created worktrees that can be assigned to branches on demand.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SlotInfo:
    """Represents an initialized pool slot.

    A slot is a pre-created worktree with a placeholder branch.
    Slots can be either inactive (available) or active (has an assignment).

    Attributes:
        name: The slot identifier (e.g., "erk-managed-wt-01")
    """

    name: str


@dataclass(frozen=True)
class SlotAssignment:
    """Represents a branch assignment to a worktree slot.

    Attributes:
        slot_name: The pool slot identifier (e.g., "erk-managed-wt-01")
        branch_name: The git branch assigned to this slot
        assigned_at: ISO timestamp when the assignment was made
        worktree_path: Filesystem path to the worktree directory
    """

    slot_name: str
    branch_name: str
    assigned_at: str
    worktree_path: Path


@dataclass(frozen=True)
class PoolState:
    """Represents the complete state of the worktree pool.

    Attributes:
        version: Schema version for forward compatibility
        pool_size: Maximum number of slots in the pool
        assignments: Tuple of current slot assignments (immutable)
        slots: Tuple of initialized slots (immutable)
    """

    version: str
    pool_size: int
    assignments: tuple[SlotAssignment, ...]
    slots: tuple[SlotInfo, ...]


def load_pool_state(pool_json_path: Path) -> PoolState | None:
    """Load pool state from JSON file.

    Args:
        pool_json_path: Path to the pool.json file

    Returns:
        PoolState if file exists and is valid, None otherwise
    """
    if not pool_json_path.exists():
        return None

    content = pool_json_path.read_text(encoding="utf-8")
    data = json.loads(content)

    assignments = tuple(
        SlotAssignment(
            slot_name=a["slot_name"],
            branch_name=a["branch_name"],
            assigned_at=a["assigned_at"],
            worktree_path=Path(a["worktree_path"]),
        )
        for a in data.get("assignments", [])
    )

    slots = tuple(SlotInfo(name=s["name"]) for s in data.get("slots", []))

    return PoolState(
        version=data.get("version", "1.0"),
        pool_size=data.get("pool_size", 4),
        assignments=assignments,
        slots=slots,
    )


def save_pool_state(pool_json_path: Path, state: PoolState) -> None:
    """Save pool state to JSON file.

    Creates parent directories if they don't exist.

    Args:
        pool_json_path: Path to the pool.json file
        state: Pool state to persist
    """
    pool_json_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": state.version,
        "pool_size": state.pool_size,
        "assignments": [
            {
                "slot_name": a.slot_name,
                "branch_name": a.branch_name,
                "assigned_at": a.assigned_at,
                "worktree_path": str(a.worktree_path),
            }
            for a in state.assignments
        ],
        "slots": [{"name": s.name} for s in state.slots],
    }

    pool_json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
