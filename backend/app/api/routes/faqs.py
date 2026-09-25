from fastapi import APIRouter
from backend.app.schemas.api import Faq
from backend.app.services.data_service import list_faqs
router=APIRouter(prefix="/faqs",tags=["faqs"])
@router.get("",response_model=list[Faq])
def faqs(): return list_faqs()
