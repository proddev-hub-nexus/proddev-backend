from beanie import Document, Link
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from database.models.user import User


class Dashboard(Document):
    owner: Link[User]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "dashboards"
        indexes = [
            "owner",
            "created_at",
        ]

class GetUserDashboardResponse(BaseModel):
    id: str
    owner: str
    created_at: datetime

class GetUserDashboardRequest(BaseModel):
    user_id: str