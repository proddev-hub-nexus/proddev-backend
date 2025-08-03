from datetime import datetime, timedelta, timezone
import os
from uuid import uuid4
from beanie import Link
from bson import DBRef
from fastapi import HTTPException, Response, status
import bleach
import logging
from database.models.user import User, UserResponse
from database.models.dashboard import Dashboard
from utils.auth import (
    VerifyEmailContext,
    hash_password,
    generate_access_token,
    send_email_verification_link_async,
    verify_access_token,
    set_access_token_cookie,
    verify_password,
    clear_access_token_cookie
)

# Configure logging
logging.basicConfig(
    filename="app.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class AuthService:

    async def register(self, full_name: str, email: str, password: str) -> UserResponse:
        full_name = bleach.clean(full_name).strip().title()
        email = bleach.clean(email).strip().lower()

        # Check if user already exists
        existing_user = await User.find_one(User.email == email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="E-mail is already registered."
            )

        # Hash password
        hashed_password = hash_password(password)

        # Create user
        user = User(
            full_name=full_name,
            email=email,
            password=hashed_password,
            is_verified=False
        )
        await user.insert()

        # Generate email verification token
        email_verification_token = generate_access_token(
            data={"sub": str(user.id)}
        )

        # Build verification link
        verification_link = f"{os.environ['FRONTEND_URL']}/verify-email?token={email_verification_token}"
        context = VerifyEmailContext(
            full_name=user.full_name,
            verification_link=verification_link,
            subject="Verify your email"
        )

        # Send email
        try:
            await send_email_verification_link_async(
                subject="Email Verification",
                email_to=user.email,
                context=context
            )
        except Exception as e:
            logging.error(f"Failed to send verification to {user.email}: {e}")

        return UserResponse(
            id=str(user.id),
            full_name=user.full_name,
            email=user.email,
            is_verified=user.is_verified,
            created_at=user.created_at
        )

    async def verify_email(self, token: str, response: Response, device: str = "desktop") -> dict:
        try:
            # Decode the token
            payload = verify_access_token(token)
            user_id = payload.get("sub")

            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token payload."
                )

            # Find the user
            user = await User.get(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found."
                )

            # Ensure active_tokens is initialized
            if user.active_tokens is None:
                user.active_tokens = []

            # Already verified → log in
            if user.is_verified:
                access_token = generate_access_token(data={"sub": str(user.id)})
                active_token_entry = {
                    "active_token_id": str(uuid4()),
                    "expires_in": (datetime.now(timezone.utc) + timedelta(minutes=60)).isoformat(),
                    "device": device
                }
                user.active_tokens.append(active_token_entry)
                await user.save()

                set_access_token_cookie(access_token, response)
                return {"message": "Email already verified. You are now logged in."}

            # Mark user as verified
            user.is_verified = True

            # Create dashboard
            user_dashboard = Dashboard(
                owner=Link(
                    DBRef(
                        collection=User.get_collection_name(),
                        id=user.id
                    ),
                    document_class=User
                )
            )

            await user_dashboard.insert()
            await user.save()

            # Generate token + set cookie
            access_token = generate_access_token(data={"sub": str(user.id)})
            active_token_entry = {
                "active_token_id": str(uuid4()),
                "expires_in": (datetime.now(timezone.utc) + timedelta(minutes=60)).isoformat(),
                "device": device
            }
            user.active_tokens.append(active_token_entry)
            await user.save()

            set_access_token_cookie(access_token, response)

            return {"message": "Email verification successful. You are now logged in."}

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

        # Find user
        user = await User.find_one(User.email == email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found with this email."
            )

        if user.is_verified:
            return {"message": "Email is already verified."}

        # Generate a new token
        email_verification_token = generate_access_token(
            data={"sub": str(user.id)}
        )

        # Build context
        verification_link = f"https://localhost:3000/verify-email?token={email_verification_token}"
        context = VerifyEmailContext(
            full_name=user.full_name,
            verification_link=verification_link,
            subject="Verify your email"
        )

        try:
            await send_email_verification_link_async(
                subject="Resend Email Verification",
                email_to=user.email,
                context=context
            )
        except Exception as e:
            logging.error(f"Failed to resend verification email to {user.email}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email. Please try again later."
            )

        return {"message": "Verification email resent successfully."}

    async def login(self, email: str, password: str, response: Response, device: str = "desktop") -> UserResponse:
        email = bleach.clean(email).strip().lower()

        # Find user
        user = await User.find_one(User.email == email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        if not verify_password(password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        # If not verified → send link
        if not user.is_verified:
            email_verification_token = generate_access_token(data={"sub": str(user.id)})
            verification_link = f"https://localhost:3000/verify-email?token={email_verification_token}"
            context = VerifyEmailContext(
                full_name=user.full_name,
                verification_link=verification_link,
                subject="Verify your email"
            )

            try:
                await send_email_verification_link_async(
                    subject="Verify your email",
                    email_to=user.email,
                    context=context
                )
            except Exception as e:
                logging.error(f"Failed to resend verification email to {user.email}: {e}")

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. A new verification link has been sent."
            )

        # Ensure active_tokens is initialized
        if user.active_tokens is None:
            user.active_tokens = []

        # Generate token + session
        access_token = generate_access_token(data={"sub": str(user.id)})
        active_token_entry = {
            "active_token_id": str(uuid4()),
            "expires_in": (datetime.now(timezone.utc) + timedelta(minutes=60)).isoformat(),
            "device": device
        }
        user.active_tokens.append(active_token_entry)
        await user.save()

        set_access_token_cookie(access_token, response)

        return UserResponse(
            id=str(user.id),
            full_name=user.full_name,
            email=user.email,
            is_verified=user.is_verified,
            created_at=user.created_at
        )

    async def get_profile(self, user: User) -> UserResponse:
        return UserResponse(
            id=str(user.id),
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

    async def logout(self, user: User, response: Response) -> dict:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated."
            )

        # Clear active tokens
        user.active_tokens = []
        await user.save()

        # Clear session cookie
        clear_access_token_cookie(response)

        return {"message": "Logout successful."}
