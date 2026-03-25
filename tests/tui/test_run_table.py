"""Tests for RunDataTable widget."""

from erk.tui.data.types import RunRowData
from erk.tui.widgets.run_table import RunDataTable
from tests.fakes.tests.tui_plan_data_provider import make_run_row


class TestRunRowData:
    """Tests for RunRowData dataclass."""

    def test_make_run_row_defaults(self) -> None:
        """make_run_row creates row with sensible defaults."""
        row = make_run_row("12345")
        assert row.run_id == "12345"
        assert row.run_url == "https://github.com/test/repo/actions/runs/12345"
        assert row.status == "completed"
        assert row.conclusion == "success"
        assert row.status_display == "\u2705 Success"
        assert row.workflow_name == "plan-implement"
        assert row.pr_number is None
        assert row.pr_url is None
        assert row.pr_display == "-"
        assert row.pr_title is None
        assert row.title_display == "-"
        assert row.checks_display == "-"
        assert row.run_id_display == "12345"

    def test_make_run_row_with_pr(self) -> None:
        """make_run_row with PR data."""
        row = make_run_row(
            "12345",
            pr_number=456,
            pr_url="https://github.com/test/repo/pull/456",
            pr_display="#456",
            pr_title="Fix auth bug",
            title_display="Fix auth bug",
        )
        assert row.pr_number == 456
        assert row.pr_display == "#456"
        assert row.pr_title == "Fix auth bug"
        assert row.title_display == "Fix auth bug"

    def test_make_run_row_custom_workflow(self) -> None:
        """make_run_row with custom workflow name."""
        row = make_run_row("12345", workflow_name="pr-address")
        assert row.workflow_name == "pr-address"

    def test_make_run_row_with_failure(self) -> None:
        """make_run_row with failed conclusion."""
        row = make_run_row(
            "12345",
            status="completed",
            conclusion="failure",
            status_display="\u274c Failure",
        )
        assert row.conclusion == "failure"
        assert row.status_display == "\u274c Failure"

    def test_run_row_data_is_frozen(self) -> None:
        """RunRowData is a frozen dataclass."""
        row = make_run_row("12345")
        try:
            row.run_id = "99999"  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass


class TestRunDataTable:
    """Tests for RunDataTable widget construction."""

    def test_cursor_type_is_row(self) -> None:
        """RunDataTable uses row cursor type."""
        table = RunDataTable()
        assert table.cursor_type == "row"

    def test_initial_rows_empty(self) -> None:
        """RunDataTable starts with empty rows."""
        table = RunDataTable()
        assert table._rows == []

    def test_get_selected_row_data_empty(self) -> None:
        """get_selected_row_data returns None when no rows exist."""
        table = RunDataTable()
        assert table.get_selected_row_data() is None


class TestRunDataTableRowValues:
    """Tests for RunDataTable._row_to_values."""

    def test_row_to_values_basic(self) -> None:
        """_row_to_values returns correct tuple for basic run."""
        table = RunDataTable()
        row = make_run_row("12345")
        values = table._row_to_values(row)
        # Should be: run_id, status, submitted, workflow, pr, branch, chks
        assert len(values) == 7
        # run_id should be linkified
        assert "12345" in values[0]
        assert "[link=" in values[0]
        assert values[1] == "\u2705 Success"
        assert values[2] == "03-09 14:30"
        assert values[3] == "plan-implement"
        assert values[4] == "-"  # no PR
        assert values[5] == "-"  # no branch
        assert values[6] == "-"  # no checks

    def test_row_to_values_with_pr(self) -> None:
        """_row_to_values linkifies PR when URL present."""
        table = RunDataTable()
        row = make_run_row(
            "12345",
            pr_number=42,
            pr_url="https://github.com/test/repo/pull/42",
            pr_display="#42",
        )
        values = table._row_to_values(row)
        # PR cell should be linkified
        assert "[link=" in values[4]
        assert "#42" in values[4]
        assert values[5] == "-"  # branch

    def test_row_to_values_no_run_url(self) -> None:
        """_row_to_values doesn't linkify run-id when no URL."""
        table = RunDataTable()
        # Construct directly to set run_url=None
        row_no_url = RunRowData(
            run_id="12345",
            run_url=None,
            status="completed",
            conclusion="success",
            status_display="\u2705 Success",
            workflow_name="plan-implement",
            pr_number=None,
            pr_url=None,
            pr_display="-",
            pr_title=None,
            pr_state=None,
            title_display="-",
            branch_display="main",
            submitted_display="03-09 14:30",
            created_at=None,
            checks_display="-",
            run_id_display="12345",
            branch="-",
        )
        values = table._row_to_values(row_no_url)
        assert values[0] == "12345"
        assert "[link=" not in values[0]


class TestFakePrDataProviderRuns:
    """Tests for FakePrDataProvider.fetch_runs."""

    def test_fetch_runs_empty_by_default(self) -> None:
        """FakePrDataProvider.fetch_runs returns empty list by default."""
        from tests.fakes.tests.tui_plan_data_provider import FakePrDataProvider

        provider = FakePrDataProvider()
        assert provider.fetch_runs() == []

    def test_fetch_runs_returns_set_data(self) -> None:
        """FakePrDataProvider.fetch_runs returns data set via set_runs."""
        from tests.fakes.tests.tui_plan_data_provider import FakePrDataProvider

        provider = FakePrDataProvider()
        rows = [make_run_row("111"), make_run_row("222")]
        provider.set_runs(rows)
        result = provider.fetch_runs()
        assert len(result) == 2
        assert result[0].run_id == "111"
        assert result[1].run_id == "222"

    def test_fetch_runs_returns_copy(self) -> None:
        """FakePrDataProvider.fetch_runs returns a new list each time."""
        from tests.fakes.tests.tui_plan_data_provider import FakePrDataProvider

        provider = FakePrDataProvider()
        rows = [make_run_row("111")]
        provider.set_runs(rows)
        result1 = provider.fetch_runs()
        result2 = provider.fetch_runs()
        assert result1 is not result2
