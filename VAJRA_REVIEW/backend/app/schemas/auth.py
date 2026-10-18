from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    service_id: str
    password: str

class UserResponse(BaseModel):
    id: int
    service_id: str
    name: str
    role: str
    base_id: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
