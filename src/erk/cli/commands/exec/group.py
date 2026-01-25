"""Static exec group for erk scripts.

This module provides the `erk exec` command group with all scripts
statically registered.
"""

import click

# Import and register all scripts
from erk.cli.commands.exec.scripts.add_reaction_to_comment import (
    add_reaction_to_comment,
)
from erk.cli.commands.exec.scripts.add_remote_execution_note import (
    add_remote_execution_note,
)
from erk.cli.commands.exec.scripts.capture_session_info import (
    capture_session_info,
)
from erk.cli.commands.exec.scripts.check_impl import check_impl
from erk.cli.commands.exec.scripts.ci_update_pr_body import ci_update_pr_body
from erk.cli.commands.exec.scripts.close_issue_with_comment import (
    close_issue_with_comment,
)
from erk.cli.commands.exec.scripts.create_issue_from_session import (
    create_issue_from_session,
)
from erk.cli.commands.exec.scripts.create_plan_from_context import (
    create_plan_from_context,
)
from erk.cli.commands.exec.scripts.create_worker_impl_from_issue import (
    create_worker_impl_from_issue,
)
from erk.cli.commands.exec.scripts.detect_trunk_branch import detect_trunk_branch
from erk.cli.commands.exec.scripts.discover_reviews import discover_reviews
from erk.cli.commands.exec.scripts.download_remote_session import (
    download_remote_session,
)
from erk.cli.commands.exec.scripts.exit_plan_mode_hook import exit_plan_mode_hook
from erk.cli.commands.exec.scripts.extract_latest_plan import extract_latest_plan
from erk.cli.commands.exec.scripts.find_project_dir import find_project_dir
from erk.cli.commands.exec.scripts.generate_pr_address_summary import (
    generate_pr_address_summary,
)
from erk.cli.commands.exec.scripts.generate_pr_summary import generate_pr_summary
from erk.cli.commands.exec.scripts.get_closing_text import get_closing_text
from erk.cli.commands.exec.scripts.get_embedded_prompt import get_embedded_prompt
from erk.cli.commands.exec.scripts.get_issue_body import get_issue_body
from erk.cli.commands.exec.scripts.get_issue_timeline_prs import (
    get_issue_timeline_prs,
)
from erk.cli.commands.exec.scripts.get_learn_sessions import get_learn_sessions
from erk.cli.commands.exec.scripts.get_plan_metadata import get_plan_metadata
from erk.cli.commands.exec.scripts.get_plans_for_objective import (
    get_plans_for_objective,
)
from erk.cli.commands.exec.scripts.get_pr_body_footer import get_pr_body_footer
from erk.cli.commands.exec.scripts.get_pr_commits import get_pr_commits
from erk.cli.commands.exec.scripts.get_pr_discussion_comments import (
    get_pr_discussion_comments,
)
from erk.cli.commands.exec.scripts.get_pr_for_plan import get_pr_for_plan
from erk.cli.commands.exec.scripts.get_pr_review_comments import (
    get_pr_review_comments,
)
from erk.cli.commands.exec.scripts.handle_no_changes import handle_no_changes
from erk.cli.commands.exec.scripts.impl_init import impl_init
from erk.cli.commands.exec.scripts.impl_signal import impl_signal
from erk.cli.commands.exec.scripts.impl_verify import impl_verify
from erk.cli.commands.exec.scripts.issue_title_to_filename import (
    issue_title_to_filename,
)
from erk.cli.commands.exec.scripts.land_execute import land_execute
from erk.cli.commands.exec.scripts.list_sessions import list_sessions
from erk.cli.commands.exec.scripts.mark_impl_ended import mark_impl_ended
from erk.cli.commands.exec.scripts.mark_impl_started import mark_impl_started
from erk.cli.commands.exec.scripts.marker import marker
from erk.cli.commands.exec.scripts.objective_save_to_issue import (
    objective_save_to_issue,
)
from erk.cli.commands.exec.scripts.plan_save_to_issue import plan_save_to_issue
from erk.cli.commands.exec.scripts.plan_update_issue import plan_update_issue
from erk.cli.commands.exec.scripts.post_or_update_pr_summary import (
    post_or_update_pr_summary,
)
from erk.cli.commands.exec.scripts.post_pr_inline_comment import (
    post_pr_inline_comment,
)
from erk.cli.commands.exec.scripts.post_workflow_started_comment import (
    post_workflow_started_comment,
)
from erk.cli.commands.exec.scripts.pr_sync_commit import pr_sync_commit
from erk.cli.commands.exec.scripts.preprocess_session import preprocess_session
from erk.cli.commands.exec.scripts.promote_to_tripwire import promote_to_tripwire
from erk.cli.commands.exec.scripts.quick_submit import quick_submit
from erk.cli.commands.exec.scripts.rebase_with_conflict_resolution import (
    rebase_with_conflict_resolution,
)
from erk.cli.commands.exec.scripts.reply_to_discussion_comment import (
    reply_to_discussion_comment,
)
from erk.cli.commands.exec.scripts.resolve_review_thread import (
    resolve_review_thread,
)
from erk.cli.commands.exec.scripts.run_review import run_review
from erk.cli.commands.exec.scripts.session_id_injector_hook import (
    session_id_injector_hook,
)
from erk.cli.commands.exec.scripts.setup_impl_from_issue import (
    setup_impl_from_issue,
)
from erk.cli.commands.exec.scripts.track_learn_evaluation import (
    track_learn_evaluation,
)
from erk.cli.commands.exec.scripts.track_learn_result import (
    track_learn_result,
)
from erk.cli.commands.exec.scripts.trigger_async_learn import trigger_async_learn
from erk.cli.commands.exec.scripts.tripwires_reminder_hook import (
    tripwires_reminder_hook,
)
from erk.cli.commands.exec.scripts.update_dispatch_info import update_dispatch_info
from erk.cli.commands.exec.scripts.update_issue_body import update_issue_body
from erk.cli.commands.exec.scripts.update_plan_remote_session import (
    update_plan_remote_session,
)
from erk.cli.commands.exec.scripts.upload_learn_materials import (
    upload_learn_materials,
)
from erk.cli.commands.exec.scripts.upload_session import upload_session
from erk.cli.commands.exec.scripts.user_prompt_hook import user_prompt_hook
from erk.cli.commands.exec.scripts.validate_claude_credentials import (
    validate_claude_credentials,
)
from erk.cli.commands.exec.scripts.validate_plan_content import (
    validate_plan_content,
)
from erk.cli.commands.exec.scripts.wrap_plan_in_metadata_block import (
    wrap_plan_in_metadata_block,
)


# Create the exec group (hidden from top-level help)
@click.group(name="exec", hidden=True)
def exec_group() -> None:
    """Execute erk workflow scripts."""


# Register all commands
exec_group.add_command(add_reaction_to_comment, name="add-reaction-to-comment")
exec_group.add_command(add_remote_execution_note, name="add-remote-execution-note")
exec_group.add_command(capture_session_info, name="capture-session-info")
exec_group.add_command(check_impl, name="check-impl")
exec_group.add_command(create_issue_from_session, name="create-issue-from-session")
exec_group.add_command(create_plan_from_context, name="create-plan-from-context")
exec_group.add_command(create_worker_impl_from_issue, name="create-worker-impl-from-issue")
exec_group.add_command(detect_trunk_branch, name="detect-trunk-branch")
exec_group.add_command(discover_reviews, name="discover-reviews")
exec_group.add_command(download_remote_session, name="download-remote-session")
exec_group.add_command(exit_plan_mode_hook, name="exit-plan-mode-hook")
exec_group.add_command(extract_latest_plan, name="extract-latest-plan")
exec_group.add_command(find_project_dir, name="find-project-dir")
exec_group.add_command(generate_pr_address_summary, name="generate-pr-address-summary")
exec_group.add_command(generate_pr_summary, name="generate-pr-summary")
exec_group.add_command(get_closing_text, name="get-closing-text")
exec_group.add_command(get_plan_metadata, name="get-plan-metadata")
exec_group.add_command(get_plans_for_objective, name="get-plans-for-objective")
exec_group.add_command(get_pr_for_plan, name="get-pr-for-plan")
exec_group.add_command(get_embedded_prompt, name="get-embedded-prompt")
exec_group.add_command(get_issue_body, name="get-issue-body")
exec_group.add_command(get_issue_timeline_prs, name="get-issue-timeline-prs")
exec_group.add_command(get_learn_sessions, name="get-learn-sessions")
exec_group.add_command(get_pr_body_footer, name="get-pr-body-footer")
exec_group.add_command(handle_no_changes, name="handle-no-changes")
exec_group.add_command(get_pr_commits, name="get-pr-commits")
exec_group.add_command(get_pr_discussion_comments, name="get-pr-discussion-comments")
exec_group.add_command(get_pr_review_comments, name="get-pr-review-comments")
exec_group.add_command(impl_init, name="impl-init")
exec_group.add_command(impl_signal, name="impl-signal")
exec_group.add_command(impl_verify, name="impl-verify")
exec_group.add_command(issue_title_to_filename, name="issue-title-to-filename")
exec_group.add_command(land_execute, name="land-execute")
exec_group.add_command(list_sessions, name="list-sessions")
exec_group.add_command(mark_impl_ended, name="mark-impl-ended")
exec_group.add_command(mark_impl_started, name="mark-impl-started")
exec_group.add_command(marker, name="marker")
exec_group.add_command(objective_save_to_issue, name="objective-save-to-issue")
exec_group.add_command(plan_save_to_issue, name="plan-save-to-issue")
exec_group.add_command(plan_update_issue, name="plan-update-issue")
exec_group.add_command(post_or_update_pr_summary, name="post-or-update-pr-summary")
exec_group.add_command(post_pr_inline_comment, name="post-pr-inline-comment")
exec_group.add_command(pr_sync_commit, name="pr-sync-commit")
exec_group.add_command(post_workflow_started_comment, name="post-workflow-started-comment")
exec_group.add_command(preprocess_session, name="preprocess-session")
exec_group.add_command(promote_to_tripwire, name="promote-to-tripwire")
exec_group.add_command(quick_submit, name="quick-submit")
exec_group.add_command(rebase_with_conflict_resolution, name="rebase-with-conflict-resolution")
exec_group.add_command(resolve_review_thread, name="resolve-review-thread")
exec_group.add_command(run_review, name="run-review")
exec_group.add_command(reply_to_discussion_comment, name="reply-to-discussion-comment")
exec_group.add_command(session_id_injector_hook, name="session-id-injector-hook")
exec_group.add_command(setup_impl_from_issue, name="setup-impl-from-issue")
exec_group.add_command(track_learn_evaluation, name="track-learn-evaluation")
exec_group.add_command(track_learn_result, name="track-learn-result")
exec_group.add_command(trigger_async_learn, name="trigger-async-learn")
exec_group.add_command(tripwires_reminder_hook, name="tripwires-reminder-hook")
exec_group.add_command(update_dispatch_info, name="update-dispatch-info")
exec_group.add_command(update_issue_body, name="update-issue-body")
exec_group.add_command(update_plan_remote_session, name="update-plan-remote-session")
exec_group.add_command(upload_learn_materials, name="upload-learn-materials")
exec_group.add_command(upload_session, name="upload-session")
exec_group.add_command(ci_update_pr_body)
exec_group.add_command(close_issue_with_comment, name="close-issue-with-comment")
exec_group.add_command(user_prompt_hook, name="user-prompt-hook")
exec_group.add_command(validate_claude_credentials, name="validate-claude-credentials")
exec_group.add_command(validate_plan_content, name="validate-plan-content")
exec_group.add_command(wrap_plan_in_metadata_block, name="wrap-plan-in-metadata-block")
