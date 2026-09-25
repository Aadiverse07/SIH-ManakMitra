from fastapi import APIRouter
from backend.app.schemas.api import Lab,CertStep
from backend.app.services.data_service import list_labs,list_cert_steps
router=APIRouter(tags=["resources"])
@router.get("/labs",response_model=list[Lab])
def labs(): return list_labs()
@router.get("/cert-steps",response_model=list[CertStep])
def cert_steps(): return list_cert_steps()
