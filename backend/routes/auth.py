from fastapi import APIRouter, Depends, Request, Response, Query
from pydantic import BaseModel
from database.models.user import User, UserCreateRequest, UserRegisterResponse, UserProfileResponse, UserLoginResponse
from services.auth import AuthService
from schemas.auth import (
    ResendVerificationRequest,  
    VerifyEmailResponse,
    LoginRequest
)
from utils.auth import get_current_user, get_device_info_from_request
from utils.rate_limiter import limiter

auth_router = APIRouter()
auth_service = AuthService()

# ------------------ AUTH ROUTES ------------------ #

# Register a new user with full name, email, and password
@auth_router.post("/register", response_model=UserRegisterResponse)
@limiter.limit("3/minute")
async def register_user(request: Request, create_user_request: UserCreateRequest):
    """
    Register a new user account.

    Rate limit: 3 requests per minute to prevent abuse.
    """
    return await auth_service.register(
        full_name=create_user_request.full_name,
        email=create_user_request.email,
        password=create_user_request.password
    )



@auth_router.get("/verify-email", response_model=VerifyEmailResponse)
@limiter.limit("10/minute")
async def verify_email_route(request: Request, response: Response, token: str = Query(...)):
    """
    Verify a user's email using the token sent via email.
    
    Rate limit: 10 requests per minute.
    """
    device_info = get_device_info_from_request(request)
    return await auth_service.verify_email(token=token, response=response, device=device_info["platform"])

# Resend email verification link
@auth_router.post("/resend-verification-mail", response_model=VerifyEmailResponse)
@limiter.limit("3/minute")
async def resend_verification_link(request: Request, response: Response, request_payload: ResendVerificationRequest):
    """
    Resend the email verification link to a user who hasn't verified yet.

    Rate limit: 3 requests per minute to prevent spamming.
    """
    device_info = get_device_info_from_request(request)

    return await auth_service.resend_verification_link(request_payload.email)

# Login a user and set HttpOnly cookie
@auth_router.post("/login", response_model=UserLoginResponse)
@limiter.limit("5/minute")
async def login_user(payload: LoginRequest, response: Response, request: Request):
    """
    Login a registered user and return profile details with secure cookie.

    Rate limit: 5 requests per minute.
    """
    device_info = get_device_info_from_request(request)
    return await auth_service.login(
        email=payload.email,
        password=payload.password,
        device=device_info["platform"]
    )

# Get the authenticated user's profile
# Updated profile endpoint with debug logging
# Updated profile endpoint with debug logging - FIXED
@auth_router.get("/profile", response_model=UserProfileResponse)
@limiter.limit("30/minute")
async def get_profile_route(request: Request, current_user: User = Depends(get_current_user)):
    """
    Retrieve the currently authenticated user's profile.

    Rate limit: 30 requests per minute.
    """
    
    # Debug logging - print what we receive
    print(f"=== PROFILE ENDPOINT DEBUG ===")
    print(f"Request URL: {request.url}")
    print(f"Request method: {request.method}")
    print(f"Request headers origin: {request.headers.get('origin')}")
    print(f"Request headers host: {request.headers.get('host')}")
    print(f"Request headers cookie: {request.headers.get('cookie')}")
    print(f"All cookies: {dict(request.cookies)}")
    
    # Fixed: Handle None case properly
    access_token = request.cookies.get('access_token')
    if access_token:
        print(f"Access token from cookies: {access_token[:20]}...")
    else:
        print(f"Access token from cookies: None")
    
    print(f"Current user: {current_user.email if current_user else 'None'}")
    print(f"============================")
    
    return await auth_service.get_profile(current_user)

# Logout the current user
@auth_router.post("/logout")
@limiter.limit("10/minute")
async def logout_user(
    request: Request,
    response: Response,
    user_data: tuple[User, str] = Depends(get_current_user)
):
    user, token_id = user_data
    return await auth_service.logout(user, token_id)

# ------------------ ONBOARDING ------------------ #

class UpdateOnboardingStatusResponse(BaseModel):
    message: str

# Mark onboarding as completed
@auth_router.patch("/onboarding-complete", response_model=UpdateOnboardingStatusResponse)
@limiter.limit("10/minute")
async def complete_onboarding_route(request: Request, current_user: User = Depends(get_current_user)):
    """
    Mark the onboarding process as completed for the current user.

    Rate limit: 10 requests per minute.
    """
    return await auth_service.mark_onboarding_complete(current_user)


