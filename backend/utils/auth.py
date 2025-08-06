import os
import jwt
from pathlib import Path
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException, Header, status, Response, Request, BackgroundTasks
from passlib.context import CryptContext
from typing import Optional
from pydantic import BaseModel, SecretStr
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from database.models.user import User

# Validate and fetch environment variables
try:
    SECRET_KEY = os.environ["SECRET_KEY"]
    ALGORITHM = os.environ["ALGORITHM"]
    ACCESS_TOKEN_MINUTES = float(os.environ.get("ACCESS_TOKEN_MINUTES", 60))

    MAIL_USERNAME = os.environ["MAIL_USERNAME"]
    MAIL_PASSWORD = os.environ["MAIL_PASSWORD"]
    MAIL_FROM = os.environ["MAIL_FROM"]
    MAIL_PORT = int(os.environ["MAIL_PORT"])
    MAIL_SERVER = os.environ["MAIL_SERVER"]
    MAIL_FROM_NAME = os.environ["MAIL_FROM_NAME"]

except KeyError as e:
    raise RuntimeError(f"Missing required environment variable: {e}")
except ValueError:
    raise RuntimeError("ACCESS_TOKEN_MINUTES and MAIL_PORT must be numbers.")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

conf = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=SecretStr(os.environ["MAIL_PASSWORD"]),
    MAIL_FROM=MAIL_FROM,
    MAIL_PORT=MAIL_PORT,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_FROM_NAME=MAIL_FROM_NAME,
    MAIL_STARTTLS=True, 
    MAIL_SSL_TLS=False,        
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER=Path("templates/verify-email")
)

def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(password)

def verify_password(given_password: str, hashed_password: str) -> bool:
    """Verify a given password against its hashed version."""
    return pwd_context.verify(given_password, hashed_password)

def generate_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a JWT access token with expiration.
    Adds 'exp' field to the payload.
    """
    payload_to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_MINUTES))
    payload_to_encode.update({"exp": expire})
    
    return jwt.encode(payload_to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_access_token(token: str) -> dict:
    """
    Verify and decode a JWT token. Raise 401 if invalid or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except (InvalidTokenError, ExpiredSignatureError):
        raise credentials_exception

import os
import logging

# Add this to your auth.py
def set_access_token_cookie(access_token: str, response: Response, expires_delta: Optional[timedelta] = None):
    """
    Set the JWT token in an HTTP-only secure cookie.
    """
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_MINUTES))
    max_age = int((expire - datetime.now(timezone.utc)).total_seconds())

    # Check if we're in development or production
    is_production = os.environ.get("ENVIRONMENT", "development") == "production"
    
    # Debug logging
    print(f"Setting cookie with:")
    print(f"  - access_token length: {len(access_token)}")
    print(f"  - max_age: {max_age}")
    print(f"  - is_production: {is_production}")
    print(f"  - secure: {is_production}")
    print(f"  - samesite: {'none' if is_production else 'lax'}")
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=max_age,
        httponly=True,
        secure=is_production,  # Only secure in production (HTTPS)
        samesite="lax" if not is_production else "none",  # Use 'lax' for development
        path='/', 
    )
    
    print("Cookie set successfully")

def get_access_token_cookie(request: Request) -> dict:
    """
    Extract and verify the access token from cookies.
    Returns the payload with user_id if valid.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token missing from cookies.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_access_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing user ID.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"user_id": user_id}

def clear_access_token_cookie(response: Response):
    response.delete_cookie(
        key="access_token",
        #httponly=True,
        #secure=True,
        #path="/"
    )

class VerifyEmailContext(BaseModel):
    full_name: str
    verification_link: str
    subject: str


async def send_email_verification_link_async(subject: str, email_to: str, context: VerifyEmailContext):
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        template_body=context.model_dump(),
        subtype=MessageType.html
    )

    fmail = FastMail(conf)
    await fmail.send_message(message, template_name='verify-email.html')

def send_email_verification_link_background(background_tasks: BackgroundTasks, subject: str, email_to: str, context: VerifyEmailContext):
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        template_body=context.model_dump(),
        subtype=MessageType.html,
    )
    fm = FastMail(conf)
    background_tasks.add_task(
       fm.send_message, message, template_name='verify-email.html')

async def get_current_user_with_token(request: Request) -> tuple[User, str]:
    """Get current user and token_id - for logout endpoint"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = auth_header.split(" ")[1]
    payload = verify_access_token(token)

    user_id = payload.get("sub")
    token_id = payload.get("token_id")
    if not user_id or not token_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await User.get(user_id)
    if not user or not any(t["active_token_id"] == token_id for t in user.active_tokens):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user, token_id


async def get_current_user(request: Request) -> User:
    """Get current user only - for profile endpoint"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = auth_header.split(" ")[1]
    payload = verify_access_token(token)

    user_id = payload.get("sub")
    token_id = payload.get("token_id")
    if not user_id or not token_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await User.get(user_id)
    if not user or not any(t["active_token_id"] == token_id for t in user.active_tokens):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user  # Return just the user, not a tuple

        
def get_device_info_from_request(request: Request):
    """Extract device information from request headers in FastAPI"""
    user_agent = request.headers.get('User-Agent', '')
    ip_address = request.client.host if request.client else "unknown"

    device_info = {
        'user_agent': user_agent,
        'ip_address': ip_address,
        'platform': 'unknown'
    }

    if 'Mobile' in user_agent:
        device_info['platform'] = 'mobile'
    elif 'Tablet' in user_agent:
        device_info['platform'] = 'tablet'
    else:
        device_info['platform'] = 'desktop'

    return device_info
