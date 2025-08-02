from fastapi import APIRouter, Depends, Request, Response, Query
from pydantic import BaseModel
from database.models.user import User, UserCreateRequest, UserResponse
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
@auth_router.post("/register", response_model=UserResponse)
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
async def verify_email_route(request: Request, token: str = Query(...)):
    """
    Verify a user's email using the token sent via email.
    
    Rate limit: 10 requests per minute.
    """
    return await auth_service.verify_email(token=token)

# Resend email verification link
@auth_router.post("/resend-verification-mail", response_model=VerifyEmailResponse)
@limiter.limit("3/minute")
async def resend_verification_link(request: Request, request_payload: ResendVerificationRequest):
    """
    Resend the email verification link to a user who hasn't verified yet.

    Rate limit: 3 requests per minute to prevent spamming.
    """
    return await auth_service.resend_verification_link(request_payload.email)

# Login a user and set HttpOnly cookie
@auth_router.post("/login", response_model=UserResponse)
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
        response=response,
        device=device_info["platform"]
    )

# Get the authenticated user's profile
@auth_router.get("/profile", response_model=UserResponse)
@limiter.limit("30/minute")
async def get_profile_route(request: Request, current_user: User = Depends(get_current_user)):
    """
    Retrieve the currently authenticated user's profile.

    Rate limit: 30 requests per minute.
    """
    return await auth_service.get_profile(current_user)

# Logout the current user
@auth_router.post("/logout")
@limiter.limit("10/minute")
async def logout_user(request: Request, response: Response, user: User = Depends(get_current_user)):
    """
    Log the user out by clearing their authentication cookie and active token.

    Rate limit: 10 requests per minute.
    """
    return await auth_service.logout(user, response)

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
