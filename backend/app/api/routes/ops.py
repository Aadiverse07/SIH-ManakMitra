from fastapi import APIRouter, Header, HTTPException
from backend.app.core.config import settings
from backend.app.core.usage import metrics
from backend.app.scheduler.runtime import scheduler

router = APIRouter(tags=["operations"])


def _require_ops_token(x_ops_token: str | None) -> None:
    """Keep operational telemetry out of the public surface in production."""
    expected = settings.OPS_ADMIN_TOKEN
    if settings.ENVIRONMENT.lower() == "production" and not expected:
        raise HTTPException(503, "Operations access is not configured.")
    if expected and x_ops_token != expected:
        raise HTTPException(401, "Invalid operations credentials.")
    if settings.ENVIRONMENT.lower() != "production" and not expected:
        # Development convenience: no token is required unless one is configured.
        return


@router.get("/ops/usage")
def usage(x_ops_token: str | None = Header(default=None, alias="X-Ops-Token")):
    _require_ops_token(x_ops_token)
    return metrics.snapshot()


@router.get("/ops/jobs")
def jobs(x_ops_token: str | None = Header(default=None, alias="X-Ops-Token")):
    _require_ops_token(x_ops_token)
    return {"scheduler_enabled": scheduler.enabled, "jobs": scheduler.status()}


@router.get("/ops/evaluations")
def evaluation_runs(limit: int = 20, x_ops_token: str | None = Header(default=None, alias="X-Ops-Token")):
    _require_ops_token(x_ops_token)
    from backend.evaluation.repository import list_runs
    return {"runs": list_runs(limit)}

@router.get("/ops/evaluations/{run_id}")
def evaluation_run(run_id: str, x_ops_token: str | None = Header(default=None, alias="X-Ops-Token")):
    _require_ops_token(x_ops_token)
    from backend.evaluation.repository import get_run
    result = get_run(run_id)
    if result is None:
        raise HTTPException(404, "Evaluation run not found.")
    return result
