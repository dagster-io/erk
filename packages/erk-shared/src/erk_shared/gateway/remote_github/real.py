"""Real implementation of RemoteGitHub using HttpClient.

All GitHub operations are performed via the REST API through HttpClient,
with no local git repository or gh CLI required.
"""

import base64
import secrets
import string

from erk_shared.gateway.http.abc import HttpClient
from erk_shared.gateway.remote_github.abc import RemoteGitHub
from erk_shared.gateway.time.abc import Time
from erk_shared.output.output import user_output


class RealRemoteGitHub(RemoteGitHub):
    """Production implementation using HttpClient for all GitHub API calls."""

    def __init__(self, *, http_client: HttpClient, time: Time) -> None:
        """Create RealRemoteGitHub.

        Args:
            http_client: Authenticated HTTP client for GitHub API
            time: Time gateway for polling delays
        """
        self._http = http_client
        self._time = time

    def get_authenticated_user(self) -> str:
        """Get the authenticated GitHub username."""
        response = self._http.get("user")
        login = response.get("login")
        if login is None:
            raise RuntimeError("GitHub API returned user without login field")
        return login

    def get_default_branch_name(self, *, owner: str, repo: str) -> str:
        """Get the default branch name for a repository."""
        response = self._http.get(f"repos/{owner}/{repo}")
        branch = response.get("default_branch")
        if branch is None:
            raise RuntimeError(
                f"GitHub API returned repo {owner}/{repo} without default_branch field"
            )
        return branch

    def get_default_branch_sha(self, *, owner: str, repo: str) -> str:
        """Get the SHA of the default branch HEAD."""
        default_branch = self.get_default_branch_name(owner=owner, repo=repo)
        response = self._http.get(f"repos/{owner}/{repo}/git/ref/heads/{default_branch}")
        sha = response.get("object", {}).get("sha")
        if sha is None:
            raise RuntimeError(
                f"GitHub API returned ref for {owner}/{repo} heads/{default_branch} without SHA"
            )
        return sha

    def create_ref(self, *, owner: str, repo: str, ref: str, sha: str) -> None:
        """Create a git reference (branch)."""
        self._http.post(
            f"repos/{owner}/{repo}/git/refs",
            data={"ref": ref, "sha": sha},
        )

    def create_file_commit(
        self,
        *,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
    ) -> str:
        """Create a file commit using the GitHub Contents API."""
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
        response = self._http.put(
            f"repos/{owner}/{repo}/contents/{path}",
            data={
                "message": message,
                "content": encoded_content,
                "branch": branch,
            },
        )
        sha = response.get("commit", {}).get("sha")
        if sha is None:
            raise RuntimeError(
                f"GitHub Contents API returned response without commit SHA for {path}"
            )
        return sha

    def create_pull_request(
        self,
        *,
        owner: str,
        repo: str,
        head: str,
        base: str,
        title: str,
        body: str,
        draft: bool,
    ) -> int:
        """Create a pull request."""
        response = self._http.post(
            f"repos/{owner}/{repo}/pulls",
            data={
                "head": head,
                "base": base,
                "title": title,
                "body": body,
                "draft": draft,
            },
        )
        pr_number = response.get("number")
        if pr_number is None:
            raise RuntimeError("GitHub API returned PR without number field")
        return pr_number

    def update_pull_request_body(
        self,
        *,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
    ) -> None:
        """Update a pull request's body."""
        self._http.patch(
            f"repos/{owner}/{repo}/pulls/{pr_number}",
            data={"body": body},
        )

    def add_labels(
        self,
        *,
        owner: str,
        repo: str,
        issue_number: int,
        labels: tuple[str, ...],
    ) -> None:
        """Add labels to an issue or PR."""
        self._http.post(
            f"repos/{owner}/{repo}/issues/{issue_number}/labels",
            data={"labels": list(labels)},
        )

    def dispatch_workflow(
        self,
        *,
        owner: str,
        repo: str,
        workflow: str,
        ref: str,
        inputs: dict[str, str],
    ) -> str:
        """Dispatch a workflow and poll for the run ID.

        Replicates the dispatch+poll pattern from RealLocalGitHub.trigger_workflow
        but uses HttpClient instead of subprocess.
        """
        distinct_id = _generate_distinct_id()

        # Dispatch the workflow
        payload = {"ref": ref, "inputs": {"distinct_id": distinct_id, **inputs}}
        self._http.post(
            f"repos/{owner}/{repo}/actions/workflows/{workflow}/dispatches",
            data=payload,
        )

        # Poll for the run by matching distinct_id in display_title
        max_attempts = 11
        for attempt in range(max_attempts):
            user_output(f"  Waiting for workflow run... (attempt {attempt + 1}/{max_attempts})")

            runs_response = self._http.get(
                f"repos/{owner}/{repo}/actions/workflows/{workflow}/runs?per_page=10"
            )
            runs_data = runs_response.get("workflow_runs", [])

            for run in runs_data:
                display_title = run.get("display_title", "")
                if f":{distinct_id}" not in display_title:
                    continue

                conclusion = run.get("conclusion")
                if conclusion in ("skipped", "cancelled"):
                    raise RuntimeError(
                        f"Workflow '{workflow}' run was {conclusion}.\n"
                        f"Run ID: {run['id']}, title: '{display_title}'"
                    )

                return str(run["id"])

            # Exponential backoff: 1, 2, 4, 8, 8, 8, ...
            delay = min(2**attempt, 8)
            self._time.sleep(delay)

        raise RuntimeError(
            f"Timed out waiting for workflow '{workflow}' run after {max_attempts} attempts"
        )

    def add_issue_comment(
        self,
        *,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
    ) -> None:
        """Add a comment to an issue or PR."""
        self._http.post(
            f"repos/{owner}/{repo}/issues/{issue_number}/comments",
            data={"body": body},
        )


def _generate_distinct_id() -> str:
    """Generate a random base36 ID for workflow dispatch correlation.

    Returns:
        6-character base36 string (e.g., 'a1b2c3')
    """
    base36_chars = string.digits + string.ascii_lowercase
    return "".join(secrets.choice(base36_chars) for _ in range(6))
