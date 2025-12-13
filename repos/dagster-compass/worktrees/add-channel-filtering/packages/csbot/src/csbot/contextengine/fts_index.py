"""Full-text search index using Tantivy.

This module provides FTSIndex, a tantivy-based search index for context documents.
Extracted from context_engine.py to avoid circular import dependencies.
"""

import tempfile
from collections.abc import Sequence

import tantivy

from csbot.utils.check_async_context import ensure_not_in_async_context


class FTSIndex:
    """Tantivy-based full-text search index.

    This class wraps a Tantivy index for fast and accurate full-text search.
    It was originally using sqlite and fts5, but had poor recall and seemed buggy.
    Then it used a custom index, but it was too much code to maintain.
    Now using Tantivy for production-ready search.
    """

    def __init__(self, docs: Sequence[tuple[str, str]]):
        """Initialize a Tantivy search index for full-text search.

        Args:
            docs: Sequence of (doc_id, content) tuples to index
        """
        ensure_not_in_async_context()
        self.docs = docs
        self.doc_ids = [doc_id for doc_id, _ in docs]  # Keep track of doc_ids for compatibility

        self.temp_dir = tempfile.TemporaryDirectory()

        schema_builder = tantivy.SchemaBuilder()
        schema_builder.add_text_field("doc_id", stored=True)
        schema_builder.add_text_field("content", stored=False)
        schema = schema_builder.build()
        self.index = tantivy.Index(schema, path=self.temp_dir.name)
        self.writer = self.index.writer()

        # Add documents to the index
        for doc_id, content in docs:
            doc = tantivy.Document()
            doc.add_text("doc_id", doc_id)
            doc.add_text("content", content)
            self.writer.add_document(doc)

        # Commit the changes
        self.writer.commit()
        self.index.reload()

        # Create a searcher
        self.searcher = self.index.searcher()

    def search(self, query: str, limit: int) -> list[str]:
        """Search the index for documents matching the query using Tantivy.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of document IDs ordered by relevance
        """
        ensure_not_in_async_context()
        if not query.strip():
            return []

        parsed_query = self.index.parse_query(query)
        search_results = self.searcher.search(parsed_query, limit)

        # Extract document IDs from results
        doc_ids = []
        for _, doc_address in search_results.hits:
            doc = self.searcher.doc(doc_address)
            doc_id = doc.get_first("doc_id")
            if doc_id:
                doc_ids.append(doc_id)

        return doc_ids

    def __del__(self) -> None:
        """Wait for merge threads and close resources before cleanup.

        Note: Cleanup errors are suppressed as __del__ cannot raise exceptions.
        The OSError [Errno 66] "Directory not empty" occurs when Tantivy's
        internal cleanup hasn't completed. We allow Python's garbage collector
        to handle final cleanup naturally.
        """
        # Close writer and wait for background threads
        if hasattr(self, "writer"):
            self.writer.wait_merging_threads()

        # Close searcher to release file handles
        if hasattr(self, "searcher"):
            del self.searcher

        # Close index to release resources
        if hasattr(self, "index"):
            del self.index

        # Attempt cleanup - suppress errors as __del__ cannot raise
        if hasattr(self, "temp_dir"):
            try:
                self.temp_dir.cleanup()
            except OSError:
                # Tantivy may still hold file handles - ignore cleanup errors
                # Python's garbage collector will eventually clean up the temp dir
                pass
