from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str  # plain str — .local TLD fails EmailStr; wrong email just won't match DB
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
    email: str  # plain str — .local TLD fails EmailStr validation
    password: str
    role: str = "admin"
    city_id: str | None = None
    full_name: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str
