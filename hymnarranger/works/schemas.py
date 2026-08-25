import uuid
from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field, StringConstraints
from typing import Annotated

T = TypeVar("T")


class WorkRename(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class WorkSummary(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    input_params: dict
    has_source: bool

    class Config:
        from_attributes = True


class WorkDetail(WorkSummary):
    musicxml_content: str
    source_abc: Optional[str] = None


class WorksPage(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int