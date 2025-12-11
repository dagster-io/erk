from dataclasses import dataclass

from csbot.contextengine.contextstore_protocol import ContextStore


@dataclass
class ContextStoreMutation:
    title: str
    body: str
    commit: bool
    before: ContextStore
    after: ContextStore


class FakeContextStoreManager:
    """Fake ContextStoreManager for testing."""

    def __init__(
        self,
        initial_context_store: ContextStore,
        mutations: list[ContextStoreMutation] | None = None,
    ):
        self._context_store = initial_context_store
        self._mutations = [] if mutations is None else mutations
        self._pr_url = "https://github.com/test/repo/pull/123"

    def get_last_mutation(self) -> ContextStoreMutation:
        if not self._mutations:
            raise RuntimeError("No mutations")
        return self._mutations[-1]

    async def get_context_store(self) -> ContextStore:
        """Return the current ContextStore."""
        return self._context_store

    async def mutate(
        self, title: str, body: str, commit: bool, before: ContextStore, after: ContextStore
    ) -> str:
        """Record mutation and return fake PR URL."""
        self._context_store = after
        self._mutations.append(
            ContextStoreMutation(
                title=title,
                body=body,
                commit=commit,
                before=before,
                after=after,
            )
        )
        return self._pr_url

    def update_context_store(self, new_context_store: ContextStore):
        """Update the stored ContextStore (for testing mutations)."""
        self._context_store = new_context_store
