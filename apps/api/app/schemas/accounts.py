from typing import Literal
from uuid import UUID

from pydantic import EmailStr, Field, SecretStr, field_validator

from .api import StrictModel


class EmailInput(StrictModel):
    email: EmailStr = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.casefold()


class RegisterInput(EmailInput):
    merchant_name: str = Field(min_length=1, max_length=120)
    password: SecretStr = Field(min_length=12, max_length=128)


class LoginInput(EmailInput):
    password: SecretStr = Field(min_length=1, max_length=128)


class TokenInput(StrictModel):
    token: str = Field(min_length=40, max_length=100)


class PasswordResetInput(TokenInput):
    password: SecretStr = Field(min_length=12, max_length=128)


class AuthOptions(StrictModel):
    registration_enabled: bool
    local_inbox_enabled: bool
    demo_enabled: bool


class DevEmailView(StrictModel):
    id: UUID
    recipient: str
    subject: str
    body: str
    status: str


class ConsentInput(TokenInput):
    decision: Literal["OPT_IN", "OPT_OUT"]
