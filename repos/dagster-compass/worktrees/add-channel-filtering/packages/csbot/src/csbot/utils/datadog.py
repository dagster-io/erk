import os
import signal
import sys
import time
from asyncio import CancelledError
from contextlib import contextmanager
from functools import wraps
from typing import TYPE_CHECKING, Any

from datadog import initialize
from datadog.dogstatsd import statsd  # pyright: ignore
from ddtrace.trace import tracer
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_slack_response import AsyncSlackResponse

from csbot.utils.misc import detect_team_from_interactive_payload

DOGSTATSD_PORT = 8125

if TYPE_CHECKING:
    from csbot.slackbot.slack_types import SlackEvent, SlackInteractivePayload


def augment_span_from_slack_event_data(event: "SlackEvent") -> None:
    span = tracer.current_span()
    if not span:
        return

    span.set_tag("event_type", event["type"])
    span.set_tag("team_id", event.get("team_id"))
    channel_id = event.get("channel")
    if isinstance(channel_id, dict):
        channel_id = channel_id.get("id")
    span.set_tag("channel_id", channel_id)
    span.set_tag("user", event.get("user"))
    span.set_tag("thread_ts", event.get("thread_ts") or event.get("ts"))


def augment_span_from_slack_interactive_data(payload: "SlackInteractivePayload") -> None:
    span = tracer.current_span()
    if not span:
        return

    span.set_tag("event_type", "interactive")
    span.set_tag("team_id", detect_team_from_interactive_payload(payload))
    channel_id = payload.get("channel", {}).get("id")
    origin_channel_id = payload.get("container", {}).get("channel_id")
    span.set_tag("channel_id", channel_id)
    span.set_tag("origin_channel_id", origin_channel_id)
    span.set_tag("thread_ts", payload.get("thread_ts") or payload.get("ts"))


def sigusr1_handler(signum, frame):
    """Handle SIGUSR1 by printing stack traces of all threads using faulthandler."""
    import faulthandler

    print("\n" + "=" * 80, file=sys.stderr)
    print("SIGUSR1 received - dumping stack traces for all threads:", file=sys.stderr)
    print("=" * 80, file=sys.stderr)

    # faulthandler.dump_traceback() dumps all threads without blocking
    faulthandler.dump_traceback(file=sys.stderr, all_threads=True)

    print("\n" + "=" * 80, file=sys.stderr)
    print("End of stack trace dump", file=sys.stderr)
    print("=" * 80 + "\n", file=sys.stderr)


def initialize_datadog():
    # Register SIGUSR1 handler (complements dd profiling in case
    # that gets stuck)
    signal.signal(signal.SIGUSR1, sigusr1_handler)

    if not os.getenv("DD_ENV"):
        from ddtrace.trace import tracer

        tracer.enabled = False
        statsd._enabled = False  # noqa: SLF001

        return

    import ddtrace.profiling.auto  # noqa: F401 # type: ignore
    from ddtrace import config, patch
    from ddtrace.trace import Span, tracer

    # requests/aiohttp/httpx outbound request tracing
    # futures = propagate across thread pool executor submissions
    patch(requests=True, aiohttp=True, httpx=True, futures=True, anthropic=True)
    _patch_slack_client()

    # for http libraries use the domain name as the ddtrace service name,
    # showing stripe, segment etc as different services
    config.requests["split_by_domain"] = True
    config.aiohttp_client["split_by_domain"] = True
    config.httpx["split_by_domain"] = True
    config.anthropic["span_prompt_completion_sample_rate"] = 0.0

    tags = ["organization", "dd-organization"]

    def copy_tags(new_span: Span):
        git_commit = os.getenv("RENDER_GIT_COMMIT")
        if git_commit:
            new_span.set_tags({"version": git_commit})

        root_span = tracer.current_root_span()
        if root_span:
            tags_dict: dict[str | bytes, str] = {}
            for tag in tags:
                value = root_span.get_tag(tag)
                if value is not None:
                    tags_dict[tag] = value
            new_span.set_tags(tags_dict)

    tracer.on_start_span(copy_tags)

    dd_agent_host = os.getenv("DD_AGENT_HOST")
    if dd_agent_host:
        initialize(
            statsd_host=dd_agent_host,
            statsd_port=DOGSTATSD_PORT,
            statsd_disable_buffering=False,
            statsd_disable_aggregation=False,
        )
        # it is recommended that we add a shutdown hook to flush
        # the queue upon termination, but when we're running
        # in the cluster we give ourselves a termination grace
        # period anyway, and worst case we lose a small number
        # of metrics, so I think it's not that important (metrics
        # shouldn't be perfect)
        statsd.enable_background_sender()


def _patch_slack_client() -> None:
    """Patch Slack SDK client class to send metrics to Datadog.

    Wraps the api_call method to track all Slack API calls with metrics.
    """
    from slack_sdk.web.async_client import AsyncWebClient

    original_api_call = AsyncWebClient.api_call

    async def patched_api_call(
        self,
        api_method: str,
        *,
        http_verb: str = "POST",
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | Any | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        auth: dict[str, Any] | None = None,
    ) -> Any:
        start_time = time.monotonic()
        tags = [f"api_method:{api_method}"]

        try:
            response = await original_api_call(
                self,
                api_method,
                http_verb=http_verb,
                files=files,
                data=data,
                params=params,
                json=json,
                headers=headers,
                auth=auth,
            )

            # Add response status tags
            ok = response.get("ok")
            if ok is not None:
                tags.append(f"ok:{ok}")

            error = response.get("error")
            if error:
                tags.append(f"error:{error}")

            return response
        except SlackApiError as e:
            error = (
                isinstance(e.response, AsyncSlackResponse)
                and isinstance(e.response.data, dict)
                and e.response.data.get("error")
            )
            if error:
                tags.append(f"error:{error}")

            # Tag with exception type on error
            tags.append(f"exception:{e.__class__.__name__}")
            raise
        except (Exception, CancelledError) as e:
            # Tag with exception type on error
            tags.append(f"exception:{e.__class__.__name__}")
            raise
        finally:
            # Send duration histogram to Datadog
            duration_ms = (time.monotonic() - start_time) * 1000
            statsd.histogram("compass.slack.sdk.requests.duration_ms", duration_ms, tags=tags)

    AsyncWebClient.api_call = patched_api_call  # type: ignore[method-assign]


def instrument(arg, tags=None):
    if callable(arg):
        return _do_instrument(arg, f"fn.{arg.__name__}", tags=None)
    else:
        name = arg

        def decorator(f):
            return _do_instrument(f, name, tags=tags)

        return decorator


def _do_instrument(f, name: str, tags: list[str] | None = None):
    if os.getenv("DISABLE_METRICS_INSTRUMENT") == "true":
        return f

    @wraps(f)
    def wrapper(*args, **kwargs):
        start = time.monotonic()
        try:
            result = f(*args, **kwargs)
        except Exception as e:
            log_fn_error(name, start, e, tags)
            raise
        else:
            log_fn_success(name, start, tags=tags)
            return result

    return wrapper


def log_fn_error(
    name: str, start_timestamp_ms: float, error: Exception, tags: list[str] | None = None
) -> None:
    duration_ms = 1000 * (time.monotonic() - start_timestamp_ms)
    statsd.histogram(
        f"{name}.error.latency_ms",
        duration_ms,
        tags=(tags or []) + [f"error:{error.__class__.__name__}"],
    )


def log_fn_success(
    name: str,
    start_timestamp_ms: float,
    buckets_ms: list[int] | None = None,
    tags: list[str] | None = None,
) -> None:
    duration_ms = int(1000 * (time.monotonic() - start_timestamp_ms))
    instrument_histogram_with_buckets(
        f"{name}.success.latency_ms", duration_ms, buckets_ms, tags=tags
    )


def instrument_histogram_with_buckets(
    name: str, x: int, buckets_ms: list[int] | None, tags: list[str] | None = None
):
    statsd.histogram(name, x, tags=tags)
    if buckets_ms:
        for bucket in buckets_ms:
            if x >= bucket:
                statsd.increment(f"{name}.ge_{bucket}", tags=tags)
            else:
                break


@contextmanager
def instrument_context(
    metric: str, buckets_ms: list[int] | None = None, tags: list[str] | None = None
):
    """If provided, we will also instrument the number of times
    the latency is >= each bucket. buckets must be sorted (ascending).
    """
    if os.getenv("DISABLE_METRICS_INSTRUMENT") == "true":
        yield
        return

    start = time.monotonic()
    try:
        yield
    except Exception as e:
        log_fn_error(metric, start, e, tags)
        raise
    else:
        log_fn_success(metric, start, buckets_ms, tags)
