import os
import logging
import requests
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from database.models.user import User, UserLoginResponse
from utils.auth import generate_access_token

class OAuthService:
    async def login_with_google(self, auth_code: str, device: str = "desktop") -> UserLoginResponse:
        # Step 1: Exchange code for access token from Google
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

        google_access_token = token_response.json().get("access_token")
        if not google_access_token:
            raise HTTPException(status_code=401, detail="Access token missing from Google response")

        # Step 2: Get user info from Google
        user_info = requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {google_access_token}'}
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
                password="oauth_google",
                is_verified=is_verified,
                has_completed_onboarding=False
            )
            await user.insert()
        else:
            if not user.is_verified and is_verified:
                user.is_verified = True

        # Step 4: Create app token + track token_id
        token_id = str(uuid4())
        app_access_token = generate_access_token(data={
            "sub": str(user.id),
            "token_id": token_id
        })

        user.active_tokens.append({
            "active_token_id": token_id,
            "expires_in": (datetime.now(timezone.utc) + timedelta(minutes=60)).isoformat(),
            "device": device
        })
        await user.save()

        # Step 5: Return your app’s token + token_id
        return UserLoginResponse(
            user_id=str(user.id),
            token_id=token_id,
            access_token=app_access_token
        )
