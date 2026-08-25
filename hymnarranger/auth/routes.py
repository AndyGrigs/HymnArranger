import os
from datetime import datetime, timedelta, timezone

from hymnarranger.auth.email import (
    send_already_registered_email, send_password_reset_email, send_verification_email,
)

from hymnarranger.auth.schemas import (
    ForgotPasswordRequest, MessageResponse, ResetPasswordRequest, VerifyEmailRequest,
)

from hymnarranger.auth.security import generate_reset_token, hash_token
from hymnarranger.db.models import EmailVerificationToken, PasswordResetToken

from fastapi import APIRouter, Depends, HTTPException, Request, status

from hymnarranger.auth.limiter import limiter
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hymnarranger.auth.schemas import UserCreate, UserRead
from hymnarranger.auth.security import hash_password
from hymnarranger.db.models import User
from hymnarranger.db.session import get_db

from hymnarranger.auth.dependencies import get_current_user
from hymnarranger.auth.schemas import LoginRequest, Token
from hymnarranger.auth.security import _DUMMY_HASH, create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
RESET_TOKEN_EXPIRE_MINUTES = 30
FRONTEND_RESET_URL = os.getenv("FRONTEND_RESET_URL", "http://localhost:5173/reset-password")

VERIFICATION_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 години
FRONTEND_VERIFY_URL = os.getenv("FRONTEND_VERIFY_URL", "http://localhost:5173/verify-email")
FRONTEND_LOGIN_URL = os.getenv("FRONTEND_LOGIN_URL", "http://localhost:5173/login")


_REGISTER_RESPONSE = MessageResponse(message="Якщо ця адреса нова — на неї надіслано лист для підтвердження")


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
def register(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        try:
            send_already_registered_email(existing.email, FRONTEND_LOGIN_URL)
        except RuntimeError:
            pass
        return _REGISTER_RESPONSE

    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Гонка: інший запит зареєстрував цей email між перевіркою і commit.
        db.rollback()
        return _REGISTER_RESPONSE
    db.refresh(user)

    raw_token, token_hash_value = generate_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_TOKEN_EXPIRE_MINUTES)
    db.add(EmailVerificationToken(
        user_id=user.id,
        token_hash=token_hash_value,
        expires_at=expires_at,
    ))
    db.commit()

    verify_link = f"{FRONTEND_VERIFY_URL}?token={raw_token}"
    try:
        send_verification_email(user.email, verify_link)
    except RuntimeError:
        pass

    return _REGISTER_RESPONSE

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    hashed = user.hashed_password if user is not None else _DUMMY_HASH
    password_ok = verify_password(payload.password, hashed)
    if not password_ok or user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірна пошта або пароль",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Обліковий запис заблоковано",
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Підтвердьте пошту перед входом",
        )
    return Token(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/hour")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    generic_response = MessageResponse(
        message="Якщо ця пошта зареєстрована, на неї надіслано лист з інструкціями"
    )

    user = db.query(User).filter(User.email == payload.email).first()
    if user is None:
        return generic_response

    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False,
    ).update({"used": True})

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
    user.password_changed_at = datetime.now(timezone.utc)
    reset_token.used = True
    db.commit()

    return MessageResponse(message="Пароль успішно змінено")


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    invalid_error = HTTPException(
        status.HTTP_400_BAD_REQUEST, "Токен недійсний або термін його дії закінчився"
    )

    token_hash_value = hash_token(payload.token)
    verification_token = (
        db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.token_hash == token_hash_value)
        .first()
    )

    if verification_token is None or verification_token.used:
        raise invalid_error

    expires_at = verification_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise invalid_error

    user = db.query(User).filter(User.id == verification_token.user_id).first()
    if user is None:
        raise invalid_error

    user.is_verified = True
    verification_token.used = True
    db.commit()

    return MessageResponse(message="Пошту підтверджено")


@router.post("/resend-verification", response_model=MessageResponse)
@limiter.limit("3/hour")
def resend_verification(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    generic_response = MessageResponse(
        message="Якщо ця пошта зареєстрована і не підтверджена, на неї надіслано лист"
    )

    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or user.is_verified:
        return generic_response

    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.used == False,
    ).update({"used": True})

    raw_token, token_hash_value = generate_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_TOKEN_EXPIRE_MINUTES)
    db.add(EmailVerificationToken(
        user_id=user.id,
        token_hash=token_hash_value,
        expires_at=expires_at,
    ))
    db.commit()

    verify_link = f"{FRONTEND_VERIFY_URL}?token={raw_token}"
    try:
        send_verification_email(user.email, verify_link)
    except RuntimeError:
        pass

    return generic_response