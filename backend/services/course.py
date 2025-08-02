from fastapi import HTTPException, status
from database.models.course import Course
from beanie import PydanticObjectId

class CourseService:
    async def get_all_courses(self):
        courses = await Course.find_all().to_list()
        return courses

    async def get_course_by_id(self, course_id: str):
        try:
            course = await Course.get(PydanticObjectId(course_id))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid course ID."
            )

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found."
            )
        return course

    async def get_courses_by_category(self, category: str):
        courses = await Course.find(Course.category == category).to_list()
        if not courses:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No courses found in category '{category}'."
            )
        return courses