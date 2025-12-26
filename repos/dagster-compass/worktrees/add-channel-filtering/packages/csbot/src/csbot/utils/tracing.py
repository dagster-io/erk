import sys
from collections.abc import Mapping
from typing import Any

from ddtrace.trace import tracer


def _sanitize_org_for_datadog(org: str) -> str:
    return org.lower().replace(" ", "_")


def try_set_tag(k: str, v: Any):
    span = tracer.current_span()
    if span:
        span.set_tag(k, v)
        if k == "organization" and isinstance(v, str):
            span.set_tag("dd-organization", _sanitize_org_for_datadog(v))


def try_set_root_tags(tags: Mapping[str, Any]):
    if "organization" in tags:
        tags = {**tags, "dd-organization": _sanitize_org_for_datadog(tags["organization"])}
    root = tracer.current_root_span()
    if root:
        root.set_tags({**tags})


def try_set_exception():
    span = tracer.current_span()
    if not span:
        return

    info = sys.exc_info()
    if info:
        span.set_exc_info(*info)  # pyright: ignore


def try_incr_metrics(namespace: str, metrics: Mapping[str, int]):
    span = tracer.current_span()
    if not span:
        return

    existing = {k: span.get_metric(f"{namespace}.{k}") or 0 for k in metrics}
    span.set_metrics({f"{namespace}.{k}": existing[k] + v for k, v in metrics.items()})
