---
title: Agent Back Pressure via Gates
read_when:
  - "designing validation for agent-generated output"
  - "choosing between silent transformation and rejection of invalid input"
  - "implementing retry loops for agent-produced values"
  - "adding validation to agent-facing APIs"
tripwires:
  - action: "silently transforming agent output (sanitize/normalize) instead of rejecting invalid values"
    warning: "Silent transformation masks mistakes and prevents the agent from learning. Use a validation gate that rejects invalid input with actionable feedback so the agent can self-correct."
  - action: "adding a validation gate without actionable feedback in the error message"
    warning: "Gates must include the expected pattern, the actual value, and examples so the agent can self-correct. See InvalidObjectiveSlug.message for the pattern."
  - action: "adding guidance to the agent without a programmatic gate to enforce it"
    warning: "Guidance without enforcement is optional compliance. The gate is the hard boundary. The agent should have guidance to help it succeed on the first try, but the gate is what enforces correctness."
last_audited: "2026-02-22"
---

# Agent Back Pressure via Gates

## Core Concept

A **gate** is any programmatic invariant check that an agent's output must pass through. The agent has maximum flexibility in _how_ it produces its output, but the gate enforces _what_ the output must look like. If the agent's output fails the gate, the workflow loops: the agent receives the failure feedback and retries until it passes.

## The Pattern is General

A gate can be:

- A regex check on a generated slug (simple)
- A type checker run on generated code (complex)
- A test suite that must pass (sophisticated)
- A schema validator on generated JSON/YAML
- A linter enforcing style rules
- Any programmatic invariant, from trivial to arbitrarily complex

## Two Components

1. **Guidance** — Instructions to the agent describing what the gate expects (rules, patterns, examples). This is a _hint_ to help the agent succeed on the first try, but it is not the enforcement mechanism.
2. **Gate** — The programmatic check that enforces the invariant. This is the hard boundary. The agent cannot bypass it. The gate produces actionable feedback on failure so the agent can self-correct.

**Key insight:** The guidance and the gate are independent. The guidance can be imprecise or incomplete — the gate is what matters. The workflow is structured so that the agent keeps trying until the gate passes.

## Spectrum of Gate Complexity

| Gate                | Invariant              | Feedback                      |
| ------------------- | ---------------------- | ----------------------------- |
| Regex validation    | String format          | Pattern + actual value        |
| Type checker (ty)   | Type correctness       | Type errors with locations    |
| Test suite (pytest) | Behavioral correctness | Test failures with assertions |
| Linter (ruff)       | Style/convention       | Rule violations with fixes    |
| Schema validator    | Structural correctness | Missing/invalid fields        |

## When to Use Gates vs. Silent Transformation

- **Gates**: When the agent is the producer and should learn to produce correct output
- **Silent transformation**: When a human is the producer and UX matters more than compliance signals

## Anti-Patterns

- **Gates without actionable feedback**: The agent can't self-correct if the error message just says "invalid". Include the pattern, the actual value, and examples.
- **Guidance without a gate**: No enforcement means compliance is optional. The agent may drift over time.
- **Transforming agent output silently**: Masks mistakes, prevents learning. The agent never discovers that its output was wrong.

## Example: Objective Slug Validation

The objective slug migration demonstrates this pattern:

- **Before (silent transformation):** The previous implementation, `sanitize_objective_slug()` (now removed), accepted any string, lowercased it, replaced special characters, collapsed hyphens, and returned a valid slug. The agent never knew if its input was wrong.
- **After (validation gate):** `validate_objective_slug()` checks the slug against `_OBJECTIVE_SLUG_PATTERN` (defined in `naming.py`) and 3-40 character length. On failure, it returns an `InvalidObjectiveSlug` with the pattern, rules, actual value, and examples. The agent receives this feedback and retries.
- **Guidance:** The `objective-create` skill includes the exact regex pattern, length constraints, rules, and valid/invalid examples.
- **Gate:** `validate_objective_slug()` in `naming.py` enforces the invariant programmatically.
