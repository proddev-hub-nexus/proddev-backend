from pydantic import BaseModel, EmailStr

class VerifyEmailTokenRequest(BaseModel):
    token: str

class VerifyEmailContext(BaseModel):
    full_name: str
    verification_link: str
    subject: str


class VerifyEmailResponse(BaseModel):
    message: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str