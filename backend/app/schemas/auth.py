from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    # pydantic models validate input payload schemas
    name: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = Field("customer", pattern="^(customer|agent|admin)$")
    org_name: str = Field(..., min_length=2)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefreshRequest(BaseModel):
    refresh_token: str