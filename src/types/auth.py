from pydantic import BaseModel, Field, field_validator


class EmailPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, value: str) -> str:
        email = value.strip()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValueError("Invalid email format")
        return email.lower()


class LoginRequest(EmailPasswordRequest):
    pass


class AuthUser(BaseModel):
    id: str
    email: str | None = None
    phone: str | None = None
    app_metadata: dict | None = None
    user_metadata: dict | None = None


class AuthResponse(BaseModel):
    authenticated: bool
    user: AuthUser | None = None
    message: str | None = None


class LogoutResponse(BaseModel):
    authenticated: bool = False
    message: str = "Signed out"


class SignupRequest(EmailPasswordRequest):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)