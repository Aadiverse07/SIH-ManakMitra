from fastapi import APIRouter,HTTPException
from backend.app.schemas.api import Service
from backend.app.services.data_service import list_services,get_service
router=APIRouter(prefix="/services",tags=["services"])
@router.get("",response_model=list[Service])
def services(): return list_services()
@router.get("/{service_id}",response_model=Service)
def service(service_id:str):
    result=get_service(service_id)
    if result is None: raise HTTPException(404,f"Service '{service_id}' not found")
    return result
