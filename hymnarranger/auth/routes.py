import os
from datetime import datetime, timedelta, timezone

from hymnarranger.auth.email import send_password_reset_email, send_verification_email

from hymnarranger.auth.schemas import (
    ForgotPasswordRequest, MessageResponse, ResetPasswordRequest, VerifyEmailRequest,
)

from hymnarranger.auth.security import generate_reset_token, hash_token
from hymnarranger.db.models import PasswordResetToken

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hymnarranger.auth.schemas import UserCreate, UserRead
from hymnarranger.auth.security import hash_password
from hymnarranger.db.models import User
from hymnarranger.db.session import get_db

from hymnarranger.auth.dependencies import get_current_user
from hymnarranger.auth.schemas import LoginRequest, Token
from hymnarranger.auth.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
RESET_TOKEN_EXPIRE_MINUTES = 30
FRONTEND_RESET_URL = os.getenv("FRONTEND_RESET_URL", "http://localhost:5173/reset-password")

VERIFICATION_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 години
FRONTEND_VERIFY_URL = os.getenv("FRONTEND_VERIFY_URL", "http://localhost:5173/verify-email")


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Користувач з такою поштою вже існує",
        )

    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
        # IntegrityError ловить рідкісну гонку (race condition), коли два запити реєструються з однаковим email одночасно — БД-рівень unique constraint це страхує.
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Користувач з такою поштою вже існує",
        )
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірна пошта або пароль",
        )
    return Token(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    generic_response = MessageResponse(
        message="Якщо ця пошта зареєстрована, на неї надіслано лист з інструкціями"
    )

    user = db.query(User).filter(User.email == payload.email).first()
    if user is None:
        return generic_response

    raw_token, token_hash_value = generate_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)

    db.add(PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash_value,
        expires_at=expires_at,
    ))
    db.commit()

    reset_link = f"{FRONTEND_RESET_URL}?token={raw_token}"
    try:
        send_password_reset_email(user.email, reset_link)
    except RuntimeError:
        pass

    return generic_response


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    invalid_error = HTTPException(
        status.HTTP_400_BAD_REQUEST, "Токен недійсний або термін його дії закінчився"
    )

    token_hash_value = hash_token(payload.token)
    reset_token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash_value)
        .first()
    )

    if reset_token is None or reset_token.used:
        raise invalid_error

    expires_at = reset_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise invalid_error

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if user is None:
        raise invalid_error

    user.hashed_password = hash_password(payload.new_password)
    reset_token.used = True
    db.commit()

    return MessageResponse(message="Пароль успішно змінено")