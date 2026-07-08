from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import bearer_scheme, create_access_token, decode_token
from app.modules.auth.schemas import LoginRequest, RefreshRequest, TokenResponse
from app.modules.auth.service import authenticate_user, issue_tokens
from app.schemas.common import ApiEnvelope

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=ApiEnvelope[TokenResponse])
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, body.email, body.password)
    tokens = issue_tokens(user)
    return ApiEnvelope(data=tokens)


@router.post("/auth/refresh", response_model=ApiEnvelope[dict])
async def refresh(body: RefreshRequest):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise UnauthorizedError("Refresh token required")
    new_access = create_access_token(
        {"sub": payload["sub"], "email": payload["email"], "role": payload["role"], "city_id": payload.get("city_id")}
    )
    return ApiEnvelope(data={"access_token": new_access, "token_type": "bearer"})


@router.post("/auth/logout", response_model=ApiEnvelope[dict])
async def logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    # Stateless JWT — client just discards tokens. Redis blacklist is a prod enhancement.
    return ApiEnvelope(data={"message": "Logged out"})
