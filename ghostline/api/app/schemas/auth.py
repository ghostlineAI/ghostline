from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    """Schema for user registration"""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: str | None = None


class UserLogin(BaseModel):
    """Schema for user login"""

    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for JWT token response"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenData(BaseModel):
    """Schema for token payload data"""

    user_id: str
    email: str | None = None
    username: str | None = None


class UserResponse(BaseModel):
    """Schema for user response"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    username: str
    full_name: str | None = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    token_balance: int
    billing_plan_id: str | None = None
