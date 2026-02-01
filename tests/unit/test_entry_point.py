from unittest.mock import patch


def test_main_prints_greeting() -> None:
    """Verify main() outputs greeting before invoking CLI."""
    with patch("erk.click.echo") as mock_echo, patch("erk.cli") as _mock_cli:
        from erk import main

        main()

    mock_echo.assert_called_once_with("Hello from erk")
