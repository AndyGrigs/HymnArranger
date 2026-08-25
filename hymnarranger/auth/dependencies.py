import uuid
from datetime import datetime, timezone

import jwt
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from hymnarranger.auth.security import decode_access_token
from hymnarranger.db.models import User
from hymnarranger.db.session import get_db

bearer_scheme = HTTPBearer()


def _check_token_not_revoked(payload: dict, user: User) -> None:
    """Відхиляє токен виданий до останньої зміни пароля."""
    if user.password_changed_at is None:
        return
    iat = payload.get("iat")
    if iat is None:
        return
    issued_at = datetime.fromtimestamp(iat, tz=timezone.utc)
    changed_at = user.password_changed_at
    if changed_at.tzinfo is None:
        changed_at = changed_at.replace(tzinfo=timezone.utc)
    if issued_at < changed_at:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Токен анульовано — змінено пароль")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Термін дії токена закінчився")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Недійсний токен")

    user_id = payload.get("sub")
    try:
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Недійсний токен")
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Користувача не знайдено")
    _check_token_not_revoked(payload, user)
    return user

optional_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Те саме, що get_current_user, але не кидає 401 — повертає None,
    якщо токена немає або він недійсний. Для ендпоінтів, які мають
    працювати і для гостей, і для залогінених."""
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    try:
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    except (ValueError, TypeError):
        return None
    if user is None:
        return None
    try:
        _check_token_not_revoked(payload, user)
    except HTTPException:
        return None
    return user

