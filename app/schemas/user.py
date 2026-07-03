import uuid
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    identifier: str  # can be email OR phone
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: Optional[str] = None

    class Config:
        from_attributes = True  # lets Pydantic read directly from SQLAlchemy objects


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"