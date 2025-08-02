from fastapi import APIRouter, Response
from pydantic import BaseModel
from services.oauth import OAuthService

oauth_router = APIRouter()
oauth_service = OAuthService()

# ------------------ SCHEMAS ------------------ #

class GoogleLoginRequest(BaseModel):
    """
    Request schema for initiating Google OAuth login.
    """
    code: str
    device: str = "desktop"

# ------------------ ROUTES ------------------ #

@oauth_router.post("/google", summary="Google OAuth login")
async def google_oauth_login(data: GoogleLoginRequest, response: Response):
    """
    Authenticate a user via Google OAuth.

    Expects an OAuth authorization code from the frontend (obtained via Google login).
    On success, logs in or upgrades the user account and returns auth cookie + profile data.

    Args:
        data (GoogleLoginRequest): The OAuth authorization code and optional device info.
        response (Response): The FastAPI response object for setting auth cookies.

    Returns:
        dict: User info and login status.
    """
    return await oauth_service.login_with_google(data.code, response, device=data.device)
