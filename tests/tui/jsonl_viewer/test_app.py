"""Tests for JsonlViewerApp TUI."""

from pathlib import Path

import pytest
from textual.widgets import ListView

from erk.tui.jsonl_viewer.app import JsonlViewerApp
from erk.tui.jsonl_viewer.widgets import JsonlEntryItem


@pytest.fixture
def sample_jsonl_file(tmp_path: Path) -> Path:
    """Create a sample JSONL file for testing."""
    jsonl_file = tmp_path / "session.jsonl"
    jsonl_file.write_text(
        '{"type": "user", "message": {"content": [{"type": "text", "text": "Hello"}]}}\n'
        '{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}}\n'
        '{"type": "tool_result", "message": {"content": [{"type": "text", "text": "output"}]}}\n',
        encoding="utf-8",
    )
    return jsonl_file


class TestJsonlViewerAppCompose:
    """Tests for app composition."""

    @pytest.mark.asyncio
    async def test_app_shows_entries(self, sample_jsonl_file: Path) -> None:
        """App displays entries from JSONL file."""
        app = JsonlViewerApp(sample_jsonl_file)

        async with app.run_test():
            list_view = app.query_one(ListView)
            # ListView should have 3 items (one per entry)
            assert len(list_view.children) == 3

    @pytest.mark.asyncio
    async def test_entries_are_jsonl_entry_items(self, sample_jsonl_file: Path) -> None:
        """All list items are JsonlEntryItem widgets."""
        app = JsonlViewerApp(sample_jsonl_file)

        async with app.run_test():
            list_view = app.query_one(ListView)
            for item in list_view.children:
                assert isinstance(item, JsonlEntryItem)


class TestJsonlViewerAppNavigation:
    """Tests for keyboard navigation."""

    @pytest.mark.asyncio
    async def test_quit_on_q(self, sample_jsonl_file: Path) -> None:
        """Pressing q quits the app."""
        app = JsonlViewerApp(sample_jsonl_file)

        async with app.run_test() as pilot:
            await pilot.press("q")
            # App should have exited

    @pytest.mark.asyncio
    async def test_quit_on_escape(self, sample_jsonl_file: Path) -> None:
        """Pressing escape quits the app."""
        app = JsonlViewerApp(sample_jsonl_file)

        async with app.run_test() as pilot:
            await pilot.press("escape")
            # App should have exited

    @pytest.mark.asyncio
    async def test_vim_j_moves_down(self, sample_jsonl_file: Path) -> None:
        """Pressing j moves cursor down."""
        app = JsonlViewerApp(sample_jsonl_file)

        async with app.run_test() as pilot:
            await pilot.pause()
            list_view = app.query_one(ListView)

            # Initially first item is highlighted
            initial_index = list_view.index

            # Press j to move down
            await pilot.press("j")
            await pilot.pause()

            assert list_view.index == initial_index + 1

    @pytest.mark.asyncio
    async def test_vim_k_moves_up(self, sample_jsonl_file: Path) -> None:
        """Pressing k moves cursor up."""
        app = JsonlViewerApp(sample_jsonl_file)

        async with app.run_test() as pilot:
            await pilot.pause()
            list_view = app.query_one(ListView)

            # Move down first, then up
            await pilot.press("j")
            await pilot.pause()
            await pilot.press("k")
            await pilot.pause()

            assert list_view.index == 0


class TestJsonlViewerAppExpandCollapse:
    """Tests for expand/collapse functionality."""

    @pytest.mark.asyncio
    async def test_enter_expands_entry(self, sample_jsonl_file: Path) -> None:
        """Pressing Enter expands selected entry."""
        app = JsonlViewerApp(sample_jsonl_file)

        async with app.run_test() as pilot:
            await pilot.pause()
            list_view = app.query_one(ListView)
            first_item = list_view.highlighted_child
            assert isinstance(first_item, JsonlEntryItem)

            # Initially not expanded
            assert not first_item.has_class("expanded")

            # Press Enter to expand
            await pilot.press("enter")
            await pilot.pause()

            assert first_item.has_class("expanded")

    @pytest.mark.asyncio
    async def test_enter_collapses_expanded_entry(self, sample_jsonl_file: Path) -> None:
        """Pressing Enter on expanded entry collapses it."""
        app = JsonlViewerApp(sample_jsonl_file)

        async with app.run_test() as pilot:
            await pilot.pause()
            list_view = app.query_one(ListView)
            first_item = list_view.highlighted_child
            assert isinstance(first_item, JsonlEntryItem)

            # Expand then collapse
            await pilot.press("enter")
            await pilot.pause()
            assert first_item.has_class("expanded")

            await pilot.press("enter")
            await pilot.pause()
            assert not first_item.has_class("expanded")


class TestJsonlViewerAppEmptyFile:
    """Tests for handling empty/edge case files."""

    @pytest.mark.asyncio
    async def test_handles_empty_file(self, tmp_path: Path) -> None:
        """App handles empty JSONL file gracefully."""
        empty_file = tmp_path / "empty.jsonl"
        empty_file.write_text("", encoding="utf-8")

        app = JsonlViewerApp(empty_file)

        async with app.run_test() as pilot:
            await pilot.pause()
            list_view = app.query_one(ListView)
            assert len(list_view.children) == 0

            # Should still be able to quit
            await pilot.press("q")
