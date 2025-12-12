"""Simple text-based status renderer."""

import click

from erk.status.models.status_data import StatusData
from erk_shared.output.output import user_output


class SimpleRenderer:
    """Renders status information as simple formatted text."""

    def render(self, status: StatusData) -> None:
        """Render status data to console.

        Args:
            status: Status data to render
        """
        self._render_header(status)
        self._render_plan(status)
        self._render_stack(status)
        self._render_pr_status(status)
        self._render_git_status(status)
        self._render_related_worktrees(status)

    def _get_progress_emoji(self, percentage: int) -> str:
        """Get progress emoji based on completion percentage.

        Args:
            percentage: Completion percentage (0-100)

        Returns:
            Emoji indicator: ⚪ (0%), 🟡 (1-99%), or 🟢 (100%)
        """
        if percentage == 0:
            return "⚪"
        if percentage == 100:
            return "🟢"
        return "🟡"

    def _render_file_list(self, files: list[str], *, max_files: int = 3) -> None:
        """Render a list of files with truncation.

        Args:
            files: List of file paths
            max_files: Maximum number of files to display
        """
        for file in files[:max_files]:
            user_output(f"      {file}")

        if len(files) > max_files:
            remaining = len(files) - max_files
            user_output(
                click.style(
                    f"      ... and {remaining} more",
                    fg="white",
                    dim=True,
                )
            )

    def _render_header(self, status: StatusData) -> None:
        """Render worktree header section.

        Args:
            status: Status data
        """
        wt = status.worktree_info

        # Title
        name_color = "green" if wt.is_root else "cyan"
        user_output(click.style(f"Worktree: {wt.name}", fg=name_color, bold=True))

        # Location
        user_output(click.style(f"Location: {wt.path}", fg="white", dim=True))

        # Branch
        if wt.branch:
            user_output(click.style(f"Branch:   {wt.branch}", fg="yellow"))
        else:
            user_output(click.style("Branch:   (detached HEAD)", fg="red", dim=True))

        user_output()

    def _truncate_plan_filename(self, filename: str) -> str:
        """Truncate enriched plan filename to max 22 characters, stripping suffixes.

        Args:
            filename: Full filename (e.g., "very-long-plan-name-plan.md")

        Returns:
            Base name truncated to 22 chars, with "-plan.md" suffix removed
            Format: "first-14-chars...last-5-chars" (exactly 22 chars when truncated)
        """
        max_length = 22

        # Strip "-plan.md" suffix if present (9 chars)
        suffix = "-plan.md"
        if filename.endswith(suffix):
            base_name = filename[: -len(suffix)]
        else:
            base_name = filename

        # If short enough, return as-is
        if len(base_name) <= max_length:
            return base_name

        # Truncate with ellipsis: first 14 chars + "..." + last 5 chars = 22 chars
        return f"{base_name[:14]}...{base_name[-5:]}"

    def _render_plan(self, status: StatusData) -> None:
        """Render plan folder section if available.

        Args:
            status: Status data
        """
        if status.plan is None:
            return

        # Check if we have either .impl/ folder or enriched plan
        has_plan_folder = status.plan.exists
        has_enriched_plan = status.plan.enriched_plan_filename is not None

        if not has_plan_folder and not has_enriched_plan:
            return

        # Build plan header with both indicators
        plan_header = "Plan:"

        # Add .impl/ folder progress indicator if exists
        if has_plan_folder and status.plan.completion_percentage is not None:
            # New format with emoji: "Plan: 🟡 7/10"
            emoji = self._get_progress_emoji(status.plan.completion_percentage)
            # Extract fraction from progress_summary (e.g., "3/10" from "3/10 steps completed")
            if status.plan.progress_summary:
                fraction = status.plan.progress_summary.split(" ")[0]  # Get "3/10" part
                plan_header += f" {emoji} {fraction}"

        # Add enriched plan indicator if exists
        if has_enriched_plan and status.plan.enriched_plan_filename is not None:
            # Add spacing if .impl/ folder exists
            if has_plan_folder and status.plan.completion_percentage is not None:
                plan_header += "  "
            # Strip suffixes and truncate to max 22 chars for display
            display_filename = self._truncate_plan_filename(status.plan.enriched_plan_filename)
            plan_header += f"🆕 {display_filename}"

        user_output(click.style(plan_header, fg="bright_magenta", bold=True))

        # Only show plan content details if .impl/ folder exists
        if has_plan_folder:
            if status.plan.first_lines:
                for line in status.plan.first_lines:
                    user_output(f"  {line}")

            user_output(
                click.style(
                    f"  ({status.plan.line_count} lines in plan.md)",
                    fg="white",
                    dim=True,
                )
            )

            # Show GitHub issue link if available (make clickable)
            if status.plan.issue_number is not None and status.plan.issue_url:
                id_text = f"#{status.plan.issue_number}"
                colored_id = click.style(id_text, fg="cyan")
                # Make ID clickable using OSC 8
                clickable_id = f"\033]8;;{status.plan.issue_url}\033\\{colored_id}\033]8;;\033\\"
                user_output(f"  Issue: {clickable_id}")
                user_output(
                    click.style(
                        f"  {status.plan.issue_url}",
                        fg="white",
                        dim=True,
                    )
                )

        user_output()

    def _render_stack(self, status: StatusData) -> None:
        """Render worktree stack section if available.

        Args:
            status: Status data
        """
        if status.stack_position is None:
            return

        stack = status.stack_position

        user_output(click.style("Stack Position:", fg="blue", bold=True))

        # Show position in stack
        if stack.is_trunk:
            user_output("  This is a trunk branch")
        else:
            if stack.parent_branch:
                parent = click.style(stack.parent_branch, fg="yellow")
                user_output(f"  Parent: {parent}")

            if stack.children_branches:
                children = ", ".join(click.style(c, fg="yellow") for c in stack.children_branches)
                user_output(f"  Children: {children}")

        # Show stack visualization
        if len(stack.stack) > 1:
            user_output()
            user_output(click.style("  Stack:", fg="white", dim=True))
            for branch in reversed(stack.stack):
                is_current = branch == stack.current_branch

                if is_current:
                    marker = click.style("◉", fg="bright_green")
                    branch_text = click.style(branch, fg="bright_green", bold=True)
                else:
                    marker = click.style("◯", fg="bright_black")
                    branch_text = branch

                user_output(f"    {marker}  {branch_text}")

        user_output()

    def _render_pr_status(self, status: StatusData) -> None:
        """Render PR status section if available.

        Args:
            status: Status data
        """
        if status.pr_status is None:
            return

        pr = status.pr_status

        user_output(click.style("Pull Request:", fg="blue", bold=True))

        # PR number (clickable) and state
        # Make PR number clickable using OSC 8
        pr_number_text = f"#{pr.number}"
        colored_pr_number = click.style(pr_number_text, fg="cyan")
        clickable_pr = f"\033]8;;{pr.url}\033\\{colored_pr_number}\033]8;;\033\\"

        state_color = (
            "green" if pr.state == "OPEN" else "red" if pr.state == "CLOSED" else "magenta"
        )
        state_text = click.style(pr.state, fg=state_color)
        user_output(f"  {clickable_pr} {state_text}")

        # Draft status
        if pr.is_draft:
            user_output(click.style("  Draft PR", fg="yellow"))

        # Checks status
        if pr.checks_passing is not None:
            if pr.checks_passing:
                user_output(click.style("  Checks: passing", fg="green"))
            else:
                user_output(click.style("  Checks: failing", fg="red"))

        # Ready to merge
        if pr.ready_to_merge:
            user_output(click.style("  ✓ Ready to merge", fg="green", bold=True))

        user_output()

    def _render_git_status(self, status: StatusData) -> None:
        """Render git status section.

        Args:
            status: Status data
        """
        if status.git_status is None:
            return

        git = status.git_status

        user_output(click.style("Git Status:", fg="blue", bold=True))

        # Clean/dirty status
        if git.clean:
            user_output(click.style("  Working tree clean", fg="green"))
        else:
            user_output(click.style("  Working tree has changes:", fg="yellow"))

            if git.staged_files:
                user_output(click.style("    Staged:", fg="green"))
                self._render_file_list(git.staged_files, max_files=3)

            if git.modified_files:
                user_output(click.style("    Modified:", fg="yellow"))
                self._render_file_list(git.modified_files, max_files=3)

            if git.untracked_files:
                user_output(click.style("    Untracked:", fg="red"))
                self._render_file_list(git.untracked_files, max_files=3)

        # Ahead/behind
        if git.ahead > 0 or git.behind > 0:
            parts = []
            if git.ahead > 0:
                parts.append(click.style(f"{git.ahead} ahead", fg="green"))
            if git.behind > 0:
                parts.append(click.style(f"{git.behind} behind", fg="red"))

            user_output(f"  Branch: {', '.join(parts)}")

        # Recent commits
        if git.recent_commits:
            user_output()
            user_output(click.style("  Recent commits:", fg="white", dim=True))
            for commit in git.recent_commits[:3]:
                sha = click.style(commit.sha, fg="yellow")
                message = commit.message[:60]
                if len(commit.message) > 60:
                    message += "..."
                user_output(f"    {sha} {message}")

        user_output()

    def _render_related_worktrees(self, status: StatusData) -> None:
        """Render related worktrees section.

        Args:
            status: Status data
        """
        if not status.related_worktrees:
            return

        user_output(click.style("Related Worktrees:", fg="blue", bold=True))

        for wt in status.related_worktrees[:5]:
            name_color = "green" if wt.is_root else "cyan"
            name_part = click.style(wt.name, fg=name_color)

            if wt.branch:
                branch_part = click.style(f"[{wt.branch}]", fg="yellow", dim=True)
                user_output(f"  {name_part} {branch_part}")
            else:
                user_output(f"  {name_part}")

        if len(status.related_worktrees) > 5:
            remaining = len(status.related_worktrees) - 5
            user_output(
                click.style(
                    f"  ... and {remaining} more",
                    fg="white",
                    dim=True,
                )
            )

        user_output()
