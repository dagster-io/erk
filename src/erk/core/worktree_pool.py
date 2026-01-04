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

    A slot that has been pre-created with a worktree and placeholder branch,
    ready for assignment to feature branches.

    Attributes:
        name: The pool slot identifier (e.g., "erk-managed-wt-01")
        last_objective_issue: Issue number of the last objective worked on in this slot.
            Persists across assignment cycles so /erk:objective-next-plan can default to it.
    """

    name: str
    last_objective_issue: int | None


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
        slots: Tuple of initialized slots (may or may not have assignments)
        assignments: Tuple of current slot assignments (immutable)
    """

    version: str
    pool_size: int
    slots: tuple[SlotInfo, ...]
    assignments: tuple[SlotAssignment, ...]

    @classmethod
    def test(
        cls,
        *,
        version: str | None = None,
        pool_size: int | None = None,
        slots: tuple[SlotInfo, ...] | None = None,
        assignments: tuple[SlotAssignment, ...] | None = None,
    ) -> PoolState:
        """Create a PoolState with sensible test defaults.

        All parameters are optional and use sensible defaults for testing:
        - version: "1.0"
        - pool_size: 4
        - slots: ()
        - assignments: ()
        """
        return cls(
            version=version if version is not None else "1.0",
            pool_size=pool_size if pool_size is not None else 4,
            slots=slots if slots is not None else (),
            assignments=assignments if assignments is not None else (),
        )


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

    slots = tuple(
        SlotInfo(name=s["name"], last_objective_issue=s.get("last_objective_issue"))
        for s in data.get("slots", [])
    )

    assignments = tuple(
        SlotAssignment(
            slot_name=a["slot_name"],
            branch_name=a["branch_name"],
            assigned_at=a["assigned_at"],
            worktree_path=Path(a["worktree_path"]),
        )
        for a in data.get("assignments", [])
    )

    return PoolState(
        version=data.get("version", "1.0"),
        pool_size=data.get("pool_size", 4),
        slots=slots,
        assignments=assignments,
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
        "slots": [
            {"name": s.name, "last_objective_issue": s.last_objective_issue} for s in state.slots
        ],
        "assignments": [
            {
                "slot_name": a.slot_name,
                "branch_name": a.branch_name,
                "assigned_at": a.assigned_at,
                "worktree_path": str(a.worktree_path),
            }
            for a in state.assignments
        ],
    }

    pool_json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def update_slot_objective(
    state: PoolState, slot_name: str, objective_issue: int | None
) -> PoolState:
    """Return new PoolState with slot's last_objective_issue updated.

    Args:
        state: Current pool state
        slot_name: Name of the slot to update
        objective_issue: Issue number to set, or None to clear

    Returns:
        New PoolState with the updated slot. If slot_name is not found,
        returns state unchanged.
    """
    new_slots: list[SlotInfo] = []
    found = False

    for slot in state.slots:
        if slot.name == slot_name:
            new_slots.append(SlotInfo(name=slot.name, last_objective_issue=objective_issue))
            found = True
        else:
            new_slots.append(slot)

    if not found:
        return state

    return PoolState(
        version=state.version,
        pool_size=state.pool_size,
        slots=tuple(new_slots),
        assignments=state.assignments,
    )
