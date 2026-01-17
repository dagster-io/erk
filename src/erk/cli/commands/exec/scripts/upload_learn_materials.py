"""Upload preprocessed session files to learn-materials branch.

Usage:
    erk exec upload-learn-materials --issue <number> --session-id <id> <file>...

This command:
1. Creates learn-materials branch if it doesn't exist (from main/master)
2. Uploads each file to .learn-materials/<issue>/<session-id>/<filename> on that branch
3. Returns JSON with file URLs

Output:
    JSON with success status and uploaded file URLs

Exit Codes:
    0: Success - files uploaded
    1: Error - branch creation or upload failed

Examples:
    $ erk exec upload-learn-materials --issue 4991 --session-id abc123 session.xml
    {
      "success": true,
      "files": [
        {"path": ".learn-materials/4991/abc123/session.xml", "url": "https://..."}
      ]
    }
"""

import base64
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import click

from erk_shared.context.helpers import require_git, require_repo_root
from erk_shared.context.types import NoRepoSentinel

LEARN_MATERIALS_BRANCH = "learn-materials"
LEARN_MATERIALS_DIR = ".learn-materials"


@dataclass(frozen=True)
class UploadedFile:
    """Result of uploading a single file."""

    path: str
    url: str


@dataclass(frozen=True)
class UploadResult:
    """Complete result of upload operation."""

    success: bool
    files: list[dict[str, str]]
    error: str | None = None


def _output_error(message: str) -> None:
    """Output error JSON and exit."""
    result = {"success": False, "error": message}
    click.echo(json.dumps(result, indent=2))
    raise SystemExit(1)


def _get_owner_repo(ctx: click.Context) -> tuple[str, str]:
    """Get owner/repo from context."""
    repo = ctx.obj.repo
    if isinstance(repo, NoRepoSentinel):
        _output_error("Not in a git repository")
    if repo.github is None:
        _output_error("Repository has no GitHub remote configured")
    return repo.github.owner, repo.github.repo


def _get_default_branch(repo_root: Path) -> str:
    """Detect the default branch (main or master)."""
    result = subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        # Output is like "refs/remotes/origin/main"
        ref = result.stdout.strip()
        return ref.split("/")[-1]
    # Fallback: check if main or master exists
    for branch in ["main", "master"]:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return branch
    return "main"  # Default fallback


def _branch_exists(owner: str, repo: str) -> bool:
    """Check if learn-materials branch exists on remote."""
    result = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{owner}/{repo}/branches/{LEARN_MATERIALS_BRANCH}",
            "--silent",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _create_branch(owner: str, repo: str, base_branch: str) -> bool:
    """Create learn-materials branch from base branch.

    Uses GitHub API to create the branch without needing local checkout.
    """
    # First get the SHA of the base branch
    result = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{owner}/{repo}/git/refs/heads/{base_branch}",
            "--jq",
            ".object.sha",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False

    base_sha = result.stdout.strip()
    if not base_sha:
        return False

    # Create the new branch ref
    result = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{owner}/{repo}/git/refs",
            "-X",
            "POST",
            "-f",
            f"ref=refs/heads/{LEARN_MATERIALS_BRANCH}",
            "-f",
            f"sha={base_sha}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _get_existing_file_sha(owner: str, repo: str, file_path: str) -> str | None:
    """Get SHA of existing file for update, or None if not exists."""
    result = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{owner}/{repo}/contents/{file_path}",
            "-H",
            "Accept: application/vnd.github.v3+json",
            "--jq",
            ".sha",
            "-f",
            f"ref={LEARN_MATERIALS_BRANCH}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        sha = result.stdout.strip()
        if sha:
            return sha
    return None


def _upload_file(
    *,
    owner: str,
    repo: str,
    issue_number: int,
    session_id: str,
    local_path: Path,
    dest_filename: str,
) -> UploadedFile | str:
    """Upload a single file to the learn-materials branch.

    Returns UploadedFile on success, error message string on failure.
    """
    # Read and base64 encode the file
    if not local_path.exists():
        return f"File not found: {local_path}"

    content_bytes = local_path.read_bytes()
    content_b64 = base64.b64encode(content_bytes).decode("ascii")

    # Construct destination path
    dest_path = f"{LEARN_MATERIALS_DIR}/{issue_number}/{session_id}/{dest_filename}"

    # Check if file exists (need SHA for update)
    existing_sha = _get_existing_file_sha(owner, repo, dest_path)

    # Build the upload command
    cmd = [
        "gh",
        "api",
        f"repos/{owner}/{repo}/contents/{dest_path}",
        "-X",
        "PUT",
        "-f",
        f"message=Add learn materials for #{issue_number}",
        "-f",
        f"content={content_b64}",
        "-f",
        f"branch={LEARN_MATERIALS_BRANCH}",
    ]

    if existing_sha is not None:
        cmd.extend(["-f", f"sha={existing_sha}"])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        error_detail = result.stderr or result.stdout or "Unknown error"
        return f"Failed to upload {dest_filename}: {error_detail}"

    # Construct the URL to the file
    url = f"https://github.com/{owner}/{repo}/blob/{LEARN_MATERIALS_BRANCH}/{dest_path}"

    return UploadedFile(path=dest_path, url=url)


@click.command(name="upload-learn-materials")
@click.option(
    "--issue",
    "issue_number",
    type=int,
    required=True,
    help="GitHub issue number to organize files under",
)
@click.option(
    "--session-id",
    "session_id",
    type=str,
    required=True,
    help="Session ID to include in the file path",
)
@click.argument("files", nargs=-1, required=True, type=click.Path(exists=True))
@click.pass_context
def upload_learn_materials(
    ctx: click.Context,
    issue_number: int,
    session_id: str,
    files: tuple[str, ...],
) -> None:
    """Upload preprocessed session files to learn-materials branch.

    Creates the learn-materials branch if it doesn't exist, then uploads
    each file to .learn-materials/<issue>/<session-id>/<filename>.

    FILES are paths to local files to upload.
    """
    repo_root = require_repo_root(ctx)
    require_git(ctx)  # Validate we have git access

    owner, repo = _get_owner_repo(ctx)

    # Ensure learn-materials branch exists
    if not _branch_exists(owner, repo):
        default_branch = _get_default_branch(repo_root)
        if not _create_branch(owner, repo, default_branch):
            _output_error(f"Failed to create {LEARN_MATERIALS_BRANCH} branch")

    # Upload each file
    uploaded_files: list[dict[str, str]] = []
    errors: list[str] = []

    for file_path_str in files:
        file_path = Path(file_path_str)
        result = _upload_file(
            owner=owner,
            repo=repo,
            issue_number=issue_number,
            session_id=session_id,
            local_path=file_path,
            dest_filename=file_path.name,
        )
        if isinstance(result, str):
            errors.append(result)
        else:
            uploaded_files.append({"path": result.path, "url": result.url})

    if errors:
        # Partial failure
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "files": uploaded_files,
                    "errors": errors,
                },
                indent=2,
            )
        )
        raise SystemExit(1)

    click.echo(
        json.dumps(
            {
                "success": True,
                "files": uploaded_files,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    upload_learn_materials()
