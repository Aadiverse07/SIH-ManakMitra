"""Application scheduler wiring."""
from backend.app.core.config import settings
from backend.app.scheduler.scheduler import JobScheduler
from backend.app.jobs.cache_cleanup import run as cache_cleanup
from backend.app.jobs.usage_stats import run as usage_stats
from backend.app.jobs.bis_sync import run as bis_sync
from backend.app.jobs.temporary_cleanup import run as temporary_cleanup

class SchedulerRuntime:
    def __init__(self):
        self.enabled = settings.SCHEDULER_ENABLED
        self._scheduler = JobScheduler()
        self._configured = False

    def configure(self):
        if self._configured:
            return
        if self.enabled:
            self._scheduler.add_job("cache_cleanup", settings.CACHE_CLEANUP_INTERVAL, cache_cleanup)
            self._scheduler.add_job("usage_stats", settings.USAGE_STATS_INTERVAL, usage_stats)
            self._scheduler.add_job("temporary_cleanup", settings.TEMPORARY_DATA_CLEANUP_INTERVAL, temporary_cleanup)
            self._scheduler.add_job("bis_sync", settings.BIS_SYNC_INTERVAL, bis_sync)
        self._configured = True

    async def start(self):
        self.configure()
        if self.enabled:
            # The API already requires Supabase configuration. Resolve it lazily
            # so importing the scheduler remains safe in tests.
            try:
                from backend.app.database.client import supabase
                from backend.app.jobs.usage_stats import run as persist_usage
                from backend.app.jobs.bis_sync import run as sync_bis
                self._scheduler.jobs["usage_stats"] = (
                    self._scheduler.jobs["usage_stats"][0],
                    lambda: persist_usage(supabase),
                )
                self._scheduler.jobs["bis_sync"] = (
                    self._scheduler.jobs["bis_sync"][0],
                    lambda: sync_bis(supabase),
                )
            except Exception:
                pass
            await self._scheduler.start()

    async def stop(self):
        if self.enabled:
            await self._scheduler.stop()

    def status(self):
        return self._scheduler.status()

scheduler = SchedulerRuntime()
