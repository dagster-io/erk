"""Core ABCs for erk and erk-kits.

This module provides abstract base classes that define interfaces for erk-specific
operations. These ABCs are in erk_shared so that ErkContext can have proper type
hints without circular imports.

Real implementations remain in the erk package. Test fakes are in erk_shared.
"""

from erk_shared.core.claude_executor import ClaudeEvent as ClaudeEvent
from erk_shared.core.claude_executor import ClaudeExecutor as ClaudeExecutor
from erk_shared.core.claude_executor import CommandResult as CommandResult
from erk_shared.core.claude_executor import ErrorEvent as ErrorEvent
from erk_shared.core.claude_executor import IssueNumberEvent as IssueNumberEvent
from erk_shared.core.claude_executor import NoOutputEvent as NoOutputEvent
from erk_shared.core.claude_executor import NoTurnsEvent as NoTurnsEvent
from erk_shared.core.claude_executor import PrNumberEvent as PrNumberEvent
from erk_shared.core.claude_executor import ProcessErrorEvent as ProcessErrorEvent
from erk_shared.core.claude_executor import PromptResult as PromptResult
from erk_shared.core.claude_executor import PrTitleEvent as PrTitleEvent
from erk_shared.core.claude_executor import PrUrlEvent as PrUrlEvent
from erk_shared.core.claude_executor import SpinnerUpdateEvent as SpinnerUpdateEvent
from erk_shared.core.claude_executor import TextEvent as TextEvent
from erk_shared.core.claude_executor import ToolEvent as ToolEvent
from erk_shared.core.config_store import ConfigStore as ConfigStore

# Fakes for testing and minimal contexts
from erk_shared.core.fakes import FakeClaudeExecutor as FakeClaudeExecutor
from erk_shared.core.fakes import FakeConfigStore as FakeConfigStore
from erk_shared.core.fakes import FakePlanListService as FakePlanListService
from erk_shared.core.fakes import FakePlannerRegistry as FakePlannerRegistry
from erk_shared.core.fakes import FakeScriptWriter as FakeScriptWriter
from erk_shared.core.plan_list_service import PlanListData as PlanListData
from erk_shared.core.plan_list_service import PlanListService as PlanListService
from erk_shared.core.planner_registry import PlannerRegistry as PlannerRegistry
from erk_shared.core.planner_registry import RegisteredPlanner as RegisteredPlanner
from erk_shared.core.script_writer import ScriptResult as ScriptResult
from erk_shared.core.script_writer import ScriptWriter as ScriptWriter
