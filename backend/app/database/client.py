from supabase import Client, create_client
from backend.app.core.config import settings, validate_required_settings

validate_required_settings()
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
