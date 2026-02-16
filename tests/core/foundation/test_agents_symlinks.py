from pathlib import Path


def test_each_agents_md_has_claude_md_reference() -> None:
    """Verify that every AGENTS.md has a peer CLAUDE.md that starts with '@AGENTS.md'.

    This follows the AGENTS.md standard where AGENTS.md is the primary file and
    CLAUDE.md starts with @AGENTS.md (may include additional Claude-specific content).

    See: https://code.claude.com/docs/en/claude-code-on-the-web
    """
    repo_root = Path(__file__).parent.parent

    # Find all AGENTS.md files
    agents_files = list(repo_root.rglob("AGENTS.md"))

    # Ensure we found at least one (so test doesn't pass vacuously)
    assert len(agents_files) > 0, "Expected to find at least one AGENTS.md file"

    for agents_file in agents_files:
        # Check for peer CLAUDE.md
        claude_file = agents_file.parent / "CLAUDE.md"

        assert claude_file.exists(), (
            f"Missing CLAUDE.md peer for {agents_file.relative_to(repo_root)}"
        )

        assert claude_file.is_file(), (
            f"{claude_file.relative_to(repo_root)} exists but is not a regular file"
        )

        # Verify first line is @AGENTS.md
        content = claude_file.read_text(encoding="utf-8")
        assert content.strip().split("\n")[0].strip() == "@AGENTS.md", (
            f"{claude_file.relative_to(repo_root)} first line is "
            f"'{content.strip().split(chr(10))[0].strip()}', expected '@AGENTS.md'"
        )
