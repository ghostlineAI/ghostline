import uuid
from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.billing_plan import BillingPlan
from app.models.user import User
from app.schemas.auth import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for handling authentication operations"""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> TokenData | None:
        """Verify and decode a JWT token"""
        try:
            # Handle edge cases
            if not token or not isinstance(token, str):
                return None
                
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            token_data = TokenData(
                user_id=user_id,
                email=payload.get("email"),
                username=payload.get("username"),
            )
            return token_data
        except JWTError:
            return None
        except Exception:
            # Catch any other exceptions (e.g., malformed tokens)
            return None

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User | None:
        """Authenticate a user by email and password"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not AuthService.verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def create_user(
        db: Session,
        email: str,
        username: str,
        password: str,
        full_name: str | None = None,
    ) -> User:
        """Create a new user with default billing plan"""
        # Get the default (Basic) billing plan
        basic_plan = db.query(BillingPlan).filter(BillingPlan.name == "basic").first()
        if not basic_plan:
            # Create basic plan if it doesn't exist
            basic_plan = BillingPlan(
                id=str(uuid.uuid4()),
                name="basic",
                display_name="Basic",
                description="Basic plan for getting started",
                monthly_token_quota=100000,
                price_cents=0,
                is_active=True,
            )
            db.add(basic_plan)
            db.commit()

        # Create the user
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            username=username,
            hashed_password=AuthService.get_password_hash(password),
            full_name=full_name,
            billing_plan_id=basic_plan.id,
            token_balance=basic_plan.monthly_token_quota,  # Start with full quota
            is_active=True,
            is_verified=False,  # Email verification can be added later
        )

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user_by_email_or_username(db: Session, identifier: str) -> User | None:
        """Get user by email or username"""
        return (
            db.query(User)
            .filter(or_(User.email == identifier, User.username == identifier))
            .first()
        )
