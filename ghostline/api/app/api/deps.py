"""API Dependencies for dependency injection."""

import uuid
from collections.abc import Generator
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import SessionLocal
from app.models.user import User
from app.services.auth import AuthService

# Security scheme - auto_error=False allows us to handle missing auth gracefully
security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_dev_user(db: Session) -> User:
    """Get or create a development user for local testing."""
    DEV_USER_EMAIL = "dev@ghostline.local"
    DEV_USER_ID = "00000000-0000-0000-0000-000000000001"

    # Try to find existing dev user
    dev_user = db.query(User).filter(User.email == DEV_USER_EMAIL).first()
    
    if dev_user:
        return dev_user

    # Create dev user if it doesn't exist
    dev_user = User(
        id=DEV_USER_ID,
        email=DEV_USER_EMAIL,
        username="dev",
        hashed_password="not-used-in-dev-mode",
        full_name="Development User",
        token_balance=1000000,  # Plenty of tokens for testing
        is_active=True,
        is_verified=True,
        is_superuser=True,  # Full access in dev mode
    )
    
    try:
        db.add(dev_user)
        db.commit()
        db.refresh(dev_user)
        print("[AUTH] Created development user: dev@ghostline.local")
    except Exception as e:
        db.rollback()
        # Try to fetch again in case of race condition
        dev_user = db.query(User).filter(User.email == DEV_USER_EMAIL).first()
        if not dev_user:
            raise RuntimeError(f"Failed to create dev user: {e}")
    
    return dev_user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get current authenticated user.
    
    When AUTH_DISABLED=true, returns a development user without requiring a token.
    """
    # Auth bypass for local development
    if settings.AUTH_DISABLED:
        return get_or_create_dev_user(db)

    # Normal auth flow
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token = credentials.credentials
        
        # Handle empty or None tokens
        if not token or token == "undefined" or token == "null":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = AuthService.verify_token(token)

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User not found"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Inactive user"
            )

        return user
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
