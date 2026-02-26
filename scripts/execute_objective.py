#!/usr/bin/env python3
"""Execute all pending nodes in an objective, creating a stack of PRs.

Usage:
    python scripts/execute_objective.py <ISSUE_NUMBER> [OPTIONS]

Options:
    --dry-run              Preview without executing
    --max-nodes N          Limit number of nodes to execute
    --max-review-cycles N  Max review/address cycles per node (default: 2)
    --skip-reviews         Skip automated review feedback cycle
    --model MODEL          Claude model to use
    --dangerous            Skip Claude permissions
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# --- Utilities ---


def tprint(*args: object, **kwargs: object) -> None:
    """Print with a [HH:MM:SS] timestamp prefix."""
    stamp = time.strftime("%H:%M:%S")
    print(f"[{stamp}]", *args, **kwargs)


def slugify(text: str, *, max_len: int) -> str:
    """Convert text to a branch-name-safe slug."""
    slug = text.lower().replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    return slug.strip("-")[:max_len].rstrip("-")


def _build_claude_env() -> dict[str, str]:
    """Build environment for Claude subprocess.

    Strips CLAUDECODE to avoid nested session guard.
    """
    env = os.environ.copy()
    if "CLAUDECODE" in env:
        del env["CLAUDECODE"]
    return env


# --- Objective state ---


def get_objective_state(issue_number: int) -> dict:
    """Fetch and validate objective, return JSON state."""
    result = subprocess.run(
        ["erk", "objective", "check", str(issue_number), "--json-output"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        tprint(f"  objective check failed (exit {result.returncode})")
        if result.stderr:
            tprint(f"  stderr: {result.stderr.strip()}")
        # Try to parse stdout anyway — json-output writes JSON even on failure
        if result.stdout.strip():
            return json.loads(result.stdout)
        sys.exit(1)
    return json.loads(result.stdout)


def get_objective_body(issue_number: int) -> str:
    """Fetch the objective issue body for context."""
    result = subprocess.run(
        ["gh", "issue", "view", str(issue_number), "--json", "body", "-q", ".body"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


# --- Branch management ---


def create_stacked_branch(branch_name: str) -> None:
    """Create a new branch stacked on current using gt."""
    subprocess.run(
        ["gt", "create", branch_name, "--no-interactive"],
        check=True,
    )


# --- Implementation context ---


def write_impl_plan(
    issue_number: int,
    node: dict,
    objective_body: str,
    prior_results: list[tuple[str, int]],
) -> None:
    """Write .impl/plan.md with objective context + node task."""
    impl_dir = Path(".impl")
    impl_dir.mkdir(exist_ok=True)

    prior_section = ""
    if prior_results:
        lines = [f"- Step {nid}: PR #{pr}" for nid, pr in prior_results]
        prior_section = "## Prior Steps Completed\n" + "\n".join(lines) + "\n\n"

    plan = f"""# Objective #{issue_number}: Step {node["id"]}

## Context
This is step {node["id"]} of objective #{issue_number}.
Phase: {node.get("phase", "unknown")}

## Task
{node["description"]}

{prior_section}## Objective Background
{objective_body[:3000]}

## Implementation Notes
Implement the changes described above. Follow existing code patterns and conventions.
Run tests to verify your changes work correctly.
Commit your changes when done.
"""
    (impl_dir / "plan.md").write_text(plan, encoding="utf-8")


# --- Claude execution ---


def run_claude_implement(*, model: str | None, dangerous: bool) -> None:
    """Run Claude locally to implement the plan in .impl/plan.md."""
    cmd = ["claude", "--print", "--no-session-persistence"]
    if model:
        cmd.extend(["--model", model])
    if dangerous:
        cmd.append("--dangerously-skip-permissions")
    cmd.append("/erk:plan-implement")
    subprocess.run(cmd, check=True, env=_build_claude_env())


def run_claude_address_review(pr_number: int, *, model: str | None, dangerous: bool) -> None:
    """Run Claude locally to address PR review feedback."""
    cmd = ["claude", "--print", "--no-session-persistence"]
    if model:
        cmd.extend(["--model", model])
    if dangerous:
        cmd.append("--dangerously-skip-permissions")
    cmd.append(f"/erk:pr-address --pr {pr_number}")
    subprocess.run(cmd, check=True, env=_build_claude_env())


# --- PR submission ---


def submit_pr() -> int:
    """Submit PR via gt and return PR number."""
    subprocess.run(
        ["gt", "submit", "--no-interactive", "--no-edit"],
        check=True,
    )
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    result = subprocess.run(
        ["gh", "pr", "list", "--head", branch, "--json", "number", "-q", ".[0].number"],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(result.stdout.strip())


# --- Review cycle ---


def wait_for_code_reviews(pr_number: int, *, timeout: int, poll_interval: int) -> bool:
    """Wait for code-reviews workflow to complete on the PR. Returns True if completed."""
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    elapsed = 0
    while elapsed < timeout:
        result = subprocess.run(
            [
                "gh",
                "run",
                "list",
                "--workflow",
                "code-reviews.yml",
                "--branch",
                branch,
                "--limit",
                "1",
                "--json",
                "status,conclusion",
                "-q",
                ".[0]",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            run_info = json.loads(result.stdout.strip())
            if run_info.get("status") == "completed":
                return True

        time.sleep(poll_interval)
        elapsed += poll_interval
        tprint(f"    Waiting for code reviews... ({elapsed}s)")

    tprint(f"    Code review timeout after {timeout}s")
    return False


def has_unresolved_review_threads(pr_number: int) -> bool:
    """Check if a PR has unresolved review threads."""
    result = subprocess.run(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "reviewThreads",
            "-q",
            "[.reviewThreads[] | select(.isResolved == false)] | length",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    output = result.stdout.strip()
    if not output.isdigit():
        return False
    return int(output) > 0


def review_cycle(
    pr_number: int,
    *,
    max_cycles: int,
    model: str | None,
    dangerous: bool,
) -> None:
    """Run review -> address -> re-push cycle."""
    for cycle in range(max_cycles):
        tprint(f"  Review cycle {cycle + 1}/{max_cycles}:")

        # Wait for code reviews to run
        tprint(f"    Waiting for code reviews on PR #{pr_number}...")
        reviews_done = wait_for_code_reviews(pr_number, timeout=600, poll_interval=15)
        if not reviews_done:
            tprint("    Skipping review cycle (timeout).")
            break

        # Check for unresolved threads
        if not has_unresolved_review_threads(pr_number):
            tprint("    No unresolved review comments. Clean!")
            break

        # Address feedback
        tprint("    Addressing review feedback...")
        run_claude_address_review(pr_number, model=model, dangerous=dangerous)

        # Re-push
        tprint("    Pushing changes...")
        subprocess.run(["git", "push"], check=True)


# --- Objective update ---


def update_objective_node(issue_number: int, node_id: str, pr_number: int) -> None:
    """Mark node as in_progress with PR reference."""
    subprocess.run(
        [
            "erk",
            "exec",
            "update-objective-node",
            str(issue_number),
            "--node",
            node_id,
            "--pr",
            f"#{pr_number}",
            "--status",
            "in_progress",
        ],
        check=True,
    )


# --- Main loop ---


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute an objective's roadmap")
    parser.add_argument("issue_number", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-nodes", type=int, default=None)
    parser.add_argument("--max-review-cycles", type=int, default=2)
    parser.add_argument("--skip-reviews", action="store_true")
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--dangerous", action="store_true")
    args = parser.parse_args()

    issue_number = args.issue_number
    nodes_executed = 0
    results: list[tuple[str, int]] = []

    # Fetch objective body once for context
    objective_body = "" if args.dry_run else get_objective_body(issue_number)

    while True:
        if args.max_nodes is not None and nodes_executed >= args.max_nodes:
            tprint(f"\nReached --max-nodes limit ({args.max_nodes}).")
            break

        # Re-fetch objective state each iteration
        state = get_objective_state(issue_number)
        if not state.get("success", False):
            tprint(f"Objective validation failed: {state}")
            sys.exit(1)

        next_node = state.get("next_node")
        if next_node is None:
            summary = state.get("summary", {})
            if summary.get("done", 0) + summary.get("skipped", 0) >= summary.get("total_nodes", 0):
                tprint("\nAll nodes complete!")
            else:
                tprint("\nNo pending unblocked nodes remaining.")
            break

        node_id = next_node["id"]
        description = next_node["description"]
        phase = next_node.get("phase", "")
        total = state.get("summary", {}).get("total_nodes", "?")

        tprint(f"\n[{nodes_executed + 1}/{total}] Node {node_id}: {description} (Phase: {phase})")

        if args.dry_run:
            tprint(f"  Would execute: {node_id}: {description}")
            nodes_executed += 1
            continue

        # 1. Create stacked branch
        slug = next_node.get("slug") or slugify(description, max_len=30)
        branch_name = f"obj-{issue_number}-{node_id}-{slug}"
        tprint(f"  Creating branch {branch_name}...")
        create_stacked_branch(branch_name)

        # 2. Write .impl/plan.md
        tprint("  Writing implementation context...")
        write_impl_plan(issue_number, next_node, objective_body, results)

        # 3. Run Claude (implement)
        tprint("  Running Claude (plan + implement)...")
        run_claude_implement(model=args.model, dangerous=args.dangerous)

        # 4. Submit PR
        tprint("  Submitting PR...")
        pr_number = submit_pr()
        tprint(f"  -> PR #{pr_number} created")

        # 5. Review cycle
        if not args.skip_reviews:
            review_cycle(
                pr_number,
                max_cycles=args.max_review_cycles,
                model=args.model,
                dangerous=args.dangerous,
            )

        # 6. Update objective
        tprint("  Updating objective roadmap...")
        update_objective_node(issue_number, node_id, pr_number)

        results.append((node_id, pr_number))
        nodes_executed += 1

    # Summary
    if results:
        tprint(f"\nDone! Created {len(results)} PR(s) in stack:")
        for nid, pr in results:
            tprint(f"  PR #{pr}: node {nid}")
    elif not args.dry_run:
        tprint("\nNo nodes were executed.")


if __name__ == "__main__":
    main()
