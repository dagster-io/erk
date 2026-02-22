# Phase 1: Tripwire Candidates Validation Gate

**Objective**: [#7823](https://github.com/anthropics/erk/issues/7823) — Nodes 1.1, 1.2, 1.3

## Context

The tripwire candidates pipeline (agent produces JSON -> normalize -> validate -> store) uses exception-based validation (`ValueError`). This violates erk's LBYL pattern and provides poor feedback to agents. This phase applies the discriminated union back-pressure pattern — modeled after `ValidObjectiveSlug | InvalidObjectiveSlug` in `naming.py` — to tripwire candidate validation.

## Step 1: Add discriminated union types + update validation (Node 1.1)

**File**: `packages/erk-shared/src/erk_shared/gateway/github/metadata/tripwire_candidates.py`

Add two frozen dataclasses after `TripwireCandidate` (line 35):

```python
@dataclass(frozen=True)
class ValidTripwireCandidates:
    candidates: list[TripwireCandidate]

@dataclass(frozen=True)
class InvalidTripwireCandidates:
    raw_data: dict | list | str | int | float | None
    reason: str

    @property
    def error_type(self) -> str:
        return "invalid-tripwire-candidates"

    @property
    def message(self) -> str:
        # Actionable agent feedback: reason, expected schema, rules, valid/invalid examples
        # Follow InvalidObjectiveSlug.message pattern (naming.py:96-113)
```

The `.message` property must include:
- The specific reason this input failed
- The expected schema (`{"candidates": [{"action": str, "warning": str, "target_doc_path": str}]}`)
- Rules enforced (root must be object, `candidates` key required, must be list, each entry needs 3 string fields)
- A valid example and an invalid example

**Update `validate_candidates_data()`** (lines 116-159): Change return type from `list[TripwireCandidate]` to `ValidTripwireCandidates | InvalidTripwireCandidates`. Replace each `raise ValueError(...)` with `return InvalidTripwireCandidates(raw_data=data, reason=...)`. Success path returns `ValidTripwireCandidates(candidates=results)`.

**Update `validate_candidates_json()`** (lines 162-187): Same union return type. Convert the `FileNotFoundError` (line 182) to `return InvalidTripwireCandidates(raw_data=None, reason=...)`. Wrap `json.loads` in a try/except at the I/O boundary and convert `json.JSONDecodeError` to `InvalidTripwireCandidates(raw_data=raw, reason=...)`.

## Step 2: Wire validation into normalize and store (Node 1.2)

### normalize_tripwire_candidates.py

**File**: `src/erk/cli/commands/exec/scripts/normalize_tripwire_candidates.py`

**Pre-normalization structural gate** — add above the Click command:

```python
@dataclass(frozen=True)
class UnsalvageableInput:
    reason: str

def check_salvageable(data: object) -> UnsalvageableInput | None:
    """Reject inputs too structurally broken for normalization."""
    # 1. not isinstance(data, dict) -> reject
    # 2. no candidates-like key (neither "candidates" nor any ROOT_KEY_ALIASES) -> reject
    # 3. candidates-like value is not a list -> reject
    # Returns None if salvageable
```

**Wire into the Click command** (lines 109-146):
1. Replace the `isinstance(data, dict)` check (lines 132-137) with `check_salvageable(data)` — if `UnsalvageableInput`, exit 1 with reason
2. After `normalize_candidates_data()` (line 139), add post-normalization gate: call `validate_candidates_data()` on the normalized data. If `InvalidTripwireCandidates`, exit 1 with `.message`
3. Only write the file and report success if validation passes

New imports: `InvalidTripwireCandidates`, `validate_candidates_data` from `erk_shared.gateway.github.metadata.tripwire_candidates`

### store_tripwire_candidates.py

**File**: `src/erk/cli/commands/exec/scripts/store_tripwire_candidates.py`

Replace the broad try/except block (lines 61-74) with LBYL:
- Keep file existence check (`if not path.is_file()`) — exit 1 with `StoreError`
- Keep `json.loads` try/except (I/O boundary) — exit 1 with `StoreError` on `json.JSONDecodeError`
- Keep `isinstance(data, dict)` check — exit 1 with `StoreError`
- Replace `validate_candidates_data()` call: use `isinstance(result, InvalidTripwireCandidates)` check instead of catching `ValueError`. Access validated candidates via `result.candidates`

New import: `InvalidTripwireCandidates` from `erk_shared.gateway.github.metadata.tripwire_candidates`

## Step 3: Update agent guidance (Node 1.3)

**File**: `.claude/agents/learn/tripwire-extractor.md`

Add a `### Schema Rules (Enforced by Validation Gate)` section after Step 4 (line 63):
- Exact required JSON schema with field descriptions
- Rules enforced by the gate (root must be object, `candidates` key, list of objects, three required string fields)
- Field naming table: correct names vs common drift names that get normalized (`description` -> `warning`, `title`/`name` -> `action`)
- Valid example JSON
- Invalid examples with explanations of what fails

Update Quality Criteria (lines 80-85):
- `action` must start with a gerund or "Before"
- `warning` must be imperative
- `target_doc_path` must be relative within `docs/learned/`

## Step 4: Update tests

### test_tripwire_candidates_metadata.py

**File**: `tests/shared/github/test_tripwire_candidates_metadata.py`

Update 6 existing tests to use discriminated union assertions:

| Test (line) | Current assertion | New assertion |
|---|---|---|
| `test_validate_candidates_data_with_dict` (161) | `results = validate_candidates_data(data)` | `assert isinstance(result, ValidTripwireCandidates)`, use `result.candidates` |
| `test_validate_candidates_json` (110) | `results = validate_candidates_json(...)` | Same pattern |
| `test_validate_candidates_json_missing_file` (125) | `pytest.raises(FileNotFoundError)` | `assert isinstance(result, InvalidTripwireCandidates)` |
| `test_validate_candidates_json_invalid_structure` (131) | `pytest.raises(ValueError)` | `assert isinstance(result, InvalidTripwireCandidates)` |
| `test_validate_candidates_json_not_object` (143) | `pytest.raises(ValueError)` | `assert isinstance(result, InvalidTripwireCandidates)` |
| `test_validate_candidates_json_empty_candidates` (152) | `results = validate_candidates_json(...)` | `assert isinstance(result, ValidTripwireCandidates)`, `result.candidates == []` |

Add 2 new tests:
- `test_invalid_tripwire_candidates_message_includes_schema`: verify `.message` includes schema, rules, examples
- `test_invalid_tripwire_candidates_error_type`: verify `.error_type == "invalid-tripwire-candidates"`

### test_normalize_tripwire_candidates.py

**File**: `tests/unit/cli/commands/exec/scripts/test_normalize_tripwire_candidates.py`

Add 4 new tests:
- `test_unsalvageable_array_root`: JSON array input -> exit 1
- `test_unsalvageable_no_candidates_key`: `{"data": [...]}` -> exit 1
- `test_unsalvageable_candidates_not_list`: `{"candidates": "string"}` -> exit 1
- `test_post_normalization_validation_rejects_missing_fields`: normalizable root key but still-invalid candidates after normalization -> exit 1

### test_store_tripwire_candidates.py

Existing tests (5 passing + 3 normalization) should pass as-is — they check exit codes, not error message format.

## Files Modified

| File | Change |
|---|---|
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/tripwire_candidates.py` | Add `ValidTripwireCandidates`, `InvalidTripwireCandidates`; update `validate_candidates_data` and `validate_candidates_json` |
| `src/erk/cli/commands/exec/scripts/normalize_tripwire_candidates.py` | Add `check_salvageable()`, pre/post-normalization gates |
| `src/erk/cli/commands/exec/scripts/store_tripwire_candidates.py` | Replace try/except with isinstance check |
| `.claude/agents/learn/tripwire-extractor.md` | Add schema rules section |
| `tests/shared/github/test_tripwire_candidates_metadata.py` | Update 6 tests, add 2 new |
| `tests/unit/cli/commands/exec/scripts/test_normalize_tripwire_candidates.py` | Add 4 new tests |

## Verification

1. `pytest tests/shared/github/test_tripwire_candidates_metadata.py`
2. `pytest tests/unit/cli/commands/exec/scripts/test_normalize_tripwire_candidates.py`
3. `pytest tests/unit/cli/commands/exec/scripts/test_store_tripwire_candidates.py`
4. `ty` on modified files
5. `ruff` on modified files
