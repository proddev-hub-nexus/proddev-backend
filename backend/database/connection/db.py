from dotenv import load_dotenv
load_dotenv()
import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from database.models.user import User 
from database.models.course import Course
from database.models.dashboard import Dashboard

MONGO_URI = os.environ["MONGO_INITDB_ROOT_URI"]


async def init_db():
    client = AsyncIOMotorClient(MONGO_URI)
    await init_beanie(database=client.proddev, document_models=[User, Course, Dashboard]) # type: ignore
    info = await client.server_info()
    print(f"✅ Connected to MongoDB {info.get('version')}")