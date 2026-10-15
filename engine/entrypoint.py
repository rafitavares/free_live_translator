#!/usr/bin/env python3
"""Run the shared Church Cap engine for source and packaged supervisors."""

from __future__ import annotations

import asyncio
import os
import sys
import threading
import time
from pathlib import Path

from engine.protocol import EngineCommand, EngineCommandName, EngineEvent, EngineState


LIVE_CAPTION_STATUSES = frozenset({"starting", "listening", "sensitive"})


def supervisor_process_is_alive(expected_pid: int) -> bool:
    """Probe the exact owning supervisor PID without sending it a signal."""
    if expected_pid <= 1:
        return False
    try:
        os.kill(expected_pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def monitor_supervisor_process(
    expected_pid: int,
    request_shutdown,
    force_exit=os._exit,
    sleep=time.sleep,
    poll_seconds: float = 0.5,
    force_timeout_seconds: float = 5.0,
) -> None:
    """Stop a packaged engine if its owning desktop process disappears."""
    while supervisor_process_is_alive(expected_pid):
        sleep(poll_seconds)
    try:
        request_shutdown("supervisor_process_exited")
    finally:
        sleep(force_timeout_seconds)
        # There is no owning supervisor left to enforce its normal shutdown
        # timeout. If graceful server teardown stalls, fail closed rather than
        # remaining as an invisible local service.
        force_exit(0)


def caption_state_transition(
    previous_status: str, current_status: str
) -> tuple[EngineState, str] | None:
    """Translate application caption state into the narrow desktop protocol."""
    previous_live = previous_status in LIVE_CAPTION_STATUSES
    current_live = current_status in LIVE_CAPTION_STATUSES
    if current_live and (not previous_live or current_status != previous_status):
        if current_status == "starting":
            detail = "The live caption session is starting."
        elif current_status == "sensitive":
            detail = "Live captions are active; audience output is blanked for a private moment."
        else:
            detail = "Live captions are active."
        return EngineState.CAPTIONS_LIVE, detail
    if previous_live and not current_live:
        if current_status == "error":
            detail = "The caption session stopped after an error; open Church Cap for details."
        else:
            detail = "The caption session has stopped; the browser service remains ready."
        return EngineState.CAPTIONS_IDLE, detail
    return None


async def monitor_caption_state(hub, emit, shutdown_requested: asyncio.Event) -> None:
    # Treat the monitor as initially idle so a session that begins in the
    # narrow interval between listener readiness and monitor scheduling still
    # emits its first safety boundary.
    previous_status = "stopped"
    while not shutdown_requested.is_set():
        await asyncio.sleep(0.2)
        current_status = hub.state().status
        transition = caption_state_transition(previous_status, current_status)
        if transition is not None and not shutdown_requested.is_set():
            emit(*transition)
        previous_status = current_status


def configure_runtime_environment() -> None:
    # This must happen before app.settings is imported so both listeners use
    # the existing dual-port security middleware and one shared app state.
    os.environ["DUAL_PORT_MODE"] = "true"
    if os.environ.get("CHURCH_CAP_RUNTIME_MODE", "").strip().lower() == "packaged":
        data_dir = os.environ.get("CHURCH_CAP_DATA_DIR", "").strip()
        if data_dir:
            os.environ.setdefault("HF_HOME", str(Path(data_dir) / "cache" / "huggingface"))


async def serve() -> None:
    configure_runtime_environment()

    import uvicorn

    from app.main import app, hub
    from app.runtime_config import load_runtime_config
    from app.settings import get_settings

    settings = get_settings()
    runtime = load_runtime_config()
    lock_operator = bool(runtime.get("lock_operator_to_localhost", settings.lock_operator_to_localhost))
    # The listener stays on the configured host so a separately scoped
    # service-leader session can connect; application middleware keeps the
    # full Operator dashboard localhost-only when that lock is enabled.
    operator_host = settings.host

    viewer_config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.viewer_port,
        log_level="info",
        lifespan="on",
        access_log=False,
    )
    operator_config = uvicorn.Config(
        app,
        host=operator_host,
        port=settings.operator_port,
        log_level="info",
        lifespan="off",
        access_log=False,
    )

    event_fields = {
        "app_version": settings.app_version,
        "viewer_url": f"http://127.0.0.1:{settings.viewer_port}/",
        "operator_url": f"http://127.0.0.1:{settings.operator_port}/operator",
    }

    def emit(state: EngineState, detail: str = "") -> None:
        print(EngineEvent(state=state, detail=detail, **event_fields).line(), flush=True)

    emit(
        EngineState.STARTING,
        f"operator_localhost_lock={'on' if lock_operator else 'off'}",
    )

    viewer_server = uvicorn.Server(viewer_config)
    operator_server = uvicorn.Server(operator_config)
    servers = (viewer_server, operator_server)
    loop = asyncio.get_running_loop()
    stopping_emitted = False
    shutdown_requested = asyncio.Event()
    expected_parent = os.environ.get("CHURCH_CAP_SUPERVISOR_PID", "").strip()
    expected_parent_pid: int | None = None
    if expected_parent:
        try:
            candidate_parent_pid = int(expected_parent)
        except ValueError:
            pass
        else:
            if candidate_parent_pid > 1:
                expected_parent_pid = candidate_parent_pid

    def request_shutdown(detail: str = "supervisor_command") -> None:
        nonlocal stopping_emitted
        shutdown_requested.set()
        if not stopping_emitted:
            emit(EngineState.STOPPING, detail)
            stopping_emitted = True
        for server in servers:
            server.should_exit = True

    def listen_for_supervisor_commands() -> None:
        for line in sys.stdin:
            command = EngineCommand.parse(line.strip())
            if command and command.command is EngineCommandName.SHUTDOWN:
                loop.call_soon_threadsafe(request_shutdown)
                return
        if os.environ.get("CHURCH_CAP_RUNTIME_MODE", "").strip().lower() == "packaged":
            # A closed command pipe means the owning desktop supervisor exited.
            # When the exact-PID watchdog is configured, it owns disconnect
            # recovery and its force deadline. Do not race it by separately
            # setting the shared graceful-shutdown flag from this thread.
            if expected_parent_pid is None:
                loop.call_soon_threadsafe(request_shutdown, "supervisor_disconnected")

    threading.Thread(
        target=listen_for_supervisor_commands,
        name="church-cap-supervisor-commands",
        daemon=True,
    ).start()
    if expected_parent and expected_parent_pid is None:
        request_shutdown("invalid_supervisor_process")
    elif expected_parent_pid is not None:
        threading.Thread(
            target=monitor_supervisor_process,
            args=(
                expected_parent_pid,
                lambda detail: loop.call_soon_threadsafe(request_shutdown, detail),
            ),
            name="church-cap-supervisor-parent-monitor",
            daemon=True,
        ).start()
    tasks = tuple(asyncio.create_task(server.serve()) for server in servers)
    stopped_emitted = False
    caption_monitor: asyncio.Task | None = None

    try:
        while not all(server.started for server in servers):
            failed = next((task for task in tasks if task.done()), None)
            if failed is not None:
                await failed
                raise RuntimeError("A Church Cap listener stopped before startup completed")
            await asyncio.sleep(0.05)

        emit(EngineState.READY)
        caption_monitor = asyncio.create_task(
            monitor_caption_state(hub, emit, shutdown_requested),
            name="church-cap-caption-state-monitor",
        )
        try:
            await asyncio.gather(*tasks)
        finally:
            shutdown_requested.set()
            caption_monitor.cancel()
            await asyncio.gather(caption_monitor, return_exceptions=True)
    except asyncio.CancelledError:
        if not stopping_emitted:
            emit(EngineState.STOPPING, "shutdown_requested")
            stopping_emitted = True
        for server in servers:
            server.should_exit = True
        await asyncio.gather(*tasks, return_exceptions=True)
        emit(EngineState.STOPPED)
        stopped_emitted = True
        raise
    finally:
        if not stopped_emitted and all(task.done() for task in tasks):
            emit(EngineState.STOPPED)


def main() -> int:
    resource_install = os.environ.get("CHURCH_CAP_RESOURCE_INSTALL", "").strip()
    if "--install-windows-cuda-runtime" in sys.argv[1:]:
        resource_install = "cuda"
    if resource_install:
        try:
            from app.resource_installer import (
                install_translation,
                install_tts,
                validate_packaged_installer_runtime,
            )

            if resource_install == "translation":
                install_translation(os.environ.get("CHURCH_CAP_RESOURCE_KIND", "argos"))
            elif resource_install == "tts":
                install_tts(os.environ.get("CHURCH_CAP_RESOURCE_PACKAGES", ""))
            elif resource_install == "cuda":
                from app.windows_cuda_runtime import install_windows_cuda_runtime

                install_windows_cuda_runtime()
            elif resource_install == "validate":
                validate_packaged_installer_runtime()
                print("Church Cap packaged resource installers are ready.", flush=True)
            else:
                raise ValueError("Unknown packaged resource installer mode.")
        except Exception as exc:
            print(f"Church Cap resource installation failed: {exc}", file=sys.stderr, flush=True)
            return 1
        return 0
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        # A desktop supervisor terminates the child process through the same
        # interrupt path. Treat an intentional stop as a successful exit.
        return 0
    except Exception as exc:
        print(f"Church Cap engine failed: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
