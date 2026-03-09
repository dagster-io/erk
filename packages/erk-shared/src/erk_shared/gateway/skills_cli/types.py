"""Types for the Skills CLI gateway."""

from dataclasses import dataclass

from erk_shared.context.types import AgentBackend


@dataclass(frozen=True)
class SkillsCliResult:
    """Result from a skills CLI operation."""

    success: bool
    exit_code: int
    message: str


def backend_to_skills_agent(backend: AgentBackend) -> str:
    """Map erk backend name to skills CLI agent identifier.

    Args:
        backend: Erk agent backend name ("claude" or "codex").

    Returns:
        Skills CLI agent string (e.g. "claude-code", "codex").
    """
    mapping: dict[str, str] = {
        "claude": "claude-code",
        "codex": "codex",
    }
    if backend in mapping:
        return mapping[backend]
    return backend
