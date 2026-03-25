"""Tests for erk_mcp.__main__ arg parsing and startup."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click import ClickException

from erk_mcp.__main__ import (
    _get_oauth_discovery_url,
    _get_oauth_protected_resource_url,
    _parse_args,
    main,
)


class TestParseArgs:
    """Tests for _parse_args argument parsing."""

    def test_defaults(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            args = _parse_args([])
        assert args.host == "0.0.0.0"
        assert args.port == 9000

    def test_env_var_host_override(self) -> None:
        with patch.dict("os.environ", {"ERK_MCP_HOST": "127.0.0.1"}):
            args = _parse_args([])
        assert args.host == "127.0.0.1"

    def test_env_var_port_does_not_override_default(self) -> None:
        with patch.dict("os.environ", {"ERK_MCP_PORT": "8888"}):
            args = _parse_args([])
        assert args.port == 9000

    def test_cli_host_flag(self) -> None:
        args = _parse_args(["--host", "192.168.1.1"])
        assert args.host == "192.168.1.1"

    def test_cli_port_flag(self) -> None:
        args = _parse_args(["--port", "7777"])
        assert args.port == 7777

    def test_transport_flag_is_rejected(self) -> None:
        with pytest.raises(SystemExit):
            _parse_args(["--transport", "stdio"])


class TestMain:
    """Tests for main() startup behavior."""

    def test_http_transport_runs_with_host_port(self, capsys: pytest.CaptureFixture[str]) -> None:
        mock_auth = MagicMock()
        mock_auth.base_url = "https://erk.example.com"
        mock_mcp = MagicMock()
        mock_mcp.auth = mock_auth
        with patch("erk_mcp.__main__.create_startup_mcp", return_value=mock_mcp):
            with patch("erk_mcp.__main__._parse_args") as mock_parse:
                mock_parse.return_value = MagicMock(
                    host="0.0.0.0",
                    port=9000,
                )
                main()

        mock_mcp.add_middleware.assert_not_called()
        mock_mcp.run.assert_called_once_with(
            transport="streamable-http",
            host="0.0.0.0",
            port=9000,
        )
        captured = capsys.readouterr()
        assert "http://0.0.0.0:9000/mcp" in captured.out

    def test_http_transport_prints_url(self, capsys: pytest.CaptureFixture[str]) -> None:
        mock_auth = MagicMock()
        mock_auth.base_url = "https://erk.example.com"
        mock_mcp = MagicMock()
        mock_mcp.auth = mock_auth
        with patch("erk_mcp.__main__.create_startup_mcp", return_value=mock_mcp):
            with patch("erk_mcp.__main__._parse_args") as mock_parse:
                mock_parse.return_value = MagicMock(
                    host="127.0.0.1",
                    port=8080,
                )
                main()

        captured = capsys.readouterr()
        assert "http://127.0.0.1:8080/mcp" in captured.out
        assert "https://erk.example.com/.well-known/oauth-authorization-server" in captured.out

    def test_http_transport_prints_oauth_discovery_url(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_auth = MagicMock()
        mock_auth.base_url = "https://erk.example.com"
        mock_mcp = MagicMock()
        mock_mcp.auth = mock_auth
        with patch("erk_mcp.__main__.create_startup_mcp", return_value=mock_mcp):
            with patch("erk_mcp.__main__._parse_args") as mock_parse:
                mock_parse.return_value = MagicMock(
                    host="0.0.0.0",
                    port=9000,
                )
                main()

        captured = capsys.readouterr()
        assert "https://erk.example.com/.well-known/oauth-authorization-server" in captured.out
        assert "https://erk.example.com/.well-known/oauth-protected-resource" in captured.out

    def test_http_transport_value_error_becomes_click_exception(self) -> None:
        with patch("erk_mcp.__main__.create_startup_mcp", side_effect=ValueError("broken config")):
            with patch("erk_mcp.__main__._parse_args") as mock_parse:
                mock_parse.return_value = MagicMock(
                    host="0.0.0.0",
                    port=9000,
                )
                with pytest.raises(ClickException, match="broken config"):
                    main()

    def test_http_transport_missing_oauth_becomes_click_exception(self) -> None:
        with patch(
            "erk_mcp.__main__.create_startup_mcp",
            side_effect=ValueError("Missing required environment variables"),
        ):
            with patch("erk_mcp.__main__._parse_args") as mock_parse:
                mock_parse.return_value = MagicMock(
                    host="0.0.0.0",
                    port=9000,
                )
                with pytest.raises(ClickException, match="Missing required environment variables"):
                    main()


class TestGetOAuthDiscoveryUrl:
    def test_returns_none_without_auth(self) -> None:
        mock_mcp = MagicMock()
        mock_mcp.auth = None

        assert _get_oauth_discovery_url(mock_mcp) is None

    def test_returns_url_when_auth_has_base_url(self) -> None:
        mock_auth = MagicMock()
        mock_auth.base_url = "https://erk.example.com/"
        mock_mcp = MagicMock()
        mock_mcp.auth = mock_auth

        assert (
            _get_oauth_discovery_url(mock_mcp)
            == "https://erk.example.com/.well-known/oauth-authorization-server"
        )


class TestGetOAuthProtectedResourceUrl:
    def test_returns_none_without_auth(self) -> None:
        mock_mcp = MagicMock()
        mock_mcp.auth = None

        assert _get_oauth_protected_resource_url(mock_mcp) is None

    def test_returns_url_when_auth_has_base_url(self) -> None:
        mock_auth = MagicMock()
        mock_auth.base_url = "https://erk.example.com/"
        mock_mcp = MagicMock()
        mock_mcp.auth = mock_auth

        assert (
            _get_oauth_protected_resource_url(mock_mcp)
            == "https://erk.example.com/.well-known/oauth-protected-resource"
        )
