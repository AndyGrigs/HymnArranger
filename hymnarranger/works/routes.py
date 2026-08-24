import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from hymnarranger.auth.dependencies import get_current_user
from hymnarranger.db.models import User
from hymnarranger.db.session import get_db
from hymnarranger.db.works import get_user_work, list_user_works, rename_user_work, delete_user_work
from hymnarranger.works.schemas import WorkDetail, WorkSummary, WorkRename, WorksPage
from hymnarranger.auth.schemas import MessageResponse

router = APIRouter(prefix="/works", tags=["works"])


@router.get("", response_model=WorksPage[WorkSummary])
def get_my_works(
    search: Optional[str] = Query(None, max_length=255),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skip = (page - 1) * page_size
    items, total = list_user_works(db, current_user, search=search, skip=skip, limit=page_size)
    return WorksPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{work_id}", response_model=WorkDetail)
def get_my_work(
    work_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    work = get_user_work(db, current_user, work_id)
    if work is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Роботу не знайдено")
    return work

@router.patch("/{work_id}", response_model=WorkSummary)
def rename_my_work(
    work_id: uuid.UUID,
    body: WorkRename,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    work = rename_user_work(db, current_user, work_id, body.title)
    if work is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Роботу не знайдено")
    return work


@router.delete("/{work_id}", response_model=MessageResponse)
def delete_my_work(
    work_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = delete_user_work(db, current_user, work_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Роботу не знайдено")
    return MessageResponse(message="Роботу видалено")