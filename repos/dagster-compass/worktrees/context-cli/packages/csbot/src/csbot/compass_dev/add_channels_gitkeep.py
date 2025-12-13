"""Add channels/.gitkeep file to a GitHub repository."""

import base64
import sys
from urllib.parse import urlparse

import click
import requests

from csbot.local_context_store.github.config import GitHubAppAuthSource


def extract_repo_info(repo_url: str) -> tuple[str, str]:
    """Extract owner and repo name from GitHub URL."""
    parsed = urlparse(repo_url)
    if parsed.hostname != "github.com":
        raise ValueError("Repository URL must be a GitHub URL")

    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) < 2:
        raise ValueError("Invalid GitHub repository URL")

    owner, repo = path_parts[0], path_parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]

    return owner, repo


@click.command()
@click.argument("repo_url")
@click.argument("app_id", type=int)
@click.argument("installation_id", type=int)
@click.argument("private_key_path", type=click.Path(exists=True))
def add_channels_gitkeep(repo_url: str, app_id: int, installation_id: int, private_key_path: str):
    """Add channels/.gitkeep file to a GitHub repository.

    Creates a channels subdirectory with a .gitkeep file and commits it to master
    with the message "Add separate channels subdirectory".

    REPO_URL: GitHub repository URL (e.g., https://github.com/user/repo)
    APP_ID: GitHub App ID
    INSTALLATION_ID: GitHub App Installation ID
    PRIVATE_KEY_PATH: Path to the GitHub App private key file
    """
    try:
        owner, repo = extract_repo_info(repo_url)
    except ValueError as e:
        click.echo(f"Error: {e}")
        sys.exit(1)

    # Create GitHub App auth source and get token
    try:
        auth_source = GitHubAppAuthSource(
            app_id=app_id, installation_id=installation_id, private_key_path=private_key_path
        )
        github_token = auth_source.get_auth_token_sync()
    except Exception as e:
        click.echo(f"Error getting GitHub App token: {e}")
        sys.exit(1)

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "compass-dev-cli",
    }

    # Get the latest commit SHA from the default branch (try master first, then main)
    default_branch = None
    default_sha = None

    for branch_name in ["master", "main"]:
        click.echo(f"Checking for {branch_name} branch...")
        branch_ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{branch_name}"
        response = requests.get(branch_ref_url, headers=headers)

        if response.status_code == 200:
            default_branch = branch_name
            default_sha = response.json()["object"]["sha"]
            click.echo(f"Found {branch_name} branch with commit SHA: {default_sha}")
            break
        elif response.status_code == 404:
            click.echo(f"Branch {branch_name} not found")
            continue
        else:
            click.echo(
                f"Error checking {branch_name} branch: {response.status_code} - {response.text}"
            )
            sys.exit(1)

    if not default_branch or not default_sha:
        click.echo("Error: Neither 'master' nor 'main' branch found in the repository")
        sys.exit(1)

    # Get the tree SHA from the latest commit
    commit_url = f"https://api.github.com/repos/{owner}/{repo}/git/commits/{default_sha}"
    response = requests.get(commit_url, headers=headers)

    if response.status_code != 200:
        click.echo(f"Error getting commit details: {response.status_code} - {response.text}")
        sys.exit(1)

    tree_sha = response.json()["tree"]["sha"]
    click.echo(f"Base tree SHA: {tree_sha}")

    # Create a blob for the .gitkeep file (empty content)
    click.echo("Creating blob for .gitkeep file...")
    blob_url = f"https://api.github.com/repos/{owner}/{repo}/git/blobs"
    blob_data = {"content": base64.b64encode(b"").decode("utf-8"), "encoding": "base64"}

    response = requests.post(blob_url, json=blob_data, headers=headers)
    if response.status_code != 201:
        click.echo(f"Error creating blob: {response.status_code} - {response.text}")
        sys.exit(1)

    blob_sha = response.json()["sha"]
    click.echo(f"Created blob SHA: {blob_sha}")

    # Create a new tree with the .gitkeep file
    click.echo("Creating new tree with channels/.gitkeep...")
    tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees"
    tree_data = {
        "base_tree": tree_sha,
        "tree": [{"path": "channels/.gitkeep", "mode": "100644", "type": "blob", "sha": blob_sha}],
    }

    response = requests.post(tree_url, json=tree_data, headers=headers)
    if response.status_code != 201:
        click.echo(f"Error creating tree: {response.status_code} - {response.text}")
        sys.exit(1)

    new_tree_sha = response.json()["sha"]
    click.echo(f"Created new tree SHA: {new_tree_sha}")

    # Create a new commit
    click.echo("Creating commit...")
    commit_url = f"https://api.github.com/repos/{owner}/{repo}/git/commits"
    commit_data = {
        "message": "Add separate channels subdirectory",
        "tree": new_tree_sha,
        "parents": [default_sha],
        "author": {"name": "dagster-compass-bot[bot]", "email": "noreply@github.com"},
        "committer": {"name": "dagster-compass-bot[bot]", "email": "noreply@github.com"},
    }

    response = requests.post(commit_url, json=commit_data, headers=headers)
    if response.status_code != 201:
        click.echo(f"Error creating commit: {response.status_code} - {response.text}")
        sys.exit(1)

    new_commit_sha = response.json()["sha"]
    click.echo(f"Created commit SHA: {new_commit_sha}")

    # Update the default branch to point to the new commit
    click.echo(f"Updating {default_branch} branch...")
    update_ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{default_branch}"
    update_data = {"sha": new_commit_sha, "force": False}

    response = requests.patch(update_ref_url, json=update_data, headers=headers)
    if response.status_code != 200:
        click.echo(
            f"Error updating {default_branch} branch: {response.status_code} - {response.text}"
        )
        sys.exit(1)

    click.echo(f"Successfully added channels/.gitkeep to {default_branch} branch!")
    click.echo(f"Repository: https://github.com/{owner}/{repo}")
    click.echo(f"Commit: https://github.com/{owner}/{repo}/commit/{new_commit_sha}")
