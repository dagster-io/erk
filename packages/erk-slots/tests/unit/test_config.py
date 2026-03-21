"""Unit tests for erk_slots.config module."""

from pathlib import Path

from erk_slots.config import DEFAULT_POOL_SIZE, load_pool_config


class TestLoadPoolConfig:
    """Tests for load_pool_config function."""

    def test_returns_defaults_when_file_missing(self, tmp_path: Path) -> None:
        """Returns defaults when config.toml doesn't exist."""
        result = load_pool_config(tmp_path)

        assert result.pool_size == DEFAULT_POOL_SIZE
        assert result.pool_checkout_commands == []
        assert result.pool_checkout_shell is None

    def test_loads_pool_max_slots(self, tmp_path: Path) -> None:
        """Loads pool.max_slots from config."""
        erk_dir = tmp_path / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            "[pool]\nmax_slots = 8\n",
            encoding="utf-8",
        )

        result = load_pool_config(tmp_path)

        assert result.pool_size == 8

    def test_pool_size_defaults_when_section_absent(self, tmp_path: Path) -> None:
        """pool_size defaults to DEFAULT_POOL_SIZE when [pool] section absent."""
        erk_dir = tmp_path / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            '[env]\nFOO = "bar"\n',
            encoding="utf-8",
        )

        result = load_pool_config(tmp_path)

        assert result.pool_size == DEFAULT_POOL_SIZE

    def test_loads_pool_checkout_commands(self, tmp_path: Path) -> None:
        """Loads pool.checkout.commands from config."""
        erk_dir = tmp_path / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            '[pool.checkout]\ncommands = ["git fetch origin", "echo hello"]\n',
            encoding="utf-8",
        )

        result = load_pool_config(tmp_path)

        assert result.pool_checkout_commands == ["git fetch origin", "echo hello"]

    def test_loads_pool_checkout_shell(self, tmp_path: Path) -> None:
        """Loads pool.checkout.shell from config."""
        erk_dir = tmp_path / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            '[pool.checkout]\nshell = "zsh"\n',
            encoding="utf-8",
        )

        result = load_pool_config(tmp_path)

        assert result.pool_checkout_shell == "zsh"

    def test_pool_checkout_defaults_to_empty(self, tmp_path: Path) -> None:
        """pool_checkout_commands defaults to empty list when section absent."""
        erk_dir = tmp_path / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            '[env]\nFOO = "bar"\n',
            encoding="utf-8",
        )

        result = load_pool_config(tmp_path)

        assert result.pool_checkout_commands == []
        assert result.pool_checkout_shell is None

    def test_loads_full_pool_config(self, tmp_path: Path) -> None:
        """Loads full pool config including checkout section."""
        erk_dir = tmp_path / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            """
[pool]
max_slots = 4

[pool.checkout]
shell = "bash"
commands = ["git fetch origin", "uv sync"]
""",
            encoding="utf-8",
        )

        result = load_pool_config(tmp_path)

        assert result.pool_size == 4
        assert result.pool_checkout_shell == "bash"
        assert result.pool_checkout_commands == ["git fetch origin", "uv sync"]
