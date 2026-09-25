"""Lightweight, explicit in-process scheduler for a single API/scheduler worker.

Enable only when the deployment runs one designated scheduler process. For
multi-replica production, use the platform's cron/worker scheduler and invoke
the same job functions; this avoids duplicate BIS synchronization.
"""
from __future__ import annotations
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger(__name__)

@dataclass
class JobState:
    name: str
    interval_seconds: int
    running: bool = False
    last_started_at: float | None = None
    last_finished_at: float | None = None
    last_success: bool | None = None
    last_error: str | None = None
    runs: int = 0

class JobScheduler:
    def __init__(self):
        self.jobs: dict[str, tuple[JobState, Callable[[], object]]] = {}
        self.tasks: list[asyncio.Task] = []
        self._stopped = False

    def add_job(self, name: str, interval_seconds: int, fn: Callable[[], object]):
        self.jobs[name] = (JobState(name, interval_seconds), fn)

    async def _loop(self, state: JobState, fn):
        # Initial delay prevents startup from immediately hammering external
        # systems; operations are then repeated on the configured interval.
        while not self._stopped:
            await asyncio.sleep(state.interval_seconds)
            if self._stopped or state.running:
                continue
            state.running = True
            state.last_started_at = time.time()
            try:
                result = await asyncio.to_thread(fn)
                failed = isinstance(result, dict) and str(result.get("status", "")).upper() == "FAILED"
                if failed:
                    state.last_success = False
                    state.last_error = str(result.get("reason") or "job_failed")
                    logger.error(
                        "job=%s success=false error_category=%s",
                        state.name, state.last_error,
                    )
                else:
                    state.last_success = True
                    state.last_error = None
            except Exception as exc:
                state.last_success = False
                state.last_error = exc.__class__.__name__
                logger.exception("job=%s success=false error_category=%s", state.name, state.last_error)
            finally:
                state.runs += 1
                state.last_finished_at = time.time()
                state.running = False

    async def start(self):
        self._stopped = False
        self.tasks = [
            asyncio.create_task(self._loop(state, fn), name=f"manakai-job-{name}")
            for name, (state, fn) in self.jobs.items()
        ]

    async def stop(self):
        self._stopped = True
        for task in self.tasks:
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks = []

    def status(self):
        return {
            name: {
                "interval_seconds": state.interval_seconds,
                "running": state.running,
                "last_started_at": state.last_started_at,
                "last_finished_at": state.last_finished_at,
                "last_success": state.last_success,
                "last_error": state.last_error,
                "runs": state.runs,
            }
            for name, (state, _) in self.jobs.items()
        }
