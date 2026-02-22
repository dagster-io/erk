"""Tests for command palette registry."""

from erk.tui.commands.registry import get_all_commands, get_available_commands, get_display_name
from erk.tui.commands.types import CommandCategory, CommandContext
from erk.tui.views.types import ViewMode
from erk_shared.gateway.plan_data_provider.fake import make_plan_row


def test_all_commands_have_unique_ids() -> None:
    """All commands should have unique IDs."""
    commands = get_all_commands()
    ids = [cmd.id for cmd in commands]
    assert len(ids) == len(set(ids)), "Command IDs must be unique"


def test_all_commands_have_required_fields() -> None:
    """All commands should have required fields populated."""
    commands = get_all_commands()
    for cmd in commands:
        assert cmd.id, f"Command missing id: {cmd}"
        assert cmd.name, f"Command {cmd.id} missing name"
        assert cmd.description, f"Command {cmd.id} missing description"
        assert isinstance(cmd.category, CommandCategory), f"Command {cmd.id} missing valid category"
        assert callable(cmd.is_available), f"Command {cmd.id} missing is_available"


def test_open_issue_available_when_issue_url_exists() -> None:
    """open_issue should be available when issue URL exists."""
    row = make_plan_row(123, "Test", plan_url="https://github.com/test/repo/issues/123")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "open_issue" in cmd_ids


def test_open_pr_available_when_pr_url_exists() -> None:
    """open_pr should be available when PR URL exists."""
    row = make_plan_row(123, "Test", pr_url="https://github.com/test/repo/pull/456")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "open_pr" in cmd_ids


def test_open_pr_not_available_when_no_pr() -> None:
    """open_pr should not be available when no PR URL."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "open_pr" not in cmd_ids


def test_open_run_available_when_run_url_exists() -> None:
    """open_run should be available when run URL exists."""
    row = make_plan_row(123, "Test", run_url="https://github.com/test/repo/actions/runs/789")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "open_run" in cmd_ids


def test_open_run_not_available_when_no_run() -> None:
    """open_run should not be available when no run URL."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "open_run" not in cmd_ids


def test_copy_checkout_available_when_worktree_branch_exists() -> None:
    """copy_checkout should be available when worktree_branch exists."""
    row = make_plan_row(123, "Test", worktree_branch="feature-123")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "copy_checkout" in cmd_ids


def test_copy_checkout_not_available_when_worktree_branch_none() -> None:
    """copy_checkout should not be available when worktree_branch is None."""
    row = make_plan_row(123, "Test")  # worktree_branch defaults to None
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "copy_checkout" not in cmd_ids


def test_copy_pr_checkout_available_when_pr_exists() -> None:
    """copy_pr_checkout should be available when PR number exists."""
    row = make_plan_row(123, "Test", pr_number=456)
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "copy_pr_checkout" in cmd_ids


def test_copy_pr_checkout_not_available_when_no_pr() -> None:
    """copy_pr_checkout should not be available when no PR number."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "copy_pr_checkout" not in cmd_ids


def test_prepare_commands_available_in_github_mode() -> None:
    """Prepare commands should be available in plans view with github backend."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "copy_prepare" in cmd_ids
    assert "copy_submit" in cmd_ids


def test_close_plan_always_available() -> None:
    """close_plan should always be available in plans view."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "close_plan" in cmd_ids


def test_close_plan_has_no_shortcut() -> None:
    """close_plan should have no keyboard shortcut (must use palette)."""
    commands = get_all_commands()
    close_plan = next(cmd for cmd in commands if cmd.id == "close_plan")
    assert close_plan.shortcut is None


def test_land_pr_available_when_all_conditions_met() -> None:
    """land_pr should be available when PR is open."""
    row = make_plan_row(
        123,
        "Test",
        pr_number=456,
        pr_state="OPEN",
        exists_locally=True,
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "land_pr" in cmd_ids


def test_land_pr_not_available_when_no_pr() -> None:
    """land_pr should not be available when no PR."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "land_pr" not in cmd_ids


def test_land_pr_not_available_when_pr_merged() -> None:
    """land_pr should not be available when PR is already merged."""
    row = make_plan_row(
        123,
        "Test",
        pr_number=456,
        pr_state="MERGED",
        exists_locally=False,
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "land_pr" not in cmd_ids


def test_land_pr_available_when_exists_locally() -> None:
    """land_pr should be available even when worktree exists locally."""
    row = make_plan_row(
        123,
        "Test",
        pr_number=456,
        pr_state="OPEN",
        exists_locally=True,
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "land_pr" in cmd_ids


def test_land_pr_available_without_run_url() -> None:
    """land_pr should be available even without a remote run."""
    row = make_plan_row(
        123,
        "Test",
        pr_number=456,
        pr_state="OPEN",
        exists_locally=False,
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "land_pr" in cmd_ids


def test_fix_conflicts_remote_available_when_pr_exists() -> None:
    """fix_conflicts_remote should be available when PR number exists."""
    row = make_plan_row(123, "Test", pr_number=456)
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "fix_conflicts_remote" in cmd_ids


def test_fix_conflicts_remote_not_available_when_no_pr() -> None:
    """fix_conflicts_remote should not be available when no PR number."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "fix_conflicts_remote" not in cmd_ids


def test_copy_replan_available_when_issue_url_exists() -> None:
    """copy_replan should be available when issue URL exists."""
    row = make_plan_row(123, "Test", plan_url="https://github.com/test/repo/issues/123")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "copy_replan" in cmd_ids


# === Dynamic Display Name Tests (Plan Commands) ===


def test_display_name_close_plan_shows_cli_command() -> None:
    """close_plan should show the CLI command with issue number."""
    row = make_plan_row(5831, "Test Plan")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "close_plan")
    assert get_display_name(cmd, ctx) == "erk plan close 5831"


def test_display_name_submit_to_queue_shows_cli_command() -> None:
    """submit_to_queue should show the CLI command with issue number."""
    row = make_plan_row(5831, "Test Plan")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "submit_to_queue")
    assert get_display_name(cmd, ctx) == "erk plan submit 5831"


def test_display_name_land_pr_shows_cli_command() -> None:
    """land_pr should show the CLI command with PR number."""
    row = make_plan_row(5831, "Test Plan", pr_number=456)
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "land_pr")
    assert get_display_name(cmd, ctx) == "erk land 456"


def test_display_name_fix_conflicts_remote_shows_cli_command() -> None:
    """fix_conflicts_remote should show the launch command with PR number."""
    row = make_plan_row(5831, "Test Plan", pr_number=456)
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "fix_conflicts_remote")
    assert get_display_name(cmd, ctx) == "erk launch pr-fix-conflicts --pr 456"


def test_display_name_open_issue_shows_bare_url() -> None:
    """open_issue should show the bare issue URL (no prefix)."""
    row = make_plan_row(
        5831,
        "Test Plan",
        plan_url="https://github.com/test/repo/issues/5831",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "open_issue")
    assert get_display_name(cmd, ctx) == "https://github.com/test/repo/issues/5831"


def test_display_name_open_pr_shows_bare_url() -> None:
    """open_pr should show the bare PR URL (no prefix)."""
    row = make_plan_row(
        5831,
        "Test Plan",
        pr_url="https://github.com/test/repo/pull/456",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "open_pr")
    assert get_display_name(cmd, ctx) == "https://github.com/test/repo/pull/456"


def test_display_name_open_run_shows_bare_url() -> None:
    """open_run should show the bare run URL (no prefix)."""
    row = make_plan_row(
        5831,
        "Test Plan",
        run_url="https://github.com/test/repo/actions/runs/789",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "open_run")
    assert get_display_name(cmd, ctx) == "https://github.com/test/repo/actions/runs/789"


def test_display_name_copy_checkout_shows_branch() -> None:
    """copy_checkout should show the worktree branch."""
    row = make_plan_row(5831, "Test Plan", worktree_branch="feature-5831")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "copy_checkout")
    assert get_display_name(cmd, ctx) == "erk br co feature-5831"


def test_display_name_copy_checkout_falls_back_to_pr() -> None:
    """copy_checkout should fall back to PR number if no worktree branch."""
    row = make_plan_row(5831, "Test Plan", pr_number=456)
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "copy_checkout")
    assert get_display_name(cmd, ctx) == "erk pr co 456"


def test_display_name_copy_pr_checkout_shows_pr() -> None:
    """copy_pr_checkout should show the PR number in the full command."""
    row = make_plan_row(5831, "Test Plan", pr_number=456)
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "copy_pr_checkout")
    expected = 'source "$(erk pr checkout 456 --script)" && erk pr sync --dangerous'
    assert get_display_name(cmd, ctx) == expected


def test_display_name_copy_prepare_shows_issue() -> None:
    """copy_prepare should show the issue number."""
    row = make_plan_row(5831, "Test Plan")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "copy_prepare")
    assert get_display_name(cmd, ctx) == "erk br co --for-plan 5831"


def test_display_name_copy_prepare_activate_shows_full_command() -> None:
    """copy_prepare_activate should show the full source && implement command."""
    row = make_plan_row(5831, "Test Plan")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "copy_prepare_activate")
    expected = 'source "$(erk br co --for-plan 5831 --script)" && erk implement --dangerous'
    assert get_display_name(cmd, ctx) == expected


def test_display_name_copy_submit_shows_issue() -> None:
    """copy_submit should show the issue number."""
    row = make_plan_row(5831, "Test Plan")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "copy_submit")
    assert get_display_name(cmd, ctx) == "erk plan submit 5831"


def test_display_name_copy_replan_shows_issue() -> None:
    """copy_replan should show the issue number."""
    row = make_plan_row(5831, "Test Plan")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "copy_replan")
    assert get_display_name(cmd, ctx) == "erk plan replan 5831"


def test_all_commands_have_get_display_name() -> None:
    """All commands should have get_display_name defined."""
    commands = get_all_commands()
    for cmd in commands:
        assert cmd.get_display_name is not None, f"Command {cmd.id} missing get_display_name"


# === Palette Display Formatting Tests ===


def test_format_palette_display_produces_styled_text() -> None:
    """_format_palette_display produces Text with correct structure and dim command."""
    from rich.text import Text

    from erk.tui.commands.provider import _format_palette_display

    result = _format_palette_display("⚡", "close", "erk plan close 123")

    # Result should be a Text object
    assert isinstance(result, Text)

    # Plain text should match expected format
    assert result.plain == "⚡ close: erk plan close 123"

    # Command portion should be dimmed
    # Check that "dim" style is applied to the command text
    spans = list(result.spans)
    # The structure is: emoji + " ", label + ": ", (command_text, "dim")
    # Find the span covering the command text portion
    command_start = len("⚡ close: ")
    command_span = next((s for s in spans if s.start == command_start), None)
    assert command_span is not None, "Expected span for command text"
    assert command_span.style == "dim"


def test_format_search_display_preserves_highlighting() -> None:
    """_format_search_display preserves fuzzy match highlights in dim portion."""
    from rich.text import Text

    from erk.tui.commands.provider import _format_search_display

    # Simulate highlighted text from fuzzy matcher
    # e.g., "close: erk plan close 123" with "close" highlighted
    highlighted = Text("close: erk plan close 123")
    highlighted.stylize("bold", 0, 5)  # First "close" highlighted

    result = _format_search_display("⚡", highlighted, len("close"))

    assert isinstance(result, Text)
    assert result.plain == "⚡ close: erk plan close 123"


# === View Mode Filtering Tests ===


def test_plan_commands_hidden_in_objectives_view() -> None:
    """Plan commands should not appear in Objectives view."""
    row = make_plan_row(
        123,
        "Test",
        plan_url="https://github.com/test/repo/issues/123",
        pr_number=456,
        pr_url="https://github.com/test/repo/pull/456",
        pr_state="OPEN",
        worktree_branch="feature-123",
        run_url="https://github.com/test/repo/actions/runs/789",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.OBJECTIVES, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]

    # All plan commands should be absent
    plan_cmd_ids = [
        "close_plan",
        "submit_to_queue",
        "land_pr",
        "fix_conflicts_remote",
        "address_remote",
        "open_issue",
        "open_pr",
        "open_run",
        "copy_checkout",
        "copy_pr_checkout",
        "copy_prepare",
        "copy_prepare_activate",
        "copy_submit",
        "copy_replan",
    ]
    for plan_id in plan_cmd_ids:
        assert plan_id not in cmd_ids, f"Plan command {plan_id} should be hidden in Objectives view"


def test_objective_commands_hidden_in_plans_view() -> None:
    """Objective commands should not appear in Plans view."""
    row = make_plan_row(123, "Test", plan_url="https://github.com/test/repo/issues/123")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]

    objective_cmd_ids = [
        "one_shot_plan",
        "check_objective",
        "close_objective",
        "open_objective",
        "copy_plan",
        "copy_view",
        "codespace_run_plan",
    ]
    for obj_id in objective_cmd_ids:
        assert obj_id not in cmd_ids, f"Objective command {obj_id} should be hidden in Plans view"


def test_objective_commands_appear_in_objectives_view() -> None:
    """All 7 objective commands should appear in Objectives view."""
    row = make_plan_row(123, "Test", plan_url="https://github.com/test/repo/issues/123")
    ctx = CommandContext(row=row, view_mode=ViewMode.OBJECTIVES, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]

    expected = [
        "one_shot_plan",
        "check_objective",
        "close_objective",
        "open_objective",
        "copy_plan",
        "copy_view",
        "codespace_run_plan",
    ]
    for obj_id in expected:
        assert obj_id in cmd_ids, f"Objective command {obj_id} should appear in Objectives view"


def test_plan_commands_available_in_learn_view() -> None:
    """Plan commands should still appear in Learn view (not objectives)."""
    row = make_plan_row(123, "Test", plan_url="https://github.com/test/repo/issues/123")
    ctx = CommandContext(row=row, view_mode=ViewMode.LEARN, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "close_plan" in cmd_ids
    assert "copy_prepare" in cmd_ids


# === Dynamic Display Name Tests (Objective Commands) ===


def test_display_name_one_shot_plan() -> None:
    """one_shot_plan should show the objective command with --one-shot."""
    row = make_plan_row(7100, "Test Objective")
    ctx = CommandContext(row=row, view_mode=ViewMode.OBJECTIVES, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "one_shot_plan")
    assert get_display_name(cmd, ctx) == "erk objective plan 7100 --one-shot"


def test_display_name_check_objective() -> None:
    """check_objective should show the check command."""
    row = make_plan_row(7100, "Test Objective")
    ctx = CommandContext(row=row, view_mode=ViewMode.OBJECTIVES, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "check_objective")
    assert get_display_name(cmd, ctx) == "erk objective check 7100"


def test_display_name_close_objective() -> None:
    """close_objective should show the close command with --force."""
    row = make_plan_row(7100, "Test Objective")
    ctx = CommandContext(row=row, view_mode=ViewMode.OBJECTIVES, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "close_objective")
    assert get_display_name(cmd, ctx) == "erk objective close 7100 --force"


def test_display_name_open_objective() -> None:
    """open_objective should show the issue URL."""
    row = make_plan_row(
        7100,
        "Test Objective",
        plan_url="https://github.com/test/repo/issues/7100",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.OBJECTIVES, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "open_objective")
    assert get_display_name(cmd, ctx) == "https://github.com/test/repo/issues/7100"


def test_display_name_copy_plan() -> None:
    """copy_plan should show the plan command."""
    row = make_plan_row(7100, "Test Objective")
    ctx = CommandContext(row=row, view_mode=ViewMode.OBJECTIVES, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "copy_plan")
    assert get_display_name(cmd, ctx) == "erk objective plan 7100"


def test_display_name_codespace_run_plan() -> None:
    """codespace_run_plan should show the codespace run command."""
    row = make_plan_row(7100, "Test Objective")
    ctx = CommandContext(row=row, view_mode=ViewMode.OBJECTIVES, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "codespace_run_plan")
    assert get_display_name(cmd, ctx) == "erk codespace run objective plan 7100"


def test_codespace_run_plan_available_in_objectives_view() -> None:
    """codespace_run_plan should be available in Objectives view."""
    row = make_plan_row(123, "Test", plan_url="https://github.com/test/repo/issues/123")
    ctx = CommandContext(row=row, view_mode=ViewMode.OBJECTIVES, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "codespace_run_plan" in cmd_ids


def test_codespace_run_plan_not_available_in_plans_view() -> None:
    """codespace_run_plan should not be available in Plans view."""
    row = make_plan_row(123, "Test", plan_url="https://github.com/test/repo/issues/123")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "codespace_run_plan" not in cmd_ids


def test_display_name_copy_view() -> None:
    """copy_view should show the view command."""
    row = make_plan_row(7100, "Test Objective")
    ctx = CommandContext(row=row, view_mode=ViewMode.OBJECTIVES, plan_backend="github")
    cmd = next(c for c in get_all_commands() if c.id == "copy_view")
    assert get_display_name(cmd, ctx) == "erk objective view 7100"


# === Shortcut Safety Tests ===


def test_shortcuts_no_conflicts_within_view() -> None:
    """Shortcuts should not conflict within the same view mode.

    Plan commands and objective commands can reuse shortcuts (e.g., "i", "s", "1")
    because they are mutually exclusive (filtered by view mode). But within a single
    view, shortcuts must be unique. Check both github and draft_pr backends.
    """
    row = make_plan_row(
        123,
        "Test",
        plan_url="https://github.com/test/repo/issues/123",
        pr_number=456,
        pr_url="https://github.com/test/repo/pull/456",
        pr_state="OPEN",
        worktree_branch="feature-123",
        run_url="https://github.com/test/repo/actions/runs/789",
    )

    for plan_backend in ("github", "draft_pr"):
        for view_mode in (ViewMode.PLANS, ViewMode.OBJECTIVES):
            ctx = CommandContext(row=row, view_mode=view_mode, plan_backend=plan_backend)
            commands = get_available_commands(ctx)
            shortcuts = [cmd.shortcut for cmd in commands if cmd.shortcut is not None]
            assert len(shortcuts) == len(set(shortcuts)), (
                f"Duplicate shortcuts in {view_mode.name} view"
                f" (backend={plan_backend}): {shortcuts}"
            )


# === Draft PR Backend Tests ===


def test_prepare_commands_hidden_in_draft_pr_mode() -> None:
    """Prepare commands should be hidden when plan backend is draft_pr."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="draft_pr")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "copy_prepare" not in cmd_ids
    assert "copy_prepare_activate" not in cmd_ids


def test_commands_available_in_draft_pr_mode() -> None:
    """Non-prepare plan commands should remain available in draft_pr mode."""
    row = make_plan_row(
        123,
        "Test",
        plan_url="https://github.com/test/repo/pull/123",
        pr_number=456,
        pr_url="https://github.com/test/repo/pull/456",
        pr_state="OPEN",
        worktree_branch="feature-123",
        run_url="https://github.com/test/repo/actions/runs/789",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="draft_pr")
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]

    # These should all still be available
    expected_available = [
        "close_plan",
        "submit_to_queue",
        "fix_conflicts_remote",
        "address_remote",
        "land_pr",
        "open_issue",
        "open_pr",
        "open_run",
        "copy_checkout",
        "copy_pr_checkout",
        "copy_submit",
        "copy_replan",
    ]
    for cmd_id in expected_available:
        assert cmd_id in cmd_ids, f"Command {cmd_id} should be available in draft_pr mode"
