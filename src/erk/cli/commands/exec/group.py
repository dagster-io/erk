"""Static exec group for erk scripts.

This module provides the `erk exec` command group with all scripts
statically registered.
"""

import click

# Import and register all scripts
from erk.cli.commands.exec.scripts.add_objective_node import add_objective_node
from erk.cli.commands.exec.scripts.add_plan_label import add_plan_label
from erk.cli.commands.exec.scripts.add_plan_labels import add_plan_labels
from erk.cli.commands.exec.scripts.add_pr_labels_cmd import add_pr_labels
from erk.cli.commands.exec.scripts.add_remote_execution_note import (
    add_remote_execution_note,
)
from erk.cli.commands.exec.scripts.capture_session_info import (
    capture_session_info,
)
from erk.cli.commands.exec.scripts.ci_fetch_summaries import ci_fetch_summaries
from erk.cli.commands.exec.scripts.ci_generate_summaries import ci_generate_summaries
from erk.cli.commands.exec.scripts.ci_update_pr_body import ci_update_pr_body
from erk.cli.commands.exec.scripts.ci_verify_autofix import ci_verify_autofix
from erk.cli.commands.exec.scripts.cleanup_impl_context import cleanup_impl_context
from erk.cli.commands.exec.scripts.close_pr import (
    close_pr,
)
from erk.cli.commands.exec.scripts.close_prs import close_prs
from erk.cli.commands.exec.scripts.cmux_checkout_workspace import cmux_open_pr
from erk.cli.commands.exec.scripts.create_impl_context_from_plan import (
    create_impl_context_from_plan,
)
from erk.cli.commands.exec.scripts.create_pr_from_session import (
    create_pr_from_session,
)
from erk.cli.commands.exec.scripts.dash_data import dash_data
from erk.cli.commands.exec.scripts.detect_plan_from_branch import (
    detect_plan_from_branch,
)
from erk.cli.commands.exec.scripts.detect_trunk_branch import detect_trunk_branch
from erk.cli.commands.exec.scripts.discover_reviews import discover_reviews
from erk.cli.commands.exec.scripts.download_remote_session import (
    download_remote_session,
)
from erk.cli.commands.exec.scripts.exit_plan_mode_hook import exit_plan_mode_hook
from erk.cli.commands.exec.scripts.extract_latest_plan import extract_latest_plan
from erk.cli.commands.exec.scripts.fetch_sessions import fetch_sessions
from erk.cli.commands.exec.scripts.generate_pr_address_summary import (
    generate_pr_address_summary,
)
from erk.cli.commands.exec.scripts.get_embedded_prompt import get_embedded_prompt
from erk.cli.commands.exec.scripts.get_issue_body import get_issue_body
from erk.cli.commands.exec.scripts.get_issue_timeline_prs import (
    get_issue_timeline_prs,
)
from erk.cli.commands.exec.scripts.get_learn_sessions import get_learn_sessions
from erk.cli.commands.exec.scripts.get_plan_info import get_plan_info
from erk.cli.commands.exec.scripts.get_plan_metadata import get_plan_metadata
from erk.cli.commands.exec.scripts.get_plans_for_objective import (
    get_plans_for_objective,
)
from erk.cli.commands.exec.scripts.get_pr_body_footer import get_pr_body_footer
from erk.cli.commands.exec.scripts.get_pr_commits import get_pr_commits
from erk.cli.commands.exec.scripts.get_pr_context import get_pr_context
from erk.cli.commands.exec.scripts.get_pr_discussion_comments import (
    get_pr_discussion_comments,
)
from erk.cli.commands.exec.scripts.get_pr_feedback import get_pr_feedback
from erk.cli.commands.exec.scripts.get_pr_for_plan import get_pr_for_plan
from erk.cli.commands.exec.scripts.get_pr_review_comments import (
    get_pr_review_comments,
)
from erk.cli.commands.exec.scripts.get_pr_view import get_pr_view
from erk.cli.commands.exec.scripts.get_review_activity_log import (
    get_review_activity_log,
)
from erk.cli.commands.exec.scripts.handle_no_changes import handle_no_changes
from erk.cli.commands.exec.scripts.impl_init import impl_init
from erk.cli.commands.exec.scripts.impl_signal import impl_signal
from erk.cli.commands.exec.scripts.impl_verify import impl_verify
from erk.cli.commands.exec.scripts.incremental_dispatch import (
    incremental_dispatch,
)
from erk.cli.commands.exec.scripts.land_execute import land_execute
from erk.cli.commands.exec.scripts.list_sessions import list_sessions
from erk.cli.commands.exec.scripts.marker import marker
from erk.cli.commands.exec.scripts.migrate_objective_schema import (
    migrate_objective_schema,
)
from erk.cli.commands.exec.scripts.normalize_tripwire_candidates import (
    normalize_tripwire_candidates,
)
from erk.cli.commands.exec.scripts.objective_apply_landed_update import (
    objective_apply_landed_update,
)
from erk.cli.commands.exec.scripts.objective_fetch_context import (
    objective_fetch_context,
)
from erk.cli.commands.exec.scripts.objective_link_pr import (
    objective_link_pr,
)
from erk.cli.commands.exec.scripts.objective_plan_setup import (
    objective_plan_setup,
)
from erk.cli.commands.exec.scripts.objective_post_action_comment import (
    objective_post_action_comment,
)
from erk.cli.commands.exec.scripts.objective_render_roadmap import (
    objective_render_roadmap,
)
from erk.cli.commands.exec.scripts.objective_save_to_issue import (
    objective_save_to_issue,
)
from erk.cli.commands.exec.scripts.objective_update_after_land import (
    objective_update_after_land,
)
from erk.cli.commands.exec.scripts.plan_save import plan_save
from erk.cli.commands.exec.scripts.plan_update import plan_update
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
from erk.cli.commands.exec.scripts.pre_tool_use_hook import pre_tool_use_hook
from erk.cli.commands.exec.scripts.preprocess_session import preprocess_session
from erk.cli.commands.exec.scripts.push_and_create_pr import push_and_create_pr
from erk.cli.commands.exec.scripts.push_session import push_session
from erk.cli.commands.exec.scripts.quick_submit import quick_submit
from erk.cli.commands.exec.scripts.rebase_with_conflict_resolution import (
    rebase_with_conflict_resolution,
)
from erk.cli.commands.exec.scripts.register_one_shot_plan import (
    register_one_shot_plan,
)
from erk.cli.commands.exec.scripts.reply_to_discussion_comment import (
    reply_to_discussion_comment,
)
from erk.cli.commands.exec.scripts.resolve_objective_ref import (
    resolve_objective_ref,
)
from erk.cli.commands.exec.scripts.resolve_review_thread import (
    resolve_review_thread,
)
from erk.cli.commands.exec.scripts.resolve_review_threads import (
    resolve_review_threads,
)
from erk.cli.commands.exec.scripts.run_review import run_review
from erk.cli.commands.exec.scripts.session_id_injector_hook import (
    session_id_injector_hook,
)
from erk.cli.commands.exec.scripts.set_local_review_marker import (
    set_local_review_marker,
)
from erk.cli.commands.exec.scripts.set_pr_description import set_pr_description
from erk.cli.commands.exec.scripts.setup_impl import setup_impl
from erk.cli.commands.exec.scripts.setup_impl_from_pr import (
    setup_impl_from_pr,
)
from erk.cli.commands.exec.scripts.store_tripwire_candidates import (
    store_tripwire_candidates,
)
from erk.cli.commands.exec.scripts.summarize_impl_failure import (
    summarize_impl_failure,
)
from erk.cli.commands.exec.scripts.track_learn_evaluation import (
    track_learn_evaluation,
)
from erk.cli.commands.exec.scripts.track_learn_result import (
    track_learn_result,
)
from erk.cli.commands.exec.scripts.update_issue_body import update_issue_body
from erk.cli.commands.exec.scripts.update_objective_node import update_objective_node
from erk.cli.commands.exec.scripts.update_plan_header import update_plan_header
from erk.cli.commands.exec.scripts.update_pr_description import (
    update_pr_description,
)
from erk.cli.commands.exec.scripts.upload_impl_session import upload_impl_session
from erk.cli.commands.exec.scripts.user_prompt_hook import user_prompt_hook
from erk.cli.commands.exec.scripts.validate_claude_credentials import (
    validate_claude_credentials,
)
from erk.cli.commands.exec.scripts.validate_plan_content import (
    validate_plan_content,
)


# Create the exec group (hidden from top-level help)
@click.group(name="exec", hidden=True)
def exec_group() -> None:
    """Execute erk workflow scripts."""


# Register all commands
exec_group.add_command(add_objective_node, name="add-objective-node")
exec_group.add_command(add_plan_label, name="add-plan-label")
exec_group.add_command(add_plan_labels, name="add-plan-labels")
exec_group.add_command(add_pr_labels, name="add-pr-labels")
exec_group.add_command(add_remote_execution_note, name="add-remote-execution-note")
exec_group.add_command(capture_session_info, name="capture-session-info")
exec_group.add_command(cleanup_impl_context, name="cleanup-impl-context")
exec_group.add_command(cmux_open_pr, name="cmux-open-pr")
exec_group.add_command(create_pr_from_session, name="create-pr-from-session")
exec_group.add_command(dash_data, name="dash-data")
exec_group.add_command(create_impl_context_from_plan, name="create-impl-context-from-plan")
exec_group.add_command(detect_plan_from_branch, name="detect-plan-from-branch")
exec_group.add_command(detect_trunk_branch, name="detect-trunk-branch")
exec_group.add_command(discover_reviews, name="discover-reviews")
exec_group.add_command(download_remote_session, name="download-remote-session")
exec_group.add_command(exit_plan_mode_hook, name="exit-plan-mode-hook")
exec_group.add_command(extract_latest_plan, name="extract-latest-plan")
exec_group.add_command(fetch_sessions, name="fetch-sessions")
exec_group.add_command(generate_pr_address_summary, name="generate-pr-address-summary")
exec_group.add_command(get_plan_info, name="get-plan-info")
exec_group.add_command(get_plan_metadata, name="get-plan-metadata")
exec_group.add_command(get_plans_for_objective, name="get-plans-for-objective")
exec_group.add_command(get_pr_for_plan, name="get-pr-for-plan")
exec_group.add_command(get_pr_view, name="get-pr-view")
exec_group.add_command(get_embedded_prompt, name="get-embedded-prompt")
exec_group.add_command(get_issue_body, name="get-issue-body")
exec_group.add_command(get_issue_timeline_prs, name="get-issue-timeline-prs")
exec_group.add_command(get_learn_sessions, name="get-learn-sessions")
exec_group.add_command(get_pr_body_footer, name="get-pr-body-footer")
exec_group.add_command(get_pr_context, name="get-pr-context")
exec_group.add_command(handle_no_changes, name="handle-no-changes")
exec_group.add_command(get_pr_commits, name="get-pr-commits")
exec_group.add_command(get_pr_discussion_comments, name="get-pr-discussion-comments")
exec_group.add_command(get_pr_feedback, name="get-pr-feedback")
exec_group.add_command(get_pr_review_comments, name="get-pr-review-comments")
exec_group.add_command(get_review_activity_log, name="get-review-activity-log")
exec_group.add_command(incremental_dispatch, name="incremental-dispatch")
exec_group.add_command(impl_init, name="impl-init")
exec_group.add_command(impl_signal, name="impl-signal")
exec_group.add_command(impl_verify, name="impl-verify")
exec_group.add_command(land_execute, name="land-execute")
exec_group.add_command(list_sessions, name="list-sessions")
exec_group.add_command(marker, name="marker")
exec_group.add_command(migrate_objective_schema, name="migrate-objective-schema")
exec_group.add_command(normalize_tripwire_candidates, name="normalize-tripwire-candidates")
exec_group.add_command(objective_render_roadmap, name="objective-render-roadmap")
exec_group.add_command(objective_save_to_issue, name="objective-save-to-issue")
exec_group.add_command(objective_apply_landed_update, name="objective-apply-landed-update")
exec_group.add_command(objective_fetch_context, name="objective-fetch-context")
exec_group.add_command(objective_plan_setup, name="objective-plan-setup")
exec_group.add_command(objective_link_pr, name="objective-link-pr")
exec_group.add_command(objective_update_after_land, name="objective-update-after-land")
exec_group.add_command(objective_post_action_comment, name="objective-post-action-comment")
exec_group.add_command(plan_save, name="plan-save")
exec_group.add_command(plan_update, name="plan-update")
exec_group.add_command(post_or_update_pr_summary, name="post-or-update-pr-summary")
exec_group.add_command(post_pr_inline_comment, name="post-pr-inline-comment")
exec_group.add_command(pr_sync_commit, name="pr-sync-commit")
exec_group.add_command(post_workflow_started_comment, name="post-workflow-started-comment")
exec_group.add_command(pre_tool_use_hook, name="pre-tool-use-hook")
exec_group.add_command(preprocess_session, name="preprocess-session")
exec_group.add_command(push_and_create_pr, name="push-and-create-pr")
exec_group.add_command(push_session, name="push-session")
exec_group.add_command(quick_submit, name="quick-submit")
exec_group.add_command(rebase_with_conflict_resolution, name="rebase-with-conflict-resolution")
exec_group.add_command(register_one_shot_plan, name="register-one-shot-plan")
exec_group.add_command(resolve_objective_ref, name="resolve-objective-ref")
exec_group.add_command(resolve_review_thread, name="resolve-review-thread")
exec_group.add_command(resolve_review_threads, name="resolve-review-threads")
exec_group.add_command(run_review, name="run-review")
exec_group.add_command(reply_to_discussion_comment, name="reply-to-discussion-comment")
exec_group.add_command(session_id_injector_hook, name="session-id-injector-hook")
exec_group.add_command(set_local_review_marker, name="set-local-review-marker")
exec_group.add_command(set_pr_description, name="set-pr-description")
exec_group.add_command(setup_impl, name="setup-impl")
exec_group.add_command(setup_impl_from_pr, name="setup-impl-from-pr")
exec_group.add_command(store_tripwire_candidates, name="store-tripwire-candidates")
exec_group.add_command(summarize_impl_failure, name="summarize-impl-failure")
exec_group.add_command(track_learn_evaluation, name="track-learn-evaluation")
exec_group.add_command(track_learn_result, name="track-learn-result")
exec_group.add_command(update_issue_body, name="update-issue-body")
exec_group.add_command(update_plan_header, name="update-plan-header")
exec_group.add_command(update_objective_node, name="update-objective-node")
exec_group.add_command(update_pr_description, name="update-pr-description")
exec_group.add_command(upload_impl_session, name="upload-impl-session")
exec_group.add_command(ci_fetch_summaries, name="ci-fetch-summaries")
exec_group.add_command(ci_generate_summaries, name="ci-generate-summaries")
exec_group.add_command(ci_update_pr_body)
exec_group.add_command(ci_verify_autofix, name="ci-verify-autofix")
exec_group.add_command(close_pr, name="close-pr")
exec_group.add_command(close_prs, name="close-prs")
exec_group.add_command(user_prompt_hook, name="user-prompt-hook")
exec_group.add_command(validate_claude_credentials, name="validate-claude-credentials")
exec_group.add_command(validate_plan_content, name="validate-plan-content")
