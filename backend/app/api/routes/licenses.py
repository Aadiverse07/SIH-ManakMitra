from fastapi import APIRouter,HTTPException
from backend.app.schemas.api import License
from backend.app.services.data_service import get_license
router=APIRouter(prefix="/licenses",tags=["licenses"])
@router.get("/{number}",response_model=License)
def license(number:str):
    result=get_license(number)
    if result is None: raise HTTPException(404,f"License '{number}' not found")
    return result
