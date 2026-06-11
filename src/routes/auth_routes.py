from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.db import get_db
from src import models, schemas
from src.utils.security import get_password_hash, verify_password, create_access_token
import logging

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@auth_router.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(user: schemas.UserRegister, db: Session = Depends(get_db)):
    # Check if username or email exists
    existing_user = (
        db.query(models.User)
        .filter(
            (models.User.username == user.username) | (models.User.email == user.email)
        )
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    # Hash password and save user
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username, email=user.email, hashed_password=hashed_password
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    logger.info(f"New user registered: {db_user.username}")
    return db_user


@auth_router.post("/login", response_model=schemas.TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    # Authenticate user
    user = (
        db.query(models.User).filter(models.User.username == form_data.username).first()
    )

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create token
    access_token = create_access_token(subject=str(user.id))

    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}
