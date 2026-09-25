"""Security helpers. Service-role credentials remain backend-only."""
def redact_error_message(message: str) -> str:
    return "Backend request failed. Check the server logs for details."
