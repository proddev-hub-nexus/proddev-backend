from fastapi import APIRouter, Depends, Request
from database.models.dashboard import GetUserDashboardResponse
from database.models.user import User
from services.dashboard import DashboardService
from utils.auth import get_current_user
from utils.rate_limiter import limiter

dashboard_router = APIRouter()
dashboard_service = DashboardService()

# ------------------ DASHBOARD ROUTES ------------------ #

@dashboard_router.get("/", response_model=GetUserDashboardResponse, summary="Get user dashboard")
@limiter.limit("30/minute")
async def get_user_dashboard(request: Request, current_user: User = Depends(get_current_user)):
    """
    Retrieve the dashboard data for the currently authenticated user.

    This endpoint provides a personalized view based on the user's progress,
    enrolled courses, and onboarding status.

    Returns:
        A structured dashboard response (`GetUserDashboardResponse`) containing relevant user metrics and states.

    Rate limit: 30 requests per minute.
    """
    return await dashboard_service.get_user_dashboard(str(current_user.id))
