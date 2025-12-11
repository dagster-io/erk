from typing import Any

from temporalio import workflow
from temporalio.activity import _Definition
from temporalio.worker import (
    ActivityInboundInterceptor,
    ActivityOutboundInterceptor,
    ExecuteActivityInput,
    Interceptor,
    WorkflowInboundInterceptor,
    WorkflowInterceptorClassInput,
)

with workflow.unsafe.imports_passed_through():
    import structlog
    from datadog.dogstatsd import statsd  # pyright: ignore

    from csbot.utils.datadog import instrument_context

logger = structlog.getLogger(__name__)


class WorkerActivityInterceptor(ActivityInboundInterceptor):
    def __init__(self, next: ActivityInboundInterceptor) -> None:
        self.next = next

    def init(self, outbound: ActivityOutboundInterceptor) -> None:
        self.next.init(outbound)

    async def execute_activity(self, input: ExecuteActivityInput) -> Any:
        fn = input.fn
        definition = getattr(fn, "__temporal_activity_definition", None)
        if not isinstance(definition, _Definition):
            statsd.increment("compass.unexpected_activity")
            return await self.next.execute_activity(input)

        activity_name = definition.name
        try:
            with instrument_context(
                "compass.temporal.execute_activity", tags=[f"activity:{activity_name}"]
            ):
                return await self.next.execute_activity(input)
        except Exception as e:
            logger.exception(
                f"Failed executing activity {activity_name}", exception_type=e.__class__.__name__
            )
            raise


class WorkerInterceptor(Interceptor):
    def intercept_activity(self, next: ActivityInboundInterceptor) -> ActivityInboundInterceptor:
        return WorkerActivityInterceptor(next)

    def workflow_interceptor_class(
        self, input: WorkflowInterceptorClassInput
    ) -> type[WorkflowInboundInterceptor] | None:
        return None
