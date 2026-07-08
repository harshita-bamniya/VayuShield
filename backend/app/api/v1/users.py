from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ConflictError
from app.core.security import get_current_user, require_role
from app.modules.auth.repository import create_user, get_user_by_email, get_user_by_id
from app.modules.auth.schemas import CreateUserRequest, UserOut
from app.schemas.common import ApiEnvelope

router = APIRouter(tags=["users"])


@router.get("/users/me", response_model=ApiEnvelope[UserOut])
async def get_me(payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = await get_user_by_id(db, payload["sub"])
    return ApiEnvelope(data=UserOut.model_validate(user))


@router.post("/users", response_model=ApiEnvelope[UserOut], status_code=201)
async def create_new_user(
    body: CreateUserRequest,
    payload: dict = Depends(require_role("sysadmin")),
    db: AsyncSession = Depends(get_db),
):
    if await get_user_by_email(db, body.email):
        raise ConflictError(f"User with email {body.email} already exists")
    user = await create_user(db, body.email, body.password, body.role, body.city_id, body.full_name)
    return ApiEnvelope(data=UserOut.model_validate(user))
