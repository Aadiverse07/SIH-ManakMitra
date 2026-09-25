from typing import Optional
from fastapi import APIRouter,HTTPException,Query
from backend.app.schemas.api import AvailabilityResponse
from backend.app.services.data_service import check_availability
router=APIRouter(prefix="/auth",tags=["auth"])
@router.get("/availability",response_model=AvailabilityResponse)
def availability(email:Optional[str]=Query(None),phone:Optional[str]=Query(None)):
    if not email and not phone: raise HTTPException(400,"Provide at least one of email or phone.")
    return check_availability(email,phone)
