# Split test_preprocess_session.py into subpackage

## Context

`tests/unit/cli/commands/exec/scripts/test_preprocess_session.py` is 2,182 lines — the largest test file in the codebase. It has 93 test functions organized into 15 clearly marked sections. Splitting it into a subpackage improves navigability without changing any test behavior.

This is a **pure reorg** — no logic changes, no fixes to pre-existing issues.

## Target

Replace the monolith with a subpackage directory:

```
tests/unit/cli/commands/exec/scripts/test_preprocess_session/
├── __init__.py
├── test_xml_escaping.py          (~30 lines, 4 tests)
├── test_deduplication.py         (~60 lines, 5 tests)
├── test_xml_generation.py        (~330 lines, 19 tests)
├── test_log_processing.py        (~80 lines, 6 tests)
├── test_agent_discovery.py       (~370 lines, 11 tests)
├── test_session_helpers.py       (~170 lines, 16 tests)
├── test_preprocess_workflow.py   (~480 lines, 12 tests)
└── test_splitting.py             (~480 lines, 21 tests)
```

## Section-to-file mapping

| New file | Original sections (line ranges) |
|----------|-------------------------------|
| `test_xml_escaping.py` | §1 XML Escaping (33–59) |
| `test_deduplication.py` | §2 Deduplication (61–120) |
| `test_xml_generation.py` | §3 XML Generation (122–453) |
| `test_log_processing.py` | §4 Log Processing (455–530) |
| `test_agent_discovery.py` | §5 Agent Log Discovery (532–678) + §6 Planning Agent Discovery (680–898) |
| `test_session_helpers.py` | §8 Session Analysis & Helpers (1022–1187) |
| `test_preprocess_workflow.py` | §7 Full Workflow (900–1020) + §9 Integration (1189–1348) + §10 Stdout Mode (1350–1443) + §11 Session ID (1445–1578) |
| `test_splitting.py` | §12 Token Estimation (1580–1606) + §13 Split Entries (1608–1706) + §14 Max Tokens (1708–1920) + §15 Output Dir (1922–2182) |

## Shared code

- **Imports**: Each file gets only the imports it needs from `erk.cli.commands.exec.scripts.preprocess_session`
- **`from . import fixtures`**: Used by several files — each consumer imports it directly
- **No shared helpers/constants** between sections — each section is self-contained

## Execution steps

1. Create `tests/unit/cli/commands/exec/scripts/test_preprocess_session/` directory
2. Create empty `__init__.py`
3. Create each of the 8 files, copying code verbatim from the monolith with only the needed imports
4. Delete the original `test_preprocess_session.py`
5. Run `ruff check --fix` on the new files for import sorting

## Verification

1. Count definitions before and after (expect 93 = 93)
2. Grep for dangling references to the old module name
3. Run tests: `pytest tests/unit/cli/commands/exec/scripts/test_preprocess_session/ -x`
4. Run linter + type checker on the new files
