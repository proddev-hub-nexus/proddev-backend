from fastapi import APIRouter, Request
from services.course import CourseService
from utils.rate_limiter import limiter

course_router = APIRouter()
course_service = CourseService()

# ------------------ COURSE ROUTES ------------------ #

@course_router.get("/", summary="Fetch all courses")
@limiter.limit("30/minute")
async def get_all_courses(request: Request):
    """
    Retrieve a list of all available courses.

    Useful for general course browsing.

    Rate limit: 30 requests per minute.
    """
    return await course_service.get_all_courses()

@course_router.get("/category/{category}", summary="Get courses by category")
@limiter.limit("30/minute")
async def get_courses_by_category(category: str, request: Request):
    """
    Retrieve all courses filtered by a specific category.

    Args:
        category (str): The category to filter courses by.

    Returns:
        List of courses within the specified category.

    Rate limit: 30 requests per minute.
    """
    return await course_service.get_courses_by_category(category)

@course_router.get("/{course_id}", summary="Get a course by ID")
@limiter.limit("30/minute")
async def get_course_by_id(course_id: str, request: Request):
    """
    Retrieve a single course using its unique ID.

    Args:
        course_id (str): The unique identifier of the course.

    Returns:
        Course details if found, otherwise raises 404 error.

    Rate limit: 30 requests per minute.
    """
    return await course_service.get_course_by_id(course_id)
