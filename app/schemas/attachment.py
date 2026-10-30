from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    storage_key: str
    file_name: str
    mime_type: str
    size_bytes: int
    created_at: datetime

