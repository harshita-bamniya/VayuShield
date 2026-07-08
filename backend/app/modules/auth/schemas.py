from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    city_id: str | None
    full_name: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "admin"
    city_id: str | None = None
    full_name: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str
