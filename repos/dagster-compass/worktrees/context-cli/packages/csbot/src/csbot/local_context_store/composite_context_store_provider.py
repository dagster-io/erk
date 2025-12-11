"""Composite context store manager that combines multiple context stores.

This module provides a CompositeContextStoreManager that merges a mutable
user-accessible context store with read-only shared context stores (e.g., for
dataset documentation). The composite manager presents a unified view where:

- Datasets from both stores are merged (shared store provides read-only dataset docs)
- General context, channels, and cronjobs come only from the mutable store
- System prompts come from the mutable store
- The project configuration comes from the mutable store
- Write operations filter out shared datasets (only writes mutable datasets)

This enables sharing common dataset documentation across multiple organizations
while allowing each organization to maintain their own context and configuration.
"""

import asyncio
from collections.abc import Sequence
from typing import TYPE_CHECKING

from csbot.contextengine.contextstore_protocol import ContextStore
from csbot.contextengine.diff import compare_datasets

if TYPE_CHECKING:
    from csbot.contextengine.protocol import ContextStoreManager


class CompositeContextStoreManager:
    """Manager that merges a mutable context store with read-only shared stores.

    The composite manager combines multiple context stores:
    1. Mutable manager: User-accessible manager for org-specific context, channels, cronjobs
    2. Shared stores: Read-only stores containing only dataset documentation

    The merged context store includes:
    - All datasets from all stores (shared store datasets are read-only)
    - All general context, channels, and cronjobs from the mutable store only
    - System prompt from the mutable store
    - Project configuration from the mutable store

    Write operations:
    - Mutations filter out shared datasets before writing to mutable store
    - Only mutable datasets are persisted
    """

    def __init__(
        self,
        mutable_manager: "ContextStoreManager",
        shared_dataset_stores: Sequence["ContextStoreManager"],
    ):
        """Initialize the composite manager.

        Args:
            mutable_manager: Manager for the mutable user-accessible context store
            shared_dataset_stores: Stores that provide get_context_store() for read-only datasets
        """
        self.mutable_manager = mutable_manager
        self.shared_dataset_stores = shared_dataset_stores

    async def get_context_store(self) -> ContextStore:
        """Get the merged context store.

        Loads all stores in parallel and merges them, with the mutable store
        taking precedence for datasets that exist in multiple stores.

        Returns:
            ContextStore: Merged context store with datasets from all sources
        """
        stores = await asyncio.gather(
            self.mutable_manager.get_context_store(),
            *[store.get_context_store() for store in self.shared_dataset_stores],
        )
        mutable_store = stores[0]
        shared_stores = stores[1:]

        # Build sets for quick lookup
        mutable_datasets_set = {dataset for dataset, _ in mutable_store.datasets}

        # Merge datasets: add shared datasets that aren't in mutable store
        merged_datasets = list(mutable_store.datasets)
        seen_datasets = mutable_datasets_set.copy()

        for shared_store in shared_stores:
            for dataset, documentation in shared_store.datasets:
                if dataset not in seen_datasets:
                    merged_datasets.append((dataset, documentation))
                    seen_datasets.add(dataset)

        # Sort merged datasets to ensure consistent ordering
        merged_datasets.sort(key=lambda x: (x[0].connection, x[0].table_name))

        # Create merged context store using mutable store as base
        return mutable_store.model_copy(update={"datasets": merged_datasets})

    async def mutate(
        self, title: str, body: str, commit: bool, before: ContextStore, after: ContextStore
    ) -> str:
        """Mutate the context store, validating no changes to shared datasets.

        Only datasets that exist in the mutable store are written. Raises an error
        if any shared (immutable) datasets are modified.

        Args:
            title: PR title
            body: PR body
            commit: Whether to auto-merge
            before: Context store before mutation
            after: Context store after mutation

        Returns:
            PR URL or commit URL

        Raises:
            ValueError: If any shared (immutable) datasets are modified
        """
        # Get current shared datasets (LBYL - check before acting)
        shared_stores = await asyncio.gather(
            *[store.get_context_store() for store in self.shared_dataset_stores]
        )

        # Build set of shared dataset keys for quick lookup
        shared_dataset_keys = set()
        for shared_store in shared_stores:
            for dataset, _ in shared_store.datasets:
                shared_dataset_keys.add(dataset)

        # Filter to only shared datasets from before/after
        before_shared_datasets = [
            (ds, doc) for ds, doc in before.datasets if ds in shared_dataset_keys
        ]
        after_shared_datasets = [
            (ds, doc) for ds, doc in after.datasets if ds in shared_dataset_keys
        ]

        # Use compare_datasets to detect changes to shared datasets (LBYL)
        added, removed, modified = compare_datasets(before_shared_datasets, after_shared_datasets)

        # If any shared datasets were modified, raise an error
        if added or removed or modified:
            error_messages = []
            for ds, _ in added:
                error_messages.append(f"{ds.connection}/{ds.table_name} (added)")
            for ds in removed:
                error_messages.append(f"{ds.connection}/{ds.table_name} (removed)")
            for ds_diff in modified:
                error_messages.append(
                    f"{ds_diff.dataset.connection}/{ds_diff.dataset.table_name} (modified)"
                )

            raise ValueError(
                f"Cannot modify shared (immutable) datasets: {', '.join(error_messages)}"
            )

        # Filter datasets to only include mutable ones
        mutable_before_datasets = [
            (dataset, doc) for dataset, doc in before.datasets if dataset not in shared_dataset_keys
        ]
        mutable_after_datasets = [
            (dataset, doc) for dataset, doc in after.datasets if dataset not in shared_dataset_keys
        ]

        # Create filtered context stores with only mutable datasets
        filtered_before = before.model_copy(update={"datasets": mutable_before_datasets})
        filtered_after = after.model_copy(update={"datasets": mutable_after_datasets})

        # Delegate to mutable manager with filtered datasets
        return await self.mutable_manager.mutate(
            title, body, commit, filtered_before, filtered_after
        )


if TYPE_CHECKING:
    _manager_check: ContextStoreManager = CompositeContextStoreManager(...)  # type: ignore[abstract, arg-type]
