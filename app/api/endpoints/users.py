import uuid
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.database import get_db
from app.crud import user as crud_user
from app.models.user import User
from app.schemas.user import (
    UserResponse,
    UserCreate,
    UserUpdate,
    UserUpdateAdmin,
    WatchlistCreate,
    WatchlistResponse,
    WatchlistUpdate,
)

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def read_user_me(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Get profile of current logged-in user."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_user_me(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Update profile information of current logged-in user."""
    user = await crud_user.update_user(db, db_obj=current_user, obj_in=user_in)
    return user


# User Watchlist Endpoints
@router.get("/me/watchlists", response_model=List[WatchlistResponse])
async def read_watchlists(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Retrieve all watchlists for current logged-in user."""
    watchlists = await crud_user.get_user_watchlists(db, user_id=current_user.id)
    return watchlists


@router.post("/me/watchlists", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
async def create_user_watchlist(
    *,
    db: AsyncSession = Depends(get_db),
    watchlist_in: WatchlistCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Create a new watchlist for current logged-in user."""
    # Symbols should be uppercase
    watchlist_in.symbols = [s.upper() for s in watchlist_in.symbols]
    watchlist = await crud_user.create_watchlist(
        db, user_id=current_user.id, obj_in=watchlist_in
    )
    return watchlist


@router.get("/me/watchlists/{watchlist_id}", response_model=WatchlistResponse)
async def read_watchlist_detail(
    watchlist_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Retrieve details of a specific watchlist by ID."""
    watchlist = await crud_user.get_watchlist(db, watchlist_id=watchlist_id)
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found",
        )
    if watchlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )
    return watchlist


@router.put("/me/watchlists/{watchlist_id}", response_model=WatchlistResponse)
async def update_user_watchlist(
    watchlist_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    watchlist_in: WatchlistUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Update details of a specific watchlist."""
    watchlist = await crud_user.get_watchlist(db, watchlist_id=watchlist_id)
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found",
        )
    if watchlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )
    # Convert symbols to uppercase
    watchlist_in.symbols = [s.upper() for s in watchlist_in.symbols]
    updated_watchlist = await crud_user.update_watchlist(
        db, db_obj=watchlist, obj_in=watchlist_in
    )
    return updated_watchlist


@router.delete("/me/watchlists/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_user_watchlist(
    watchlist_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> None:
    """Delete a watchlist."""
    watchlist = await crud_user.get_watchlist(db, watchlist_id=watchlist_id)
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found",
        )
    if watchlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )
    await crud_user.delete_watchlist(db, db_obj=watchlist)
    return None


# =====================================================================
# ADMINISTRATIVE USER MANAGEMENT ENDPOINTS (Admin Only)
# =====================================================================

@router.get("/", response_model=List[UserResponse])
async def read_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Get list of users (Admin only)."""
    users = await crud_user.get_users(db, skip=skip, limit=limit)
    return users


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate,
    current_user: User = Depends(deps.get_current_admin_user),
) -> Any:
    """Create new user account (Admin only)."""
    user = await crud_user.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )
    new_user = await crud_user.create_user(db, obj_in=user_in)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserUpdateAdmin,
    current_user: User = Depends(deps.get_current_admin_user),
) -> Any:
    """Update a user's details (Admin only)."""
    user = await crud_user.get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    # Prevent admin from deactivating themselves
    if user.id == current_user.id:
        if user_in.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admins cannot deactivate themselves.",
            )
    updated_user = await crud_user.update_user(db, db_obj=user, obj_in=user_in)
    await db.commit()
    await db.refresh(updated_user)
    return updated_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
) -> None:
    """Delete a user (Admin only)."""
    user = await crud_user.get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot delete themselves.",
        )
    await crud_user.delete_user(db, db_obj=user)
    await db.commit()
    return None

