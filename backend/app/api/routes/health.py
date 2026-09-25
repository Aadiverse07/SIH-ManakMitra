from fastapi import APIRouter
from backend.app.core.config import settings
router=APIRouter(tags=["meta"])
@router.get("/health")
def health(): return {"status":"ok","service":settings.APP_NAME}
@router.get("/")
def root(): return {"service":"manakmitra-api","status":"ok","docs":"/docs"}
