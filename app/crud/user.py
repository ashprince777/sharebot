import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserWatchlist
from app.schemas.user import UserCreate, UserUpdate, WatchlistCreate, WatchlistUpdate


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Retrieve user from DB by email address."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    """Retrieve user from DB by UUID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    """Retrieve list of users from DB."""
    result = await db.execute(select(User).offset(skip).limit(limit).order_by(User.created_at.desc()))
    return list(result.scalars().all())


async def delete_user(db: AsyncSession, db_obj: User) -> bool:
    """Remove user from database."""
    await db.delete(db_obj)
    await db.flush()
    return True



async def create_user(db: AsyncSession, obj_in: UserCreate) -> User:
    """Hash password and insert new user into DB."""
    db_obj = User(
        email=obj_in.email,
        hashed_password=get_password_hash(obj_in.password),
        full_name=obj_in.full_name,
        is_active=obj_in.is_active,
        is_verified=obj_in.is_verified,
        role=obj_in.role or "user",
    )
    db.add(db_obj)
    await db.flush()
    return db_obj


async def update_user(db: AsyncSession, db_obj: User, obj_in: UserUpdate) -> User:
    """Update user properties and hash password if modified."""
    update_data = obj_in.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        hashed_password = get_password_hash(update_data["password"])
        db_obj.hashed_password = hashed_password
        del update_data["password"]

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    await db.flush()
    return db_obj


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> Optional[User]:
    """Authenticate user with email and password."""
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# Watchlist operations
async def get_user_watchlists(
    db: AsyncSession, user_id: uuid.UUID
) -> List[UserWatchlist]:
    """Retrieve all watchlists owned by user."""
    result = await db.execute(
        select(UserWatchlist).where(UserWatchlist.user_id == user_id)
    )
    return list(result.scalars().all())


async def get_watchlist(
    db: AsyncSession, watchlist_id: uuid.UUID
) -> Optional[UserWatchlist]:
    """Retrieve a single watchlist by UUID."""
    result = await db.execute(
        select(UserWatchlist).where(UserWatchlist.id == watchlist_id)
    )
    return result.scalars().first()


async def create_watchlist(
    db: AsyncSession, user_id: uuid.UUID, obj_in: WatchlistCreate
) -> UserWatchlist:
    """Create a new watchlist."""
    db_obj = UserWatchlist(
        user_id=user_id,
        name=obj_in.name,
        symbols=obj_in.symbols,
    )
    db.add(db_obj)
    await db.flush()
    return db_obj


async def update_watchlist(
    db: AsyncSession, db_obj: UserWatchlist, obj_in: WatchlistUpdate
) -> UserWatchlist:
    """Update properties of an existing watchlist."""
    db_obj.name = obj_in.name
    db_obj.symbols = obj_in.symbols
    db.add(db_obj)
    await db.flush()
    return db_obj


async def delete_watchlist(db: AsyncSession, db_obj: UserWatchlist) -> bool:
    """Remove watchlist from database."""
    await db.delete(db_obj)
    await db.flush()
    return True
