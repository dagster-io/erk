"""Unit tests for land command parsing utilities."""

from erk.cli.commands.land_cmd import ParsedArgument, parse_argument


def test_parse_argument_pr_number() -> None:
    """Test parsing a plain PR number."""
    result = parse_argument("123")
    assert result == ParsedArgument(arg_type="pr-number", pr_number=123)


def test_parse_argument_pr_number_single_digit() -> None:
    """Test parsing single-digit PR number."""
    result = parse_argument("1")
    assert result == ParsedArgument(arg_type="pr-number", pr_number=1)


def test_parse_argument_pr_number_large() -> None:
    """Test parsing large PR number."""
    result = parse_argument("99999")
    assert result == ParsedArgument(arg_type="pr-number", pr_number=99999)


def test_parse_argument_pr_url_github() -> None:
    """Test parsing GitHub PR URL."""
    result = parse_argument("https://github.com/owner/repo/pull/456")
    assert result == ParsedArgument(arg_type="pr-url", pr_number=456)


def test_parse_argument_pr_url_with_trailing_content() -> None:
    """Test parsing PR URL with trailing path segments."""
    result = parse_argument("https://github.com/owner/repo/pull/789/files")
    assert result == ParsedArgument(arg_type="pr-url", pr_number=789)


def test_parse_argument_pr_url_graphite() -> None:
    """Test parsing Graphite PR URL."""
    result = parse_argument("https://app.graphite.dev/github/pr/owner/repo/321")
    assert result == ParsedArgument(arg_type="pr-url", pr_number=321)


def test_parse_argument_pr_url_graphite_with_title() -> None:
    """Test parsing Graphite PR URL with title slug."""
    result = parse_argument(
        "https://app.graphite.com/github/pr/dagster-io/erk/3718/"
        "Add-dynamic-tripwire-enforcement-system?utm_source=chrome-extension"
    )
    assert result == ParsedArgument(arg_type="pr-url", pr_number=3718)


def test_parse_argument_branch_simple() -> None:
    """Test parsing a simple branch name."""
    result = parse_argument("feature-branch")
    assert result == ParsedArgument(arg_type="branch", pr_number=None)


def test_parse_argument_branch_with_slashes() -> None:
    """Test parsing a branch name with slashes."""
    result = parse_argument("feature/add-new-thing")
    assert result == ParsedArgument(arg_type="branch", pr_number=None)


def test_parse_argument_branch_numeric_prefix() -> None:
    """Test parsing a branch name that starts with numbers but isn't purely numeric."""
    result = parse_argument("123-fix-bug")
    assert result == ParsedArgument(arg_type="branch", pr_number=None)


def test_parse_argument_branch_main() -> None:
    """Test parsing 'main' branch name."""
    result = parse_argument("main")
    assert result == ParsedArgument(arg_type="branch", pr_number=None)


def test_parse_argument_branch_master() -> None:
    """Test parsing 'master' branch name."""
    result = parse_argument("master")
    assert result == ParsedArgument(arg_type="branch", pr_number=None)
