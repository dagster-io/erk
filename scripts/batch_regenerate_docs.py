#!/usr/bin/env python3
"""Batch regenerate and audit recently created docs.

Discovers docs created in the last 2 weeks, regenerates each against
current content quality standards via `claude --print`, then audits
with /local:audit-doc.

Automatically resumable: completed docs are tracked in logs/batch-regen-state.json.
Re-running the script skips previously succeeded docs and retries failed ones.

Usage:
    python scripts/batch_regenerate_docs.py                           # sonnet regen, opus audit
    python scripts/batch_regenerate_docs.py --regen-model opus        # opus for both steps
    python scripts/batch_regenerate_docs.py --dry-run                 # list docs only
    python scripts/batch_regenerate_docs.py --limit 5                 # first 5 docs
    python scripts/batch_regenerate_docs.py --fresh                   # ignore prior progress
    python scripts/batch_regenerate_docs.py --file docs/learned/x.md  # target a specific file
"""

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

STATE_FILE = Path("logs/batch-regen-state.json")


@dataclass(frozen=True)
class DocResult:
    """Outcome of processing a single doc."""

    path: str
    succeeded: bool
    failed_step: str  # "" if succeeded, "regen" or "audit" if failed
    elapsed_seconds: int
    regen_seconds: int
    audit_seconds: int
    lines_before: int
    lines_after_regen: int
    lines_after_audit: int


def load_state(path: Path) -> dict[str, dict[str, str | int]]:
    """Read and return the state dict. Return empty dict if file doesn't exist."""
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_state(path: Path, state: dict[str, dict[str, str | int]]) -> None:
    """Write state dict to file atomically (write to .tmp, then rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(state, indent=2) + "\n")
    tmp_path.rename(path)


REGEN_PROMPT_TEMPLATE = """\
You are regenerating a learned doc to meet current content quality standards.

## Instructions

1. Read the content quality standards from .claude/skills/learned-docs/learned-docs-core.md
2. Read the document at: {doc_path}
3. Extract all source code file references from the document (file paths, imports, function names)
4. Read every referenced source file to understand the actual code
5. Completely rewrite the document following the quality standards:
   - Only cross-cutting insights (not single-artifact knowledge)
   - Explain WHY, not WHAT — the code already shows the what
   - One Code Rule: no reproduced source code except: data formats, third-party API patterns, \
anti-patterns marked WRONG, and I/O examples
   - Use source pointers (see docs/learned/documentation/source-pointers.md for format) instead \
of code blocks
   - Keep: decision tables, anti-patterns with explanations, cross-cutting patterns, historical \
context, tripwires
   - Remove: import paths, function signatures, docstring paraphrases, file listings
6. Preserve the frontmatter structure (title, read_when, tripwires) — improve their quality if \
needed but keep the same fields
7. Save the rewritten document to the same path

Do NOT change the document's topic or scope. Regenerate it in-place with higher quality content."""


def count_lines(path: str) -> int:
    """Return the number of lines in a file, or 0 if it doesn't exist."""
    p = Path(path)
    if not p.exists():
        return 0
    return len(p.read_text().splitlines())


def format_line_delta(before: int, after: int) -> str:
    """Format a line-count change as e.g. '42 -> 35 (-7)' or '42 -> 50 (+8)'."""
    delta = after - before
    sign = "+" if delta > 0 else ""
    return f"{before} -> {after} ({sign}{delta})"


def discover_docs() -> list[str]:
    """Discover docs created in the last 2 weeks via git log."""
    result = subprocess.run(
        [
            "git",
            "log",
            "--since=2 weeks ago",
            "--diff-filter=A",
            "--name-only",
            "--pretty=format:",
            "--",
            "docs/learned/",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"Error running git log: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    seen: set[str] = set()
    docs: list[str] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if not line.endswith(".md"):
            continue
        if line.endswith("index.md"):
            continue
        if line.endswith("tripwires.md"):
            continue
        if line.endswith("tripwires-index.md"):
            continue
        if line in seen:
            continue
        seen.add(line)
        docs.append(line)

    docs.sort()

    # Filter to docs that still exist on disk
    return [doc for doc in docs if Path(doc).exists()]


def build_regen_prompt(*, doc_path: str) -> str:
    """Return the regeneration prompt for a given doc path."""
    return REGEN_PROMPT_TEMPLATE.format(doc_path=doc_path)


def run_claude(
    *,
    prompt: str,
    model: str,
    timeout: int,
    log_path: Path,
) -> int:
    """Run claude --print and return the exit code. Output goes to log_path."""
    cmd = [
        "claude",
        "--print",
        "--dangerously-skip-permissions",
        "--model",
        model,
        prompt,
    ]
    with log_path.open("w") as log_file:
        result = subprocess.run(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    return result.returncode


def _failed_result(
    *,
    doc: str,
    step: str,
    start: float,
    regen_seconds: int,
    lines_before: int,
    lines_after_regen: int,
) -> DocResult:
    """Build a DocResult for a failed step."""
    elapsed = int(time.monotonic() - start)
    return DocResult(
        path=doc,
        succeeded=False,
        failed_step=step,
        elapsed_seconds=elapsed,
        regen_seconds=regen_seconds,
        audit_seconds=0,
        lines_before=lines_before,
        lines_after_regen=lines_after_regen,
        lines_after_audit=lines_after_regen,
    )


def process_doc(
    *,
    doc: str,
    regen_model: str,
    audit_model: str,
    timeout: int,
    log_dir: Path,
) -> DocResult:
    """Process a single doc: regenerate then audit. Returns the outcome."""
    sanitized = doc.replace("/", "-")
    start = time.monotonic()
    lines_before = count_lines(doc)

    # Step 1: Regenerate
    regen_prompt = build_regen_prompt(doc_path=doc)
    regen_log = log_dir / f"{sanitized}-regen.log"

    print(f"  Regenerating ({regen_model})... ", end="", flush=True)
    regen_start = time.monotonic()
    try:
        regen_exit = run_claude(
            prompt=regen_prompt,
            model=regen_model,
            timeout=timeout,
            log_path=regen_log,
        )
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT after {timeout}s")
        return _failed_result(
            doc=doc, step="regen", start=start,
            regen_seconds=timeout, lines_before=lines_before, lines_after_regen=lines_before,
        )
    regen_secs = int(time.monotonic() - regen_start)
    lines_after_regen = count_lines(doc)

    if regen_exit != 0:
        print(f"FAILED (exit {regen_exit}) [{regen_secs}s]")
        return _failed_result(
            doc=doc, step="regen", start=start,
            regen_seconds=regen_secs, lines_before=lines_before,
            lines_after_regen=lines_after_regen,
        )

    print(f"done [{regen_secs}s, lines {format_line_delta(lines_before, lines_after_regen)}]")

    # Step 2: Audit
    audit_log = log_dir / f"{sanitized}-audit.log"
    audit_prompt = f"/local:audit-doc {doc} --auto-apply"

    print(f"  Auditing ({audit_model})... ", end="", flush=True)
    audit_start = time.monotonic()
    try:
        audit_exit = run_claude(
            prompt=audit_prompt,
            model=audit_model,
            timeout=timeout,
            log_path=audit_log,
        )
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT after {timeout}s")
        elapsed = int(time.monotonic() - start)
        return DocResult(
            path=doc, succeeded=False, failed_step="audit",
            elapsed_seconds=elapsed, regen_seconds=regen_secs, audit_seconds=timeout,
            lines_before=lines_before, lines_after_regen=lines_after_regen,
            lines_after_audit=count_lines(doc),
        )
    audit_secs = int(time.monotonic() - audit_start)
    lines_after_audit = count_lines(doc)

    elapsed = int(time.monotonic() - start)

    if audit_exit != 0:
        print(f"FAILED (exit {audit_exit}) [{audit_secs}s]")
        return DocResult(
            path=doc, succeeded=False, failed_step="audit",
            elapsed_seconds=elapsed, regen_seconds=regen_secs, audit_seconds=audit_secs,
            lines_before=lines_before, lines_after_regen=lines_after_regen,
            lines_after_audit=lines_after_audit,
        )

    print(f"done [{audit_secs}s, lines {format_line_delta(lines_after_regen, lines_after_audit)}]")
    print(f"  Total: {elapsed}s, net lines {format_line_delta(lines_before, lines_after_audit)}")
    return DocResult(
        path=doc, succeeded=True, failed_step="",
        elapsed_seconds=elapsed, regen_seconds=regen_secs, audit_seconds=audit_secs,
        lines_before=lines_before, lines_after_regen=lines_after_regen,
        lines_after_audit=lines_after_audit,
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Batch regenerate and audit recently created docs.",
    )
    parser.add_argument(
        "--regen-model",
        default="sonnet",
        help="Claude model for regeneration step (default: sonnet)",
    )
    parser.add_argument(
        "--audit-model",
        default="opus",
        help="Claude model for audit step (default: opus)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List docs that would be processed, then exit",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N docs (0 = no limit)",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Clear state file and start from scratch (ignore prior progress)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds per claude invocation (default: 300)",
    )
    parser.add_argument(
        "--file",
        action="append",
        dest="files",
        help="Target specific file(s) instead of git log discovery (repeatable, ignores state)",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point."""
    args = parse_args()

    # Determine doc list: explicit files or git log discovery
    if args.files:
        missing = [f for f in args.files if not Path(f).exists()]
        if missing:
            for f in missing:
                print(f"Error: file not found: {f}", file=sys.stderr)
            sys.exit(1)
        all_docs = args.files
        print(f"Targeting {len(all_docs)} specified file(s)")
        # --file mode ignores state (always processes)
        state: dict[str, dict[str, str | int]] = {}
        skipped: list[str] = []
        docs = list(all_docs)
    else:
        print("Discovering docs created in the last 2 weeks...")
        all_docs = discover_docs()
        print(f"Found {len(all_docs)} docs (after filtering deleted/renamed)")

        # Handle --fresh: clear state file
        if args.fresh and STATE_FILE.exists():
            STATE_FILE.unlink()
            print("Cleared state file (--fresh)")

        # Load state and filter out already-succeeded docs
        state = load_state(STATE_FILE)
        skipped = [d for d in all_docs if state.get(d, {}).get("status") == "succeeded"]
        docs = [d for d in all_docs if state.get(d, {}).get("status") != "succeeded"]

        if skipped:
            print(f"Skipping {len(skipped)} already-succeeded docs, {len(docs)} remaining")

    # Handle --limit
    if args.limit > 0 and args.limit < len(docs):
        docs = docs[: args.limit]
        print(f"Limited to {args.limit} docs")

    # Dry run
    if args.dry_run:
        print()
        if skipped:
            print(f"Skipped ({len(skipped)} already succeeded):")
            for doc in skipped:
                print(f"  {doc}")
            print()
        print(f"Would process ({len(docs)} docs):")
        print()
        for doc in docs:
            prior = state.get(doc, {})
            if prior.get("status") == "failed":
                suffix = f" (retry — previously failed: {prior['failed_step']})"
            else:
                suffix = ""
            print(f"  {doc}{suffix}")
        print()
        print(f"Total: {len(docs)} to process, {len(skipped)} skipped")
        return

    # Create log directory
    log_dir = Path("logs") / f"batch-regen-{time.strftime('%Y%m%d-%H%M%S')}"
    log_dir.mkdir(parents=True, exist_ok=True)
    print(f"Log directory: {log_dir}")

    # Process docs
    results: list[DocResult] = []
    start_time = time.monotonic()

    for i, doc in enumerate(docs, start=1):
        print()
        print(f"[{i}/{len(docs)}] Processing: {doc}")
        result = process_doc(
            doc=doc,
            regen_model=args.regen_model,
            audit_model=args.audit_model,
            timeout=args.timeout,
            log_dir=log_dir,
        )
        results.append(result)

        # Record result in state file immediately (survives interruption)
        if result.succeeded:
            state[doc] = {"status": "succeeded", "elapsed_seconds": result.elapsed_seconds}
        else:
            state[doc] = {
                "status": "failed",
                "failed_step": result.failed_step,
                "elapsed_seconds": result.elapsed_seconds,
            }
        save_state(STATE_FILE, state)

        # Write to summary log
        summary_path = log_dir / "summary.log"
        status = "OK" if result.succeeded else f"FAILED ({result.failed_step})"
        line_summary = (
            f"lines {result.lines_before}->{result.lines_after_regen}->{result.lines_after_audit}"
        )
        timing = (
            f"regen {result.regen_seconds}s + audit {result.audit_seconds}s"
            f" = {result.elapsed_seconds}s"
        )
        with summary_path.open("a") as f:
            f.write(f"{result.path} | {status} | {timing} | {line_summary}\n")

    # Final summary
    total_elapsed = int(time.monotonic() - start_time)
    succeeded = sum(1 for r in results if r.succeeded)
    failed_results = [r for r in results if not r.succeeded]

    total_regen_secs = sum(r.regen_seconds for r in results)
    total_audit_secs = sum(r.audit_seconds for r in results)
    total_lines_before = sum(r.lines_before for r in results)
    total_lines_after = sum(r.lines_after_audit for r in results)
    net_lines = total_lines_after - total_lines_before
    net_sign = "+" if net_lines > 0 else ""

    print()
    print("==========================================")
    print("Batch Regeneration Complete")
    print("==========================================")
    print(f"Total docs:    {len(docs)}")
    print(f"Succeeded:     {succeeded}")
    print(f"Failed:        {len(failed_results)}")
    print(f"Wall clock:    {total_elapsed}s")
    print(f"Regen time:    {total_regen_secs}s total")
    print(f"Audit time:    {total_audit_secs}s total")
    print(f"Lines before:  {total_lines_before}")
    print(f"Lines after:   {total_lines_after} ({net_sign}{net_lines})")
    print(f"Logs:          {log_dir}/")
    print("==========================================")

    if failed_results:
        print()
        print("Failed docs (retry manually):")
        for r in failed_results:
            print(f"  {r.path} ({r.failed_step})")


if __name__ == "__main__":
    main()
