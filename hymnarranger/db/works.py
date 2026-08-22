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
) -> GeneratedWork:
    work = GeneratedWork(
        user_id=user.id,
        title=title,
        input_params=input_params,
        musicxml_content=musicxml_content,
    )
    db.add(work)
    db.commit()
    db.refresh(work)
    return work

def list_user_works(db: Session, user: User) -> list[GeneratedWork]:
    return (
        db.query(GeneratedWork)
        .filter(GeneratedWork.user_id == user.id)
        .order_by(GeneratedWork.created_at.desc())
        .all()
    )


def get_user_work(db: Session, user: User, work_id: uuid.UUID) -> Optional[GeneratedWork]:
    return (
        db.query(GeneratedWork)
        .filter(GeneratedWork.user_id == user.id, GeneratedWork.id == work_id)
        .first()
    )

def delete_user_work(db: Session, user: User, work_id: uuid.UUID) -> bool:
    work = get_user_work(db, user, work_id)
    if work is None:
        return False
    db.delete(work)
    db.commit()
    return True