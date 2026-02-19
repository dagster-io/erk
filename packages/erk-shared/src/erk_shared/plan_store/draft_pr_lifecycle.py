"""Draft PR Lifecycle.

Draft PRs serve as the backing store for plans when the plan backend is
"github-draft-pr". Unlike issue-based plans (where the plan issue and
implementation PR are separate), draft-PR-backed plans evolve through
lifecycle stages within a single PR.

Branch Files
------------
Draft PR branches contain ``.erk/branch-data/plan.md`` and
``.erk/branch-data/ref.json``, committed before PR creation to avoid
GitHub's "empty branch" rejection. ``plan.md`` enables inline review
comments on the plan via the PR's "Files Changed" tab and gets replaced
when implementation begins. ``ref.json`` carries plan reference metadata
(provider, objective_id).

Stages
------

0. One-Shot Dispatch (optional, UNIMPLEMENTED for draft_pr backend)
   Currently one-shot uses issue-based storage: it creates a skeleton plan
   issue, creates a draft PR referencing it, and dispatches to GitHub Actions
   for remote planning + implementation. Adapting one-shot to the draft_pr
   backend would mean the draft PR IS the plan (no separate issue), and the
   workflow would update the PR body through stages 1-3 below.

   Status: Not yet implemented. One-shot continues to use issue-based storage.

1. Plan Creation
   ``plan_save`` / ``DraftPRPlanBackend.create_plan()`` creates a draft PR.
   The body contains the plan-header metadata block, the plan content
   collapsed in a <details> tag, and a checkout footer.

   Body format::

       [metadata block]
       \\n\\n---\\n\\n
       <details>
       <summary><code>original-plan</code></summary>

       [plan content]

       </details>
       \\n---\\n
       [checkout footer]

2. Implementation
   After code changes, ``erk pr submit`` / ``erk pr rewrite`` rewrites the body.
   The metadata block is preserved. The AI-generated summary is inserted
   before the collapsed plan. The footer is regenerated.

   Body format::

       [metadata block]
       \\n\\n---\\n\\n
       [AI-generated summary]

       <details>
       <summary><code>original-plan</code></summary>

       [plan content]

       </details>
       \\n---\\n
       [checkout footer]

   Key invariant: No "Closes #N" in footer. The draft PR IS the plan --
   the plan_id from prepare_state is the PR's own number. Using it in
   Closes would be self-referential.

3. Review & Merge
   PR is marked ready for review. Standard review/merge flow.
   No body format changes in this stage.

Separators
----------
- Content separator: ``\\n\\n---\\n\\n`` (double newline each side) --
  between metadata block and content section
- Footer separator: ``\\n---\\n`` (single newline each side) --
  standard PR footer delimiter

These are distinct: find() matches the first (content), rsplit() matches
the last (footer).
"""

PLAN_CONTENT_SEPARATOR = "\n\n---\n\n"
DETAILS_OPEN = "<details>\n<summary><code>original-plan</code></summary>\n\n"
_LEGACY_DETAILS_OPEN = "<details>\n<summary>original-plan</summary>\n\n"
DETAILS_CLOSE = "\n\n</details>"


def build_plan_stage_body(metadata_body: str, plan_content: str) -> str:
    """Build Stage 1 body: metadata + separator + details-wrapped plan.

    The footer is NOT included here because it needs the PR number,
    which isn't known until after ``create_pr`` returns.

    Args:
        metadata_body: Rendered plan-header metadata block
        plan_content: Plan markdown content

    Returns:
        Combined PR body ready for ``create_pr`` (without footer)
    """
    return metadata_body + PLAN_CONTENT_SEPARATOR + DETAILS_OPEN + plan_content + DETAILS_CLOSE


def build_original_plan_section(plan_content: str) -> str:
    """Build the ``<details><summary>original-plan</summary>`` section.

    Used by both Stage 1 (plan creation) and Stage 2 (implementation)
    to wrap the original plan content in a collapsible section.

    Args:
        plan_content: Plan markdown content

    Returns:
        Details-wrapped plan section
    """
    return "\n\n" + DETAILS_OPEN + plan_content + DETAILS_CLOSE


def extract_plan_content(pr_body: str) -> str:
    """Extract plan content from a PR body at any lifecycle stage.

    Looks for ``DETAILS_OPEN`` / ``DETAILS_CLOSE`` tags and extracts the
    content between them. Falls back to the old flat format (content after
    ``PLAN_CONTENT_SEPARATOR``) for backward compatibility.

    Args:
        pr_body: Full PR body string

    Returns:
        Plan content portion of the body
    """
    # Try new <code>-tagged format first, then legacy plain-text format
    for details_open in (DETAILS_OPEN, _LEGACY_DETAILS_OPEN):
        open_idx = pr_body.find(details_open)
        if open_idx != -1:
            content_start = open_idx + len(details_open)
            close_idx = pr_body.find(DETAILS_CLOSE, content_start)
            if close_idx != -1:
                return pr_body[content_start:close_idx]

    # Backward compat: old flat format (metadata + separator + plan content)
    separator_index = pr_body.find(PLAN_CONTENT_SEPARATOR)
    if separator_index == -1:
        return pr_body
    return pr_body[separator_index + len(PLAN_CONTENT_SEPARATOR) :]


def extract_metadata_prefix(pr_body: str) -> str:
    """Extract the metadata block + separator for preservation during stage transitions.

    Returns everything up to and including the content separator.
    If no separator is found, returns an empty string.

    Args:
        pr_body: Full PR body string

    Returns:
        Metadata prefix (metadata block + separator) or empty string
    """
    separator_index = pr_body.find(PLAN_CONTENT_SEPARATOR)
    if separator_index == -1:
        return ""
    return pr_body[: separator_index + len(PLAN_CONTENT_SEPARATOR)]
