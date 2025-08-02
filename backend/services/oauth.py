import os
import logging
import requests
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status, Response
from database.models.user import User, UserResponse
from utils.auth import generate_access_token, set_access_token_cookie

class OAuthService:
    async def login_with_google(self, auth_code: str, response: Response, device: str = "desktop") -> UserResponse:
        # Step 1: Exchange code for access token
        token_data = {
            'code': auth_code,
            'client_id': os.environ['GOOGLE_CLIENT_ID'],
            'client_secret': os.environ['GOOGLE_SECRET_KEY'],
            'redirect_uri': 'postmessage',
            'grant_type': 'authorization_code'
        }

        token_response = requests.post("https://oauth2.googleapis.com/token", data=token_data)
        if not token_response.ok:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to obtain access token from Google."
            )

        access_token = token_response.json().get("access_token")
        if not access_token:
            raise HTTPException(status_code=401, detail="Access token missing from Google response")

        # Step 2: Get user info
        user_info = requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        ).json()

        email = user_info.get("email")
        oauth_id = user_info.get("sub")
        is_verified = user_info.get("email_verified", False)
        full_name = user_info.get("name", "Google User")

        if not email or not oauth_id:
            raise HTTPException(status_code=400, detail="Incomplete user info from Google")

        # Step 3: Find or create user
        user = await User.find_one(User.email == email)

        if not user:
            user = User(
                full_name=full_name,
                email=email,
                password="oauth_google",  # You may skip login-based password verification
                is_verified=is_verified,
                has_completed_onboarding=False,
                active_tokens=[]
            )
            await user.insert()
        else:
            if not user.is_verified and is_verified:
                user.is_verified = True

        # Step 4: Set active token
        token_entry = {
            "active_token_id": str(uuid4()),
            "expires_in": (datetime.now(timezone.utc) + timedelta(minutes=60)).isoformat(),
            "device": device
        }

        if user.active_tokens is None:
            user.active_tokens = []

        user.active_tokens.append(token_entry)
        await user.save()

        # Step 5: Set secure cookie
        app_token = generate_access_token(data={"sub": str(user.id)})
        set_access_token_cookie(app_token, response)

        return UserResponse(
            id=str(user.id),
            full_name=user.full_name,
            email=user.email,
            is_verified=user.is_verified,
            created_at=user.created_at
        )
