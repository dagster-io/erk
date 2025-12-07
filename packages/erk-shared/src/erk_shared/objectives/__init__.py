"""Objectives module for long-running goal tracking.

An objective is a declarative, state-based goal that generates plans on demand
through a "turn" mechanism. Objectives are stored as files in the repository.

Import from submodules:
- types: ObjectiveDefinition, ObjectiveNotes, NoteEntry, TurnResult, ObjectiveType
- storage: ObjectiveStore (ABC), FileObjectiveStore, FakeObjectiveStore
- parser: parse_objective_definition, parse_objective_notes
- turn: build_turn_prompt, TurnPrompt
"""
