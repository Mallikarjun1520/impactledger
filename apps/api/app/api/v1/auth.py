from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user

router = APIRouter()


@router.get("/auth/me")
def get_me(
    user_id: UUID = Depends(get_current_user),
) -> dict[str, str]:
    return {
        "user_id": str(user_id),
    }