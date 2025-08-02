from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional

class Course(Document):
    name: str
    description: Optional[str]
    tutor: Optional[str] = "Olude"
    category: Optional[str]
    price: Optional[float] = 200000
    duration: Optional[str] = "12 weeks"
    available: bool = True
    max_students: Optional[int] = 10
    language: Optional[str] = "english"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "courses"
        indexes = [
            "category",
            "available",
            "tutor",
            "created_at",
            [("category", 1), ("available", 1)], 
        ]
