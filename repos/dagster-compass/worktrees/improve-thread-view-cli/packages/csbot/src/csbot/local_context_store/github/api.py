"""Direct GitHub API functions.

This module provides direct wrappers around GitHub API endpoints with minimal logic.
Each function corresponds to a single GitHub API operation.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytz
import structlog
import yaml
from attr import dataclass

from csbot.local_context_store.github.config import GithubAuthSource

if TYPE_CHECKING:
    from csbot.contextengine.contextstore_protocol import (
        ContextAdditionRequestStatus,
    )
    from csbot.local_context_store.github.config import GithubConfig
    from csbot.slackbot.channel_bot.personalization import CompanyInfo

from .types import InitializedContextRepository
from .utils import extract_pr_number_from_url

logger = structlog.get_logger(__name__)


def create_repository(
    github_auth_source: GithubAuthSource, repo_name: str, org_name: str = "dagster-compass"
) -> str:
    """
    Create a new GitHub repository in the specified organization.

    Args:
        github_token: GitHub API token with repo creation permissions
        repo_name: Name of the repository to create
        org_name: Organization name (defaults to "dagster-compass")

    Returns:
        str: URL of the created repository

    Raises:
        Exception: If repository creation fails
    """
    g = github_auth_source.get_github_client()
    org = g.get_organization(org_name)

    repo = org.create_repo(
        name=repo_name,
        description=f"Context repository for {repo_name}",
        private=True,
        auto_init=True,
        gitignore_template="Python",
    )

    return repo.html_url


def initialize_contextstore_repository(
    github_auth_source: GithubAuthSource,
    repo_name: str,
    project_name: str,
    org_name: str,
    company: "CompanyInfo | None",
) -> InitializedContextRepository:
    """
    Initialize a contextstore repository with the necessary configuration files.

    Args:
        github_token: GitHub API token with repo write permissions
        repo_name: Name of the repository to initialize
        project_name: Name of the contextstore project (format: "org/project")
        org_name: Organization name (defaults to "dagster-compass")

    Returns:
        InitializedContextRepository: Object representing the initialized repository

    Raises:
        Exception: If file creation fails
    """
    from csbot.local_context_store.github.config import GithubConfig

    g = github_auth_source.get_github_client()
    repo = g.get_organization(org_name).get_repo(repo_name)

    # Create contextstore_project.yaml content
    project_config = {"project_name": project_name, "teams": {}}
    contextstore_yaml_content = yaml.safe_dump(project_config)

    # Create system_prompt.md content
    system_prompt_content = """
You are a friendly and helpful AI data analysis assistant.

You should be friendly, a bit cheeky, and respond to users in all lowercase.
Instead of saying stuff like "you're absolutely right!" when the user corrects you,
use an emoji like 🫠
""".strip()

    if company:
        system_prompt_content += f"\n\nYou are deployed at {company.name}. {company.description}"

    system_prompt_content = system_prompt_content.strip()

    # Create files in the repository
    created_files: list[str] = []

    try:
        # Create contextstore_project.yaml
        repo.create_file(
            path="contextstore_project.yaml",
            message="Initialize contextstore project configuration",
            content=contextstore_yaml_content,
            branch=repo.default_branch,
        )
        created_files.append("contextstore_project.yaml")

        # Create system_prompt.md
        repo.create_file(
            path="system_prompt.md",
            message="Initialize system prompt for AI assistant",
            content=system_prompt_content,
            branch=repo.default_branch,
        )
        created_files.append("system_prompt.md")

        # Create channels subfolder with .gitkeep
        repo.create_file(
            path="channels/.gitkeep",
            message="Initialize channels directory structure",
            content="",
            branch=repo.default_branch,
        )
        created_files.append("channels/.gitkeep")
    except Exception as e:
        raise Exception("Failed to initialize contextstore repository files") from e

    # Create GitHub configuration
    full_repo_name = f"{org_name}/{repo_name}"
    github_config = GithubConfig(auth_source=github_auth_source, repo_name=full_repo_name)

    return InitializedContextRepository(
        github_config=github_config,
        project_name=project_name,
        html_url=repo.html_url,
        created_files=created_files,
    )


def add_collaborator_to_repository(
    github_auth_source: GithubAuthSource,
    repo_name: str,
    collaborator: str,
    permission: str = "push",
    org_name: str = "dagster-compass",
) -> None:
    """
    Add a collaborator to a GitHub repository.

    Args:
        github_token: GitHub API token with repo administration permissions
        repo_name: Name of the repository
        collaborator: GitHub username or email address of the collaborator
        permission: Permission level ('pull', 'push', 'admin', 'maintain', 'triage')
        org_name: Organization name (defaults to "dagster-compass")

    Raises:
        Exception: If adding collaborator fails
    """
    g = github_auth_source.get_github_client()
    repo = g.get_organization(org_name).get_repo(repo_name)

    try:
        # Try to add the collaborator
        # Note: This works with GitHub usernames or email addresses if they have
        # a GitHub account associated with that email
        invitation = repo.add_to_collaborators(collaborator, permission=permission)

        if invitation is None:
            # User is already a collaborator
            return

    except Exception as e:
        raise Exception(
            f"Failed to add collaborator {collaborator} to repository {repo_name}: {e}"
        ) from e


def create_pull_request(
    config: "GithubConfig",
    title: str,
    body: str,
    head_branch: str,
) -> str:
    """
    Create a pull request in a GitHub repository.

    Args:
        config: GitHub configuration containing token and repo info
        title: Pull request title
        body: Pull request body
        head_branch: Name of the branch with changes

    Returns:
        str: URL of the created pull request
    """
    g = config.auth_source.get_github_client()
    github_repo = g.get_repo(config.repo_name)

    pr = github_repo.create_pull(
        title=title, body=body, head=head_branch, base=github_repo.default_branch
    )
    return pr.html_url


def merge_pull_request(config: "GithubConfig", pr_number: int) -> None:
    """
    Merge a pull request.

    Args:
        config: GitHub configuration containing token and repo info
        pr_number: Pull request number
    """
    g = config.auth_source.get_github_client()
    github_repo = g.get_repo(config.repo_name)
    pr = github_repo.get_pull(pr_number)
    pr.merge()


def create_issue(
    config: "GithubConfig",
    title: str,
    body: str,
    labels: list[str] | None = None,
) -> str:
    """
    Create an issue in a GitHub repository.

    Args:
        config: GitHub configuration containing token and repo info
        title: Issue title
        body: Issue body
        labels: Optional list of label names

    Returns:
        str: URL of the created issue
    """
    g = config.auth_source.get_github_client()
    github_repo = g.get_repo(config.repo_name)

    issue = github_repo.create_issue(title=title, body=body, labels=labels or [])
    return issue.html_url


def create_data_request_issue(
    config: "GithubConfig", title: str, body: str, attribution: str | None = None
) -> str:
    """
    Create a data request issue with standardized title prefix.

    Args:
        config: GitHub configuration containing token and repo info
        title: Issue title (will be prefixed with "REQUEST: ")
        body: Issue body
        attribution: Optional attribution to prepend to body

    Returns:
        str: URL of the created issue
    """
    final_body = body
    if attribution:
        final_body = f"{attribution}\n\n{body}"

    prefixed_title = f"REQUEST: {title}"
    return create_issue(config, prefixed_title, final_body)


def get_pull_request_status(
    config: "GithubConfig", pr_number: int
) -> "ContextAdditionRequestStatus":
    """
    Get the status of a pull request.

    Args:
        config: GitHub configuration containing token and repo info
        pr_number: Pull request number

    Returns:
        ContextAdditionRequestStatus: The status of the pull request
    """
    g = config.auth_source.get_github_client()
    github_repo = g.get_repo(config.repo_name)
    pr = github_repo.get_pull(pr_number)

    if pr.state == "closed":
        if pr.merged:
            return "approved"
        else:
            return "rejected"
    else:
        return "pending"


def add_pull_request_comment(config: "GithubConfig", pr_number: int, message: str) -> None:
    """
    Add a comment to a pull request.

    Args:
        config: GitHub configuration containing token and repo info
        pr_number: Pull request number
        message: Comment message
    """
    g = config.auth_source.get_github_client()
    github_repo = g.get_repo(config.repo_name)
    pr = github_repo.get_pull(pr_number)
    pr.create_issue_comment(message)


def close_pull_request(config: "GithubConfig", pr_number: int) -> None:
    """
    Close a pull request without merging.

    Args:
        config: GitHub configuration containing token and repo info
        pr_number: Pull request number
    """
    g = config.auth_source.get_github_client()
    github_repo = g.get_repo(config.repo_name)
    pr = github_repo.get_pull(pr_number)
    pr.edit(state="closed")


@dataclass(frozen=True)
class PrDetails:
    title: str
    body: str
    files: dict[str, str | None]


def get_pr_details(config: "GithubConfig", pr_number: int) -> PrDetails | None:
    g = config.auth_source.get_github_client()
    pr = g.get_repo(config.repo_name).get_pull(pr_number)
    files = pr.get_files()

    # Check if PR is too large (more than 10 files or total changes > 1000 lines)
    file_count = files.totalCount
    if file_count > 10:
        return None

    total_changes = sum(f.changes for f in files if f.changes)
    if total_changes > 1000:
        return None

    # Get file contents
    file_contents = {}
    repo = g.get_repo(config.repo_name)

    for file in files:
        if file.status == "removed":
            file_contents[file.filename] = (
                f"[FILE REMOVED] - Previous content was:\n{file.patch or ''}"
            )
        elif file.status == "added":
            try:
                content_result = repo.get_contents(file.filename, ref=pr.head.sha)
                # Handle both single file and list of files
                if isinstance(content_result, list):
                    content = content_result[0] if content_result else None
                else:
                    content = content_result

                if content and hasattr(content, "decoded_content"):
                    file_contents[file.filename] = content.decoded_content.decode("utf-8")
                else:
                    file_contents[file.filename] = f"[BINARY FILE] - {file.filename}"
            except Exception:
                file_contents[file.filename] = f"[ERROR READING FILE] - {file.filename}"
        else:  # modified
            try:
                content_result = repo.get_contents(file.filename, ref=pr.head.sha)
                # Handle both single file and list of files
                if isinstance(content_result, list):
                    content = content_result[0] if content_result else None
                else:
                    content = content_result

                if content and hasattr(content, "decoded_content"):
                    file_contents[file.filename] = content.decoded_content.decode("utf-8")
                else:
                    file_contents[file.filename] = f"[BINARY FILE] - {file.filename}"
            except Exception:
                file_contents[file.filename] = f"[ERROR READING FILE] - {file.filename}"

    return PrDetails(title=pr.title, body=pr.body or "", files=file_contents)


def update_pr_files(
    config: "GithubConfig",
    pr_number: int,
    file_updates: Mapping[str, str | None],
    commit_message: str,
) -> bool:
    g = config.auth_source.get_github_client()
    pr = g.get_repo(config.repo_name).get_pull(pr_number)
    pr_url = pr.html_url
    repo = g.get_repo(config.repo_name)

    # Get the head branch
    head_branch = pr.head.ref

    # Separate operations by type
    files_to_create = []
    files_to_update = []
    files_to_delete = []
    current_files = {}

    for file_path, desired_content in file_updates.items():
        try:
            # Check if file exists
            try:
                contents_result = repo.get_contents(file_path, ref=head_branch)
                # Handle both single file and list of files
                if isinstance(contents_result, list):
                    contents = contents_result[0] if contents_result else None
                else:
                    contents = contents_result

                if contents:
                    # File exists
                    current_content = contents.decoded_content.decode("utf-8")
                    current_files[file_path] = {
                        "content": current_content,
                        "sha": contents.sha,
                        "desired_content": desired_content,
                        "exists": True,
                    }

                    if desired_content is None:
                        # File should be deleted
                        files_to_delete.append(file_path)
                        logger.info(f"File {file_path} marked for deletion")
                    elif current_content.strip() != desired_content.strip():
                        # File needs update
                        files_to_update.append(file_path)
                        logger.info(f"File {file_path} needs update - content changed")
                    else:
                        # File is up to date
                        logger.info(f"File {file_path} already up to date - skipping")
                else:
                    # This shouldn't happen but handle it
                    if desired_content is not None:
                        files_to_create.append(file_path)
                        current_files[file_path] = {
                            "desired_content": desired_content,
                            "exists": False,
                        }
                        logger.info(f"File {file_path} marked for creation")

            except Exception:
                # File doesn't exist
                if desired_content is not None:
                    files_to_create.append(file_path)
                    current_files[file_path] = {
                        "desired_content": desired_content,
                        "exists": False,
                    }
                    logger.info(f"File {file_path} marked for creation")
                else:
                    # Trying to delete a file that doesn't exist - that's okay
                    logger.info(f"File {file_path} doesn't exist - deletion skipped")

        except Exception as e:
            logger.error(f"Error checking file {file_path} in PR {pr_url}: {e}")
            return False

    # If no operations needed, we're done
    total_operations = len(files_to_create) + len(files_to_update) + len(files_to_delete)
    if total_operations == 0:
        logger.info(f"All files in PR {pr_url} are already up to date")
        return True

    # Track successful operations
    operations_completed = 0

    # Handle file creations
    for file_path in files_to_create:
        try:
            file_info = current_files[file_path]

            # Create the file
            repo.create_file(
                path=file_path,
                message=f"{commit_message} - Create {file_path}",
                content=file_info["desired_content"],
                branch=head_branch,
            )
            operations_completed += 1
            logger.info(f"Successfully created {file_path}")

        except Exception as e:
            logger.error(f"Error creating file {file_path} in PR {pr_url}: {e}")
            # Continue with other files

    # Handle file updates
    for file_path in files_to_update:
        try:
            file_info = current_files[file_path]

            # Double-check that file hasn't changed since we read it
            # This handles concurrent modifications
            latest_contents_result = repo.get_contents(file_path, ref=head_branch)
            if isinstance(latest_contents_result, list):
                latest_contents = latest_contents_result[0] if latest_contents_result else None
            else:
                latest_contents = latest_contents_result

            if not latest_contents or latest_contents.sha != file_info["sha"]:
                logger.warning(f"File {file_path} was modified concurrently - skipping update")
                continue

            # Update the file
            repo.update_file(
                path=file_path,
                message=f"{commit_message} - Update {file_path}",
                content=file_info["desired_content"],
                sha=file_info["sha"],
                branch=head_branch,
            )
            operations_completed += 1
            logger.info(f"Successfully updated {file_path}")

        except Exception as e:
            logger.error(f"Error updating file {file_path} in PR {pr_url}: {e}")
            # Continue with other files

    # Handle file deletions
    for file_path in files_to_delete:
        try:
            file_info = current_files[file_path]

            # Double-check that file hasn't changed since we read it
            latest_contents_result = repo.get_contents(file_path, ref=head_branch)
            if isinstance(latest_contents_result, list):
                latest_contents = latest_contents_result[0] if latest_contents_result else None
            else:
                latest_contents = latest_contents_result

            if not latest_contents or latest_contents.sha != file_info["sha"]:
                logger.warning(f"File {file_path} was modified concurrently - skipping deletion")
                continue

            # Delete the file
            repo.delete_file(
                path=file_path,
                message=f"{commit_message} - Delete {file_path}",
                sha=file_info["sha"],
                branch=head_branch,
            )
            operations_completed += 1
            logger.info(f"Successfully deleted {file_path}")

        except Exception as e:
            logger.error(f"Error deleting file {file_path} in PR {pr_url}: {e}")
            # Continue with other files

    # Report results
    if operations_completed == 0:
        logger.warning(f"No file operations were completed in PR {pr_url}")
        return False
    elif operations_completed < total_operations:
        logger.warning(
            f"Only {operations_completed}/{total_operations} file operations "
            f"completed in PR {pr_url}"
        )

    logger.info(
        f"Successfully completed {operations_completed} file operations in PR {pr_url} "
        f"({len(files_to_create)} created, {len(files_to_update)} updated, "
        f"{len(files_to_delete)} deleted)"
    )
    return True


def update_pr_title_and_body(
    config: "GithubConfig", pr_number: int, title: str | None, body: str | None, user_name: str
) -> bool:
    g = config.auth_source.get_github_client()
    pr = g.get_repo(config.repo_name).get_pull(pr_number)

    update_kwargs = {}
    if title is not None:
        update_kwargs["title"] = title
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    attribution = f"**Updated by:** {user_name} at {timestamp}\n\n"
    if body is not None:
        update_kwargs["body"] = attribution + body
    else:
        update_kwargs["body"] = attribution + pr.body

    if update_kwargs:
        pr.edit(**update_kwargs)
        return True
    return False


def comment_on_pr(config: "GithubConfig", pr_number: int, comment: str) -> None:
    g = config.auth_source.get_github_client()
    pr = g.get_repo(config.repo_name).get_pull(pr_number)
    pr.create_issue_comment(comment)


@dataclass
class PrCreatedEvent:
    repo_name: str
    url: str
    pr_title: str
    pr_description: str
    timestamp: datetime


@dataclass
class PrMergedEvent:
    repo_name: str
    url: str
    pr_title: str
    pr_description: str
    timestamp: datetime


@dataclass
class PrClosedEvent:
    repo_name: str
    url: str
    pr_title: str
    pr_description: str
    timestamp: datetime


@dataclass
class IssueOpenedEvent:
    repo_name: str
    url: str
    issue_title: str
    issue_description: str
    timestamp: datetime


@dataclass
class IssueClosedEvent:
    repo_name: str
    url: str
    issue_title: str
    issue_description: str
    timestamp: datetime


PrEvent = PrCreatedEvent | PrMergedEvent | PrClosedEvent
IssueEvent = IssueOpenedEvent | IssueClosedEvent

GithubMonitorEvent = PrEvent | IssueEvent


def github_monitor_event_tick(
    config: "GithubConfig", since: datetime | None
) -> tuple[datetime | None, Sequence[GithubMonitorEvent]]:
    events = []

    # Get the repository
    g = config.auth_source.get_github_client()
    repo = g.get_repo(config.repo_name)
    first_page = repo.get_issues(state="all", sort="updated", direction="desc").get_page(0)
    if not first_page:
        if since and (datetime.now(pytz.utc) - since > timedelta(days=1)):
            # event when there are no updates, we should periodically update
            # the db indicating that we've checked up until this moment (-1 hours
            # to account for late arriving events)
            return datetime.now(pytz.utc) - timedelta(hours=1), []

        return None, []

    if not since:
        logger.info(f"No since timestamp, initializing to {first_page[0].updated_at}")
        return first_page[0].updated_at, []

    issues = repo.get_issues(
        state="all",
        sort="updated",
        direction="asc",
        since=since,
    )
    last_updated_at: datetime | None = None
    for issue in issues:
        if issue.updated_at == since:
            continue
        last_updated_at = issue.updated_at

        if issue.closed_at:
            if issue.pull_request:
                if issue.pull_request.merged_at:
                    events.append(
                        PrMergedEvent(
                            repo_name=config.repo_name,
                            url=issue.html_url,
                            pr_title=issue.title,
                            pr_description=issue.body or "",
                            timestamp=issue.closed_at,
                        )
                    )
                else:
                    events.append(
                        PrClosedEvent(
                            repo_name=config.repo_name,
                            url=issue.html_url,
                            pr_title=issue.title,
                            pr_description=issue.body or "",
                            timestamp=issue.closed_at,
                        )
                    )
            else:
                events.append(
                    IssueClosedEvent(
                        repo_name=config.repo_name,
                        url=issue.html_url,
                        issue_title=issue.title,
                        issue_description=issue.body or "",
                        timestamp=issue.closed_at,
                    )
                )
        else:
            if issue.pull_request:
                events.append(
                    PrCreatedEvent(
                        repo_name=config.repo_name,
                        url=issue.html_url,
                        pr_title=issue.title,
                        pr_description=issue.body or "",
                        timestamp=issue.created_at,
                    )
                )
            else:
                events.append(
                    IssueOpenedEvent(
                        repo_name=config.repo_name,
                        url=issue.html_url,
                        issue_title=issue.title,
                        issue_description=issue.body or "",
                        timestamp=issue.created_at,
                    )
                )

    return last_updated_at, events


def add_pr_attribution(config: "GithubConfig", pr_number: int, attribution: str) -> None:
    g = config.auth_source.get_github_client()
    repo = g.get_repo(config.repo_name)
    pr = repo.get_pull(pr_number)

    # Get current description
    current_body = pr.body or ""

    # Add attribution at the top
    new_body = f"{attribution}\n\n{current_body}"

    # Update the PR
    pr.edit(body=new_body)


def update_contextstore_system_prompt(
    github_auth_source: GithubAuthSource,
    git_org_name: str,
    repo_name: str,
    organization_name: str,
    industry: str,
) -> None:
    """
    Update the system prompt in an existing contextstore repository to include industry information.

    Args:
        github_token: GitHub API token with repo write permissions
        git_org_name: Name of the GitHub organization
        repo_name: Name of the repository to update
        organization_name: Name of the organization
        industry: Industry type (e.g., "B2B software", "Other")

    Raises:
        Exception: If file update fails
    """
    g = github_auth_source.get_github_client()
    repo = g.get_organization(git_org_name).get_repo(repo_name)

    # Create updated system_prompt.md content with industry information
    system_prompt_content = f"""
You are a friendly and helpful AI data analysis assistant for {organization_name}, a {industry} company.

You should be friendly, a bit cheeky, and respond to users in all lowercase.
Instead of saying stuff like "you're absolutely right!" when the user corrects you,
use an emoji like 🫠
""".strip()

    try:
        # Get the existing file to update it
        file_contents = repo.get_contents("system_prompt.md")

        # Handle the case where get_contents returns a list or single file
        if isinstance(file_contents, list):
            file = file_contents[0]
        else:
            file = file_contents

        # Update the file with new content
        repo.update_file(
            path="system_prompt.md",
            message="Update system prompt to include industry context",
            content=system_prompt_content,
            sha=file.sha,
            branch=repo.default_branch,
        )

    except Exception as e:
        raise Exception(f"Failed to update system prompt in contextstore repository: {e}") from e


def create_and_merge_pull_request(
    config: "GithubConfig",
    title: str,
    body: str,
    head_branch: str,
) -> str:
    """
    Create a pull request and immediately merge it.

    Args:
        config: GitHub configuration containing token and repo info
        title: Pull request title
        body: Pull request body
        head_branch: Name of the branch with changes

    Returns:
        str: URL of the created and merged pull request
    """
    pr_url = create_pull_request(config, title, body, head_branch)
    pr_number = extract_pr_number_from_url(pr_url)
    merge_pull_request(config, pr_number)
    return pr_url


def dispatch_workflow(
    config: "GithubConfig",
    workflow_id: str,
    ref: str,
    inputs: dict[str, str],
) -> int:
    """
    Dispatch a GitHub Actions workflow using workflow_dispatch trigger.

    Args:
        config: GitHub configuration containing token and repo info
        workflow_id: The workflow filename (e.g., 'deploy.yml') or ID
        ref: The git reference (branch/tag) to run the workflow on
        inputs: Dictionary of input parameters for the workflow

    Returns:
        int: The workflow run ID of the dispatched workflow
    """
    g = config.auth_source.get_github_client()
    github_repo = g.get_repo(config.repo_name)

    workflow = github_repo.get_workflow(workflow_id)
    workflow.create_dispatch(ref=ref, inputs=inputs)

    # Get the latest run for this workflow to return the run ID
    runs = workflow.get_runs()
    latest_run = next(iter(runs))
    return latest_run.id
