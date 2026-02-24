import re
from importlib import resources
from importlib.util import find_spec
from pathlib import Path

from erkbot.config import Settings

_QUOTE_RESOURCE_PACKAGE = "erkbot.resources"
_QUOTE_RESOURCE_NAME = "QUOTE.md"
_PR_URL_RE = re.compile(r"^PR:\s+(https://\S+)")
_RUN_URL_RE = re.compile(r"^Run:\s+(https://\S+)")


def extract_slack_message_ts(message_result: object) -> str | None:
    if message_result is None:
        return None
    if isinstance(message_result, dict):
        ts = message_result.get("ts")
        return str(ts) if ts else None

    get_method = getattr(message_result, "get", None)
    if callable(get_method):
        ts = get_method("ts")
        if ts:
            return str(ts)

    data = getattr(message_result, "data", None)
    if isinstance(data, dict):
        ts = data.get("ts")
        return str(ts) if ts else None
    return None


def extract_one_shot_links(output: str) -> tuple[str | None, str | None]:
    pr_url: str | None = None
    run_url: str | None = None
    for line in output.splitlines():
        if pr_url is None:
            pr_match = _PR_URL_RE.match(line.strip())
            if pr_match:
                pr_url = pr_match.group(1)
        if run_url is None:
            run_match = _RUN_URL_RE.match(line.strip())
            if run_match:
                run_url = run_match.group(1)
        if pr_url and run_url:
            break
    return pr_url, run_url


def tail_output_lines(output: str, *, max_lines: int) -> str:
    lines = [line for line in output.splitlines() if line.strip()]
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[-max_lines:])


def chunk_for_slack(text: str, *, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.splitlines():
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = line
            continue
        remainder = line
        while len(remainder) > max_chars:
            chunks.append(remainder[:max_chars])
            remainder = remainder[max_chars:]
        current = remainder
    if current:
        chunks.append(current)
    return chunks


def build_one_shot_progress_text(*, lines: list[str], running: bool, settings: Settings) -> str:
    state = "⏳ Running `erk one-shot`" if running else "✅ Finished `erk one-shot`."
    if not lines:
        return state
    tail = "\n".join(lines[-settings.one_shot_progress_tail_lines :])
    return f"{state}\n\n```{tail}```"


def load_quote_text() -> str:
    if find_spec(_QUOTE_RESOURCE_PACKAGE) is not None:
        resource_root = resources.files(_QUOTE_RESOURCE_PACKAGE)
        resource_quote_file = resource_root.joinpath(_QUOTE_RESOURCE_NAME)
        if resource_quote_file.is_file():
            quote = resource_quote_file.read_text(encoding="utf-8").strip()
            return quote or "QUOTE.md is empty."

    fallback_quote_file = Path(__file__).parent.joinpath("resources", _QUOTE_RESOURCE_NAME)
    if not fallback_quote_file.is_file():
        return f"{_QUOTE_RESOURCE_NAME} resource was not found."

    quote = fallback_quote_file.read_text(encoding="utf-8").strip()
    return quote or "QUOTE.md is empty."
