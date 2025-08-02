import asyncio
from database.models.course import Course
from database.connection.proddevdb import init_db  

courses_data = [
    {
        "name": "Frontend Development with React and Next.js",
        "description": "Learn how to build modern user interfaces with React and server-side rendering using Next.js.",
        "category": "Web Development",
        "tutor": "Olude",
        "price": 150000,
        "duration": "10 weeks",
        "language": "english",
    },
    {
        "name": "Backend Development with Flask",
        "description": "Master backend development with Python Flask and build RESTful APIs.",
        "category": "Backend Development",
        "price": 120000,
        "duration": "8 weeks",
    },
    {
        "name": "Backend Development with FastAPI",
        "description": "Create fast and async web backends with Python FastAPI.",
        "category": "Backend Development",
        "price": 130000,
        "duration": "8 weeks",
    },
    {
        "name": "Backend Development with Express.js",
        "description": "Build scalable REST APIs with Express.js and Node.js.",
        "category": "Backend Development",
        "price": 125000,
        "duration": "8 weeks",
    },
    {
        "name": "Fullstack Development with Flask + MySQL",
        "description": "Build fullstack applications using Flask, Jinja templates and MySQL.",
        "category": "Fullstack Development",
        "price": 180000,
        "duration": "12 weeks",
    },
    {
        "name": "Fullstack Development with MERN Stack",
        "description": "Become a fullstack developer using MongoDB, Express, React, and Node.js.",
        "category": "Fullstack Development",
        "price": 200000,
        "duration": "14 weeks",
    },
    {
        "name": "Chatbot Development with LangChain & LLMs",
        "description": "Learn to create AI-powered chatbots using LangChain and Large Language Models (LLMs).",
        "category": "Chatbot Development",
        "price": 220000,
        "duration": "10 weeks",
    },
    {
        "name": "Chatbot Development with Google Dialogflow",
        "description": "Create conversational AI experiences using Dialogflow by Google.",
        "category": "Chatbot Development",
        "price": 170000,
        "duration": "8 weeks",
    },
]

async def seed_courses():
    await init_db()  
    for course_data in courses_data:
        exists = await Course.find_one(Course.name == course_data["name"])
        if not exists:
            course = Course(**course_data)
            await course.insert()
            print(f"Inserted course: {course.name}")
        else:
            print(f"Course already exists: {course_data['name']}")

if __name__ == "__main__":
    asyncio.run(seed_courses())
