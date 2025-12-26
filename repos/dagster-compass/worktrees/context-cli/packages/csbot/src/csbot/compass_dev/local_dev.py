"""Local development command that runs slackbot and compass-admin in parallel."""

import asyncio
import logging
import os
import shutil
import signal
import sys
from enum import Enum, auto
from pathlib import Path

import aiomonitor
import click
import structlog

logger = structlog.get_logger(__name__)


SLACKBOT_COLOR = "\033[36m"  # Cyan
ADMIN_COLOR = "\033[35m"  # Magenta
TEMPORAL_COLOR = "\033[33m"  # Yellow
TEMPORAL_SERVER_COLOR = "\033[32m"  # Green
VITE_COLOR = "\033[34m"  # Blue
ADMIN_UI_COLOR = "\033[95m"  # Bright Magenta
RESET_COLOR = "\033[0m"  # Reset to default


class Service(Enum):
    ADMIN_PANEL = auto()  # Includes admin UI Vite dev server
    SLACKBOT = auto()  # Includes main UI Vite dev server
    TEMPORAL_SERVER = auto()
    TEMPORAL_WORKER = auto()


class ServiceFailed(Exception):
    def __init__(self, service: str):
        self.service = service


class ServiceTerminatedUnexpectedly(Exception):
    def __init__(self, service: str):
        self.service = service


def _handle_process_termination(proc, service: str):
    if proc.returncode != 0:
        logger.error(f"{service} exited with error", returncode=proc.returncode)
        raise ServiceFailed(service)
    else:
        raise ServiceTerminatedUnexpectedly(service)


async def _run_slackbot_backend(config_path: str, no_reset_db: bool = False):
    """Run the slackbot backend process."""
    proc = None
    try:
        logger.info("Starting slackbot backend", config_path=config_path, no_reset_db=no_reset_db)
        args = [
            sys.executable,
            "-m",
            "csbot.cli.slackbot_cli",
            "start",
            "--config",
            config_path,
        ]
        if no_reset_db:
            args.append("--no-reset-db")

        # Set HTTP_PORT for backend to run on 3100, leaving 3000 for Vite
        env = os.environ.copy()
        env["HTTP_PORT"] = "3100"

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )

        if proc.stdout:
            async for line in proc.stdout:
                print(f"{SLACKBOT_COLOR}[slackbot-backend]{RESET_COLOR} {line.decode().rstrip()}")

        await proc.wait()

        _handle_process_termination(proc, "slackbot-backend")

    except asyncio.CancelledError:
        logger.info("Slackbot backend cancelled, terminating...")
        if proc:
            proc.terminate()
            await proc.wait()
        raise
    except Exception:
        logger.exception("Slackbot backend process failed")
        raise


async def run_slackbot(config_path: str, no_reset_db: bool = False):
    """Run slackbot service (backend + Vite dev server)."""
    try:
        # Run backend and Vite dev server concurrently
        await asyncio.gather(
            _run_slackbot_backend(config_path, no_reset_db),
            run_vite_dev_server(),
        )
    except Exception:
        logger.exception("Slackbot service failed")
        raise


async def _run_compass_admin_backend(config_path: str, host: str, backend_port: int):
    """Run the compass-admin backend process."""
    proc = None
    try:
        logger.info(
            "Starting compass-admin backend", config_path=config_path, host=host, port=backend_port
        )
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "compass_admin_panel.cli",
            "--config",
            config_path,
            "--host",
            host,
            "--port",
            str(backend_port),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        if proc.stdout:
            async for line in proc.stdout:
                print(f"{ADMIN_COLOR}[admin-backend]{RESET_COLOR} {line.decode().rstrip()}")

        await proc.wait()

        _handle_process_termination(proc, "admin-backend")

    except asyncio.CancelledError:
        logger.info("Compass-admin backend cancelled, terminating...")
        if proc:
            proc.terminate()
            await proc.wait()
        raise
    except Exception:
        logger.exception("Compass-admin backend process failed")
        raise


async def run_compass_admin(config_path: str, host: str):
    """Run compass-admin service (backend + admin UI Vite dev server)."""
    try:
        # Run backend and admin UI Vite dev server concurrently
        await asyncio.gather(
            _run_compass_admin_backend(config_path, host, 8081),
            run_admin_ui_dev_server(),
        )
    except Exception:
        logger.exception("Compass-admin service failed")
        raise


async def run_temporal_server():
    """Run the Temporal development server as a subprocess."""
    proc = None
    try:
        logger.info("Starting temporal-server")
        proc = await asyncio.create_subprocess_exec(
            "temporal",
            "server",
            "start-dev",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        if proc.stdout:
            async for line in proc.stdout:
                print(
                    f"{TEMPORAL_SERVER_COLOR}[temporal-server]{RESET_COLOR} {line.decode().rstrip()}"
                )

        await proc.wait()

        _handle_process_termination(proc, "temporal-server")

    except asyncio.CancelledError:
        logger.info("Temporal server cancelled, terminating...")
        if proc:
            proc.terminate()
            await proc.wait()
        raise
    except Exception:
        logger.exception("Temporal server process failed")
        raise


async def run_temporal_worker(config_path: str, max_concurrent_activities: int):
    """Run the compass-temporal-worker as a subprocess."""
    proc = None
    try:
        logger.info(
            "Starting compass-temporal-worker",
            config_path=config_path,
        )
        env = os.environ.copy()
        env["TEMPORAL_TASK_QUEUE"] = "compass-queue"

        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "csbot.temporal.worker_cli",
            "start",
            "--config",
            config_path,
            "--max-concurrent-activities",
            str(max_concurrent_activities),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )

        if proc.stdout:
            async for line in proc.stdout:
                print(f"{TEMPORAL_COLOR}[temporal-worker]{RESET_COLOR} {line.decode().rstrip()}")

        await proc.wait()

        _handle_process_termination(proc, "temporal-worker")

    except asyncio.CancelledError:
        if proc:
            proc.terminate()
            await proc.wait()
        raise
    except Exception:
        logger.exception("Temporal worker process failed")
        raise


async def run_vite_dev_server():
    """Run the React dev server (Vite) for the React UI."""
    proc = None
    try:
        logger.info("Starting react-dev-server")

        # Get the path to the UI package directory
        # This file is in packages/csbot/src/csbot/compass_dev/local_dev.py
        # We need to get to packages/ui
        current_file = Path(__file__)
        repo_root = current_file.parent.parent.parent.parent.parent.parent
        ui_dir = repo_root / "packages" / "ui"

        if not ui_dir.exists():
            raise RuntimeError(f"UI directory not found at {ui_dir}")

        proc = await asyncio.create_subprocess_exec(
            "yarn",
            "dev",
            cwd=str(ui_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        if proc.stdout:
            async for line in proc.stdout:
                print(f"{VITE_COLOR}[react-dev-server]{RESET_COLOR} {line.decode().rstrip()}")

        await proc.wait()

        _handle_process_termination(proc, "react-dev-server")

    except asyncio.CancelledError:
        logger.info("React dev server cancelled, terminating...")
        if proc:
            proc.terminate()
            await proc.wait()
        raise
    except Exception:
        logger.exception("React dev server process failed")
        raise


async def run_admin_ui_dev_server():
    """Run the Admin UI React dev server (Vite) for the Admin Panel UI."""
    proc = None
    try:
        logger.info("Starting admin-ui-dev-server")

        # Get the path to the admin-ui package directory
        # This file is in packages/csbot/src/csbot/compass_dev/local_dev.py
        # We need to get to packages/admin-ui
        current_file = Path(__file__)
        repo_root = current_file.parent.parent.parent.parent.parent.parent
        admin_ui_dir = repo_root / "packages" / "admin-ui"

        if not admin_ui_dir.exists():
            raise RuntimeError(f"Admin UI directory not found at {admin_ui_dir}")

        proc = await asyncio.create_subprocess_exec(
            "npm",
            "run",
            "dev",
            cwd=str(admin_ui_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        if proc.stdout:
            async for line in proc.stdout:
                print(
                    f"{ADMIN_UI_COLOR}[admin-ui-dev-server]{RESET_COLOR} {line.decode().rstrip()}"
                )

        await proc.wait()

        _handle_process_termination(proc, "admin-ui-dev-server")

    except asyncio.CancelledError:
        logger.info("Admin UI dev server cancelled, terminating...")
        if proc:
            proc.terminate()
            await proc.wait()
        raise
    except Exception:
        logger.exception("Admin UI dev server process failed")
        raise


async def wait_for_services_and_print_banner(
    host: str,
    enable_temporal: bool,
    enable_compass_bot: bool,
    enable_admin_panel: bool,
):
    """Wait for services to start and print startup banner with links.

    Shows user-facing Vite dev server URLs, not internal backend ports.
    """
    await asyncio.sleep(5)

    compass_bot_url = "http://localhost:3000"
    admin_panel_url = "http://localhost:8080"
    temporal_ui_url = "http://localhost:8233"

    print("\n" + "=" * 80)
    print("🚀 Compass Local Development Environment")
    print("=" * 80)
    print()
    if enable_compass_bot:
        print(f"  Compass Bot:        {compass_bot_url}")
    if enable_admin_panel:
        print(f"  Admin Panel:        {admin_panel_url}")
    if enable_temporal:
        print(f"  Temporal UI:        {temporal_ui_url}")
    print()
    print("=" * 80)
    print()


async def run_services(
    config_path: str,
    host: str,
    services: list[Service],
    max_concurrent_activities: int,
    no_reset_db: bool = False,
):
    """Run all services in the correct order to avoid startup issues.

    Order:
    1. Temporal server (if enabled) - needed by slackbot and temporal worker
    2. Slackbot - runs DB migrations that temporal worker also needs
    3. Admin panel and temporal worker - can start after slackbot migrations complete

    Note: Backend services run on internal ports (3100 for slackbot, 8081 for admin panel),
    while Vite dev servers expose user-facing ports (3000 for slackbot, 8080 for admin panel).
    """
    tasks = []

    # Start Temporal server first if needed (slackbot connects to it)
    if Service.TEMPORAL_SERVER in services:
        tasks.append(asyncio.create_task(run_temporal_server()))
        # Wait for Temporal server to be ready
        await asyncio.sleep(2)

    # Start slackbot next (it runs DB migrations)
    if Service.SLACKBOT in services:
        tasks.append(asyncio.create_task(run_slackbot(config_path, no_reset_db)))
        # Wait for slackbot migrations to complete before starting temporal worker
        await asyncio.sleep(2)

    # Start remaining services after slackbot has completed migrations
    if Service.ADMIN_PANEL in services:
        tasks.append(asyncio.create_task(run_compass_admin(config_path, host)))
    if Service.TEMPORAL_WORKER in services:
        tasks.append(
            asyncio.create_task(run_temporal_worker(config_path, max_concurrent_activities))
        )

    banner_task = asyncio.create_task(
        wait_for_services_and_print_banner(
            host,
            Service.TEMPORAL_SERVER in services,
            Service.SLACKBOT in services,
            Service.ADMIN_PANEL in services,
        )
    )

    async def cancel_tasks():
        for task in tasks:
            task.cancel()
        banner_task.cancel()
        await asyncio.gather(*tasks, banner_task, return_exceptions=True)

    try:
        await asyncio.gather(*tasks, banner_task)
    except ServiceTerminatedUnexpectedly as e:
        logger.error(f"Service {e.service} terminated unexpectedly, shutting down...")
    except ServiceFailed as e:
        logger.error(f"Service {e.service} failed, shutting down...")
    except asyncio.CancelledError:
        logger.info("Services cancelled, shutting down...")
    finally:
        await cancel_tasks()


@click.command()
@click.option(
    "--config",
    type=click.Path(exists=True),
    required=True,
    help="Path to the compassbot.config.yaml file",
)
@click.option(
    "--host",
    default="localhost",
    help="Host to bind the admin panel to (default: localhost)",
)
@click.option(
    "--temporal-only",
    is_flag=True,
    default=False,
    help="Only run Temporal server and worker",
)
@click.option(
    "--no-reset-db",
    is_flag=True,
    default=False,
    help="Skip resetting/re-seeding the SQLite database when running slackbot",
)
def local_dev(
    config: str,
    host: str,
    temporal_only: bool,
    no_reset_db: bool,
):
    """Run slackbot, compass-admin, and temporal server+worker for local development.

    This command starts the Slack bot, Compass Admin Panel, and Temporal
    infrastructure using the same configuration file.

    User-facing ports (via Vite dev servers with HMR):
    - Compass Bot: http://localhost:3000
    - Admin Panel: http://localhost:8080

    Backend ports (internal, proxied by Vite):
    - Compass Bot backend: http://localhost:3100
    - Admin Panel backend: http://localhost:8081
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Check if temporal CLI is installed
    if shutil.which("temporal") is None:
        click.echo("Error: 'temporal' CLI not found.", err=True)
        click.echo("Please install it with: brew install temporal", err=True)
        raise click.Abort()

    config_path = str(Path(config).absolute())

    # Build services list based on mode
    if temporal_only:
        services = [Service.TEMPORAL_SERVER, Service.TEMPORAL_WORKER]
    else:
        # SLACKBOT and ADMIN_PANEL each include their Vite dev servers
        services = [
            Service.SLACKBOT,  # Includes main UI Vite dev server on port 3000
            Service.ADMIN_PANEL,  # Includes admin UI Vite dev server on port 8080
            Service.TEMPORAL_SERVER,
            Service.TEMPORAL_WORKER,
        ]

    logger.info("Starting local development environment", config=config_path, services=services)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def signal_handler(signum, frame):
        logger.info("Received shutdown signal, stopping services...")
        for task in asyncio.all_tasks(loop):
            task.cancel()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Use default Temporal configuration
    max_concurrent_activities = 4

    try:
        with aiomonitor.start_monitor(loop):
            loop.run_until_complete(
                run_services(
                    config_path,
                    host,
                    services,
                    max_concurrent_activities,
                    no_reset_db,
                )
            )
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception:
        logger.exception("Local dev environment failed")
        raise
    finally:
        loop.close()
