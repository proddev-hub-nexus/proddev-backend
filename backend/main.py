from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from typing import cast
from starlette.types import ExceptionHandler
from utils.rate_limiter import limiter
from contextlib import asynccontextmanager
from database.connection.db import init_db
from routes.auth import auth_router
from routes.dashboard import dashboard_router
from routes.course import course_router
from routes.oauth import oauth_router
from fastapi.middleware.cors import CORSMiddleware
#from utils.seed_courses import seed_courses

origins = [
    "http://localhost:3000",
    "https://proddev-frontend.vercel.app",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    #await seed_courses()  # ✅ auto-run seed script
    yield

# Initialize FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Set up rate limiting
app.state.limiter = limiter

# Add exception handler and middleware
app.add_exception_handler(
    RateLimitExceeded,
    cast(ExceptionHandler, _rate_limit_exceeded_handler)
)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Hello": "World"}

# Include your routers
app.include_router(auth_router, prefix="/auth", tags=["Users"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(course_router, prefix="/courses", tags=["Courses"])
app.include_router(oauth_router, prefix="/oauth", tags=["OAuth"])