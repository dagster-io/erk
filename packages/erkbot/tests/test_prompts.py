# NOTE: @patch usage is deliberate here. erkbot is a standalone package that
# tests third-party Slack SDK wiring and does not use erk's gateway layer.
import unittest
from pathlib import Path

from erkbot.prompts import ERK_SYSTEM_PROMPT, get_erk_system_prompt


class TestErkSystemPrompt(unittest.TestCase):
    def test_erk_system_prompt_loads_from_resources(self) -> None:
        self.assertIsInstance(ERK_SYSTEM_PROMPT, str)
        self.assertGreater(len(ERK_SYSTEM_PROMPT), 100)

    def test_erk_system_prompt_mentions_key_commands(self) -> None:
        self.assertIn("plan list", ERK_SYSTEM_PROMPT)
        self.assertIn("one-shot", ERK_SYSTEM_PROMPT)
        self.assertIn("dash", ERK_SYSTEM_PROMPT)
        self.assertIn("objective view", ERK_SYSTEM_PROMPT)

    def test_get_erk_system_prompt_returns_default(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = get_erk_system_prompt(repo_root=Path(tmp_dir))
            self.assertEqual(result, ERK_SYSTEM_PROMPT)

    def test_get_erk_system_prompt_uses_custom_when_present(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            custom_dir = tmp_path / ".erk" / "prompt-hooks"
            custom_dir.mkdir(parents=True)
            custom_file = custom_dir / "erk-system-prompt.md"
            custom_file.write_text("Custom erk prompt for testing.")

            result = get_erk_system_prompt(repo_root=tmp_path)
            self.assertEqual(result, "Custom erk prompt for testing.")
