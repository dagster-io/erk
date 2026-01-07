"""Real implementation of RepoLevelStateStore - reads/writes real filesystem."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from erk_shared.gateway.repo_state.abc import RepoLevelStateStore

if TYPE_CHECKING:
    from erk.core.worktree_pool import PoolState


class RealRepoLevelStateStore(RepoLevelStateStore):
    """Production implementation - reads/writes real filesystem.

    This is the only implementation that should access the real
    ~/.erk/repos/<repo>/ directories. All other code accesses state
    through ErkContext.repo_state_store.
    """

    def load_pool_state(self, pool_json_path: Path) -> PoolState | None:
        """Load pool state from JSON file.

        Args:
            pool_json_path: Path to the pool.json file

        Returns:
            PoolState if file exists and is valid, None otherwise
        """
        # Import here to avoid circular dependency at module level
        from erk.core.worktree_pool import PoolState, SlotAssignment, SlotInfo

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

    def save_pool_state(self, pool_json_path: Path, state: PoolState) -> None:
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
                {"name": s.name, "last_objective_issue": s.last_objective_issue}
                for s in state.slots
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
