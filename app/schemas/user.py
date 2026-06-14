import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, ConfigDict


# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_verified: Optional[bool] = False
    role: Optional[str] = "user"


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserUpdateAdmin(UserUpdate):
    role: Optional[str] = None


class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Watchlist schemas
class WatchlistBase(BaseModel):
    name: str
    symbols: List[str]


class WatchlistCreate(WatchlistBase):
    pass


class WatchlistUpdate(WatchlistBase):
    pass


class WatchlistResponse(WatchlistBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
