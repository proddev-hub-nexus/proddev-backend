from pydantic import BaseModel, EmailStr, Field
from beanie import Document, PydanticObjectId
from typing import Optional, List, Dict
from datetime import datetime, timezone

class User(Document):
    full_name: str
    email: EmailStr
    password: str
    is_verified: bool = False
    has_completed_onboarding: bool = False
    interested_courses: Optional[List[PydanticObjectId]] = []
    enrolled_courses: Optional[List[PydanticObjectId]] = []
    active_tokens: List[Dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        collection_name = "users"
        indexes = [
            "email",  # Redundant with `Indexed`, but good if adding compound indexes
            [("is_verified", 1)],  # Index on is_verified for fast filtering
            [("created_at", -1)],  # Descending index for recent users
        ]

class UserCreateRequest(BaseModel):
    full_name: str
    password: str
    email: EmailStr

class UserRegisterResponse(BaseModel):
    user_id: str
    created_at: datetime
class UserLoginResponse(BaseModel):
    token_id: str
    access_token: str
    token_expires_in: datetime
    device: str
  
class UserProfileResponse(BaseModel):
    user_id: str
    full_name: str
    is_verified: bool
    email: EmailStr
    created_at: datetime

class VerifyEmailResponse(UserLoginResponse):
    message: str = "Email verified successfully"