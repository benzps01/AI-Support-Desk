from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, TokenRefreshRequest
from app.core.security import hash_password, verify_password, create_jwt_token, verify_jwt_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    email_query = await db.execute(select(User).where(User.email == request.email))
    existing_user = email_query.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )

    org_query = await db.execute(select(Organization).where(Organization.name == request.org_name))
    org = org_query.scalars().first()

    if not org:
        org = Organization(name=request.org_name)
        db.add(org)
        await db.flush() # just runs to get org_id, but does now commit yet.

    hashed_pw = hash_password(request.password)
    user = User(
        org_id=org.id,
        email=request.email,
        password_hash=hashed_pw,
        role=request.role,
        name=request.name
    )

    db.add(user)
    await db.commit() # this commit both org query and user query atomically

    access_token = create_jwt_token(
        data={"sub": str(user.id), "role": user.role, "org_id": str(user.org_id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    )
    refresh_token = create_jwt_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_DAYS)
    )

    return {"access_token": access_token, "refresh_token": refresh_token}

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    query = await db.execute(select(User).where(User.email == request.email))
    user = query.scalars().first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or passsword"
        )

    access_token = create_jwt_token(
        data={"sub": str(user.id), "role": user.role, "org_id": str(user.org_id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    )
    refresh_token = create_jwt_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_DAYS)
    )

    return {"access_token": access_token, "refresh_token": refresh_token}

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = verify_jwt_token(request.refresh_token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user_id = int(payload.get("sub"))
    query = await db.execute(select(User).where(User.id == user_id))
    user = query.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    new_access_token = create_jwt_token(
        data={"sub": str(user.id), "role": user.role, "org_id": str(user.org_id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    )

    return {"access_token": new_access_token, "refresh_token": request.refresh_token}