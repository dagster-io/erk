"""Unit tests for status history building utilities.

Layer 3 (Pure Unit Tests): Tests for pure status history construction logic.
Zero dependencies on external systems.
"""

from erk_shared.github.status_history import build_status_history, extract_workflow_run_id


class TestExtractWorkflowRunId:
    """Test extract_workflow_run_id function."""

    def test_empty_comments(self) -> None:
        """No comments returns None."""
        run_id = extract_workflow_run_id([])
        assert run_id is None

    def test_extracts_workflow_run_id(self) -> None:
        """Extracts workflow run ID from workflow-started metadata."""
        comment_body = """
<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: '2024-01-15T11:00:00Z'
workflow_run_id: '123456789'
workflow_run_url: https://github.com/org/repo/actions/runs/123456789
issue_number: 123
```

</details>
<!-- /erk:metadata-block:workflow-started -->
"""
        run_id = extract_workflow_run_id([comment_body])
        assert run_id == "123456789"

    def test_returns_most_recent_workflow_run(self) -> None:
        """Returns most recent workflow run when multiple exist."""
        older_comment = """
<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: '2024-01-15T10:00:00Z'
workflow_run_id: '111111111'
workflow_run_url: https://github.com/org/repo/actions/runs/111111111
issue_number: 123
```

</details>
<!-- /erk:metadata-block:workflow-started -->
"""
        newer_comment = """
<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: '2024-01-15T12:00:00Z'
workflow_run_id: '222222222'
workflow_run_url: https://github.com/org/repo/actions/runs/222222222
issue_number: 123
```

</details>
<!-- /erk:metadata-block:workflow-started -->
"""
        run_id = extract_workflow_run_id([older_comment, newer_comment])
        assert run_id == "222222222"

    def test_ignores_other_metadata_blocks(self) -> None:
        """Ignores non-workflow-started metadata blocks."""
        comment_body = """
<!-- erk:metadata-block:submission-queued -->
<details>
<summary><code>submission-queued</code></summary>

```yaml
status: queued
queued_at: '2024-01-15T10:00:00Z'
submitted_by: john.doe
issue_number: 123
validation_results: {}
expected_workflow: implement-plan.yml
trigger_mechanism: label-based-webhook
```

</details>
<!-- /erk:metadata-block:submission-queued -->

<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: '2024-01-15T11:00:00Z'
workflow_run_id: '123456789'
workflow_run_url: https://github.com/org/repo/actions/runs/123456789
issue_number: 123
```

</details>
<!-- /erk:metadata-block:workflow-started -->
"""
        run_id = extract_workflow_run_id([comment_body])
        assert run_id == "123456789"

    def test_missing_workflow_run_id_field(self) -> None:
        """Returns None if workflow_run_id field is missing."""
        comment_body = """
<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: '2024-01-15T11:00:00Z'
workflow_run_url: https://github.com/org/repo/actions/runs/123456789
issue_number: 123
```

</details>
<!-- /erk:metadata-block:workflow-started -->
"""
        run_id = extract_workflow_run_id([comment_body])
        assert run_id is None

    def test_missing_started_at_field(self) -> None:
        """Returns None if started_at field is missing."""
        comment_body = """
<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
workflow_run_id: '123456789'
workflow_run_url: https://github.com/org/repo/actions/runs/123456789
issue_number: 123
```

</details>
<!-- /erk:metadata-block:workflow-started -->
"""
        run_id = extract_workflow_run_id([comment_body])
        assert run_id is None

    def test_comments_without_metadata(self) -> None:
        """Handles regular comments without metadata blocks."""
        regular_comment = "This is a regular comment without any metadata blocks."
        run_id = extract_workflow_run_id([regular_comment])
        assert run_id is None


class TestBuildStatusHistory:
    """Test build_status_history function."""

    def test_empty_comments(self) -> None:
        """No comments results in just completion event."""
        history = build_status_history([], "2024-01-15T12:00:00Z")

        assert len(history) == 1
        assert history[0]["status"] == "completed"
        assert history[0]["timestamp"] == "2024-01-15T12:00:00Z"
        assert history[0]["reason"] == "Implementation finished"

    def test_submission_queued_event(self) -> None:
        """Extracts submission-queued event from metadata."""
        comment_body = """
<!-- erk:metadata-block:submission-queued -->
<details>
<summary><code>submission-queued</code></summary>

```yaml
status: queued
queued_at: '2024-01-15T10:00:00Z'
submitted_by: john.doe
issue_number: 123
validation_results:
  issue_is_open: true
  has_erk_plan_label: true
expected_workflow: implement-plan.yml
trigger_mechanism: label-based-webhook
```

</details>
<!-- /erk:metadata-block:submission-queued -->
"""
        history = build_status_history([comment_body], "2024-01-15T12:00:00Z")

        assert len(history) == 2
        assert history[0]["status"] == "queued"
        assert history[0]["timestamp"] == "2024-01-15T10:00:00Z"
        assert history[0]["reason"] == "erk plan submit executed"
        assert history[1]["status"] == "completed"

    def test_workflow_started_event(self) -> None:
        """Extracts workflow-started event from metadata."""
        comment_body = """
<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: '2024-01-15T11:00:00Z'
workflow_run_id: '123456789'
workflow_run_url: https://github.com/org/repo/actions/runs/123456789
issue_number: 123
```

</details>
<!-- /erk:metadata-block:workflow-started -->
"""
        history = build_status_history([comment_body], "2024-01-15T12:00:00Z")

        assert len(history) == 2
        assert history[0]["status"] == "started"
        assert history[0]["timestamp"] == "2024-01-15T11:00:00Z"
        assert history[0]["reason"] == "GitHub Actions workflow triggered"
        assert history[1]["status"] == "completed"

    def test_full_lifecycle(self) -> None:
        """Extracts all events from full lifecycle."""
        queued_comment = """
<!-- erk:metadata-block:submission-queued -->
<details>
<summary><code>submission-queued</code></summary>

```yaml
status: queued
queued_at: '2024-01-15T10:00:00Z'
submitted_by: john.doe
issue_number: 123
validation_results: {}
expected_workflow: implement-plan.yml
trigger_mechanism: label-based-webhook
```

</details>
<!-- /erk:metadata-block:submission-queued -->
"""
        started_comment = """
<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: '2024-01-15T11:00:00Z'
workflow_run_id: '123456789'
workflow_run_url: https://github.com/org/repo/actions/runs/123456789
issue_number: 123
```

</details>
<!-- /erk:metadata-block:workflow-started -->
"""
        history = build_status_history(
            [queued_comment, started_comment],
            "2024-01-15T12:00:00Z",
        )

        assert len(history) == 3
        assert history[0]["status"] == "queued"
        assert history[0]["timestamp"] == "2024-01-15T10:00:00Z"
        assert history[1]["status"] == "started"
        assert history[1]["timestamp"] == "2024-01-15T11:00:00Z"
        assert history[2]["status"] == "completed"
        assert history[2]["timestamp"] == "2024-01-15T12:00:00Z"

    def test_multiple_blocks_same_comment(self) -> None:
        """Handles multiple metadata blocks in same comment."""
        comment_body = """
<!-- erk:metadata-block:submission-queued -->
<details>
<summary><code>submission-queued</code></summary>

```yaml
status: queued
queued_at: '2024-01-15T10:00:00Z'
submitted_by: john.doe
issue_number: 123
validation_results: {}
expected_workflow: implement-plan.yml
trigger_mechanism: label-based-webhook
```

</details>
<!-- /erk:metadata-block:submission-queued -->

<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: '2024-01-15T11:00:00Z'
workflow_run_id: '123456789'
workflow_run_url: https://github.com/org/repo/actions/runs/123456789
issue_number: 123
```

</details>
<!-- /erk:metadata-block:workflow-started -->
"""
        history = build_status_history([comment_body], "2024-01-15T12:00:00Z")

        assert len(history) == 3
        assert history[0]["status"] == "queued"
        assert history[1]["status"] == "started"
        assert history[2]["status"] == "completed"

    def test_ignores_other_metadata_blocks(self) -> None:
        """Ignores metadata blocks that aren't status events."""
        comment_body = """
<!-- erk:metadata-block:erk-plan -->
<details>
<summary><code>erk-plan</code></summary>

```yaml
issue_number: 123
worktree_name: feature-123
timestamp: '2024-01-15T09:00:00Z'
```

</details>
<!-- /erk:metadata-block:erk-plan -->

<!-- erk:metadata-block:submission-queued -->
<details>
<summary><code>submission-queued</code></summary>

```yaml
status: queued
queued_at: '2024-01-15T10:00:00Z'
submitted_by: john.doe
issue_number: 123
validation_results: {}
expected_workflow: implement-plan.yml
trigger_mechanism: label-based-webhook
```

</details>
<!-- /erk:metadata-block:submission-queued -->
"""
        history = build_status_history([comment_body], "2024-01-15T12:00:00Z")

        assert len(history) == 2  # queued + completed, not erk-plan
        assert history[0]["status"] == "queued"
        assert history[1]["status"] == "completed"

    def test_missing_timestamp_field(self) -> None:
        """Skips events with missing timestamp fields."""
        comment_body = """
<!-- erk:metadata-block:submission-queued -->
<details>
<summary><code>submission-queued</code></summary>

```yaml
status: queued
submitted_by: john.doe
issue_number: 123
validation_results: {}
expected_workflow: implement-plan.yml
trigger_mechanism: label-based-webhook
```

</details>
<!-- /erk:metadata-block:submission-queued -->
"""
        history = build_status_history([comment_body], "2024-01-15T12:00:00Z")

        # Should only have completion event since queued_at is missing
        assert len(history) == 1
        assert history[0]["status"] == "completed"

    def test_invalid_yaml_skipped(self) -> None:
        """Skips comments with invalid metadata blocks."""
        invalid_comment = """
<!-- erk:metadata-block:submission-queued -->
<details>
<summary><code>submission-queued</code></summary>

```yaml
invalid yaml [[ content
```

</details>
<!-- /erk:metadata-block:submission-queued -->
"""
        valid_comment = """
<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: '2024-01-15T11:00:00Z'
workflow_run_id: '123456789'
workflow_run_url: https://github.com/org/repo/actions/runs/123456789
issue_number: 123
```

</details>
<!-- /erk:metadata-block:workflow-started -->
"""
        history = build_status_history(
            [invalid_comment, valid_comment],
            "2024-01-15T12:00:00Z",
        )

        # Should only have started + completed (invalid skipped)
        assert len(history) == 2
        assert history[0]["status"] == "started"
        assert history[1]["status"] == "completed"

    def test_comments_without_metadata(self) -> None:
        """Handles regular comments without metadata blocks."""
        regular_comment = """
This is a regular comment without any metadata blocks.
Just plain text.
"""
        history = build_status_history([regular_comment], "2024-01-15T12:00:00Z")

        assert len(history) == 1
        assert history[0]["status"] == "completed"

    def test_preserves_chronological_order(self) -> None:
        """Events appear in chronological order based on input."""
        # Comments in reverse chronological order (newest first, like GitHub)
        comments = [
            """
<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: '2024-01-15T11:00:00Z'
workflow_run_id: '123456789'
workflow_run_url: https://github.com/org/repo/actions/runs/123456789
issue_number: 123
```

</details>
<!-- /erk:metadata-block:workflow-started -->
""",
            """
<!-- erk:metadata-block:submission-queued -->
<details>
<summary><code>submission-queued</code></summary>

```yaml
status: queued
queued_at: '2024-01-15T10:00:00Z'
submitted_by: john.doe
issue_number: 123
validation_results: {}
expected_workflow: implement-plan.yml
trigger_mechanism: label-based-webhook
```

</details>
<!-- /erk:metadata-block:submission-queued -->
""",
        ]

        history = build_status_history(comments, "2024-01-15T12:00:00Z")

        # Order should be: started, queued (as they appear), then completed
        assert len(history) == 3
        assert history[0]["status"] == "started"
        assert history[1]["status"] == "queued"
        assert history[2]["status"] == "completed"
