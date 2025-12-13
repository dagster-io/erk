"""Integration tests for Temporal CLI commands.

These tests validate that the Temporal infrastructure components
(server and worker) can connect and communicate properly.

NOTE: These tests are currently skipped while we refactor the worker CLI
to not require full CompassBotServerConfig validation.
"""

import asyncio
import subprocess
import time
from pathlib import Path

import pytest
import pytest_asyncio
from temporalio.client import Client

pytestmark = pytest.mark.skip(reason="Refactoring worker config loading")


@pytest_asyncio.fixture
async def temporal_server():
    """Start a Temporal development server for testing.

    Yields when the server is ready, then tears it down after the test.
    """
    proc = subprocess.Popen(
        ["temporal", "server", "start-dev", "--port", "17233"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Wait for server to be ready by attempting to connect
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            await Client.connect("localhost:17233")
            break
        except Exception:
            if attempt == max_attempts - 1:
                proc.terminate()
                proc.wait()
                raise RuntimeError("Temporal server failed to start within timeout")
            await asyncio.sleep(1)

    yield "localhost:17233"

    # Cleanup
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture
def test_config_file(tmp_path: Path) -> Path:
    """Create a minimal test configuration file."""
    config_file = tmp_path / "test.config.yaml"
    config_file.write_text("# Minimal test config\ntest: true\n")
    return config_file


@pytest.mark.skip
@pytest.mark.asyncio
async def test_compass_temporal_worker_connects_to_temporal_server(
    temporal_server: str, test_config_file: Path
):
    """Test that compass-temporal-worker CLI can connect to temporal server.

    This is a sanity check integration test that validates:
    1. The worker CLI starts successfully
    2. Worker connects to the Temporal server
    3. Worker registers the DummyWorkflow
    4. Worker begins polling for tasks
    """
    # Start the worker process using the CLI
    worker_proc = await asyncio.create_subprocess_exec(
        "uv",
        "run",
        "compass-temporal-worker",
        "start",
        "--config",
        str(test_config_file),
        "--task-queue",
        "test-sanity-queue",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    try:
        # Wait for worker to start and log success indicators
        success_indicators = [
            "Starting Compass Temporal worker",
            "Connecting to Temporal server",
            "Worker started",
            "Polling task queue",
        ]

        found_indicators = set()
        start_time = time.time()
        timeout = 15

        while time.time() - start_time < timeout and worker_proc.stdout:
            try:
                line_bytes = await asyncio.wait_for(
                    worker_proc.stdout.readline(),
                    timeout=1.0,
                )
                if not line_bytes:
                    break

                line = line_bytes.decode().strip()
                print(line)

                for indicator in success_indicators:
                    if indicator in line:
                        found_indicators.add(indicator)

                # If we found all indicators, the worker is running successfully
                if len(found_indicators) == len(success_indicators):
                    break

            except TimeoutError:
                continue

        # Verify we found all success indicators
        assert len(found_indicators) == len(success_indicators), (
            f"Worker did not start successfully. "
            f"Found indicators: {found_indicators}, "
            f"Expected: {set(success_indicators)}"
        )

        # Additional verification: connect as a client to confirm server is accessible
        await Client.connect(temporal_server)

    finally:
        # Cleanup: terminate worker
        worker_proc.terminate()
        try:
            await asyncio.wait_for(worker_proc.wait(), timeout=5)
        except TimeoutError:
            worker_proc.kill()
            await worker_proc.wait()


@pytest.mark.skip
@pytest.mark.asyncio
async def test_worker_can_execute_dummy_workflow(temporal_server: str, test_config_file: Path):
    """Test that a workflow can be executed through the worker.

    This validates the full stack:
    1. Worker starts and connects
    2. Client can submit workflow execution
    3. Worker picks up and executes the workflow
    4. Client receives the result
    """
    # Start the worker
    worker_proc = await asyncio.create_subprocess_exec(
        "uv",
        "run",
        "compass-temporal-worker",
        "start",
        "--config",
        temporal_server,
        "--task-queue",
        "test-execution-queue",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    try:
        # Wait for worker to start (give it a few seconds)
        await asyncio.sleep(3)

        # Connect as a client and execute the DummyWorkflow
        from csbot.temporal.dummy_workflow import DummyWorkflow

        client = await Client.connect(temporal_server)

        # Execute the workflow
        result = await client.execute_workflow(
            DummyWorkflow.run,
            id=f"test-dummy-workflow-{int(time.time())}",
            task_queue="test-execution-queue",
        )

        # Verify the workflow executed successfully
        assert result == "dummy workflow completed"

    finally:
        # Cleanup
        worker_proc.terminate()
        try:
            await asyncio.wait_for(worker_proc.wait(), timeout=5)
        except TimeoutError:
            worker_proc.kill()
            await worker_proc.wait()
