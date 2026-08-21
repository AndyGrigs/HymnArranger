import uuid
from datetime import datetime

from pydantic import BaseModel


class WorkSummary(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    input_params: dict

    class Config:
        from_attributes = True


class WorkDetail(WorkSummary):
    musicxml_content: str