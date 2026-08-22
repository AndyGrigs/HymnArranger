import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from hymnarranger.auth.dependencies import get_current_user
from hymnarranger.db.models import User
from hymnarranger.db.session import get_db
from hymnarranger.db.works import get_user_work, list_user_works
from hymnarranger.works.schemas import WorkDetail, WorkSummary
from hymnarranger.auth.schemas import MessageResponse
from hymnarranger.db.works import delete_user_work

router = APIRouter(prefix="/works", tags=["works"])


@router.get("", response_model=List[WorkSummary])
def get_my_works(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_user_works(db, current_user)


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