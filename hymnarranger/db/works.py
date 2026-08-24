import uuid
from typing import Optional
from sqlalchemy.orm import Session

from hymnarranger.db.models import GeneratedWork, User


def save_generated_work(
    db: Session,
    user: User,
    title: str,
    input_params: dict,
    musicxml_content: str,
    source_abc: str | None = None,
) -> GeneratedWork:
    work = GeneratedWork(
        user_id=user.id,
        title=title,
        input_params=input_params,
        musicxml_content=musicxml_content,
        source_abc=source_abc,
    )
    db.add(work)
    db.commit()
    db.refresh(work)
    return work

def list_user_works(
    db: Session,
    user: User,
    search: str | None = None,
    skip: int = 0,
    limit: int = 10,
) -> tuple[list[GeneratedWork], int]:
    q = (
        db.query(GeneratedWork)
        .filter(GeneratedWork.user_id == user.id)
    )
    if search:
        q = q.filter(GeneratedWork.title.ilike(f"%{search}%"))
    total: int = q.count()
    items = q.order_by(GeneratedWork.created_at.desc()).offset(skip).limit(limit).all()
    return items, total


def get_user_work(db: Session, user: User, work_id: uuid.UUID) -> Optional[GeneratedWork]:
    return (
        db.query(GeneratedWork)
        .filter(GeneratedWork.user_id == user.id, GeneratedWork.id == work_id)
        .first()
    )

def rename_user_work(
    db: Session, user: User, work_id: uuid.UUID, title: str
) -> Optional[GeneratedWork]:
    work = get_user_work(db, user, work_id)
    if work is None:
        return None
    work.title = title
    db.commit()
    db.refresh(work)
    return work


def delete_user_work(db: Session, user: User, work_id: uuid.UUID) -> bool:
    work = get_user_work(db, user, work_id)
    if work is None:
        return False
    db.delete(work)
    db.commit()
    return True