"""Tests for erk_mcp.__main__ arg parsing and startup."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from erk_mcp.__main__ import _parse_args, _parse_int_env, main


class TestParseIntEnv:
    """Tests for _parse_int_env helper."""

    def test_returns_default_when_env_not_set(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            result = _parse_int_env("ERK_MCP_PORT_NOTSET", 9000)
        assert result == 9000

    def test_returns_int_from_env(self) -> None:
        with patch.dict("os.environ", {"ERK_MCP_PORT": "8080"}):
            result = _parse_int_env("ERK_MCP_PORT", 9000)
        assert result == 8080


class TestParseArgs:
    """Tests for _parse_args argument parsing."""

    def test_defaults(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            args = _parse_args([])
        assert args.transport == "streamable-http"
        assert args.host == "0.0.0.0"
        assert args.port == 9000

    def test_env_var_host_override(self) -> None:
        with patch.dict("os.environ", {"ERK_MCP_HOST": "127.0.0.1"}):
            args = _parse_args([])
        assert args.host == "127.0.0.1"

    def test_env_var_port_override(self) -> None:
        with patch.dict("os.environ", {"ERK_MCP_PORT": "8888"}):
            args = _parse_args([])
        assert args.port == 8888

    def test_cli_host_flag(self) -> None:
        args = _parse_args(["--host", "192.168.1.1"])
        assert args.host == "192.168.1.1"

    def test_cli_port_flag(self) -> None:
        args = _parse_args(["--port", "7777"])
        assert args.port == 7777

    def test_cli_transport_stdio(self) -> None:
        args = _parse_args(["--transport", "stdio"])
        assert args.transport == "stdio"

    def test_cli_transport_http(self) -> None:
        args = _parse_args(["--transport", "streamable-http"])
        assert args.transport == "streamable-http"

    def test_invalid_transport_raises(self) -> None:
        with pytest.raises(SystemExit):
            _parse_args(["--transport", "invalid"])


class TestMain:
    """Tests for main() startup behavior."""

    def test_http_transport_runs_with_host_port(self, capsys: pytest.CaptureFixture[str]) -> None:
        mock_mcp = MagicMock()
        with patch("erk_mcp.__main__.create_mcp", return_value=mock_mcp):
            with patch("erk_mcp.__main__._parse_args") as mock_parse:
                mock_parse.return_value = MagicMock(
                    transport="streamable-http",
                    host="0.0.0.0",
                    port=9000,
                )
                main()

        mock_mcp.run.assert_called_once_with(transport="streamable-http", host="0.0.0.0", port=9000)
        captured = capsys.readouterr()
        assert "http://0.0.0.0:9000/mcp" in captured.out

    def test_http_transport_prints_url(self, capsys: pytest.CaptureFixture[str]) -> None:
        mock_mcp = MagicMock()
        with patch("erk_mcp.__main__.create_mcp", return_value=mock_mcp):
            with patch("erk_mcp.__main__._parse_args") as mock_parse:
                mock_parse.return_value = MagicMock(
                    transport="streamable-http",
                    host="127.0.0.1",
                    port=8080,
                )
                main()

        captured = capsys.readouterr()
        assert "http://127.0.0.1:8080/mcp" in captured.out

    def test_stdio_transport_runs_without_args(self, capsys: pytest.CaptureFixture[str]) -> None:
        mock_mcp = MagicMock()
        with patch("erk_mcp.__main__.create_mcp", return_value=mock_mcp):
            with patch("erk_mcp.__main__._parse_args") as mock_parse:
                mock_parse.return_value = MagicMock(
                    transport="stdio",
                    host="0.0.0.0",
                    port=9000,
                )
                main()

        mock_mcp.run.assert_called_once_with()
        captured = capsys.readouterr()
        assert captured.out == ""
