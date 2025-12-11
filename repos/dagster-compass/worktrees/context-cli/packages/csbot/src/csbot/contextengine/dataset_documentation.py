from typing import TYPE_CHECKING

from csbot.contextengine.contextstore_protocol import ContextStore, DatasetSearchResult

if TYPE_CHECKING:
    from csbot.contextengine.context_engine import FTSIndex


class DatasetSearcher:
    """Search and index dataset documentation using only ContextStore data.

    All dataset information including markdown content comes from ContextStore.
    No filesystem access is performed.
    """

    def __init__(
        self,
        context_store: ContextStore,
        full: bool,
        connections: list[str] | None,
    ) -> None:
        self.context_store = context_store
        self.full = full
        self.connections = connections
        self._index_built = False
        self.fts = None

    def build_index(self) -> "FTSIndex":
        """Build the search index from ContextStore datasets."""
        from csbot.contextengine.context_engine import FTSIndex

        if self.fts:
            return self.fts

        # Use ContextStore.datasets as source of truth - content already loaded
        docs = []
        for dataset, documentation in self.context_store.datasets:
            # Filter by connection if specified
            if self.connections is not None and dataset.connection not in self.connections:
                continue

            # Use the summary that's already in ContextStore
            content = documentation.summary
            searchable_content = f"{dataset.connection} {dataset.table_name} {content}"

            # Use dataset identifier as doc_id instead of file path
            doc_id = f"{dataset.connection}/{dataset.table_name}"
            docs.append((doc_id, searchable_content))

        # Create index with all documents at once
        self.fts = FTSIndex(docs)
        return self.fts

    def search(self, query: str) -> list[DatasetSearchResult]:
        """
        Search the dataset documentation index using ContextStore datasets.

        Args:
            query: Search query string

        Returns:
            List of DatasetSearchResult objects
        """
        fts = self.build_index()

        # Create a mapping from doc_id to (dataset, documentation) for quick lookup
        id_to_data = {}
        for dataset, documentation in self.context_store.datasets:
            doc_id = f"{dataset.connection}/{dataset.table_name}"
            id_to_data[doc_id] = (dataset, documentation)

        # Perform search
        results = []
        for doc_id in fts.search(query, limit=100):
            # Look up the dataset from our ContextStore data
            data = id_to_data.get(doc_id)
            if not data:
                continue  # Skip if not found in ContextStore

            dataset, documentation = data

            # Use content from ContextStore if requested
            content = None
            if self.full:
                # Summary already has frontmatter stripped
                content = documentation.summary

            result = DatasetSearchResult(
                connection=dataset.connection,
                table=dataset.table_name,
                docs_markdown=content,
                object_id=doc_id,
            )
            results.append(result)

        return results
