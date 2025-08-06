from datetime import datetime, timedelta, timezone
import os
from uuid import uuid4
from beanie import Link
from bson import DBRef
from fastapi import HTTPException, Response, status
import bleach
import logging

from database.models.user import User, UserLoginResponse, UserRegisterResponse, UserProfileResponse, VerifyEmailResponse
from database.models.dashboard import Dashboard
from utils.auth import (
    VerifyEmailContext,
    hash_password,
    generate_access_token,
    send_email_verification_link_async,
    verify_access_token,
    verify_password,
)

# Configure logging for errors only
logging.basicConfig(
    filename="app.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class AuthService:

    async def register(self, full_name: str, email: str, password: str) -> UserRegisterResponse:
        full_name = bleach.clean(full_name).strip().title()
        email = bleach.clean(email).strip().lower()

        # Check if user exists
        if await User.find_one(User.email == email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="E-mail is already registered."
            )

        # Create user
        user = User(
            full_name=full_name,
            email=email,
            password=hash_password(password),
            is_verified=False,
            created_at=datetime.now(timezone.utc)
        )
        await user.insert()

        # Send verification email
        token = generate_access_token(data={"sub": str(user.id)})
        verification_link = f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/verify-email?token={token}"
        context = VerifyEmailContext(
            full_name=user.full_name,
            verification_link=verification_link,
            subject="Verify your email"
        )

        try:
            await send_email_verification_link_async(
                "Email Verification", user.email, context
            )
        except Exception as e:
            logging.error(f"Failed to send verification email to {user.email}: {e}")

        return UserRegisterResponse(user_id=str(user.id), created_at=user.created_at)

    async def verify_email(self, token: str, response: Response, device: str = "desktop") -> UserLoginResponse:
        try:
            # Decode token
            payload = verify_access_token(token)
            user_id = payload.get("sub")

            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token payload."
                )

            user = await User.get(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found."
                )

            if user.active_tokens is None:
                user.active_tokens = []

            # Create token_id for session tracking
            token_id = str(uuid4())
            token_expires_in = datetime.now(timezone.utc) + timedelta(minutes=60)
            access_token = generate_access_token(data={
                "sub": str(user.id),
                "token_id": token_id
            })

            # Already verified
            if user.is_verified:
                user.active_tokens.append({
                    "active_token_id": token_id,
                    "expires_in": token_expires_in,
                    "device": device
                })
                await user.save()
                return UserLoginResponse(
                    token_id=token_id,
                    access_token=access_token,
                    token_expires_in=token_expires_in,
                    device=device
                )

            # Mark as verified + create dashboard
            user.is_verified = True
            dashboard = Dashboard(
                owner=Link(
                    DBRef(collection=User.get_collection_name(), id=user.id),
                    document_class=User
                )
            )
            await dashboard.insert()

            user.active_tokens.append({
                "active_token_id": token_id,
                "expires_in": token_expires_in,
                "device": device
            })
            await user.save()
          

            return VerifyEmailResponse(
                        token_id=token_id,
                        access_token=access_token,
                        token_expires_in=token_expires_in,
                        device=device,
                        message="Email verified successfully"
                    )

        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Email verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token."
            )

    async def resend_verification_link(self, email: str) -> dict:
        email = bleach.clean(email).strip().lower()
        user = await User.find_one(User.email == email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found with this email."
            )

        if user.is_verified:
            return {"message": "Email is already verified."}

        token = generate_access_token(data={"sub": str(user.id)})
        verification_link = f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/verify-email?token={token}"
        context = VerifyEmailContext(
            full_name=user.full_name,
            verification_link=verification_link,
            subject="Verify your email"
        )

        try:
            await send_email_verification_link_async(
                "Resend Email Verification", user.email, context
            )
        except Exception as e:
            logging.error(f"Failed to resend verification email to {user.email}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email."
            )

        return {"message": "Verification email resent successfully."}

    async def login(self, email: str, password: str, device: str = "desktop") -> UserLoginResponse:
        email = bleach.clean(email).strip().lower()
        user = await User.find_one(User.email == email)

        if not user or not verify_password(password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        if not user.is_verified:
            token = generate_access_token(data={"sub": str(user.id)})
            verification_link = f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/verify-email?token={token}"
            context = VerifyEmailContext(
                full_name=user.full_name,
                verification_link=verification_link,
                subject="Verify your email"
            )
            try:
                await send_email_verification_link_async(
                    "Verify your email", user.email, context
                )
            except Exception as e:
                logging.error(f"Failed to resend verification email to {user.email}: {e}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. A new verification link has been sent."
            )

        if user.active_tokens is None:
            user.active_tokens = []

        token_id = str(uuid4())
        token_expires_in = datetime.now(timezone.utc) + timedelta(minutes=60)
        access_token = generate_access_token(data={
            "sub": str(user.id),
            "token_id": token_id
        })
        user.active_tokens.append({
            "active_token_id": token_id,
            "expires_in": token_expires_in,
            "device": device
        })
        await user.save()

        return UserLoginResponse(
            access_token=access_token,
            token_id=token_id,
            token_expires_in=token_expires_in,
            device=device,
          
        )

    async def get_profile(self, user: User) -> UserProfileResponse:
        return UserProfileResponse(
            user_id=str(user.id),
            full_name=user.full_name,
            email=user.email,
            is_verified=user.is_verified,
            created_at=user.created_at
        )

    async def mark_onboarding_complete(self, user: User) -> dict:
        if user.has_completed_onboarding:
            return {"message": "Onboarding already completed."}
        user.has_completed_onboarding = True
        await user.save()
        return {"message": "User onboarding status updated successfully."}

    async def logout(self, user: User, token_id: str) -> dict:
        user.active_tokens = [
            t for t in user.active_tokens if t["active_token_id"] != token_id
        ]
        await user.save()
        return {"message": "Logout successful"}
