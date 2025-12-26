"""Shared utilities and interfaces for erk and erk-kits.

Import from submodules:
- env: in_github_actions
- git.abc: Git, WorktreeInfo, find_worktree_for_branch
- git.real: RealGit
- github.abc: GitHub
- github.types: PRInfo, PRMergeability, PRState, PullRequestInfo, WorkflowRun
- github.issues: GitHubIssues, RealGitHubIssues, FakeGitHubIssues, etc.
- github.metadata: MetadataBlock, create_metadata_block, etc.
- impl_folder: IssueReference, read_issue_reference, etc.
- naming: sanitize_worktree_name, generate_filename_from_title
- output.output: user_output, machine_output, format_duration
- subprocess_utils: run_subprocess_with_context
- gateway.graphite.*: Graphite, RealGraphite, FakeGraphite, etc.
- gateway.time.*: Time, RealTime
- gateway.parallel.*: ParallelTaskRunner, RealParallelTaskRunner
"""

__version__ = "0.1.0"
