"""Document byte storage. Local filesystem is the safe default; a future
Supabase Storage adapter can be enabled without changing ingestion contracts."""
from pathlib import Path
import re
from backend.app.core.config import settings

class DocumentStorage:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.DOCUMENT_STORAGE_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, owner_user_id: str, document_id: str, filename: str, content: bytes) -> str:
        safe_owner = re.sub(r"[^a-zA-Z0-9_-]", "_", owner_user_id)
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", document_id)
        safe_name = Path(filename).name
        directory = self.root / safe_owner / safe_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / safe_name
        path.write_bytes(content)
        return str(path)

    def read(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()

    def delete(self, storage_path: str):
        try: Path(storage_path).unlink(missing_ok=True)
        except Exception: pass
