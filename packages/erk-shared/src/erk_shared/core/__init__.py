"""Core ABCs for erk and erk-kits.

This module provides abstract base classes that define interfaces for erk-specific
operations. These ABCs are in erk_shared so that ErkContext can have proper type
hints without circular imports.

Real implementations remain in the erk package. Test fakes are in erk_shared.

Import from submodules:
- erk_shared.core.prompt_executor: PromptExecutor, events
- erk_shared.core.fakes: FakePromptExecutor, FakePlanListService, etc.
- erk_shared.core.plan_list_service: PlanListService, PlanListData
- erk_shared.core.script_writer: ScriptWriter, ScriptResult
"""
