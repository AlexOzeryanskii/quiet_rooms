from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..deps import get_db, get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=schemas.UserProfile)
def get_me(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    current_rooms = crud.get_user_active_room_count(db, current_user)
    limit = crud.get_user_active_room_limit(db, current_user)

    return schemas.UserProfile(
        id=current_user.id,
        email=current_user.email,
        max_rooms=current_user.max_rooms,
        created_at=current_user.created_at,
        current_rooms=current_rooms,
        room_limit=limit,
    )
