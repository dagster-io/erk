"""Tests for JsonlViewerApp TUI."""

from pathlib import Path

import pytest
from textual.widgets import ListView

from erk.tui.jsonl_viewer.app import JsonlViewerApp
from erk.tui.jsonl_viewer.widgets import CustomListView, JsonlEntryItem


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
    async def test_highlighted_entry_starts_collapsed(self, sample_jsonl_file: Path) -> None:
        """Highlighted entry starts collapsed (not auto-expanded)."""
        app = JsonlViewerApp(sample_jsonl_file)

        async with app.run_test() as pilot:
            await pilot.pause()
            list_view = app.query_one(CustomListView)
            first_item = list_view.highlighted_child
            assert isinstance(first_item, JsonlEntryItem)

            # First item is highlighted but NOT expanded
            assert not first_item.has_class("expanded")

    @pytest.mark.asyncio
    async def test_enter_expands_then_collapses(self, sample_jsonl_file: Path) -> None:
        """Pressing Enter toggles expand/collapse."""
        app = JsonlViewerApp(sample_jsonl_file)

        async with app.run_test() as pilot:
            await pilot.pause()
            list_view = app.query_one(CustomListView)
            first_item = list_view.highlighted_child
            assert isinstance(first_item, JsonlEntryItem)

            # Initially collapsed
            assert not first_item.has_class("expanded")

            # Press Enter to expand
            await pilot.press("enter")
            await pilot.pause()
            assert first_item.has_class("expanded")

            # Press Enter to collapse
            await pilot.press("enter")
            await pilot.pause()
            assert not first_item.has_class("expanded")

    @pytest.mark.asyncio
    async def test_expand_mode_is_sticky(self, sample_jsonl_file: Path) -> None:
        """Expand mode persists across navigation."""
        app = JsonlViewerApp(sample_jsonl_file)

        async with app.run_test() as pilot:
            await pilot.pause()
            list_view = app.query_one(CustomListView)
            first_item = list_view.highlighted_child
            assert isinstance(first_item, JsonlEntryItem)

            # Expand first item
            await pilot.press("enter")
            await pilot.pause()
            assert first_item.has_class("expanded")

            # Navigate to second item - should also be expanded
            await pilot.press("j")
            await pilot.pause()

            second_item = list_view.highlighted_child
            assert isinstance(second_item, JsonlEntryItem)

            # First collapsed, second expanded (expand mode is sticky)
            assert not first_item.has_class("expanded")
            assert second_item.has_class("expanded")

    @pytest.mark.asyncio
    async def test_collapse_mode_is_sticky(self, sample_jsonl_file: Path) -> None:
        """Collapse mode persists across navigation."""
        app = JsonlViewerApp(sample_jsonl_file)

        async with app.run_test() as pilot:
            await pilot.pause()
            list_view = app.query_one(CustomListView)
            first_item = list_view.highlighted_child
            assert isinstance(first_item, JsonlEntryItem)

            # Initially collapsed, navigate without expanding
            await pilot.press("j")
            await pilot.pause()

            second_item = list_view.highlighted_child
            assert isinstance(second_item, JsonlEntryItem)

            # Both should be collapsed (collapse mode is sticky)
            assert not first_item.has_class("expanded")
            assert not second_item.has_class("expanded")


class TestJsonlViewerAppFormatToggle:
    """Tests for format toggle functionality."""

    @pytest.mark.asyncio
    async def test_f_toggles_global_format_mode(self, tmp_path: Path) -> None:
        """Pressing f toggles global format mode."""
        jsonl_file = tmp_path / "session.jsonl"
        jsonl_file.write_text(
            '{"type": "user", "message": {"text": "line1\\\\nline2"}}\n',
            encoding="utf-8",
        )

        app = JsonlViewerApp(jsonl_file)

        async with app.run_test() as pilot:
            await pilot.pause()
            list_view = app.query_one(CustomListView)

            # Initially in raw mode
            assert list_view._formatted_mode is False

            # Press f to toggle format mode
            await pilot.press("f")
            await pilot.pause()

            # Global format mode should be toggled
            assert list_view._formatted_mode is True

    @pytest.mark.asyncio
    async def test_f_toggles_format_mode_back(self, tmp_path: Path) -> None:
        """Pressing f twice returns to raw mode."""
        jsonl_file = tmp_path / "session.jsonl"
        jsonl_file.write_text(
            '{"type": "user", "message": {"text": "test"}}\n',
            encoding="utf-8",
        )

        app = JsonlViewerApp(jsonl_file)

        async with app.run_test() as pilot:
            await pilot.pause()
            list_view = app.query_one(CustomListView)

            # Initially in raw mode
            assert list_view._formatted_mode is False

            # Press f to toggle to formatted mode
            await pilot.press("f")
            await pilot.pause()
            assert list_view._formatted_mode is True

            # Press f again to toggle back to raw mode
            await pilot.press("f")
            await pilot.pause()
            assert list_view._formatted_mode is False

    @pytest.mark.asyncio
    async def test_format_mode_persists_across_navigation(self, sample_jsonl_file: Path) -> None:
        """Format mode persists when navigating between entries."""
        app = JsonlViewerApp(sample_jsonl_file)

        async with app.run_test() as pilot:
            await pilot.pause()
            list_view = app.query_one(CustomListView)

            # Toggle to formatted mode
            await pilot.press("f")
            await pilot.pause()
            assert list_view._formatted_mode is True

            # Navigate to next entry
            await pilot.press("j")
            await pilot.pause()

            # Format mode should still be on
            assert list_view._formatted_mode is True


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
